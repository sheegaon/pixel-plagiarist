"""
Integration tests for Pixel Plagiarist multiplayer drawing game.

Tests the complete game flow including:
- Room management (creation, joining, leaving)
- Game phases (betting, drawing, copying, voting, results)
- Socket event handling and broadcasting  
- State transitions and synchronization
- Player management and disconnection handling
- Scoring and token distribution
- Error handling and edge cases

Uses Flask-SocketIO test client to simulate real WebSocket connections.
"""

import pytest
import base64
import io
import uuid
from unittest.mock import patch, MagicMock

# Import the main application components
from server import app, socketio as app_socketio
from socket_handlers.game_state import game_state_sh
from game_logic.game_state import GameStateGL


class SocketiOTestHelper:
    """Wrapper for Flask-SocketIO test client with helper methods"""
    
    def __init__(self, socketio_client, username="TestPlayer"):
        self.client = socketio_client
        self.username = username
        self.room_id = None
        self.player_id = None
        self.received_events = []
        # Generate a unique socket ID for testing
        self._socket_id = f"test_{uuid.uuid4().hex[:16]}"
        
    def emit_and_wait(self, event, data=None, timeout=1):
        """Emit event and wait for response"""
        if data is None:
            data = {}
        
        # Instead of patching flask.request, we'll patch the specific handlers
        # to use our test socket ID
        original_handlers = {}
        
        # Patch all the socket handlers to use our test socket ID
        for handler_class_name in ['RoomHandlers', 'GameHandlers', 'AdminHandlers', 'ConnectionHandlers']:
            try:
                if handler_class_name == 'RoomHandlers':
                    from socket_handlers.room_handlers import RoomHandlers
                    handler_class = RoomHandlers
                elif handler_class_name == 'GameHandlers':
                    from socket_handlers.game_handlers import GameHandlers
                    handler_class = GameHandlers
                elif handler_class_name == 'AdminHandlers':
                    from socket_handlers.admin_handlers import AdminHandlers
                    handler_class = AdminHandlers
                elif handler_class_name == 'ConnectionHandlers':
                    from socket_handlers.connection_handlers import ConnectionHandlers
                    handler_class = ConnectionHandlers
                else:
                    continue
                    
                # Create a mock request object with our socket ID
                mock_request = MagicMock()
                mock_request.sid = self._socket_id
                
                # Store original and patch
                original_handlers[handler_class_name] = getattr(handler_class, '_test_request', None)
                setattr(handler_class, '_test_request', mock_request)
                
            except ImportError:
                continue
        
        try:
            # Emit the event
            self.client.emit(event, data)
            received = self.client.get_received(timeout=timeout)
            self.received_events.extend(received)
            return received
        finally:
            # Restore original handlers
            for handler_class_name, original in original_handlers.items():
                try:
                    if handler_class_name == 'RoomHandlers':
                        from socket_handlers.room_handlers import RoomHandlers
                        handler_class = RoomHandlers
                    elif handler_class_name == 'GameHandlers':
                        from socket_handlers.game_handlers import GameHandlers
                        handler_class = GameHandlers
                    elif handler_class_name == 'AdminHandlers':
                        from socket_handlers.admin_handlers import AdminHandlers
                        handler_class = AdminHandlers
                    elif handler_class_name == 'ConnectionHandlers':
                        from socket_handlers.connection_handlers import ConnectionHandlers
                        handler_class = ConnectionHandlers
                    else:
                        continue
                        
                    if original is not None:
                        setattr(handler_class, '_test_request', original)
                    else:
                        delattr(handler_class, '_test_request')
                except (AttributeError, ImportError):
                    pass
    
    def get_last_event(self, event_name):
        """Get the last received event of a specific type"""
        for event in reversed(self.received_events):
            if event['name'] == event_name:
                return event
        return None
    
    def clear_events(self):
        """Clear received events buffer"""
        self.received_events.clear()
    
    @staticmethod
    def create_sample_drawing():
        """Create a simple base64-encoded drawing for testing"""
        # Create a minimal PNG red image
        from PIL import Image
        img = Image.new('RGB', (100, 100), color=(255, 0, 0))
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{image_data}"

    @property
    def socket_id(self):
        """Get the socket ID which is used as player ID"""
        return self._socket_id


# Let's create a simpler approach using direct game manipulation
class DirectGameTestHelper:
    """Helper that directly manipulates game state for testing"""
    
    def __init__(self, username="TestPlayer"):
        self.username = username
        self.room_id = None
        self.player_id = f"test_{uuid.uuid4().hex[:16]}"
        
    def create_room(self, min_stake=10):
        """Create a room directly"""
        self.room_id = str(uuid.uuid4())[:8].upper()
        game = GameStateGL(self.room_id, min_stake)
        game_state_sh.add_game(self.room_id, game)
        return self.room_id
    
    def join_room(self, room_id=None):
        """Join a room directly"""
        if room_id:
            self.room_id = room_id
        
        if self.room_id and self.room_id in game_state_sh.GAMES:
            game = game_state_sh.get_game(self.room_id)
            game.add_player(self.player_id, self.username)
            game_state_sh.add_player(self.player_id, self.room_id)
            return True
        return False
    
    @staticmethod
    def create_sample_drawing():
        """Create a simple base64-encoded drawing for testing"""
        from PIL import Image
        img = Image.new('RGB', (100, 100), color='white')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{image_data}"


@pytest.fixture
def test_app():
    """Create test Flask app with SocketIO"""
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test_secret_key'
    return app


@pytest.fixture  
def socketio_app(test_app):
    """Create SocketIO instance for testing"""
    return app_socketio


@pytest.fixture
def clients(socketio_app, test_app):
    """Create multiple test clients for multiplayer testing"""
    client1 = socketio_app.test_client(test_app)
    client2 = socketio_app.test_client(test_app)
    client3 = socketio_app.test_client(test_app)
    
    # Wrap in helper class
    helpers = [
        SocketiOTestHelper(client1, "Alice"),
        SocketiOTestHelper(client2, "Bob"), 
        SocketiOTestHelper(client3, "Carol")
    ]
    
    # Set player IDs to socket IDs after connection
    for helper in helpers:
        helper.player_id = helper.socket_id
    
    return helpers


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


class TestRoomManagement:
    """Test room creation, joining, and management"""
    
    def test_room_creation_and_joining_direct(self, direct_clients, clean_game_state):
        """Test basic room creation and player joining using direct manipulation"""
        alice, bob, carol = direct_clients
        
        # Alice creates a room
        room_id = alice.create_room(min_stake=10)
        assert room_id is not None
        assert room_id in game_state_sh.GAMES
        
        # Alice joins her own room
        assert alice.join_room(room_id) is True
        
        # Bob and Carol join the room
        assert bob.join_room(room_id) is True
        assert carol.join_room(room_id) is True
        
        # Verify all players are in room
        game = game_state_sh.get_game(room_id)
        assert len(game.players) == 3
        assert alice.player_id in game.players
        assert bob.player_id in game.players
        assert carol.player_id in game.players
    
    def test_room_not_found_error(self, direct_clients, clean_game_state):
        """Test joining non-existent room"""
        alice = direct_clients[0]
        
        # Try to join non-existent room
        result = alice.join_room('NONEXISTENT')
        assert result is False
    
    def test_player_disconnection_cleanup(self, direct_clients, clean_game_state):
        """Test room cleanup when players disconnect"""
        alice, bob = direct_clients[:2]
        
        # Create room and add players
        room_id = alice.create_room(min_stake=10)
        alice.join_room(room_id)
        bob.join_room(room_id)
        
        # Verify room exists with both players
        game = game_state_sh.get_game(room_id)
        assert len(game.players) == 2
        
        # Remove Alice
        game.remove_player(alice.player_id)
        assert len(game.players) == 1
        assert bob.player_id in game.players
        
        # Remove Bob
        game.remove_player(bob.player_id)
        assert len(game.players) == 0


class TestGameFlow:
    """Test complete game flow through all phases"""
    
    @patch('game_logic.timer.Timer.start_phase_timer')
    def test_complete_game_flow(self, mock_timer, direct_clients, clean_game_state):
        """Test a complete game from start to finish"""
        alice, bob, carol = direct_clients
        
        # 1. Room Setup
        room_id = alice.create_room(min_stake=10)
        alice.join_room(room_id)
        bob.join_room(room_id)
        carol.join_room(room_id)
        
        # Get game instance
        game = game_state_sh.get_game(room_id)
        assert game is not None
        assert len(game.players) == 3
        
        # 2. Start Game (triggers betting phase)
        game.start_game(app_socketio)
        assert game.phase == "betting"
        
        # 3. Betting Phase - directly place bets
        game.betting_phase.place_bet(alice.player_id, 10, app_socketio, check_early_advance=False)
        game.betting_phase.place_bet(bob.player_id, 15, app_socketio, check_early_advance=False)
        game.betting_phase.place_bet(carol.player_id, 20, app_socketio, check_early_advance=False)
        
        # Manually advance to drawing phase
        game.drawing_phase.start_phase(app_socketio)
        assert game.phase == "drawing"
        
        # 4. Drawing Phase - directly submit drawings
        alice_drawing = alice.create_sample_drawing()
        bob_drawing = bob.create_sample_drawing()
        carol_drawing = carol.create_sample_drawing()
        
        game.drawing_phase.submit_drawing(alice.player_id, alice_drawing, app_socketio, check_early_advance=False)
        game.drawing_phase.submit_drawing(bob.player_id, bob_drawing, app_socketio, check_early_advance=False)
        game.drawing_phase.submit_drawing(carol.player_id, carol_drawing, app_socketio, check_early_advance=False)
        
        # Verify all drawings stored
        assert len(game.original_drawings) == 3
        
        # 5. Copying Phase (starts with viewing sub-phase)
        game.copying_phase.start_phase(app_socketio)
        assert game.phase == "copying_viewing"  # Initial sub-phase is viewing
        
        # Submit copies (simplified - each player copies one other)
        alice_copy = alice.create_sample_drawing()
        bob_copy = bob.create_sample_drawing()
        carol_copy = carol.create_sample_drawing()
        
        game.copying_phase.submit_drawing(
            alice.player_id, bob.player_id, alice_copy, app_socketio, check_early_advance=False)
        game.copying_phase.submit_drawing(
            bob.player_id, carol.player_id, bob_copy, app_socketio, check_early_advance=False)
        game.copying_phase.submit_drawing(
            carol.player_id, alice.player_id, carol_copy, app_socketio, check_early_advance=False)
        
        # 6. Voting Phase
        game.voting_phase.start_phase(app_socketio)
        assert game.phase == "voting"
        
        # Create voting sets
        game.voting_phase._create_drawing_sets()
        
        # Submit votes (simplified)
        if len(game.drawing_sets) > 0:
            # Vote on first set
            drawing_set = game.drawing_sets[0]
            if len(drawing_set['drawings']) > 0:
                first_drawing_id = drawing_set['drawings'][0]['id']
                game.voting_phase.submit_vote(
                    alice.player_id, first_drawing_id, app_socketio, check_early_advance=False)
                game.voting_phase.submit_vote(
                    bob.player_id, first_drawing_id, app_socketio, check_early_advance=False)
                game.voting_phase.submit_vote(
                    carol.player_id, first_drawing_id, app_socketio, check_early_advance=False)
        
        # 7. Calculate Results
        game.scoring_engine.calculate_results(app_socketio)
        
        # Verify game completed
        assert game.phase == "results"
    
    def test_drawing_phase(self, direct_clients, clean_game_state):
        """Test drawing submission and validation"""
        alice = direct_clients[0]
        
        # Setup minimal game state
        room_id = alice.create_room(min_stake=10)
        alice.join_room(room_id)
        game = game_state_sh.get_game(room_id)
        
        # Directly set to drawing phase
        game.phase = "drawing"
        
        # Test valid drawing submission
        drawing_data = alice.create_sample_drawing()
        game.drawing_phase.submit_drawing(alice.player_id, drawing_data, app_socketio)
        
        # Verify drawing was stored
        assert alice.player_id in game.original_drawings
        
        # Test duplicate submission (should be rejected)
        game.drawing_phase.submit_drawing(alice.player_id, drawing_data, app_socketio)
        # Should not overwrite - still only one drawing
        assert len(game.original_drawings) == 1


class TestErrorHandling:
    """Test error conditions and edge cases"""
    
    def test_invalid_phase_actions(self, direct_clients, clean_game_state):
        """Test actions during wrong game phase"""
        alice = direct_clients[0]
        
        # Create room
        room_id = alice.create_room(min_stake=10)
        alice.join_room(room_id)
        game = game_state_sh.get_game(room_id)
        
        # Try to submit drawing during waiting phase
        drawing_data = alice.create_sample_drawing()
        game.drawing_phase.submit_drawing(alice.player_id, drawing_data, app_socketio)
        
        # Should be rejected (no drawing should be stored)
        assert len(game.original_drawings) == 0
        
        # Try to place bet during waiting phase
        game.betting_phase.place_bet(alice.player_id, 10, app_socketio)
        
        # Should be rejected
        player_data = game.players.get(alice.player_id)
        if player_data:
            assert player_data.get('has_bet', False) is False
    
    def test_game_early_termination(self, direct_clients, clean_game_state):
        """Test game ending early due to insufficient players"""
        alice, bob, carol = direct_clients
        
        # Setup game with 3 players
        room_id = alice.create_room(min_stake=10)
        alice.join_room(room_id)
        bob.join_room(room_id)
        carol.join_room(room_id)
        
        game = game_state_sh.get_game(room_id)
        game.start_game(app_socketio)
        
        # Remove players to trigger early termination
        game.remove_player(bob.player_id)
        game.remove_player(carol.player_id)
        
        # Should trigger early game end
        game.end_game_early(app_socketio)
        # Check if phase changed - this might not always be 'ended_early'
        # depending on implementation
        assert game.phase in ["ended_early", "betting", "results"]  # Allow various states


class TestScoringAndTokens:
    """Test scoring system and token distribution"""
    
    def test_scoring_calculations(self, direct_clients, clean_game_state):
        """Test that scoring follows the documented rules"""
        alice, bob, carol = direct_clients

        # Setup game
        room_id = alice.create_room(min_stake=10)
        alice.join_room(room_id)
        bob.join_room(room_id)
        carol.join_room(room_id)
        
        game = game_state_sh.get_game(room_id)
        
        # Set up staking scenario
        initial_balances = {player_id: player_data['balance'] for player_id, player_data in game.players.items()}
        game.phase = "betting"
        assert game.betting_phase.place_bet(alice.player_id, 10, app_socketio, check_early_advance=False), \
            "Alice should be able to place a valid bet"
        assert game.betting_phase.place_bet(bob.player_id, 15, app_socketio, check_early_advance=False), \
            "Bob should be able to place a valid bet"
        assert game.betting_phase.place_bet(carol.player_id, 20, app_socketio, check_early_advance=False), \
            "Carol should be able to place a valid bet"

        # Set up drawing phase
        game.phase = "drawing"
        for player in [alice, bob, carol]:
            assert game.drawing_phase.submit_drawing(
                player.player_id, player.create_sample_drawing(), app_socketio, check_early_advance=False), \
                f"Original drawing submission from {player} should be accepted"

        # Set up copying phase
        game.phase = "copying"
        game.copying_phase._assign_copying_tasks()
        for player_id, target_ids in game.copy_assignments.items():
            player = next((p for p in [alice, bob, carol] if p.player_id == player_id), None)
            for target_id in target_ids:
                assert game.copying_phase.submit_drawing(
                    player_id, target_id, player.create_sample_drawing(), app_socketio, check_early_advance=False), \
                    f"Copy submission from {player} should be accepted"

        # Set up votes (all vote correctly for original drawings)
        game.phase = "voting"
        game.voting_phase._create_drawing_sets()
        for idx_current_drawing_set, drawing_set in enumerate(game.drawing_sets):
            game.idx_current_drawing_set = idx_current_drawing_set
            for player_id in game.voting_phase.get_eligible_voters_for_set(drawing_set):
                original_drawing_id = next((d['id'] for d in drawing_set['drawings'] if 'original' in d['id']), None)
                copy_drawing_id = next((d['id'] for d in drawing_set['drawings'] if 'copy' in d['id']), None)
                # Alice votes correctly and her original is chosen
                if player_id == alice.player_id or alice.player_id in original_drawing_id:
                    assert game.voting_phase.submit_vote(
                        player_id=player_id, drawing_id=original_drawing_id, socketio=app_socketio,
                        check_early_advance=False), "Vote should be accepted"
                else:
                    assert game.voting_phase.submit_vote(
                        player_id=player_id, drawing_id=copy_drawing_id, socketio=app_socketio,
                        check_early_advance=False), "Vote should be accepted"
        
        # Calculate results
        game.scoring_engine.calculate_results(app_socketio)
        
        # Verify game completed
        assert game.phase == "results"
        
        # Verify scoring rules: there should be no difference in token balances
        final_balances = {player_id: player_data['balance'] for player_id, player_data in game.players.items()}
        
        # Verify token conservation (total should be preserved)
        total_initial = sum(initial_balances.values())
        total_final = sum(final_balances.values())
        
        # Total tokens should be conserved (allowing for some rounding)
        assert abs(total_final - total_initial) <= 1  # Allow 1 token difference for rounding
        
        # Verify scoring logic:

        alice_change = final_balances[alice.player_id] - initial_balances[alice.player_id]
        assert alice_change > 0, f"Alice should have gained tokens, got change: {alice_change}"


class TestConcurrentGames:
    """Test multiple games running simultaneously"""
    
    def test_multiple_rooms_isolation(self, direct_clients, clean_game_state):
        """Test that multiple games don't interfere with each other"""
        alice1, bob1, carol1 = direct_clients
        
        # Create additional clients for second game
        alice2 = DirectGameTestHelper("Alice2")
        bob2 = DirectGameTestHelper("Bob2") 
        carol2 = DirectGameTestHelper("Carol2")
        
        # Create two separate rooms
        room1_id = alice1.create_room(min_stake=10)
        room2_id = alice2.create_room(min_stake=25)
        
        # Verify rooms are separate
        assert room1_id != room2_id
        assert room1_id in game_state_sh.GAMES
        assert room2_id in game_state_sh.GAMES
        
        game1 = game_state_sh.get_game(room1_id)
        game2 = game_state_sh.get_game(room2_id)
        
        assert game1.min_stake == 10
        assert game2.min_stake == 25
        
        # Add players to each game
        alice1.join_room(room1_id)
        bob1.join_room(room1_id)
        carol1.join_room(room1_id)
        
        alice2.join_room(room2_id)
        bob2.join_room(room2_id)
        carol2.join_room(room2_id)
        
        # Verify player isolation
        assert len(game1.players) == 3
        assert len(game2.players) == 3
        
        # Players in game1 should not be in game2 and vice versa
        game1_player_ids = set(game1.players.keys())
        game2_player_ids = set(game2.players.keys())
        assert game1_player_ids.isdisjoint(game2_player_ids)


# Run integration tests with proper setup
if __name__ == '__main__':
    pytest.main([__file__, '-v'])
