# Administrative handlers for socket events
from flask import request
from flask_socketio import emit
from util.logging_utils import debug_log
from .game_state import GAME_STATE_SH, broadcast_room_list


class AdminHandlers:
    """Handles administrative actions like debugging and cleanup"""
    
    def __init__(self, socketio):
        self.socketio = socketio
    
    def handle_debug_game_state(self, data=None):
        """Handle debug game state request"""
        debug_info = {
            'total_games': len(GAME_STATE_SH.GAMES),
            'total_players': len(GAME_STATE_SH.PLAYERS),
            'games': {}
        }

        for room_id, game in GAME_STATE_SH.GAMES.items():
            debug_info['games'][room_id] = {
                'players': len(game.players),
                'phase': game.phase,
                'min_stake': game.prize_per_player,
                'created_at': game.created_at.isoformat()
            }

        emit('debug_info', debug_info)

    def handle_force_start_game(self, data):
        """Handle force start game request (admin only)"""
        room_id = data.get('room_id', '').upper()
        player_id = request.sid

        if room_id in GAME_STATE_SH.GAMES:
            game = GAME_STATE_SH.get_game(room_id)
            if game.phase == "waiting":
                debug_log("Force starting game", player_id, room_id, {'admin_action': True})
                game.start_game(self.socketio)
                emit('game_force_started', {
                    'success': True,
                    'message': f'Game {room_id} force started!'
                })
            else:
                emit('game_force_started', {
                    'success': False,
                    'message': 'Game is not in waiting phase'
                })
        else:
            emit('game_force_started', {
                'success': False,
                'message': 'Room not found'
            })

    def handle_cleanup_rooms(self, data=None):
        """Handle room cleanup request"""
        cleaned_rooms = []
        
        for room_id in list(GAME_STATE_SH.GAMES.keys()):
            game = GAME_STATE_SH.get_game(room_id)
            if len(game.players) == 0:
                GAME_STATE_SH.remove_game(room_id)
                cleaned_rooms.append(room_id)
                debug_log("Cleaned up empty room", None, room_id, {'admin_cleanup': True})

        # Ensure there's a default room after cleanup
        new_room_id = GAME_STATE_SH.ensure_default_room()
        if new_room_id:
            debug_log("Created replacement default room after cleanup", None, new_room_id)

        # Broadcast updated room list
        broadcast_room_list()

        emit('cleanup_complete', {
            'cleaned_rooms': cleaned_rooms,
            'count': len(cleaned_rooms)
        })