# Game state management for socket handlers
import uuid
from flask_socketio import emit
from game_logic import GameStateGL
from util.logging_utils import debug_log
from util.config import CONSTANTS


class GameStateSH:
    """Centralized game state management for socket handlers"""
    
    def __init__(self):
        self.GAMES = {}
        self.PLAYERS = {}
    
    def get_game(self, room_id):
        """Get game instance by room ID"""
        return self.GAMES.get(room_id)
    
    def get_player_room(self, player_id):
        """Get room ID for a player"""
        return self.PLAYERS.get(player_id)
    
    def add_game(self, room_id, game):
        """Add a new game to the state"""
        self.GAMES[room_id] = game
    
    def remove_game(self, room_id):
        """Remove a game from the state"""
        if room_id in self.GAMES:
            del self.GAMES[room_id]
    
    def add_player(self, player_id, room_id):
        """Add player to room tracking"""
        self.PLAYERS[player_id] = room_id
    
    def remove_player(self, player_id):
        """Remove player from tracking"""
        if player_id in self.PLAYERS:
            del self.PLAYERS[player_id]
    
    def get_all_games(self):
        """Get all games"""
        return self.GAMES
    
    def ensure_default_room(self):
        """Ensure there's always at least one Bronze level room available"""
        # Check if there's already a waiting Bronze room
        has_waiting_bronze_room = False

        for room_id, game in self.GAMES.items():
            if (game.prize_per_player == CONSTANTS['MIN_STAKE'] and
                    game.phase == "waiting" and
                    len(game.players) < game.max_players):
                has_waiting_bronze_room = True
                break

        if not has_waiting_bronze_room:
            # Create a new Bronze room
            room_id = str(uuid.uuid4())[:8].upper()
            new_game = GameStateGL(room_id, CONSTANTS['MIN_STAKE'])
            self.GAMES[room_id] = new_game
            debug_log("Created guaranteed Bronze room", None, room_id, {'stake': CONSTANTS['MIN_STAKE']})
            return room_id

        return None

    def check_and_create_default_room(self, socketio=None):
        """Check if we need to create a new default room after a game starts"""
        new_room_id = self.ensure_default_room()
        if new_room_id:
            # Broadcast the new room to all clients
            broadcast_room_list(socketio, self)
            return new_room_id
        return None


# Global game state instance
GAME_STATE_SH = GameStateSH()


def get_room_info(game_state_sh=GAME_STATE_SH):
    """
    Get information about all available rooms.
    
    Parameters
    ----------
    game_state_sh : GameState, optional
        Game state instance to use, defaults to global instance
        
    Returns
    -------
    list
        List of room information dictionaries
    """
    rooms = []
    for room_id, game in game_state_sh.get_all_games().items():
        # Only include rooms in waiting phase
        if game.phase != "waiting":
            continue

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
            'room_level': game.room_level(),
            'phase': game.phase,
            'created_at': game.created_at.isoformat(),
            'players': player_details  # Add player details for AI filtering
        }
        rooms.append(room_info)

    # Sort by creation time (newest first)
    rooms.sort(key=lambda x: x['created_at'], reverse=True)
    return rooms


def broadcast_room_list(socketio=None, game_state_sh=GAME_STATE_SH):
    """Broadcast updated room list to all clients on home screen."""
    rooms = get_room_info(game_state_sh)
    if socketio:
        # Use the provided socketio instance when called from background threads
        socketio.emit('room_list_updated', {'rooms': rooms})
    else:
        # Use the regular emit when called from within a request context
        emit('room_list_updated', {'rooms': rooms})