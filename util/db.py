# Database utility module for Pixel Plagiarist
import sqlite3
import os
import threading
from contextlib import contextmanager
from util.logging_utils import debug_log
from util.config import CONSTANTS

# Database file path
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'pixel_plagiarist.db')

# Thread-local storage for database connections
_local = threading.local()


def get_db_connection():
    """
    Get a database connection for the current thread.
    
    Returns
    -------
    sqlite3.Connection
        Database connection with row factory enabled
    """
    if not hasattr(_local, 'connection'):
        _local.connection = sqlite3.connect(DB_PATH)
        _local.connection.row_factory = sqlite3.Row  # Enable column access by name
    return _local.connection


@contextmanager
def get_db():
    """
    Context manager for database operations.
    
    Yields
    ------
    sqlite3.Connection
        Database connection that will be automatically closed
    """
    conn = get_db_connection()
    try:
        yield conn
    except Exception as e:
        conn.rollback()
        debug_log("Database operation failed", None, None, {'error': str(e)})
        raise
    finally:
        conn.commit()


def initialize_database():
    """
    Initialize the database and create tables if they don't exist.
    
    This function is called once on server startup to ensure the database
    structure is properly set up. If tables exist with old schema, they will be dropped.
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Create players table with username as primary key
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    username TEXT PRIMARY KEY,
                    email TEXT,
                    balance INTEGER DEFAULT 1000,
                    games_played INTEGER DEFAULT 0,
                    total_winnings INTEGER DEFAULT 0,
                    total_losses INTEGER DEFAULT 0,
                    successful_originals INTEGER DEFAULT 0,
                    successful_copies INTEGER DEFAULT 0,
                    total_originals INTEGER DEFAULT 0,
                    total_copies INTEGER DEFAULT 0,
                    total_votes_cast INTEGER DEFAULT 0,
                    correct_votes INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create game_history_players table for player-specific game data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS game_history_players (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    player_id TEXT NOT NULL,
                    balance_before INTEGER NOT NULL,
                    balance_after INTEGER NOT NULL,
                    stake INTEGER NOT NULL,
                    points_earned INTEGER DEFAULT 0,
                    originals_drawn INTEGER DEFAULT 0,
                    copies_made INTEGER DEFAULT 0,
                    votes_cast INTEGER DEFAULT 0,
                    correct_votes INTEGER DEFAULT 0,
                    game_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (username) REFERENCES players (username)
                )
            ''')
            
            # Create game_history_drawings table for drawing set data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS game_history_drawings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id TEXT NOT NULL,
                    set_index INTEGER NOT NULL,
                    prompt TEXT NOT NULL,
                    original_player_username TEXT NOT NULL,
                    original_player_id TEXT NOT NULL,
                    first_copier_username TEXT,
                    second_copier_username TEXT,
                    first_copier_id TEXT,
                    second_copier_id TEXT,
                    original_votes INTEGER DEFAULT 0,
                    first_copy_votes INTEGER DEFAULT 0,
                    second_copy_votes INTEGER DEFAULT 0,
                    game_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_game_history_players_room_player ON '
                'game_history_players (room_id, player_id)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_game_history_players_username ON game_history_players (username)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_game_history_drawings_room_set ON '
                'game_history_drawings (room_id, set_index)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_game_history_drawings_room ON game_history_drawings (room_id)')
            
            debug_log("Database initialized successfully", None, None, {'db_path': DB_PATH})
            
    except Exception as e:
        debug_log("Failed to initialize database", None, None, {'error': str(e), 'db_path': DB_PATH})
        raise


def get_or_create_player(username, email=None):
    """
    Get an existing player or create a new one based on username.
    
    Parameters
    ----------
    username : str
        Player's display name (now the primary key)
    email : str, optional
        Player's email address
        
    Returns
    -------
    dict
        Player data including balance and statistics
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Try to get existing player by username
            cursor.execute('SELECT * FROM players WHERE username = ?', (username,))
            player = cursor.fetchone()
            
            if player:
                # Update last played timestamp
                cursor.execute('''
                    UPDATE players 
                    SET last_played = CURRENT_TIMESTAMP 
                    WHERE username = ?
                ''', (username,))
                
                debug_log("DB operation: Retrieved existing player", None, None, {
                    'username': username,
                    'balance': player['balance'],
                    'games_played': player['games_played']
                })
                
                return dict(player)
            else:
                # Create new player
                cursor.execute('''
                    INSERT INTO players (username, email, balance)
                    VALUES (?, ?, ?)
                ''', (username, email, CONSTANTS['INITIAL_BALANCE']))
                
                # Get the newly created player
                cursor.execute('SELECT * FROM players WHERE username = ?', (username,))
                player = cursor.fetchone()
                
                debug_log("DB operation: Created new player", None, None, {
                    'username': username,
                    'initial_balance': CONSTANTS['INITIAL_BALANCE']
                })
                
                return dict(player)
                
    except Exception as e:
        debug_log("DB operation: Failed to get or create player", None, None, {
            'error': str(e),
            'username': username
        })
        raise


def delete_player(username):
    """
    Delete a player from the database.

    Parameters
    ----------
    username : str
        Player's username

    Returns
    -------
    bool
        True if deletion was successful, False if player not found
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM players WHERE username = ?', (username,))

            if cursor.rowcount > 0:
                debug_log("DB operation: Deleted player", None, None, {'username': username})
                return True
            else:
                debug_log("DB operation: Player not found for deletion", None, None, {'username': username})
                return False

    except Exception as e:
        debug_log("DB operation: Failed to delete player", None, None, {
            'error': str(e),
            'username': username
        })
        return False


def update_player_balance(username, new_balance):
    """
    Update a player's balance in the database.
    
    Parameters
    ----------
    username : str
        Player's username
    new_balance : int
        New balance amount
        
    Returns
    -------
    bool
        True if update was successful
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE players 
                SET balance = ?, last_played = CURRENT_TIMESTAMP 
                WHERE username = ?
            ''', (new_balance, username))
            
            if cursor.rowcount > 0:
                debug_log("DB operation: Updated player balance", None, None, {
                    'username': username,
                    'new_balance': new_balance
                })
                return True
            else:
                debug_log("DB operation: Player not found for balance update", None, None, {
                    'username': username,
                    'new_balance': new_balance
                })
                return False
                
    except Exception as e:
        debug_log("DB operation: Failed to update player balance", None, None, {
            'error': str(e),
            'username': username,
            'new_balance': new_balance
        })
        return False


def record_player_game_completion(username, player_id, room_id, balance_before, balance_after, stake, 
                                 points_earned=0, originals_drawn=0, copies_made=0, votes_cast=0, correct_votes=0):
    """
    Record a completed game for a specific player.
    
    Parameters
    ----------
    username : str
        Player's username
    player_id : str
        Player ID for the game
    room_id : str
        Game room identifier
    balance_before : int
        Balance before the game
    balance_after : int
        Balance after the game
    stake : int
        Amount wagered in the game
    points_earned : int, optional
        Points earned in the game
    originals_drawn : int, optional
        Number of original drawings created
    copies_made : int, optional
        Number of copies created
    votes_cast : int, optional
        Number of votes cast
    correct_votes : int, optional
        Number of correct votes cast
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Record player-specific game history in new table
            cursor.execute('''
                INSERT INTO game_history_players 
                (room_id, username, player_id, balance_before, balance_after, stake,
                 points_earned, originals_drawn, copies_made, votes_cast, correct_votes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (room_id, username, player_id, balance_before, balance_after, stake,
                  points_earned, originals_drawn, copies_made, votes_cast, correct_votes))
            
            # Record legacy game history for backward compatibility
            cursor.execute('''
                INSERT INTO game_history 
                (room_id, username, balance_before, balance_after, stake,
                 points_earned, originals_drawn, copies_made, votes_cast, correct_votes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (room_id, username, balance_before, balance_after, stake,
                  points_earned, originals_drawn, copies_made, votes_cast, correct_votes))
            
            # Update player statistics
            winnings = max(0, balance_after - balance_before)
            losses = max(0, balance_before - balance_after)
            
            cursor.execute('''
                UPDATE players SET
                    games_played = games_played + 1,
                    total_winnings = total_winnings + ?,
                    total_losses = total_losses + ?,
                    successful_originals = successful_originals + ?,
                    successful_copies = successful_copies + ?,
                    total_originals = total_originals + ?,
                    total_copies = total_copies + ?,
                    total_votes_cast = total_votes_cast + ?,
                    correct_votes = correct_votes + ?,
                    balance = ?,
                    last_played = CURRENT_TIMESTAMP
                WHERE username = ?
            ''', (winnings, losses, 
                  1 if originals_drawn > 0 and points_earned > 0 else 0,  # Successful original (earned points)
                  1 if copies_made > 0 and points_earned > 0 else 0,      # Successful copy (earned points)
                  originals_drawn, copies_made, votes_cast, correct_votes,
                  balance_after, username))
            
            debug_log("DB operation: Recorded player game completion", None, room_id, {
                'username': username,
                'player_id': player_id,
                'balance_change': balance_after - balance_before,
                'points_earned': points_earned,
                'stake': stake
            })
            
    except Exception as e:
        debug_log("DB operation: Failed to record player game completion", None, room_id, {
            'error': str(e),
            'username': username,
            'player_id': player_id
        })
        raise


def record_drawing_sets_data(room_id, drawing_sets, votes, players, player_prompts):
    """
    Record drawing set data for a completed game.
    
    Parameters
    ----------
    room_id : str
        Game room identifier
    drawing_sets : list
        Drawing sets data for the game
    votes : dict
        Vote data indexed by set
    players : dict
        Player information
    player_prompts : dict
        Prompts assigned to each player
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Record drawing set data
            for set_index, drawing_set in enumerate(drawing_sets):
                original_id = drawing_set['original_id']
                original_username = players.get(original_id, {}).get('username', 'Unknown')
                original_prompt = player_prompts.get(original_id, 'Unknown')

                # Find copiers
                copiers = []
                copier_ids = []
                for drawing in drawing_set['drawings']:
                    if drawing['type'] == 'copy':
                        copier_username = players.get(drawing['player_id'], {}).get('username', 'Unknown')
                        copiers.append(copier_username)
                        copier_ids.append(drawing['player_id'])

                # Pad copiers list to exactly 2 entries
                while len(copiers) < 2:
                    copiers.append(None)
                    copier_ids.append(None)

                # Count votes for each drawing
                set_votes = votes.get(set_index, {})
                vote_counts = {}

                for drawing in drawing_set['drawings']:
                    drawing_id = drawing['id']
                    vote_counts[drawing_id] = sum(1 for vote in set_votes.values() if vote == drawing_id)

                # Get vote counts (original first, then copies in order)
                original_drawing_id = f"original_{original_id}"
                original_votes = vote_counts.get(original_drawing_id, 0)

                copy_votes = []
                for drawing in drawing_set['drawings']:
                    if drawing['type'] == 'copy':
                        copy_votes.append(vote_counts.get(drawing['id'], 0))

                # Pad copy votes to exactly 2 entries
                while len(copy_votes) < 2:
                    copy_votes.append(0)

                cursor.execute('''
                    INSERT INTO game_history_drawings 
                    (room_id, set_index, prompt, original_player_username, original_player_id,
                     first_copier_username, second_copier_username, first_copier_id, second_copier_id,
                     original_votes, first_copy_votes, second_copy_votes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (room_id, set_index, original_prompt, original_username, original_id,
                      copiers[0], copiers[1], copier_ids[0], copier_ids[1],
                      original_votes, copy_votes[0], copy_votes[1]))
            
            debug_log("DB operation: Recorded drawing sets data", None, room_id, {
                'drawing_sets_recorded': len(drawing_sets)
            })
            
    except Exception as e:
        debug_log("DB operation: Failed to record drawing sets data", None, room_id, {
            'error': str(e)
        })
        raise


def record_game_completion(username, room_id, balance_before, balance_after, stake, points_earned=0, originals_drawn=0,
                           copies_made=0, votes_cast=0, correct_votes=0, player_id=None, drawing_sets=None, 
                           votes=None, players=None, player_prompts=None):
    """
    Record a completed game for a player and optionally record drawing set data for the entire game.
    
    This function is kept for backward compatibility. For new code, prefer using
    record_player_game_completion and record_drawing_sets_data separately.
    
    Parameters
    ----------
    username : str
        Player's username
    room_id : str
        Game room identifier
    balance_before : int
        Balance before the game
    balance_after : int
        Balance after the game
    stake : int
        Amount wagered in the game
    points_earned : int, optional
        Points earned in the game
    originals_drawn : int, optional
        Number of original drawings created
    copies_made : int, optional
        Number of copies created
    votes_cast : int, optional
        Number of votes cast
    correct_votes : int, optional
        Number of correct votes cast
    player_id : str, optional
        Player ID for the new table
    drawing_sets : list, optional
        Drawing sets data for the game (only pass for one player to avoid duplicates)
    votes : dict, optional
        Vote data indexed by set (only pass for one player to avoid duplicates)
    players : dict, optional
        Player information (only pass for one player to avoid duplicates)
    player_prompts : dict, optional
        Prompts assigned to each player (only pass for one player to avoid duplicates)
    """
    # Record player data if player_id is provided
    if player_id:
        record_player_game_completion(
            username=username,
            player_id=player_id,
            room_id=room_id,
            balance_before=balance_before,
            balance_after=balance_after,
            stake=stake,
            points_earned=points_earned,
            originals_drawn=originals_drawn,
            copies_made=copies_made,
            votes_cast=votes_cast,
            correct_votes=correct_votes
        )
    
    # Record drawing set data if all required data is provided
    if drawing_sets and votes is not None and players and player_prompts:
        record_drawing_sets_data(
            room_id=room_id,
            drawing_sets=drawing_sets,
            votes=votes,
            players=players,
            player_prompts=player_prompts
        )