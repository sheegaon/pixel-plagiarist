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
            
            # Check if we need to recreate tables (if players table exists with old schema)
            cursor.execute("PRAGMA table_info(players)")
            columns = cursor.fetchall()
            
            # Check if 'id' column exists (old schema)
            has_id_column = any(col[1] == 'id' for col in columns)
            has_username_as_pk = any(col[1] == 'username' and col[5] == 1 for col in columns)
            
            if has_id_column and not has_username_as_pk:
                debug_log("Dropping existing tables with old schema", None, None)
                # Drop existing tables to recreate with new schema
                cursor.execute("DROP TABLE IF EXISTS game_history")
                cursor.execute("DROP TABLE IF EXISTS players")
            
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
            
            # Create game_history table for detailed game tracking
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS game_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id TEXT NOT NULL,
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
                    FOREIGN KEY (username) REFERENCES players (username)
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_game_history_username ON game_history (username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_game_history_room ON game_history (room_id)')
            
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
                
                debug_log("Retrieved existing player", None, None, {
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
                
                debug_log("Created new player", None, None, {
                    'username': username,
                    'initial_balance': CONSTANTS['INITIAL_BALANCE']
                })
                
                return dict(player)
                
    except Exception as e:
        debug_log("Failed to get or create player", None, None, {
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
                debug_log("Deleted player", None, None, {'username': username})
                return True
            else:
                debug_log("Player not found for deletion", None, None, {'username': username})
                return False

    except Exception as e:
        debug_log("Failed to delete player", None, None, {
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
                debug_log("Updated player balance", None, None, {
                    'username': username,
                    'new_balance': new_balance
                })
                return True
            else:
                debug_log("Player not found for balance update", None, None, {
                    'username': username,
                    'new_balance': new_balance
                })
                return False
                
    except Exception as e:
        debug_log("Failed to update player balance", None, None, {
            'error': str(e),
            'username': username,
            'new_balance': new_balance
        })
        return False


def record_game_completion(username, room_id, balance_before, balance_after, stake, points_earned=0, originals_drawn=0,
                           copies_made=0, votes_cast=0, correct_votes=0):
    """
    Record a completed game for a player.
    
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
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Record game history
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
            
            debug_log("Recorded game completion", None, room_id, {
                'username': username,
                'balance_change': balance_after - balance_before,
                'points_earned': points_earned,
                'stake': stake
            })
            
    except Exception as e:
        debug_log("Failed to record game completion", None, room_id, {
            'error': str(e),
            'username': username
        })
        raise


def get_player_stats(username):
    """
    Get comprehensive statistics for a player.
    
    Parameters
    ----------
    username : str
        Player's username
        
    Returns
    -------
    dict or None
        Player statistics or None if player not found
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM players WHERE username = ?', (username,))
            player = cursor.fetchone()
            
            if player:
                return dict(player)
            return None
            
    except Exception as e:
        debug_log("Failed to get player stats", None, None, {
            'error': str(e),
            'username': username
        })
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