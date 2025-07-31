# Socket handlers package for Pixel Plagiarist
# Modular architecture for managing different aspects of socket communication

# Export the main setup function
from .setup import setup_socket_handlers

# Import all handler modules
from .connection_handlers import ConnectionHandlers
from .room_handlers import RoomHandlers
from .game_handlers import GameHandlers
from .admin_handlers import AdminHandlers
from .game_state import GameState, get_room_info, broadcast_room_list, game_state


# Create convenience function for backward compatibility
def check_and_create_default_room(socketio=None):
    """Backward compatibility wrapper for game_state.check_and_create_default_room"""
    return game_state.check_and_create_default_room(socketio)


__all__ = [
    'setup_socket_handlers',
    'ConnectionHandlers',
    'RoomHandlers',
    'GameHandlers',
    'AdminHandlers',
    'GameState',
    'get_room_info',
    'broadcast_room_list',
    'check_and_create_default_room'
]
