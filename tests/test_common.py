"""
Common test utilities and helpers for Pixel Plagiarist integration tests.

This module provides shared fixtures, helpers, and utilities used across
multiple test files to avoid code duplication and ensure consistent testing.
"""

import pytest
import base64
import io
import uuid
import time
import threading
from unittest.mock import patch, MagicMock
from contextlib import contextmanager

# Import the main application components
from server import app, socketio as app_socketio
from socket_handlers.game_state import GAME_STATE_SH
from game_logic.game_state import GameStateGL
from util.config import CONSTANTS


class MockSocketIOTestHelper:
    """Mock SocketIO test helper for easier testing without real WebSocket connections"""
    
    def __init__(self, username="TestPlayer"):
        self.username = username
        self.room_id = None
        self.player_id = f"test_{uuid.uuid4().hex[:16]}"
        self.received_events = []
        self.mock_socketio = MagicMock()
        
    def emit_and_wait(self, event, data=None, timeout=1):
        """Mock emit event and capture response"""
        if data is None:
            data = {}
            
        # Store the emitted event for verification
        self.received_events.append({
            'name': event,
            'data': data,
            'timestamp': time.time()
        })
        return self.received_events
    
    def get_last_event(self, event_name):
        """Get the last received event of a specific type"""
        for event in reversed(self.received_events):
            if event['name'] == event_name:
                return event
        return None
    
    def clear_events(self):
        """Clear received events buffer"""
        self.received_events.clear()
    
    @property
    def socket_id(self):
        """Get the socket ID which is used as player ID"""
        return self.player_id


class GameTestHelper:
    """Helper that directly manipulates game state for testing"""
    
    def __init__(self, username="TestPlayer"):
        self.username = username
        self.room_id = None
        self.player_id = f"test_{uuid.uuid4().hex[:16]}"

    def create_room(self, stake=100):
        """Create a room directly"""
        self.room_id = str(uuid.uuid4())[:8].upper()
        game = GameStateGL(self.room_id, stake)
        GAME_STATE_SH.add_game(self.room_id, game)
        return self.room_id
    
    def join_room(self, room_id=None):
        """Join a room directly"""
        if room_id:
            self.room_id = room_id
        
        if self.room_id and self.room_id in GAME_STATE_SH.GAMES:
            game = GAME_STATE_SH.get_game(self.room_id)
            success = game.add_player(self.player_id, self.username)
            if success:
                GAME_STATE_SH.add_player(self.player_id, self.room_id)
            return success
        return False

    def leave_room(self):
        """Leave current room"""
        if self.room_id and self.room_id in GAME_STATE_SH.GAMES:
            game = GAME_STATE_SH.get_game(self.room_id)
            game.remove_player(self.player_id)
            GAME_STATE_SH.remove_player(self.player_id)
            self.room_id = None
            return True
        return False

    def delete_player(self):
        """Remove player from DB"""
        try:
            from util import db
            db.delete_player(self.username)
        except Exception:
            pass  # Player might not exist in DB


class TimerTestHelper:
    """Helper for testing timer-related functionality"""
    
    def __init__(self):
        self.active_timers = []
        
    @contextmanager
    def mock_all_timers(self):
        """Context manager to mock all threading.Timer instances"""
        original_timer = threading.Timer
        mock_timers = []
        
        def mock_timer_constructor(interval, function, args=None, kwargs=None):
            mock_timer = MagicMock()
            mock_timer.interval = interval
            mock_timer.function = function
            mock_timer.args = args or []
            mock_timer.kwargs = kwargs or {}
            mock_timer.finished = threading.Event()
            mock_timer.is_alive = MagicMock(return_value=False)
            
            # Store for later access
            mock_timers.append(mock_timer)
            return mock_timer
            
        with patch('threading.Timer', side_effect=mock_timer_constructor):
            yield mock_timers
    
    def trigger_timer_callback(self, mock_timer):
        """Manually trigger a timer's callback function"""
        if hasattr(mock_timer, 'function') and mock_timer.function:
            try:
                mock_timer.function(*mock_timer.args, **mock_timer.kwargs)
            except Exception as e:
                print(f"Error triggering timer callback: {e}")


class DatabaseTestHelper:
    """Helper for testing database operations"""
    
    @staticmethod
    def get_player_balance(username):
        """Get player balance from database"""
        try:
            from util.db import get_player_stats
            stats = get_player_stats(username)
            return stats['balance'] if stats else None
        except Exception:
            return None
    
    @staticmethod
    def create_test_player(username, balance=1000):
        """Create a test player in the database"""
        try:
            from util.db import get_or_create_player, update_player_balance
            player = get_or_create_player(username)
            if player:
                update_player_balance(username, balance)
            return player
        except Exception as e:
            print(f"Failed to create test player: {e}")
            return None
    
    @staticmethod
    def cleanup_test_player(username):
        """Clean up test player from database"""
        try:
            from util.db import delete_player
            delete_player(username)
        except Exception:
            pass


def create_sample_drawing():
    """Create a simple base64-encoded drawing for testing"""
    try:
        from PIL import Image
        img = Image.new('RGB', (100, 100), color=(255, 0, 0))
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return f"data:image/png;base64,{image_data}"
    except ImportError:
        # Fallback for environments without PIL
        return create_minimal_base64_image()


def create_minimal_base64_image():
    """Create a minimal valid base64 image for testing without PIL"""
    # This is a minimal 1x1 pixel PNG in base64
    minimal_png = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    )
    return f"data:image/png;base64,{minimal_png}"


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
def direct_clients():
    """Create direct game manipulation clients for easier testing"""
    players = ['Alice', 'Bob', 'Carol', 'Dave', 'Eve', 'Frank', 'Grace', 'Heidi', 'Ivan', 'Judy',
               'Karl', 'Leo', 'Mallory', 'Nina', 'Oscar', 'Peggy', 'Quentin', 'Rupert', 'Sybil', 'Trent']
    return [GameTestHelper(players[n]) for n in range(20)]


@pytest.fixture
def mock_clients():
    """Create mock SocketIO clients for testing"""
    players = ['Alice', 'Bob', 'Carol', 'Dave', 'Eve', 'Frank', 'Grace', 'Heidi', 'Ivan', 'Judy']
    return [MockSocketIOTestHelper(players[n]) for n in range(10)]


@pytest.fixture
def timer_helper():
    """Create timer test helper"""
    return TimerTestHelper()


@pytest.fixture
def db_helper():
    """Create database test helper"""
    return DatabaseTestHelper()


@pytest.fixture
def clean_game_state():
    """Clean game state before each test"""
    # Clear all games and players
    GAME_STATE_SH.GAMES.clear()
    GAME_STATE_SH.PLAYERS.clear()
    yield
    # Clean up after test
    GAME_STATE_SH.GAMES.clear()
    GAME_STATE_SH.PLAYERS.clear()


@pytest.fixture
def clean_database():
    """Clean up database before and after tests"""
    # Clean up any existing test players
    test_usernames = ['TestAlice', 'TestBob', 'TestCarol', 'TestDave', 'TestEve']
    db_helper = DatabaseTestHelper()
    
    for username in test_usernames:
        db_helper.cleanup_test_player(username)
    
    yield
    
    # Clean up after test
    for username in test_usernames:
        db_helper.cleanup_test_player(username)


class ErrorSimulator:
    """Helper for simulating various error conditions"""
    
    @staticmethod
    @contextmanager
    def database_error():
        """Simulate database connection errors"""
        with patch('util.db.get_db_connection') as mock_conn:
            mock_conn.side_effect = Exception("Database connection failed")
            yield
    
    @staticmethod
    @contextmanager
    def network_error():
        """Simulate network/socket errors"""
        with patch('flask_socketio.emit') as mock_emit:
            mock_emit.side_effect = Exception("Network error")
            yield
    
    @staticmethod
    @contextmanager
    def memory_pressure():
        """Simulate high memory usage conditions"""
        # This could be expanded to actually simulate memory pressure
        yield


class ConcurrencyTestHelper:
    """Helper for testing concurrent operations"""
    
    def __init__(self):
        self.threads = []
        self.results = []
        self.lock = threading.Lock()
    
    def run_concurrent(self, func, args_list, max_workers=5):
        """Run a function concurrently with different arguments"""
        self.threads = []
        self.results = []
        
        def worker(args, index):
            try:
                result = func(*args)
                with self.lock:
                    self.results.append((index, result, None))
            except Exception as e:
                with self.lock:
                    self.results.append((index, None, e))
        
        # Start threads
        for i, args in enumerate(args_list[:max_workers]):
            thread = threading.Thread(target=worker, args=(args, i))
            thread.start()
            self.threads.append(thread)
        
        # Wait for all threads to complete
        for thread in self.threads:
            thread.join(timeout=10.0)  # 10 second timeout
        
        return self.results
    
    def cleanup(self):
        """Clean up any remaining threads"""
        for thread in self.threads:
            if thread.is_alive():
                # Can't force kill threads in Python, but we can at least track them
                pass


@pytest.fixture
def concurrency_helper():
    """Create concurrency test helper"""
    helper = ConcurrencyTestHelper()
    yield helper
    helper.cleanup()


# Common test data
SAMPLE_GAME_SCENARIOS = [
    {
        'name': 'minimum_players',
        'player_count': 3,
        'stake': 100,
        'expected_outcome': 'complete_game'
    },
    {
        'name': 'maximum_players', 
        'player_count': 12,
        'stake': 100,
        'expected_outcome': 'complete_game'
    },
    {
        'name': 'high_stakes',
        'player_count': 5,
        'stake': 1000,
        'expected_outcome': 'complete_game'
    }
]


# Common assertion helpers
def assert_game_state_valid(game):
    """Assert that a game state is in a valid condition"""
    assert game is not None
    assert hasattr(game, 'phase')
    assert hasattr(game, 'players')
    assert hasattr(game, 'room_id')
    assert len(game.room_id) > 0
    assert game.phase in ['waiting', 'drawing', 'copying', 'voting', 'results', 'ended_early']


def assert_player_in_game(game, player_id):
    """Assert that a player is properly registered in a game"""
    assert player_id in game.players
    player_data = game.players[player_id]
    assert 'username' in player_data
    assert 'balance' in player_data
    assert 'id' in player_data
    assert player_data['id'] == player_id


def assert_database_consistency(username, expected_balance=None):
    """Assert that database state is consistent"""
    from util.db import get_player_stats
    stats = get_player_stats(username)
    
    if expected_balance is not None:
        assert stats is not None, f"Player {username} not found in database"
        assert stats['balance'] == expected_balance, f"Expected balance {expected_balance}, got {stats['balance']}"
    
    return stats