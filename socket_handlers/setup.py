# Setup module for registering all socket handlers
from .connection_handlers import ConnectionHandlers
from .room_handlers import RoomHandlers
from .game_handlers import GameHandlers
from .admin_handlers import AdminHandlers
from .game_state import game_state_sh


def setup_socket_handlers(socketio):
    """
    Register all socket event handlers with the SocketIO instance.
    
    Parameters
    ----------
    socketio : SocketIO
        The Flask-SocketIO instance to register handlers with
    """
    # Initialize handler classes
    connection_handlers = ConnectionHandlers(socketio)
    room_handlers = RoomHandlers(socketio)
    game_handlers = GameHandlers(socketio)
    admin_handlers = AdminHandlers(socketio)
    
    # Ensure default room exists
    game_state_sh.ensure_default_room()
    
    # Register connection handlers
    socketio.on_event('connect', connection_handlers.handle_connect)
    socketio.on_event('disconnect', connection_handlers.handle_disconnect)
    socketio.on_event('request_room_list', connection_handlers.handle_request_room_list)
    
    # Register room management handlers
    socketio.on_event('create_room', room_handlers.handle_create_room)
    socketio.on_event('join_room', room_handlers.handle_join_room)
    socketio.on_event('leave_room', room_handlers.handle_leave_room)
    
    # Register gameplay handlers
    socketio.on_event('submit_original', game_handlers.handle_submit_original)
    socketio.on_event('submit_copy', game_handlers.handle_submit_copy)
    socketio.on_event('submit_vote', game_handlers.handle_submit_vote)
    socketio.on_event('request_review', game_handlers.handle_request_review)
    
    # Register admin handlers
    socketio.on_event('debug_game_state', admin_handlers.handle_debug_game_state)
    socketio.on_event('force_start_game', admin_handlers.handle_force_start_game)
    socketio.on_event('cleanup_rooms', admin_handlers.handle_cleanup_rooms)
