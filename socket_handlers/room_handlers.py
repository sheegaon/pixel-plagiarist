# Room management handlers for socket events
import uuid
import time
from flask import request
from flask_socketio import emit, join_room, leave_room

from game_logic import GameStateGL
from util.config import TIMER_CONFIG
from util.logging_utils import debug_log
from .game_state import game_state_sh, broadcast_room_list


class RoomHandlers:
    """Handles room creation, joining, and leaving operations"""
    
    def __init__(self, socketio):
        self.socketio = socketio
    
    def handle_create_room(self, data):
        """Handle room creation request"""
        username = data.get('username', 'Anonymous')
        player_id = request.sid
        stake = data['stake']

        # Generate unique room code
        room_id = str(uuid.uuid4())[:8].upper()

        # Create new game
        new_game = GameStateGL(room_id, stake)
        game_state_sh.add_game(room_id, new_game)

        # Add player to game and room
        if new_game.add_player(player_id, username):
            game_state_sh.add_player(player_id, room_id)
            join_room(room_id)

            emit('room_created', {
                'room_id': room_id,
                'success': True,
                'message': f'Room {room_id} created successfully!'
            })

            # Check if we should start countdown or game
            game = game_state_sh.get_game(room_id)
            if len(game.players) >= game.min_players and game.phase == "waiting":
                if len(game.players) >= game.max_players:
                    debug_log("Starting game immediately - max players reached", None, room_id,
                              {'player_count': len(game.players)})
                    game.start_game(self.socketio)
                elif game.timer.start_timer is None:
                    debug_log("Starting countdown - min players reached", None, room_id,
                              {'player_count': len(game.players)})
                    game.timer.start_joining_countdown(self.socketio)

            # Broadcast player list update
            emit('players_updated', {
                'players': list(game.players.values()),
                'count': len(game.players)
            }, room=room_id)

            # Broadcast updated room list to all clients
            broadcast_room_list()
        else:
            emit('room_created', {
                'success': False,
                'message': 'Failed to create room'
            })

    def handle_join_room(self, data):
        """Handle room join request"""
        room_id = data.get('room_id', '').upper()
        username = data.get('username', 'Anonymous')
        player_id = request.sid

        if room_id in game_state_sh.GAMES:
            game = game_state_sh.get_game(room_id)

            # First check if we can add the player
            if len(game.players) >= game.max_players:
                emit('join_room_error', {
                    'success': False,
                    'message': 'Room is full or unavailable'
                })
                return

            # Join the room first
            game_state_sh.add_player(player_id, room_id)
            join_room(room_id)

            # Then add the player to the game
            if game.add_player(player_id, username):
                emit('joined_room', {
                    'room_id': room_id,
                    'player_id': player_id,
                    'username': username,
                    'players': list(game.players.values()),
                    'success': True,
                    'message': f'Joined room {room_id} successfully!',
                    'phase': game.phase,
                    'prompt': game.prompt if game.phase != "waiting" else None
                })

                # Check if we should start countdown or game
                if len(game.players) >= game.min_players and game.phase == "waiting":
                    if len(game.players) >= game.max_players:
                        debug_log("Starting game immediately - max players reached", None, room_id,
                                  {'player_count': len(game.players)})
                        game.start_game(self.socketio)
                    elif game.timer.start_timer is None:
                        debug_log("Starting countdown - min players reached", None, room_id,
                                  {'player_count': len(game.players)})
                        game.timer.start_joining_countdown(self.socketio)
                    else:
                        # If countdown is already running, send the current countdown state to the new player
                        if hasattr(game, 'countdown_start_time'):
                            elapsed = time.time() - game.countdown_start_time
                            remaining = max(0, TIMER_CONFIG['joining'] - int(elapsed))
                            if remaining > 0:
                                debug_log("Sending countdown state to late joiner", player_id, room_id,
                                          {'remaining_seconds': remaining})
                                emit('joining_countdown_started', {'seconds': remaining}, to=player_id)

                # Broadcast player list update
                emit('players_updated', {
                    'players': list(game.players.values()),
                    'count': len(game.players)
                }, room=room_id)

                # Broadcast updated room list to all clients
                broadcast_room_list()
            else:
                # If adding failed, remove from players dict
                game_state_sh.remove_player(player_id)
                emit('join_room_error', {
                    'success': False,
                    'message': 'Failed to join room'
                })
        else:
            emit('join_room_error', {
                'success': False,
                'message': 'Room not found'
            })

    @staticmethod
    def handle_leave_room(data=None):
        """Handle player leaving a room"""
        player_id = request.sid

        if not game_state_sh.get_player_room(player_id):
            emit('room_left', {
                'success': False,
                'message': 'You are not in a room'
            })
            return

        room_id = game_state_sh.get_player_room(player_id)

        if not game_state_sh.get_game(room_id):
            # Clean up orphaned player reference
            game_state_sh.remove_player(player_id)
            emit('room_left', {
                'success': False,
                'message': 'Room no longer exists'
            })
            return

        game = game_state_sh.get_game(room_id)

        # Only allow leaving during waiting or results phases
        if game.phase not in ["waiting", "results"]:
            emit('room_left', {
                'success': False,
                'message': 'Cannot leave room after game has started'
            })
            return

        # Remove player from game and room
        if player_id in game.players:
            username = game.players[player_id]['username']
            del game.players[player_id]
            debug_log("Player left room", player_id, room_id, {'username': username})

        # Remove from players tracking
        game_state_sh.remove_player(player_id)
        leave_room(room_id)

        # Notify the leaving player
        emit('room_left', {
            'success': True,
            'message': 'You have left the room'
        })

        # Check if room is now empty and should be deleted
        if len(game.players) == 0:
            debug_log("Room is empty, deleting", None, room_id)
            game_state_sh.remove_game(room_id)
            
            # After deleting a room, ensure there's still a default $10 room available
            new_room_id = game_state_sh.ensure_default_room()
            if new_room_id:
                debug_log("Created replacement default room after deletion", None, new_room_id)
        else:
            # Notify remaining players
            emit('players_updated', {
                'players': list(game.players.values()),
                'count': len(game.players)
            }, room=room_id)

            # If we're below minimum players and countdown was active, cancel it
            if len(game.players) < game.min_players:
                if hasattr(game, 'countdown_timer') and game.countdown_timer:
                    game._stop_countdown = True  # Use the flag instead of cancel()
                    game.countdown_timer = None
                    game.countdown_start_time = None
                    debug_log("Countdown cancelled - below minimum players", None, room_id,
                              {'player_count': len(game.players)})

                    # Hide countdown for remaining players
                    emit('countdown_cancelled', {
                        'message': 'Countdown cancelled - need more players'
                    }, room=room_id)

        # Broadcast updated room list to all clients
        broadcast_room_list()
