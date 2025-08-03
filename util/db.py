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
    structure is properly set up.
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Create players table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
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
            
            # Create game_history table for detailed game tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS game_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id TEXT NOT NULL,
                    player_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    balance_before INTEGER NOT NULL,
                    balance_after INTEGER NOT NULL,
                    stake INTEGER NOT NULL,
                    points_earned INTEGER DEFAULT 0,
                    originals_drawn INTEGER DEFAULT 0,
                    copies_made INTEGER DEFAULT 0,
                    votes_cast INTEGER DEFAULT 0,
                    correct_votes INTEGER DEFAULT 0,
                    game_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (player_id) REFERENCES players (id)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_players_username ON players (username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_game_history_player ON game_history (player_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_game_history_room ON game_history (room_id)')
            
            debug_log("Database initialized successfully", None, None, {'db_path': DB_PATH})
            
    except Exception as e:
        debug_log("Failed to initialize database", None, None, {'error': str(e), 'db_path': DB_PATH})
        raise


def get_or_create_player(player_id, username, email=None):
    """
    Get an existing player or create a new one.
    
    Parameters
    ----------
    player_id : str
        Unique player identifier
    username : str
        Player's display name
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
            
            # Try to get existing player
            cursor.execute('SELECT * FROM players WHERE id = ?', (player_id,))
            player = cursor.fetchone()
            
            if player:
                # Update last played timestamp and username (in case it changed)
                cursor.execute('''
                    UPDATE players 
                    SET username = ?, last_played = CURRENT_TIMESTAMP 
                    WHERE id = ?
                ''', (username, player_id))
                
                debug_log("Retrieved existing player", player_id, None, {
                    'username': username,
                    'balance': player['balance'],
                    'games_played': player['games_played']
                })
                
                return dict(player)
            else:
                # Create new player
                cursor.execute('''
                    INSERT INTO players (id, username, email, balance)
                    VALUES (?, ?, ?, ?)
                ''', (player_id, username, email, CONSTANTS['INITIAL_BALANCE']))
                
                # Get the newly created player
                cursor.execute('SELECT * FROM players WHERE id = ?', (player_id,))
                player = cursor.fetchone()
                
                debug_log("Created new player", player_id, None, {
                    'username': username,
                    'initial_balance': CONSTANTS['INITIAL_BALANCE']
                })
                
                return dict(player)
                
    except Exception as e:
        debug_log("Failed to get or create player", player_id, None, {
            'error': str(e),
            'username': username
        })
        raise


def update_player_balance(player_id, new_balance):
    """
    Update a player's balance in the database.
    
    Parameters
    ----------
    player_id : str
        Player identifier
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
                WHERE id = ?
            ''', (new_balance, player_id))
            
            if cursor.rowcount > 0:
                debug_log("Updated player balance", player_id, None, {
                    'new_balance': new_balance
                })
                return True
            else:
                debug_log("Player not found for balance update", player_id, None, {
                    'new_balance': new_balance
                })
                return False
                
    except Exception as e:
        debug_log("Failed to update player balance", player_id, None, {
            'error': str(e),
            'new_balance': new_balance
        })
        return False


def record_game_completion(player_id, room_id, username, balance_before, balance_after, 
                           stake, points_earned=0, originals_drawn=0, copies_made=0,
                           votes_cast=0, correct_votes=0):
    """
    Record a completed game for a player.
    
    Parameters
    ----------
    player_id : str
        Player identifier
    room_id : str
        Game room identifier
    username : str
        Player's username
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
            
            # Record game history
            cursor.execute('''
                INSERT INTO game_history 
                (room_id, player_id, username, balance_before, balance_after, stake,
                 points_earned, originals_drawn, copies_made, votes_cast, correct_votes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (room_id, player_id, username, balance_before, balance_after, stake,
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
                WHERE id = ?
            ''', (winnings, losses, 
                  1 if originals_drawn > 0 and points_earned > 0 else 0,  # Successful original (earned points)
                  1 if copies_made > 0 and points_earned > 0 else 0,      # Successful copy (earned points)
                  originals_drawn, copies_made, votes_cast, correct_votes,
                  balance_after, player_id))
            
            debug_log("Recorded game completion", player_id, room_id, {
                'username': username,
                'balance_change': balance_after - balance_before,
                'points_earned': points_earned,
                'stake': stake
            })
            
    except Exception as e:
        debug_log("Failed to record game completion", player_id, room_id, {
            'error': str(e),
            'username': username
        })
        raise


def get_player_stats(player_id):
    """
    Get comprehensive statistics for a player.
    
    Parameters
    ----------
    player_id : str
        Player identifier
        
    Returns
    -------
    dict or None
        Player statistics or None if player not found
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM players WHERE id = ?', (player_id,))
            player = cursor.fetchone()
            
            if player:
                return dict(player)
            return None
            
    except Exception as e:
        debug_log("Failed to get player stats", player_id, None, {'error': str(e)})
        return None


def get_leaderboard(limit=50):
    """
    Get leaderboard data for top players.
    
    Parameters
    ----------
    limit : int, optional
        Maximum number of players to return
        
    Returns
    -------
    list
        List of player dictionaries sorted by performance metrics
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    username,
                    balance,
                    games_played,
                    total_winnings,
                    total_losses,
                    successful_originals,
                    successful_copies,
                    total_originals,
                    total_copies,
                    correct_votes,
                    total_votes_cast,
                    CASE 
                        WHEN games_played > 0 THEN CAST(total_winnings AS FLOAT) / games_played 
                        ELSE 0 
                    END as avg_winnings_per_game,
                    CASE 
                        WHEN total_originals > 0 THEN CAST(successful_originals AS FLOAT) / total_originals * 100 
                        ELSE 0 
                    END as original_success_rate,
                    CASE 
                        WHEN total_copies > 0 THEN CAST(successful_copies AS FLOAT) / total_copies * 100 
                        ELSE 0 
                    END as copy_success_rate,
                    CASE 
                        WHEN total_votes_cast > 0 THEN CAST(correct_votes AS FLOAT) / total_votes_cast * 100 
                        ELSE 0 
                    END as vote_accuracy
                FROM players 
                WHERE games_played > 0
                ORDER BY balance DESC, total_winnings DESC, games_played DESC
                LIMIT ?
            ''', (limit,))
            
            players = cursor.fetchall()
            return [dict(player) for player in players]
            
    except Exception as e:
        debug_log("Failed to get leaderboard", None, None, {'error': str(e)})
        return []


def cleanup_old_game_history(days_old=30):
    """
    Clean up old game history records to prevent database bloat.
    
    Parameters
    ----------
    days_old : int, optional
        Number of days of history to keep
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM game_history 
                WHERE game_date < datetime('now', '-{} days')
            '''.format(days_old))
            
            deleted_count = cursor.rowcount
            debug_log("Cleaned up old game history", None, None, {
                'deleted_records': deleted_count,
                'days_old': days_old
            })
            
    except Exception as e:
        debug_log("Failed to cleanup old game history", None, None, {'error': str(e)})


def close_connections():
    """Close all database connections for the current thread."""
    if hasattr(_local, 'connection'):
        _local.connection.close()
        delattr(_local, 'connection')