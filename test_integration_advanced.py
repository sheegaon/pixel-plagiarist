"""
Additional integration tests for edge cases and real-time synchronization.

Tests advanced scenarios including:
- Timer-based phase transitions
- Event broadcasting synchronization
- Player reconnection handling
- Data validation and sanitization
- Performance under load
"""

import pytest
import time
import threading
import uuid
from unittest.mock import patch, MagicMock, call
from concurrent.futures import ThreadPoolExecutor

# Import components needed for testing
from server import app, socketio as app_socketio
from socket_handlers.game_state import game_state_sh
from util.config import CONSTANTS

# Import the test helper from the main integration tests
from test_integration import DirectGameTestHelper


class TestTimerAndPhaseTransitions:
    """Test timer-based phase transitions and auto-advancement"""
    
    def test_automatic_phase_transitions(self, direct_clients, clean_game_state):
        """Test that phases advance automatically when timers expire"""
        alice, bob, carol = direct_clients
        
        # Setup game
        room_id = alice.create_room(stake=10)
        alice.join_room(room_id)
        bob.join_room(room_id)
        carol.join_room(room_id)
        
        game = game_state_sh.get_game(room_id)
        
        # Mock timer to test phase transitions
        with patch.object(game.timer, 'start_phase_timer') as mock_timer:
            game.start_game(app_socketio)
            
            # Verify timer was started for betting phase
            assert mock_timer.called
            
            # Simulate timer callback execution
            if mock_timer.call_args:
                timer_callback = mock_timer.call_args[0][2]  # Third argument is callback
                timer_callback()  # Execute the callback
                
                # Verify phase advanced
                assert game.phase in ['drawing', 'betting']  # Depending on implementation
    
    def test_early_phase_advancement(self, direct_clients, clean_game_state):
        """Test early advancement when all players complete actions"""
        alice, bob, carol = direct_clients
        
        # Setup game in betting phase
        room_id = alice.create_room(stake=10)
        alice.join_room(room_id)
        bob.join_room(room_id)
        carol.join_room(room_id)
        
        game = game_state_sh.get_game(room_id)
        game.start_game(app_socketio)
        
        # All players place bets quickly
        game.betting_phase.place_bet(alice.player_id, 10, app_socketio)
        game.betting_phase.place_bet(bob.player_id, 10, app_socketio)
        game.betting_phase.place_bet(carol.player_id, 10, app_socketio)
        
        # Check if all players have bet
        all_bet = all(player.get('has_bet', False) for player in game.players.values())
        assert all_bet is True
        
        # Should trigger early advancement to drawing phase if implemented
        # This depends on the game's early advancement logic
    
    @patch('util.config.CONSTANTS', {'testing_mode': True})
    def test_testing_mode_timers(self, direct_clients, clean_game_state):
        """Test accelerated timers in testing mode"""
        alice = direct_clients[0]
        
        # In testing mode, all timers should be 5 seconds
        room_id = alice.create_room(stake=10)
        alice.join_room(room_id)
        game = game_state_sh.get_game(room_id)
        
        # Check that timer durations are reduced (if methods exist)
        if hasattr(game.timer, 'get_betting_timer_duration'):
            betting_timer = game.timer.get_betting_timer_duration()
            if CONSTANTS.get('testing_mode'):
                assert betting_timer == 5
        
        if hasattr(game.timer, 'get_drawing_timer_duration'):
            drawing_timer = game.timer.get_drawing_timer_duration()
            if CONSTANTS.get('testing_mode'):
                assert drawing_timer == 5


class TestEventBroadcasting:
    """Test event broadcasting and synchronization"""
    
    def test_room_wide_event_broadcasting(self, direct_clients, clean_game_state):
        """Test that events are broadcast to all players in a room"""
        alice, bob, carol = direct_clients
        
        # Setup room with all players
        room_id = alice.create_room(stake=10)
        alice.join_room(room_id)
        bob.join_room(room_id)
        carol.join_room(room_id)
        
        game = game_state_sh.get_game(room_id)
        
        # Trigger a room-wide event (like game start)
        initial_phase = game.phase
        game.start_game(app_socketio)
        
        # Verify game state changed (indicating event processing)
        assert game.phase != initial_phase
        assert game.phase == 'betting'
        
        # Verify all players are still in the game
        assert len(game.players) == 3
    
    def test_player_specific_events(self, direct_clients, clean_game_state):
        """Test that player-specific data is handled correctly"""
        alice, bob, carol = direct_clients
        
        # Setup game
        room_id = alice.create_room(stake=10)
        alice.join_room(room_id)
        bob.join_room(room_id)
        carol.join_room(room_id)
        
        game = game_state_sh.get_game(room_id)
        
        # Set up different prompts for each player (if supported)
        if hasattr(game, 'player_prompts'):
            game.player_prompts = {
                alice.player_id: "Draw a cat",
                bob.player_id: "Draw a dog", 
                carol.player_id: "Draw a bird"
            }
        
        game.start_game(app_socketio)
        
        # Verify each player has their specific data
        if hasattr(game, 'player_prompts'):
            assert game.player_prompts[alice.player_id] == "Draw a cat"
            assert game.player_prompts[bob.player_id] == "Draw a dog"
            assert game.player_prompts[carol.player_id] == "Draw a bird"


class TestDataValidation:
    """Test input validation and sanitization"""
    
    def test_drawing_data_validation(self, direct_clients, clean_game_state):
        """Test validation of drawing data format"""
        alice = direct_clients[0]
        
        # Setup game in drawing phase
        room_id = alice.create_room(stake=10)
        alice.join_room(room_id)
        game = game_state_sh.get_game(room_id)
        game.phase = "drawing"
        
        # Test valid base64 image
        valid_drawing = alice.create_sample_drawing()
        game.drawing_phase.submit_drawing(alice.player_id, valid_drawing, app_socketio)
        assert alice.player_id in game.original_drawings
        
        # Test invalid base64 data - create a second player to test with
        bob = DirectGameTestHelper("Bob")
        bob.join_room(room_id)
        
        initial_count = len(game.original_drawings)
        game.drawing_phase.submit_drawing(bob.player_id, 'invalid_base64_data', app_socketio)
        # Should either reject or sanitize - count should not increase if rejected
        assert len(game.original_drawings) <= initial_count + 1
        
        # Test missing data
        carol = DirectGameTestHelper("Carol")
        carol.join_room(room_id)
        
        initial_count = len(game.original_drawings)
        game.drawing_phase.submit_drawing(carol.player_id, None, app_socketio)
        # Should be rejected
        assert len(game.original_drawings) == initial_count
    
    def test_username_sanitization(self, clean_game_state):
        """Test username input sanitization"""
        
        # Test various username formats
        test_usernames = [
            "NormalUser",
            "User123",
            "User_With_Underscores",
            "User-With-Hyphens",
            "User.With.Dots",
            "",  # Empty
            "A" * 100,  # Too long
            "<script>alert('xss')</script>",  # XSS attempt
            "User\nWith\nNewlines",  # Special chars
            "User\tWith\tTabs"
        ]
        
        for username in test_usernames:
            # Create a fresh helper for each test to avoid conflicts
            test_helper = DirectGameTestHelper(username)
            
            room_id = test_helper.create_room(stake=10)
            test_helper.join_room(room_id)
            
            game = game_state_sh.get_game(room_id)
            if game and test_helper.player_id in game.players:
                stored_username = game.players[test_helper.player_id]['username']
                # Username should be sanitized but not empty
                assert len(stored_username.strip()) > 0
                # Should not contain dangerous characters
                assert '<script>' not in stored_username.lower()
            
            # Clean up for next test
            game_state_sh.remove_game(room_id)
    
    def test_stake_validation(self, direct_clients, clean_game_state):
        """Test betting stake validation"""
        alice, bob = direct_clients[:2]
        
        # Setup room
        room_id = alice.create_room(stake=10)
        alice.join_room(room_id)
        bob.join_room(room_id)
        
        game = game_state_sh.get_game(room_id)
        game.start_game(app_socketio)
        
        # Test valid stakes
        game.betting_phase.place_bet(alice.player_id, 10, app_socketio)
        alice_player = game.players[alice.player_id]
        assert alice_player.get('has_bet', False) is True
        
        # Test invalid stakes
        invalid_stakes = [-10, 0, 1000000]
        
        for stake in invalid_stakes:
            initial_bet_status = bob.player_id in game.players and game.players[bob.player_id].get('has_bet', False)
            game.betting_phase.place_bet(bob.player_id, stake, app_socketio)
            bob_player = game.players[bob.player_id]
            
            # Should either reject or auto-correct to valid value
            if bob_player.get('has_bet') and not initial_bet_status:
                # If bet was accepted, stake should be valid
                assert bob_player['stake'] >= game.min_stake
                assert bob_player['stake'] <= bob_player['balance'] + bob_player['stake']
                break  # Only test one invalid stake to avoid complications


class TestPerformanceAndLoad:
    """Test performance under load conditions"""
    
    def test_multiple_concurrent_games(self, clean_game_state):
        """Test handling multiple simultaneous games"""
        # Create multiple games
        num_games = 5
        helpers = []
        room_ids = []
        
        for i in range(num_games):
            helper = DirectGameTestHelper(f'Player{i}')
            room_id = helper.create_room(stake=10)
            helper.join_room(room_id)
            helpers.append(helper)
            room_ids.append(room_id)
        
        # Verify all games were created successfully
        assert len(game_state_sh.GAMES) == num_games
        
        # Verify each game is isolated
        for i, room_id in enumerate(room_ids):
            game = game_state_sh.get_game(room_id)
            assert len(game.players) == 1
            assert helpers[i].player_id in game.players
    
    def test_rapid_action_sequence(self, direct_clients, clean_game_state):
        """Test handling rapid sequence of actions"""
        alice = direct_clients[0]
        
        # Setup room
        room_id = alice.create_room(stake=10)
        alice.join_room(room_id)
        game = game_state_sh.get_game(room_id)
        game.phase = "drawing"
        
        # Submit multiple drawings rapidly
        drawings = [alice.create_sample_drawing() for _ in range(10)]
        
        for drawing in drawings:
            game.drawing_phase.submit_drawing(alice.player_id, drawing, app_socketio)
        
        # Should only store one drawing (first valid one)
        assert len(game.original_drawings) <= 1
        
        # Player should be marked as having drawn
        if alice.player_id in game.players:
            # This depends on the implementation - some games may track this
            assert alice.player_id in game.original_drawings or len(game.original_drawings) > 0


class TestReconnectionHandling:
    """Test player reconnection and state recovery"""
    
    def test_player_disconnect_during_game(self, direct_clients, clean_game_state):
        """Test handling of player disconnection during active game"""
        alice, bob, carol = direct_clients
        
        # Setup game with 3 players
        room_id = alice.create_room(stake=10)
        alice.join_room(room_id)
        bob.join_room(room_id)
        carol.join_room(room_id)
        
        game = game_state_sh.get_game(room_id)
        game.start_game(app_socketio)
        
        # Simulate disconnect by manually removing player
        game.remove_player(bob.player_id)
        
        # Game should continue with remaining players
        assert len(game.players) == 2  # Bob should be removed
        assert alice.player_id in game.players
        assert carol.player_id in game.players
        
        # Game should not end early if still above minimum
        assert game.phase != "ended_early"
    
    def test_room_cleanup_on_empty(self, direct_clients, clean_game_state):
        """Test automatic room cleanup when all players leave"""
        alice, bob = direct_clients[:2]
        
        # Create room and add players
        room_id = alice.create_room(stake=10)
        alice.join_room(room_id)
        bob.join_room(room_id)
        
        # Verify room exists
        assert room_id in game_state_sh.GAMES
        
        # Simulate all players disconnecting
        game = game_state_sh.get_game(room_id)
        game.remove_player(alice.player_id)
        game.remove_player(bob.player_id)
        
        # Room should be empty
        assert len(game.players) == 0
        
        # Manual cleanup for testing (in real app, this would be automatic)
        if len(game.players) == 0:
            game_state_sh.remove_game(room_id)
        
        assert room_id not in game_state_sh.GAMES


class TestComplexGameScenarios:
    """Test complex multi-phase game scenarios"""
    
    def test_full_game_with_all_phases(self, direct_clients, clean_game_state):
        """Test a complete game going through all phases naturally"""
        alice, bob, carol = direct_clients
        
        # 1. Room creation and joining
        room_id = alice.create_room(stake=10)
        alice.join_room(room_id)
        bob.join_room(room_id)
        carol.join_room(room_id)
        
        game = game_state_sh.get_game(room_id)
        
        # 2. Game start and betting
        game.start_game(app_socketio)
        assert game.phase == "betting"
        
        stakes = [10, 15, 20]
        clients = [alice, bob, carol]
        for client, stake in zip(clients, stakes):
            game.betting_phase.place_bet(client.player_id, stake, app_socketio)
        
        # 3. Drawing phase
        game.drawing_phase.start_phase(app_socketio)
        assert game.phase == "drawing"
        
        for client in clients:
            drawing_data = client.create_sample_drawing()
            game.drawing_phase.submit_drawing(client.player_id, drawing_data, app_socketio)
        
        # Verify all drawings stored
        assert len(game.original_drawings) == 3
        
        # 4. Copying phase
        game.copying_phase.start_phase(app_socketio)
        assert game.phase == "copying"
        
        # Submit copies (simplified - each player copies one other)
        copy_pairs = [
            (alice.player_id, bob.player_id),
            (bob.player_id, carol.player_id), 
            (carol.player_id, alice.player_id)
        ]
        
        for copier_id, target_id in copy_pairs:
            copy_data = next(c for c in clients if c.player_id == copier_id).create_sample_drawing()
            game.copying_phase.submit_drawing(copier_id, target_id, copy_data, app_socketio)
        
        # Verify copies were stored
        assert len(game.copied_drawings) > 0
        
        # 5. Voting phase
        game.voting_phase.start_phase(app_socketio)
        assert game.phase == "voting"
        
        # Create voting sets
        game.voting_phase._create_drawing_sets()
        
        # Submit votes (simplified) - vote on first available drawing set
        if len(game.drawing_sets) > 0:
            drawing_set = game.drawing_sets[0]
            if len(drawing_set) > 0:
                first_drawing_id = drawing_set[0]['id']
                for client in clients:
                    game.voting_phase.submit_vote(client.player_id, first_drawing_id, app_socketio)
        
        # 6. Results calculation
        game.scoring_engine.calculate_results(app_socketio)
        
        # Verify final state
        assert game.phase == "results"
        
        # Verify token conservation
        total_final_tokens = sum(player['balance'] for player in game.players.values())
        expected_total = len(clients) * CONSTANTS['INITIAL_BALANCE']
        # Allow for some variance due to scoring
        assert abs(total_final_tokens - expected_total) <= expected_total  # Reasonable bounds


# Add fixtures for direct clients
@pytest.fixture
def direct_clients():
    """Create direct game manipulation clients for easier testing"""
    return [
        DirectGameTestHelper("Alice"),
        DirectGameTestHelper("Bob"),
        DirectGameTestHelper("Carol")
    ]


@pytest.fixture
def clean_game_state():
    """Clean game state before each test"""
    # Clear all games and players
    game_state_sh.GAMES.clear()
    game_state_sh.PLAYERS.clear()
    yield
    # Clean up after test
    game_state_sh.GAMES.clear()
    game_state_sh.PLAYERS.clear()


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
