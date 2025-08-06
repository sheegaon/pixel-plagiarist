# Connection handling for socket events
from flask import request
from flask_socketio import emit
from util.logging_utils import debug_log
from .game_state import GAME_STATE_SH, get_room_info, broadcast_room_list


class ConnectionHandlers:
    """Handles client connection and disconnection events"""
    
    def __init__(self, socketio):
        self.socketio = socketio
    
    @staticmethod
    def handle_connect():
        """Handle new client connection"""
        debug_log("Client connecting to server", None, None, {
            'connection_source': 'socket_connect',
            'session_id': request.sid if hasattr(request, 'sid') else 'unknown'
        })
        
        # Send current room list to newly connected client
        rooms = get_room_info()
        emit('room_list_updated', {'rooms': rooms})
        
        # If no rooms exist, create a default bronze room
        if not rooms:
            try:
                new_room_id = GAME_STATE_SH.ensure_default_room()
                if new_room_id:
                    debug_log("Created default room on client connect", None, new_room_id)
                    # Send updated room list with the new room
                    updated_rooms = get_room_info()
                    emit('room_list_updated', {'rooms': updated_rooms})
            except Exception as e:
                debug_log("Failed to create default room on connect", None, None, {'error': str(e)})

    @staticmethod
    def handle_disconnect():
        """Handle player disconnect"""
        player_id = request.sid

        debug_log("Client disconnecting from server", player_id, None, {
            'disconnect_source': 'socket_disconnect',
            'session_id': player_id
        })

        if player_id in GAME_STATE_SH.PLAYERS:
            room_id = GAME_STATE_SH.get_player_room(player_id)
            
            debug_log("Player disconnecting from server", player_id, room_id, {
                'disconnect_source': 'connection_handler'
            })
            
            GAME_STATE_SH.remove_player(player_id)

            if room_id in GAME_STATE_SH.GAMES:
                game = GAME_STATE_SH.get_game(room_id)
                game.remove_player(player_id)

                # Clean up empty games - but only if we haven't already deleted it
                if len(game.players) == 0 and room_id in GAME_STATE_SH.GAMES:
                    debug_log("Room is empty after disconnect, deleting", None, room_id, {
                        'deletion_source': 'connection_handler_disconnect'
                    })
                    GAME_STATE_SH.remove_game(room_id)
                    
                    # After deleting a room, ensure there's still a default bronze room available
                    new_room_id = GAME_STATE_SH.ensure_default_room()
                    if new_room_id:
                        debug_log("Created replacement default room after disconnect deletion", None, new_room_id)
                    
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
        else:
            debug_log("Disconnecting client was not in player registry", player_id, None, {
                'session_id': player_id
            })

    @staticmethod
    def handle_request_room_list(data=None):
        """Handle request for current room list"""
        rooms = get_room_info()
        emit('room_list_updated', {'rooms': rooms})