# Databasing

## Overview
Pixel Plagiarist persists player accounts, per‑game outcomes, and per‑drawing‑set results in a lightweight SQLite database. This keeps setup simple for local development and small deployments while providing structured data for stats and history.

## Engine & Location
- Engine: SQLite (bundled with Python)
- Database file: pixel_plagiarist.db at the project root
  - Path is computed in util/db.py as DB_PATH using the util directory as a reference

## Connection & Transactions
- Thread‑local connections via util.db.get_db_connection() (one connection per thread, sqlite3.Row row_factory for name‑based column access)
- Use util.db.get_db() as a context manager to automatically commit on success or rollback on exceptions and to ensure consistent logging

## Initialization
- util.db.initialize_database() creates tables and indexes if they do not exist.
- Called on server startup (see server.py). It is safe to run multiple times.

## Schema (high‑level)
1) players
   - username TEXT PRIMARY KEY
   - email TEXT
   - balance INTEGER DEFAULT 1000
   - games_played, total_winnings, total_losses
   - successful_originals, successful_copies
   - total_originals, total_copies, total_votes_cast, correct_votes
   - created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   - last_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP

2) game_history_players (one row per player per completed game)
   - id INTEGER PRIMARY KEY AUTOINCREMENT
   - room_id TEXT, username TEXT (FK -> players.username), player_id TEXT
   - balance_before, balance_after, stake
   - points_earned, originals_drawn, copies_made, votes_cast, correct_votes
   - game_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   - Indexes: (room_id, player_id) and (username)

3) game_history_drawings (one row per drawing set in a game)
   - id INTEGER PRIMARY KEY AUTOINCREMENT
   - room_id TEXT, set_index INTEGER, prompt TEXT
   - original_player_username TEXT, original_player_id TEXT
   - first_copier_username TEXT, second_copier_username TEXT
   - first_copier_id TEXT, second_copier_id TEXT
   - original_votes INTEGER, first_copy_votes INTEGER, second_copy_votes INTEGER
   - game_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   - Indexes: (room_id, set_index) and (room_id)

Legacy note: record_player_game_completion also writes to a legacy table game_history for backward compatibility. That table may exist from older versions; new analytics should rely on game_history_players and game_history_drawings.

## How data is recorded
- Creating or fetching a player: util.db.get_or_create_player(username, email=None)
- Updating balance: util.db.update_player_balance(username, new_balance)
- Recording one player's completion of a game (and updating aggregated stats):
  - util.db.record_player_game_completion(...)
- Recording drawing‑set level results for an entire game (prompts, authors, copiers, votes):
  - util.db.record_drawing_sets_data(...)
- Compatibility wrapper that can do both when provided all data:
  - util.db.record_game_completion(...)

## Configuration touchpoints
- INITIAL_BALANCE comes from util.config.CONSTANTS['INITIAL_BALANCE'] and is used when creating new players.

## Maintenance tips
- Inspect the database (from project root):
  - sqlite3 pixel_plagiarist.db
  - .tables to list tables; PRAGMA table_info(players); to inspect columns
- Back up the database:
  - Make a copy of pixel_plagiarist.db while the server is stopped
- Reset (developer only):
  - Stop the server, delete pixel_plagiarist.db, then restart; initialize_database() will re‑create schema (data will be lost)
- Migrations:
  - The current code creates tables if missing and maintains indexes. If schema changes are needed, add migration scripts or extend initialize_database() with careful backward‑compatibility handling.

