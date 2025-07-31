# Socket.IO event handlers for Pixel Plagiarist
import uuid
from flask import request
from flask_socketio import emit, join_room, leave_room
from game_logic import PixelPlagiarist
from config import TIMER_CONFIG
from logging_utils import debug_log

# Global game state
GAMES = {}
PLAYERS = {}


def get_room_info():
    """
    Get information about all available rooms.
    
    Returns
    -------
    list
        List of room information dictionaries
    """
    rooms = []
    for room_id, game in GAMES.items():
        # Include player details to help AI players identify human vs AI players
        player_details = []
        for player_id, player_data in game.players.items():
            player_details.append({
                'id': player_id,
                'username': player_data['username']
            })

        room_info = {
            'room_id': room_id,
            'player_count': len(game.players),
            'max_players': game.max_players,
            'min_stake': game.min_stake,
            'phase': game.phase,
            'created_at': game.created_at.isoformat(),
            'players': player_details  # Add player details for AI filtering
        }
        rooms.append(room_info)

    # Sort by creation time (newest first)
    rooms.sort(key=lambda x: x['created_at'], reverse=True)
    return rooms


def broadcast_room_list(socketio=None):
    """Broadcast updated room list to all clients on home screen."""
    rooms = get_room_info()
    if socketio:
        # Use the provided socketio instance when called from background threads
        socketio.emit('room_list_updated', {'rooms': rooms})
    else:
        # Use the regular emit when called from within a request context
        emit('room_list_updated', {'rooms': rooms})


def setup_socket_handlers(socketio):
    """
    Set up all Socket.IO event handlers.
    
    Parameters
    ----------
    socketio : SocketIO
        The Flask-SocketIO instance to register handlers with
    """

    @socketio.on('connect')
    def handle_connect():
        """Handle new client connection"""
        # Send current room list to newly connected client
        rooms = get_room_info()
        emit('room_list_updated', {'rooms': rooms})
        
        # If no rooms exist, create a default $10 room
        if not rooms:
            try:
                new_room_id = ensure_default_room()
                if new_room_id:
                    debug_log("Created default room on client connect", None, new_room_id, {'min_stake': 10})
                    # Send updated room list with the new room
                    updated_rooms = get_room_info()
                    emit('room_list_updated', {'rooms': updated_rooms})
            except Exception as e:
                debug_log("Failed to create default room on connect", None, None, {'error': str(e)})

    @socketio.on('request_room_list')
    def handle_request_room_list(data=None):
        """Handle request for current room list"""
        rooms = get_room_info()
        emit('room_list_updated', {'rooms': rooms})

    @socketio.on('create_room')
    def handle_create_room(data):
        """Handle room creation request"""
        username = data.get('username', 'Anonymous')
        player_id = request.sid
        min_stake = data.get('min_stake', 10)

        # Generate unique room code
        room_id = str(uuid.uuid4())[:8].upper()

        # Create new game
        GAMES[room_id] = PixelPlagiarist(room_id, min_stake)

        # Add player to game and room
        if GAMES[room_id].add_player(player_id, username):
            PLAYERS[player_id] = room_id
            join_room(room_id)

            emit('room_created', {
                'room_id': room_id,
                'success': True,
                'message': f'Room {room_id} created successfully!'
            })

            # Check if we should start countdown or game
            game = GAMES[room_id]
            if len(game.players) >= game.min_players and game.phase == "waiting":
                if len(game.players) >= game.max_players:
                    debug_log("Starting game immediately - max players reached", None, room_id,
                              {'player_count': len(game.players)})
                    game.start_game(socketio)
                elif game.timer.start_timer is None:
                    debug_log("Starting countdown - min players reached", None, room_id,
                              {'player_count': len(game.players)})
                    game.start_countdown(socketio)

            # Broadcast player list update
            emit('players_updated', {
                'players': list(GAMES[room_id].players.values()),
                'count': len(GAMES[room_id].players)
            }, room=room_id)

            # Broadcast updated room list to all clients
            broadcast_room_list()
        else:
            emit('room_created', {
                'success': False,
                'message': 'Failed to create room'
            })

    @socketio.on('join_room')
    def handle_join_room(data):
        """Handle room join request"""
        room_id = data.get('room_id', '').upper()
        username = data.get('username', 'Anonymous')
        player_id = request.sid

        if room_id in GAMES:
            game = GAMES[room_id]

            # First check if we can add the player
            if len(game.players) >= game.max_players:
                emit('join_room_error', {
                    'success': False,
                    'message': 'Room is full or unavailable'
                })
                return

            # Join the room first
            PLAYERS[player_id] = room_id
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
                        game.start_game(socketio)
                    elif game.timer.start_timer is None:
                        debug_log("Starting countdown - min players reached", None, room_id,
                                  {'player_count': len(game.players)})
                        game.start_countdown(socketio)
                    else:
                        # If countdown is already running, send the current countdown state to the new player
                        import time
                        if hasattr(game, 'countdown_start_time'):
                            elapsed = time.time() - game.countdown_start_time
                            remaining = max(0, TIMER_CONFIG['countdown'] - int(elapsed))
                            if remaining > 0:
                                debug_log("Sending countdown state to late joiner", player_id, room_id,
                                          {'remaining_seconds': remaining})
                                emit('countdown_started', {'seconds': remaining}, to=player_id)

                # Broadcast player list update
                emit('players_updated', {
                    'players': list(game.players.values()),
                    'count': len(game.players)
                }, room=room_id)

                # Broadcast updated room list to all clients
                broadcast_room_list()
            else:
                # If adding failed, remove from players dict
                del PLAYERS[player_id]
                emit('join_room_error', {
                    'success': False,
                    'message': 'Failed to join room'
                })
        else:
            emit('join_room_error', {
                'success': False,
                'message': 'Room not found'
            })

    @socketio.on('place_bet')
    def handle_place_bet(data):
        """Handle betting"""
        player_id = request.sid
        stake = data.get('stake', 10)

        if player_id in PLAYERS:
            room_id = PLAYERS[player_id]
            if room_id in GAMES:
                GAMES[room_id].place_bet(player_id, stake, socketio)

    @socketio.on('submit_drawing')
    def handle_submit_drawing(data):
        """Handle drawing submission"""
        player_id = request.sid
        drawing_data = data.get('drawing_data')

        if player_id in PLAYERS and drawing_data:
            room_id = PLAYERS[player_id]
            if room_id in GAMES:
                GAMES[room_id].submit_original_drawing(player_id, drawing_data, socketio)

    @socketio.on('submit_copy')
    def handle_submit_copy(data):
        """Handle copy submission"""
        player_id = request.sid
        target_id = data.get('target_id')
        drawing_data = data.get('drawing_data')

        if player_id in PLAYERS and target_id and drawing_data:
            room_id = PLAYERS[player_id]
            if room_id in GAMES:
                GAMES[room_id].submit_copied_drawing(player_id, target_id, drawing_data, socketio)

    @socketio.on('submit_vote')
    def handle_submit_vote(data):
        """Handle vote submission"""
        player_id = request.sid
        drawing_id = data.get('drawing_id')

        if player_id in PLAYERS and drawing_id:
            room_id = PLAYERS[player_id]
            if room_id in GAMES:
                GAMES[room_id].submit_vote(player_id, drawing_id, socketio)

    @socketio.on('request_review')
    def handle_request_review(data):
        """Handle review request"""
        player_id = request.sid
        target_id = data.get('target_id')

        if player_id in PLAYERS and target_id:
            room_id = PLAYERS[player_id]
            if room_id in GAMES:
                game = GAMES[room_id]
                if target_id in game.original_drawings:
                    # Send the original drawing for 5-second review
                    emit('review_drawing', {
                        'drawing': game.original_drawings[target_id],
                        'duration': 5000  # 5 seconds in milliseconds
                    }, to=player_id)

    @socketio.on('flag_image')
    def handle_flag_image(data):
        """Handle image flagging for inappropriate content"""
        player_id = request.sid
        drawing_id = data.get('drawing_id')
        phase = data.get('phase', 'unknown')

        if player_id in PLAYERS:
            room_id = PLAYERS[player_id]
            if room_id in GAMES:
                game = GAMES[room_id]
                reporter_username = game.players.get(player_id, {}).get('username', 'Unknown')

                # Find the drawing and its creator
                drawing_data = None
                drawer_id = None
                drawer_username = 'Unknown'

                # Check in original drawings
                if drawing_id.startswith('original_'):
                    original_player_id = drawing_id.replace('original_', '')
                    drawing_data = game.original_drawings.get(original_player_id)
                    drawer_id = original_player_id
                    drawer_username = game.players.get(original_player_id, {}).get('username', 'Unknown')

                # Check in copied drawings
                elif drawing_id.startswith('copy_'):
                    # Format: copy_{copier_id}_{target_id}
                    parts = drawing_id.replace('copy_', '').split('_')
                    if len(parts) >= 2:
                        copier_id = parts[0]
                        target_id = parts[1]
                        drawing_data = game.copied_drawings.get(copier_id, {}).get(target_id)
                        drawer_id = copier_id
                        drawer_username = game.players.get(copier_id, {}).get('username', 'Unknown')

                if drawing_data and drawer_id:
                    # Log the flagged image
                    from game_logging import log_flagged_image
                    log_flagged_image(
                        room_id=room_id,
                        image_data=drawing_data,
                        drawer_username=drawer_username,
                        drawer_id=drawer_id,
                        reporter_username=reporter_username,
                        reporter_id=player_id,
                        phase=phase
                    )

                    emit('image_flagged', {
                        'success': True,
                        'message': 'Image has been flagged and will be reviewed'
                    }, to=player_id)
                else:
                    emit('image_flagged', {
                        'success': False,
                        'message': 'Could not find the specified image'
                    }, to=player_id)

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle player disconnect"""
        player_id = request.sid

        if player_id in PLAYERS:
            room_id = PLAYERS[player_id]
            del PLAYERS[player_id]

            if room_id in GAMES:
                GAMES[room_id].remove_player(player_id)

                # Clean up empty games
                if len(GAMES[room_id].players) == 0:
                    debug_log("Room is empty after disconnect, deleting", None, room_id)
                    del GAMES[room_id]
                    
                    # After deleting a room, ensure there's still a default $10 room available
                    new_room_id = ensure_default_room()
                    if new_room_id:
                        debug_log("Created replacement default room after disconnect deletion", None, new_room_id, {'min_stake': 10})
                    
                    # Broadcast updated room list when room is deleted
                    broadcast_room_list()
                else:
                    # Broadcast updated player list
                    emit('players_updated', {
                        'players': list(GAMES[room_id].players.values()),
                        'count': len(GAMES[room_id].players)
                    }, room=room_id)

                    # Broadcast updated room list when player count changes
                    broadcast_room_list()

    @socketio.on('leave_room')
    def handle_leave_room(data=None):
        """Handle player leaving a room"""
        player_id = request.sid

        if player_id not in PLAYERS:
            emit('room_left', {
                'success': False,
                'message': 'You are not in a room'
            })
            return

        room_id = PLAYERS[player_id]

        if room_id not in GAMES:
            # Clean up orphaned player reference
            del PLAYERS[player_id]
            emit('room_left', {
                'success': False,
                'message': 'Room no longer exists'
            })
            return

        game = GAMES[room_id]

        # Only allow leaving during waiting phase
        if game.phase != "waiting":
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
        del PLAYERS[player_id]
        leave_room(room_id)

        # Notify the leaving player
        emit('room_left', {
            'success': True,
            'message': 'You have left the room'
        })

        # Check if room is now empty and should be deleted
        if len(game.players) == 0:
            debug_log("Room is empty, deleting", None, room_id)
            del GAMES[room_id]
            
            # After deleting a room, ensure there's still a default $10 room available
            new_room_id = ensure_default_room()
            if new_room_id:
                debug_log("Created replacement default room after deletion", None, new_room_id, {'min_stake': 10})
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


def ensure_default_room():
    """Ensure there's always at least one $10 minimum room available"""
    # Check if there's already a waiting $10 room
    has_waiting_ten_dollar_room = False

    for room_id, game in GAMES.items():
        if (game.min_stake == 10 and
                game.phase == "waiting" and
                len(game.players) < game.max_players):
            has_waiting_ten_dollar_room = True
            break

    if not has_waiting_ten_dollar_room:
        # Create a new $10 room
        room_id = str(uuid.uuid4())[:8].upper()
        new_game = PixelPlagiarist(room_id, 10)
        GAMES[room_id] = new_game
        debug_log("Created guaranteed $10 room", None, room_id, {'min_stake': 10})
        return room_id

    return None


def check_and_create_default_room(socketio=None):
    """Check if we need to create a new default room after a game starts"""
    new_room_id = ensure_default_room()
    if new_room_id:
        # Broadcast the new room to all clients
        broadcast_room_list(socketio)
        return new_room_id
    return None
