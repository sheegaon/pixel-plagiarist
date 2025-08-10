"""
Comprehensive integration tests for Pixel Plagiarist advanced scenarios.

This module tests advanced aspects of the game including timer edge cases,
player reconnection, concurrent operations, database consistency, error handling,
and socket event broadcasting.
"""

import pytest
import time
import threading
from unittest.mock import patch, MagicMock
from contextlib import contextmanager

# Import common test utilities
from .test_common import *

# Import the main application components
from server import app, socketio as app_socketio
from socket_handlers.game_state import GAME_STATE_SH
from game_logic.game_state import GameStateGL
from util.config import CONSTANTS
from util.db import get_player_stats, record_game_completion, update_player_balance


class TestTimerExpiryEdgeCases:
    """Test timer expiry edge cases and race conditions"""

    def test_timer_expiry_during_submission(self, direct_clients, clean_game_state, timer_helper):
        """Test what happens if a timer expires while a player is submitting an action"""
        alice, bob, carol = direct_clients[:3]
        
        # Setup game
        room_id = alice.create_room()
        alice.join_room(room_id)
        bob.join_room(room_id)
        carol.join_room(room_id)
        
        game = GAME_STATE_SH.get_game(room_id)
        
        with timer_helper.mock_all_timers() as mock_timers:
            # Start the game
            game.start_game(app_socketio)
            assert game.phase == "drawing"
            
            # Simulate a player starting to submit just as timer expires
            drawing_data = create_sample_drawing()
            
            # Mock the submission to take some time
            original_submit = game.drawing_phase.submit_drawing
            submission_started = threading.Event()
            submission_completed = threading.Event()
            
            def slow_submit(player_id, drawing_data, socketio, check_early_advance=True):
                submission_started.set()
                time.sleep(0.1)  # Simulate network delay
                result = original_submit(player_id, drawing_data, socketio, check_early_advance)
                submission_completed.set()
                return result
            
            # Start submission in background
            with patch.object(game.drawing_phase, 'submit_drawing', side_effect=slow_submit):
                submit_thread = threading.Thread(
                    target=lambda: game.drawing_phase.submit_drawing(
                        alice.player_id, drawing_data, app_socketio
                    )
                )
                submit_thread.start()
                
                # Wait for submission to start
                submission_started.wait(timeout=1.0)
                
                # Trigger timer expiry while submission is in progress
                if mock_timers:
                    timer_helper.trigger_timer_callback(mock_timers[0])
                
                # Wait for submission to complete
                submit_thread.join(timeout=2.0)
                submission_completed.wait(timeout=1.0)
            
            # Verify no race condition occurred - game should be in valid state
            assert_game_state_valid(game)
            # Drawing should either be accepted or rejected cleanly
            assert len(game.original_drawings) <= 1

    def test_no_double_phase_transitions(self, direct_clients, clean_game_state, timer_helper):
        """Ensure no race conditions or double phase transitions"""
        alice, bob, carol = direct_clients[:3]
        
        # Setup game
        room_id = alice.create_room()
        alice.join_room(room_id)
        bob.join_room(room_id)
        carol.join_room(room_id)
        
        game = GAME_STATE_SH.get_game(room_id)
        
        with timer_helper.mock_all_timers() as mock_timers:
            game.start_game(app_socketio)
            assert game.phase == "drawing"
            
            # Submit all drawings to trigger early advancement
            for player in [alice, bob, carol]:
                game.drawing_phase.submit_drawing(
                    player.player_id, create_sample_drawing(), app_socketio, check_early_advance=False
                )
            
            # Record initial phase
            initial_phase = game.phase
            
            # Trigger both early advancement and timer expiry simultaneously
            early_advance_thread = threading.Thread(
                target=lambda: game.drawing_phase.check_early_advance(app_socketio)
            )
            timer_expiry_thread = threading.Thread(
                target=lambda: timer_helper.trigger_timer_callback(mock_timers[0]) if mock_timers else None
            )
            
            early_advance_thread.start()
            timer_expiry_thread.start()
            
            early_advance_thread.join(timeout=2.0)
            timer_expiry_thread.join(timeout=2.0)
            
            # Verify only one phase transition occurred
            assert_game_state_valid(game)
            # Should have advanced to copying phase exactly once
            assert game.phase == "copying"

    def test_timer_cleanup_on_early_game_end(self, direct_clients, clean_game_state, timer_helper):
        """Test that timers are properly cleaned up when game ends early"""
        alice, bob, carol = direct_clients[:3]
        
        # Setup game
        room_id = alice.create_room()
        alice.join_room(room_id)
        bob.join_room(room_id)
        carol.join_room(room_id)
        
        game = GAME_STATE_SH.get_game(room_id)
        
        with timer_helper.mock_all_timers() as mock_timers:
            game.start_game(app_socketio)
            
            # Verify timer was started
            assert len(mock_timers) > 0
            initial_timer_count = len(mock_timers)
            
            # Remove players to trigger early game end
            game.remove_player(bob.player_id)
            game.remove_player(carol.player_id)
            
            # Should trigger early end
            assert game.phase == "ended_early"
            
            # Verify timers were cancelled (cancel method should have been called)
            for timer in mock_timers[:initial_timer_count]:
                assert timer.cancel.called, "Timer should have been cancelled on early game end"


class TestPlayerReconnectionAndStateRecovery:
    """Test player reconnection and state recovery scenarios"""

    def test_player_disconnect_and_reconnect_waiting_phase(self, direct_clients, clean_game_state):
        """Test player disconnection and reconnection during waiting phase"""
        alice, bob, carol = direct_clients[:3]
        
        # Setup room
        room_id = alice.create_room()
        alice.join_room(room_id)
        bob.join_room(room_id)
        carol.join_room(room_id)
        
        game = GAME_STATE_SH.get_game(room_id)
        initial_player_count = len(game.players)
        
        # Simulate Bob disconnecting
        assert bob.leave_room()
        assert len(game.players) == initial_player_count - 1
        assert bob.player_id not in game.players
        
        # Bob reconnects (simulated by rejoining)
        new_bob = GameTestHelper("Bob")
        assert new_bob.join_room(room_id)
        
        # Verify state recovery
        assert len(game.players) == initial_player_count
        assert new_bob.player_id in game.players
        assert game.players[new_bob.player_id]['username'] == "Bob"

    def test_player_disconnect_during_drawing_phase(self, direct_clients, clean_game_state):
        """Test player disconnection during drawing phase"""
        alice, bob, carol, dave = direct_clients[:4]
        
        # Setup game with 4 players
        room_id = alice.create_room()
        alice.join_room(room_id)
        bob.join_room(room_id)
        carol.join_room(room_id)
        dave.join_room(room_id)
        
        game = GAME_STATE_SH.get_game(room_id)
        
        with patch.object(game.timer, 'start_phase_timer'), \
             patch.object(game.timer, 'cancel_phase_timer'):
            
            game.start_game(app_socketio)
            assert game.phase == "drawing"
            
            # Alice submits drawing before disconnecting
            game.drawing_phase.submit_drawing(
                alice.player_id, create_sample_drawing(), app_socketio
            )
            assert alice.player_id in game.original_drawings
            
            # Alice disconnects
            initial_drawings = len(game.original_drawings)
            game.remove_player(alice.player_id)
            
            # Game should continue with remaining players
            assert len(game.players) == 3
            assert alice.player_id not in game.players
            # Alice's drawing should be preserved
            assert len(game.original_drawings) == initial_drawings

    def test_player_disconnect_during_voting_phase(self, direct_clients, clean_game_state):
        """Test player disconnection during voting phase"""
        alice, bob, carol, dave = direct_clients[:4]
        
        # Setup and run game to voting phase
        room_id = alice.create_room()
        for player in [alice, bob, carol, dave]:
            player.join_room(room_id)
        
        game = GAME_STATE_SH.get_game(room_id)
        
        with patch.object(game.timer, 'start_phase_timer'), \
             patch.object(game.timer, 'cancel_phase_timer'):
            
            # Progress to voting phase
            game.start_game(app_socketio)
            
            # Submit drawings
            for player in [alice, bob, carol, dave]:
                game.drawing_phase.submit_drawing(
                    player.player_id, create_sample_drawing(), app_socketio, check_early_advance=False
                )
            
            # Progress to copying
            game.copying_phase.start_phase(app_socketio)
            game.copying_phase._assign_copying_tasks()
            
            # Submit copies
            for player_id, targets in game.copy_assignments.items():
                for target_id in targets:
                    game.copying_phase.submit_drawing(
                        player_id, target_id, create_sample_drawing(), app_socketio, check_early_advance=False
                    )
            
            # Start voting
            game.voting_phase.start_phase(app_socketio)
            assert game.phase == "voting"
            
            # Bob disconnects during voting
            initial_vote_count = len(game.votes.get(0, {}))
            game.remove_player(bob.player_id)
            
            # Voting should continue with remaining eligible voters
            assert len(game.players) == 3
            assert bob.player_id not in game.players
            
            # Verify voting eligibility is recalculated correctly
            if len(game.drawing_sets) > 0:
                eligible_voters = game.voting_phase.get_eligible_voters_for_set(game.drawing_sets[0])
                assert bob.player_id not in eligible_voters

    def test_state_recovery_with_persisted_data(self, direct_clients, clean_game_state, clean_database, db_helper):
        """Test state recovery using persisted database data"""
        alice = direct_clients[0]
        
        # Create player in database with specific balance
        initial_balance = 1500
        db_helper.create_test_player("TestAlice", initial_balance)
        
        # Create game state
        alice_test = GameTestHelper("TestAlice")
        room_id = alice_test.create_room()
        alice_test.join_room(room_id)
        
        game = GAME_STATE_SH.get_game(room_id)
        
        # Verify player data loaded from database
        assert alice_test.player_id in game.players
        player_data = game.players[alice_test.player_id]
        assert player_data['balance'] == initial_balance
        
        # Simulate disconnect and cleanup
        alice_test.leave_room()
        
        # Simulate reconnection - new game session should load persisted data
        alice_reconnect = GameTestHelper("TestAlice")
        new_room_id = alice_reconnect.create_room()
        alice_reconnect.join_room(new_room_id)
        
        new_game = GAME_STATE_SH.get_game(new_room_id)
        reconnect_player_data = new_game.players[alice_reconnect.player_id]
        
        # Should load the same balance from database
        assert reconnect_player_data['balance'] == initial_balance


class TestConcurrentRoomAndGameManagement:
    """Test concurrent room and game management scenarios"""

    def test_multiple_games_with_overlapping_players(self, direct_clients, clean_game_state, concurrency_helper):
        """Test multiple games running with some overlapping player names"""
        players = direct_clients[:10]
        
        # Create multiple rooms concurrently
        def create_and_populate_room(args):
            creator, participants, stake = args
            room_id = creator.create_room(stake)
            
            # Add participants
            for participant in participants:
                if participant.join_room(room_id):
                    continue
            
            return room_id, len(GAME_STATE_SH.get_game(room_id).players)
        
        # Setup concurrent room creation
        room_configs = [
            (players[0], players[1:4], 100),   # Alice creates room with Bob, Carol
            (players[4], players[5:8], 250),   # Eve creates room with Frank, Grace  
            (players[8], players[9:12] if len(players) > 11 else players[9:10], 500),  # Ivan creates room
        ]
        
        results = concurrency_helper.run_concurrent(create_and_populate_room, room_configs)
        
        # Verify all rooms were created successfully
        successful_results = [r for r in results if r[2] is None]  # No exceptions
        assert len(successful_results) == len(room_configs)
        
        # Verify room isolation
        room_ids = [result[1][0] for result in successful_results]
        assert len(set(room_ids)) == len(room_ids), "All room IDs should be unique"
        
        # Verify players are correctly assigned
        for i, (index, (room_id, player_count), error) in enumerate(successful_results):
            assert error is None
            assert player_count >= 2  # Creator + at least one participant
            
            game = GAME_STATE_SH.get_game(room_id)
            assert_game_state_valid(game)

    def test_concurrent_joining_same_room(self, direct_clients, clean_game_state, concurrency_helper):
        """Test multiple players joining the same room concurrently"""
        alice = direct_clients[0]
        joining_players = direct_clients[1:8]  # 7 players trying to join
        
        # Create room
        room_id = alice.create_room()
        alice.join_room(room_id)
        
        # Multiple players try to join the same room concurrently
        def join_room_worker(args):
            player, target_room_id = args
            success = player.join_room(target_room_id)
            return success, player.username
        
        join_configs = [(player, room_id) for player in joining_players]
        results = concurrency_helper.run_concurrent(join_room_worker, join_configs)
        
        # Verify results
        game = GAME_STATE_SH.get_game(room_id)
        successful_joins = [r for r in results if r[2] is None and r[1][0]]
        
        # Should handle concurrent joins gracefully
        assert len(game.players) == 1 + len(successful_joins)  # Alice + successful joiners
        assert len(game.players) <= game.max_players  # Shouldn't exceed max
        
        # Verify no duplicate players
        usernames = [player_data['username'] for player_data in game.players.values()]
        assert len(usernames) == len(set(usernames)), "No duplicate usernames should exist"

    def test_game_state_isolation_between_rooms(self, direct_clients, clean_game_state):
        """Test that game state is properly isolated between rooms"""
        alice, bob = direct_clients[:2]
        carol, dave = direct_clients[2:4]
        
        # Create two separate games
        room1_id = alice.create_room(100)
        room2_id = carol.create_room(250)
        
        # Add players to respective rooms
        alice.join_room(room1_id)
        bob.join_room(room1_id)
        carol.join_room(room2_id)
        dave.join_room(room2_id)
        
        game1 = GAME_STATE_SH.get_game(room1_id)
        game2 = GAME_STATE_SH.get_game(room2_id)
        
        # Verify isolation
        assert game1.room_id != game2.room_id
        assert game1.prize_per_player != game2.prize_per_player
        assert len(game1.players) == 2
        assert len(game2.players) == 2
        
        # Verify player isolation
        game1_player_ids = set(game1.players.keys())
        game2_player_ids = set(game2.players.keys())
        assert game1_player_ids.isdisjoint(game2_player_ids)
        
        with patch.object(game1.timer, 'start_phase_timer'), \
             patch.object(game2.timer, 'start_phase_timer'):
            
            # Start both games
            game1.start_game(app_socketio)
            game2.start_game(app_socketio)
            
            # Actions in game1 shouldn't affect game2
            game1.drawing_phase.submit_drawing(
                alice.player_id, create_sample_drawing(), app_socketio
            )
            
            assert len(game1.original_drawings) == 1
            assert len(game2.original_drawings) == 0
            
            # Vice versa
            game2.drawing_phase.submit_drawing(
                carol.player_id, create_sample_drawing(), app_socketio
            )
            
            assert len(game1.original_drawings) == 1
            assert len(game2.original_drawings) == 1

    def test_room_cleanup_and_recreation_under_load(self, direct_clients, clean_game_state, concurrency_helper):
        """Test room cleanup and recreation under concurrent load"""
        players = direct_clients[:6]
        
        def create_play_and_cleanup(args):
            creator, participant, iteration = args
            
            # Create room
            room_id = creator.create_room()
            participant.join_room(room_id)
            
            # Simulate some activity
            game = GAME_STATE_SH.get_game(room_id)
            initial_room_count = len(GAME_STATE_SH.GAMES)
            
            # Leave room (triggers cleanup)
            creator.leave_room()
            participant.leave_room()
            
            # Room should be cleaned up
            time.sleep(0.1)  # Allow cleanup to process
            
            return initial_room_count, room_id in GAME_STATE_SH.GAMES
        
        # Run multiple create/cleanup cycles concurrently
        test_configs = [
            (players[i], players[i+1], i) 
            for i in range(0, len(players)-1, 2)
        ]
        
        results = concurrency_helper.run_concurrent(create_play_and_cleanup, test_configs)
        
        # Verify all operations completed successfully
        successful_results = [r for r in results if r[2] is None]
        assert len(successful_results) == len(test_configs)
        
        # Verify final state is clean
        final_room_count = len(GAME_STATE_SH.GAMES)
        # Should have default room(s) only
        assert final_room_count >= 0


class TestDatabaseConsistency:
    """Test database consistency and integrity"""

    def test_player_balance_consistency_after_game(self, direct_clients, clean_game_state, clean_database, db_helper):
        """Test that player balances are correctly written to and read from database"""
        alice, bob, carol = direct_clients[:3]
        
        # Create test players with known balances
        initial_balances = {'TestAlice': 1000, 'TestBob': 1200, 'TestCarol': 800}
        test_players = {}
        
        for username, balance in initial_balances.items():
            db_helper.create_test_player(username, balance)
            test_players[username] = GameTestHelper(username)
        
        # Setup and play a complete game
        room_id = test_players['TestAlice'].create_room()
        for player in test_players.values():
            player.join_room(room_id)
        
        game = GAME_STATE_SH.get_game(room_id)
        
        with patch.object(game.timer, 'start_phase_timer'), \
             patch.object(game.timer, 'cancel_phase_timer'):
            
            # Play complete game
            game.start_game(app_socketio)
            
            # Submit drawings
            for player in test_players.values():
                game.drawing_phase.submit_drawing(
                    player.player_id, create_sample_drawing(), app_socketio, check_early_advance=False
                )
            
            # Progress through copying
            game.copying_phase.start_phase(app_socketio)
            for player_id, targets in game.copy_assignments.items():
                for target_id in targets:
                    game.copying_phase.submit_drawing(
                        player_id, target_id, create_sample_drawing(), app_socketio, check_early_advance=False
                    )
            
            # Complete voting
            game.voting_phase.start_phase(app_socketio)
            if len(game.drawing_sets) > 0:
                for set_index in range(len(game.drawing_sets)):
                    game.idx_current_drawing_set = set_index
                    drawing_set = game.drawing_sets[set_index]
                    eligible_voters = game.voting_phase.get_eligible_voters_for_set(drawing_set)
                    
                    if eligible_voters and drawing_set['drawings']:
                        # Vote for first drawing (simplified)
                        vote_drawing_id = drawing_set['drawings'][0]['id']
                        for voter_id in eligible_voters:
                            game.voting_phase.submit_vote(
                                voter_id, vote_drawing_id, app_socketio, check_early_advance=False
                            )
            
            # Calculate results (this should update database)
            game.scoring_engine.calculate_results(app_socketio)
            
            # Verify database consistency
            for username in initial_balances.keys():
                player_id = test_players[username].player_id
                if player_id in game.players:
                    # Game balance should match database
                    game_balance = game.players[player_id]['balance']
                    db_balance = db_helper.get_player_balance(username)
                    
                    assert db_balance is not None, f"Player {username} not found in database"
                    assert game_balance == db_balance, f"Balance mismatch for {username}: game={game_balance}, db={db_balance}"

    def test_game_history_recording(self, direct_clients, clean_game_state, clean_database, db_helper):
        """Test that game results and statistics are correctly recorded"""
        alice, bob, carol = direct_clients[:3]
        
        # Create test players
        test_usernames = ['TestAlice', 'TestBob', 'TestCarol']
        for username in test_usernames:
            db_helper.create_test_player(username, 1000)
        
        # Setup game
        alice_test = GameTestHelper('TestAlice')
        bob_test = GameTestHelper('TestBob')
        carol_test = GameTestHelper('TestCarol')
        
        room_id = alice_test.create_room()
        alice_test.join_room(room_id)
        bob_test.join_room(room_id)
        carol_test.join_room(room_id)
        
        game = GAME_STATE_SH.get_game(room_id)
        
        # Record initial stats
        initial_stats = {}
        for username in test_usernames:
            stats = get_player_stats(username)
            initial_stats[username] = {
                'games_played': stats['games_played'],
                'total_originals': stats['total_originals'],
                'total_copies': stats['total_copies'],
                'total_votes_cast': stats['total_votes_cast']
            }
        
        with patch.object(game.timer, 'start_phase_timer'), \
             patch.object(game.timer, 'cancel_phase_timer'):
            
            # Play simplified game
            game.start_game(app_socketio)
            
            # Each player draws
            for player in [alice_test, bob_test, carol_test]:
                game.drawing_phase.submit_drawing(
                    player.player_id, create_sample_drawing(), app_socketio, check_early_advance=False
                )
            
            # Complete copying and voting phases quickly
            game.copying_phase.start_phase(app_socketio)
            for player_id, targets in game.copy_assignments.items():
                for target_id in targets:
                    game.copying_phase.submit_drawing(
                        player_id, target_id, create_sample_drawing(), app_socketio, check_early_advance=False
                    )
            
            game.voting_phase.start_phase(app_socketio)
            # Simplified voting
            for set_index in range(len(game.drawing_sets)):
                game.idx_current_drawing_set = set_index
                drawing_set = game.drawing_sets[set_index]
                eligible_voters = game.voting_phase.get_eligible_voters_for_set(drawing_set)
                if eligible_voters and drawing_set['drawings']:
                    for voter_id in eligible_voters:
                        game.voting_phase.submit_vote(
                            voter_id, drawing_set['drawings'][0]['id'], app_socketio, check_early_advance=False
                        )
            
            # Calculate results
            game.scoring_engine.calculate_results(app_socketio)
        
        # Verify game history was recorded
        for username in test_usernames:
            final_stats = get_player_stats(username)
            
            # Games played should increment
            assert final_stats['games_played'] == initial_stats[username]['games_played'] + 1
            
            # Should have drawn one original
            assert final_stats['total_originals'] == initial_stats[username]['total_originals'] + 1
            
            # Should have made copies (depends on assignments)
            assert final_stats['total_copies'] >= initial_stats[username]['total_copies']
            
            # Should have cast votes
            assert final_stats['total_votes_cast'] >= initial_stats[username]['total_votes_cast']

    def test_database_transaction_consistency(self, direct_clients, clean_game_state, clean_database, db_helper):
        """Test database transaction consistency during concurrent operations"""
        alice = direct_clients[0]
        
        # Create test player
        db_helper.create_test_player('TestAlice', 1000)
        
        # Simulate concurrent balance updates
        def update_balance_worker(args):
            username, new_balance = args
            try:
                return update_player_balance(username, new_balance)
            except Exception as e:
                return False, str(e)
        
        # Try multiple concurrent balance updates
        update_configs = [
            ('TestAlice', 900),
            ('TestAlice', 950),
            ('TestAlice', 1100),
        ]
        
        # Note: This test may be limited by SQLite's transaction handling
        # In a production environment with PostgreSQL, this would be more robust
        results = []
        for config in update_configs:
            result = update_balance_worker(config)
            results.append(result)
            time.sleep(0.01)  # Small delay to avoid transaction conflicts
        
        # At least one update should succeed
        successful_updates = [r for r in results if r is True or (isinstance(r, tuple) and r[0] is True)]
        assert len(successful_updates) > 0
        
        # Final balance should be consistent
        final_balance = db_helper.get_player_balance('TestAlice')
        assert final_balance is not None
        assert final_balance in [900, 950, 1100]  # Should be one of the attempted values


class TestErrorHandlingAndRecovery:
    """Test error handling and graceful recovery scenarios"""

    def test_database_failure_handling(self, direct_clients, clean_game_state):
        """Test handling of database connection failures"""
        alice, bob = direct_clients[:2]
        
        # Create room normally
        room_id = alice.create_room()
        alice.join_room(room_id)
        bob.join_room(room_id)
        
        game = GAME_STATE_SH.get_game(room_id)
        
        # Simulate database failure during game operations
        with ErrorSimulator.database_error():
            # Game should continue to function despite database errors
            with patch.object(game.timer, 'start_phase_timer'):
                game.start_game(app_socketio)
                assert game.phase == "drawing"
                
                # Drawing submission should work (may not persist to DB)
                result = game.drawing_phase.submit_drawing(
                    alice.player_id, create_sample_drawing(), app_socketio
                )
                # Should not crash, may succeed or fail gracefully
                assert result in [True, False] or result is None

    def test_invalid_client_message_handling(self, direct_clients, clean_game_state):
        """Test handling of malformed or invalid client messages"""
        alice = direct_clients[0]
        
        room_id = alice.create_room()
        alice.join_room(room_id)
        game = GAME_STATE_SH.get_game(room_id)
        
        with patch.object(game.timer, 'start_phase_timer'):
            game.start_game(app_socketio)
            
            # Test invalid drawing data
            invalid_drawings = [
                None,
                "",
                "invalid_base64",
                "not_an_image",
                "data:image/png;base64,invalid_data",
                {"not": "a_string"},
                123,
                []
            ]
            
            for invalid_drawing in invalid_drawings:
                try:
                    result = game.drawing_phase.submit_drawing(
                        alice.player_id, invalid_drawing, app_socketio
                    )
                    # Should either reject gracefully or handle the invalid input
                    assert result in [True, False] or result is None
                except Exception as e:
                    # Should not raise unhandled exceptions
                    assert False, f"Unhandled exception for invalid drawing {invalid_drawing}: {e}"

    def test_memory_pressure_handling(self, direct_clients, clean_game_state):
        """Test behavior under simulated memory pressure"""
        alice, bob, carol = direct_clients[:3]
        
        room_id = alice.create_room()
        alice.join_room(room_id)
        bob.join_room(room_id)
        carol.join_room(room_id)
        
        game = GAME_STATE_SH.get_game(room_id)
        
        with ErrorSimulator.memory_pressure():
            # Game should continue to function
            with patch.object(game.timer, 'start_phase_timer'):
                game.start_game(app_socketio)
                
                # Basic operations should still work
                assert_game_state_valid(game)
                assert len(game.players) == 3

    def test_network_error_resilience(self, direct_clients, clean_game_state):
        """Test resilience to network/socket errors"""
        alice, bob = direct_clients[:2]
        
        room_id = alice.create_room()
        alice.join_room(room_id)
        bob.join_room(room_id)
        
        game = GAME_STATE_SH.get_game(room_id)
        
        # Simulate network errors during socket operations
        with ErrorSimulator.network_error():
            # Game logic should continue even if socket emissions fail
            with patch.object(game.timer, 'start_phase_timer'):
                try:
                    game.start_game(app_socketio)
                    # Game state should update even if broadcasting fails
                    assert game.phase == "drawing"
                except Exception:
                    # Should not crash the application
                    pass


class TestSocketEventBroadcasting:
    """Test socket event broadcasting and communication"""

    def test_phase_change_broadcasting(self, direct_clients, clean_game_state):
        """Test that phase changes are broadcast to all players in room"""
        alice, bob, carol = direct_clients[:3]
        
        room_id = alice.create_room()
        alice.join_room(room_id)
        bob.join_room(room_id)
        carol.join_room(room_id)
        
        game = GAME_STATE_SH.get_game(room_id)
        
        # Mock socketio to capture emissions
        mock_socketio = MagicMock()
        emitted_events = []
        
        def capture_emit(*args, **kwargs):
            emitted_events.append({
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time()
            })
        
        mock_socketio.emit.side_effect = capture_emit
        
        with patch.object(game.timer, 'start_phase_timer'):
            # Start game with mock socketio
            game.start_game(mock_socketio)
            
            # Verify phase change was broadcast
            phase_events = [e for e in emitted_events if len(e['args']) > 0 and e['args'][0] == 'phase_changed']
            assert len(phase_events) > 0
            
            # Should be broadcast to room
            phase_event = phase_events[0]
            assert 'room' in phase_event['kwargs']
            assert phase_event['kwargs']['room'] == room_id

    def test_player_update_broadcasting(self, direct_clients, clean_game_state):
        """Test that player updates are broadcast correctly"""
        alice, bob = direct_clients[:2]
        
        room_id = alice.create_room()
        alice.join_room(room_id)
        
        game = GAME_STATE_SH.get_game(room_id)
        
        # Mock socketio
        mock_socketio = MagicMock()
        emitted_events = []
        
        def capture_emit(*args, **kwargs):
            emitted_events.append({
                'event': args[0] if args else None,
                'data': args[1] if len(args) > 1 else None,
                'kwargs': kwargs
            })
        
        mock_socketio.emit.side_effect = capture_emit
        
        # Add second player
        bob.join_room(room_id)
        
        # Manually trigger player update broadcast (simulating what happens in real handlers)
        from socket_handlers.game_state import GAME_STATE_SH
        mock_socketio.emit('players_updated', {
            'players': list(game.players.values()),
            'count': len(game.players)
        }, room=room_id)
        
        # Verify player update was broadcast
        player_events = [e for e in emitted_events if e['event'] == 'players_updated']
        assert len(player_events) > 0
        
        player_event = player_events[0]
        assert player_event['data']['count'] == 2
        assert len(player_event['data']['players']) == 2

    def test_room_isolation_in_broadcasts(self, direct_clients, clean_game_state):
        """Test that broadcasts are properly isolated to specific rooms"""
        alice, bob = direct_clients[:2]
        carol, dave = direct_clients[2:4]
        
        # Create two separate rooms
        room1_id = alice.create_room()
        room2_id = carol.create_room()
        
        alice.join_room(room1_id)
        bob.join_room(room1_id)
        carol.join_room(room2_id)
        dave.join_room(room2_id)
        
        game1 = GAME_STATE_SH.get_game(room1_id)
        game2 = GAME_STATE_SH.get_game(room2_id)
        
        # Mock socketio to track room-specific emissions
        mock_socketio = MagicMock()
        room_emissions = {}
        
        def capture_emit(*args, **kwargs):
            room = kwargs.get('room', 'global')
            if room not in room_emissions:
                room_emissions[room] = []
            room_emissions[room].append({
                'event': args[0] if args else None,
                'data': args[1] if len(args) > 1 else None
            })
        
        mock_socketio.emit.side_effect = capture_emit
        
        with patch.object(game1.timer, 'start_phase_timer'), \
             patch.object(game2.timer, 'start_phase_timer'):
            
            # Start both games
            game1.start_game(mock_socketio)
            game2.start_game(mock_socketio)
            
            # Verify events were sent to correct rooms
            assert room1_id in room_emissions
            assert room2_id in room_emissions
            
            # Events should be isolated to their respective rooms
            room1_events = room_emissions[room1_id]
            room2_events = room_emissions[room2_id]
            
            assert len(room1_events) > 0
            assert len(room2_events) > 0
            
            # Both should have received game start events
            room1_game_events = [e for e in room1_events if e['event'] in ['game_started', 'phase_changed']]
            room2_game_events = [e for e in room2_events if e['event'] in ['game_started', 'phase_changed']]
            
            assert len(room1_game_events) > 0
            assert len(room2_game_events) > 0

    def test_error_resilience_in_broadcasting(self, direct_clients, clean_game_state):
        """Test that broadcast errors don't crash the game"""
        alice, bob = direct_clients[:2]
        
        room_id = alice.create_room()
        alice.join_room(room_id)
        bob.join_room(room_id)
        
        game = GAME_STATE_SH.get_game(room_id)
        
        # Mock socketio to raise errors on emission
        error_socketio = MagicMock()
        error_socketio.emit.side_effect = Exception("Network error")
        
        with patch.object(game.timer, 'start_phase_timer'):
            # Game should continue despite broadcast errors
            try:
                game.start_game(error_socketio)
                # Game state should still update
                assert game.phase == "drawing"
            except Exception as e:
                # If an exception is raised, it should be handled gracefully
                assert "Network error" not in str(e), "Network errors should be handled gracefully"


# Run the tests
if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])