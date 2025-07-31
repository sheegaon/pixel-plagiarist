# Connection handling for socket events
from flask import request
from flask_socketio import emit
from logging_utils import debug_log
from .game_state import game_state, get_room_info, broadcast_room_list


class ConnectionHandlers:
    """Handles client connection and disconnection events"""
    
    def __init__(self, socketio):
        self.socketio = socketio
    
    def handle_connect(self):
        """Handle new client connection"""
        # Send current room list to newly connected client
        rooms = get_room_info()
        emit('room_list_updated', {'rooms': rooms})
        
        # If no rooms exist, create a default $10 room
        if not rooms:
            try:
                new_room_id = game_state.ensure_default_room()
                if new_room_id:
                    debug_log("Created default room on client connect", None, new_room_id, {'min_stake': 10})
                    # Send updated room list with the new room
                    updated_rooms = get_room_info()
                    emit('room_list_updated', {'rooms': updated_rooms})
            except Exception as e:
                debug_log("Failed to create default room on connect", None, None, {'error': str(e)})

    def handle_disconnect(self):
        """Handle player disconnect"""
        player_id = request.sid

        if player_id in game_state.PLAYERS:
            room_id = game_state.get_player_room(player_id)
            game_state.remove_player(player_id)

            if room_id in game_state.GAMES:
                game = game_state.get_game(room_id)
                game.remove_player(player_id)

                # Clean up empty games
                if len(game.players) == 0:
                    debug_log("Room is empty after disconnect, deleting", None, room_id)
                    game_state.remove_game(room_id)
                    
                    # After deleting a room, ensure there's still a default $10 room available
                    new_room_id = game_state.ensure_default_room()
                    if new_room_id:
                        debug_log("Created replacement default room after disconnect deletion", None, new_room_id, {'min_stake': 10})
                    
                    # Broadcast updated room list when room is deleted
                    broadcast_room_list()
                else:
                    # Broadcast updated player list
                    emit('players_updated', {
                        'players': list(game.players.values()),
                        'count': len(game.players)
                    }, room=room_id)

                    # Broadcast updated room list when player count changes
                    broadcast_room_list()

    def handle_request_room_list(self, data=None):
        """Handle request for current room list"""
        rooms = get_room_info()
        emit('room_list_updated', {'rooms': rooms})