"""
Pytest configuration and shared fixtures for Pixel Plagiarist tests.

This file makes fixtures available to all test modules in the tests directory.
"""

# Import all fixtures from test_common to make them available globally
from .test_common import (
    test_app,
    socketio_app, 
    direct_clients,
    mock_clients,
    timer_helper,
    db_helper,
    clean_game_state,
    clean_database,
    concurrency_helper
)