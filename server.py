#!/usr/bin/env python3
"""
Pixel Plagiarist - Multiplayer Drawing Game Server
A real-time multiplayer drawing game where players draw originals, copy others' drawings, and vote.

This is the main entry point for the Pixel Plagiarist server.

Debug Mode
----------
Set TESTING_MODE=true as an environment variable to enable accelerated gameplay for testing:
- All timers reduced to 5 seconds (countdown, betting, drawing, copying, voting)
- Faster game progression for development and testing purposes
- Use 'heroku config:set TESTING_MODE=true' for Heroku deployments

Set DEBUG_MODE=true as an environment variable to enable detailed logging:
- Logs all user interactions (button clicks, drawing submissions, votes, etc.)
- Tracks game state changes and phase transitions
- Records player actions with timestamps and context
- Use 'heroku config:set DEBUG_MODE=true' for Heroku deployments
"""

import os
import json
from flask import Flask, render_template, session, redirect, url_for, request
from flask_socketio import SocketIO
from authlib.integrations.flask_client import OAuth

# Import our modular components
from util.config import CONSTANTS
from util.logging_utils import setup_logging
from socket_handlers import setup_socket_handlers
from socket_handlers.game_state import game_state_sh

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'pixel_plagiarist_secret_key')


# Load OAuth Configuration from JSON file
def load_oauth_config():
    """Load OAuth configuration from client secret JSON file"""
    try:
        # Find the client secret JSON file
        util_dir = os.path.join(os.path.dirname(__file__), 'util')
        json_files = [f for f in os.listdir(util_dir) if f.startswith('client_secret_') and f.endswith('.json')]

        if not json_files:
            print("No client secret JSON file found. OAuth will be disabled.")
            return None, None

        json_file = json_files[0]  # Use the first one found
        json_path = os.path.join(util_dir, json_file)

        with open(json_path, 'r') as f:
            config = json.load(f)

        # Extract client ID and secret from the JSON structure
        if 'installed' in config:
            client_id = config['installed']['client_id']
            client_secret = config['installed']['client_secret']
        elif 'web' in config:
            client_id = config['web']['client_id']
            client_secret = config['web']['client_secret']
        else:
            print("Invalid client secret JSON format. OAuth will be disabled.")
            return None, None

        print(f"OAuth configuration loaded from {json_file}")
        return client_id, client_secret

    except Exception as e:
        print(f"Error loading OAuth config: {e}. OAuth will be disabled.")
        return None, None


# Load OAuth credentials
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET = load_oauth_config()

# OAuth Configuration (only if credentials are available)
oauth = None
google = None
oauth_enabled = False

if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    try:
        app.config['GOOGLE_CLIENT_ID'] = GOOGLE_CLIENT_ID
        app.config['GOOGLE_CLIENT_SECRET'] = GOOGLE_CLIENT_SECRET

        oauth = OAuth(app)
        google = oauth.register(
            name='google',
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            server_metadata_url='https://accounts.google.com/.well-known/openid_configuration',
            client_kwargs={
                'scope': 'openid email profile'
            }
        )
        oauth_enabled = True
        print("Google OAuth initialized successfully")
    except Exception as e:
        print(f"Failed to initialize OAuth: {e}. Using username-only authentication.")
        oauth_enabled = False
else:
    print("OAuth credentials not found. Using username-only authentication.")

# Initialize Socket.IO
socketio = SocketIO(app, cors_allowed_origins="*")

# Set up logging
logger = setup_logging()

# Set up Socket.IO event handlers
setup_socket_handlers(socketio)


@app.route('/')
def index():
    """
    Serve the main game interface.
    
    Returns
    -------
    str
        Rendered HTML template for the game client interface
    """
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('index.html', user=session['user'])


@app.route('/login')
def login():
    """Serve the login page"""
    return render_template('login.html')


@app.route('/auth/google')
def google_auth():
    """Initiate Google OAuth login"""
    redirect_uri = url_for('google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@app.route('/auth/callback')
def google_callback():
    """Handle Google OAuth callback"""
    token = google.authorize_access_token()
    user_info = token.get('userinfo')

    if user_info:
        session['user'] = {
            'name': user_info.get('name'),
            'email': user_info.get('email'),
            'picture': user_info.get('picture')
        }
        return redirect(url_for('index'))

    return redirect(url_for('login'))


@app.route('/auth/username', methods=['POST'])
def username_auth():
    """Handle username-only authentication"""
    username = request.form.get('username', '').strip()

    if not username:
        return redirect(url_for('login'))

    # Create a session for username-only authentication
    session['user'] = {
        'name': username,
        'email': f"{username}@local",  # Fake email for consistency
        'picture': f"https://ui-avatars.com/api/?name={username}&background=4299e1&color=fff"  # Generated avatar
    }

    return redirect(url_for('index'))


@app.route('/logout')
def logout():
    """Logout user"""
    session.pop('user', None)
    return redirect(url_for('login'))


@app.route('/health')
def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    
    Returns
    -------
    dict
        Simple health status response
    """
    return {'status': 'healthy', 'service': 'pixel_plagiarist'}


@app.route('/util/config.json')
def serve_config():
    """Serve the configuration JSON file"""
    config_path = os.path.join(os.path.dirname(__file__), 'util', 'config.json')
    try:
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        return config_data
    except Exception as e:
        logger.error(f"Error serving config.json: {e}")
        return {'error': 'Configuration not found'}, 404


@app.route('/leaderboard')
def leaderboard():
    """Display the leaderboard page"""
    if 'user' not in session:
        return redirect(url_for('login'))

    # Read leaderboard data from game logs
    leaderboard_data = get_leaderboard_data()
    return render_template('leaderboard.html',
                           user=session['user'],
                           leaderboard=leaderboard_data)


def get_leaderboard_data():
    """
    Extract leaderboard data from game summary logs
    
    Returns
    -------
    list
        List of player statistics sorted by performance
    """
    import csv
    import os
    from collections import defaultdict

    log_file = os.path.join(os.path.dirname(__file__), 'logs', 'game_summary.csv')
    if not os.path.exists(log_file):
        return []

    player_stats = defaultdict(lambda: {
        'username': '',
        'games_played': 0,
        'total_drawings': 0,
        'successful_originals': 0,  # Originals that got votes
        'successful_copies': 0,  # Copies that fooled voters
        'correct_votes': 0,  # Votes that correctly identified originals
        'total_votes_cast': 0,
        'total_points': 0
    })

    try:
        with open(log_file, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            games_seen = set()
            for row in reader:
                game_key = f"{row['timestamp']}_{row['room_id']}"

                # Track unique games per player
                if game_key not in games_seen:
                    games_seen.add(game_key)

                # Original player stats
                original_id = row['original_player_id']
                original_username = row['original_player_username']
                original_votes = int(row['original_votes'] or 0)

                if original_id and original_username != 'Unknown':
                    stats = player_stats[original_id]
                    stats['username'] = original_username
                    stats['total_drawings'] += 1
                    if original_votes > 0:
                        stats['successful_originals'] += 1
                        stats['total_points'] += original_votes * 100

                # Copier stats
                for copier_col, votes_col in [
                    ('first_copier_username', 'first_copy_votes'),
                    ('second_copier_username', 'second_copy_votes')
                ]:
                    copier_username = row.get(copier_col, '')
                    copy_votes = int(row.get(votes_col, 0) or 0)

                    if copier_username and copier_username != '':
                        # We don't have copier IDs in the log, so use username as key
                        # This is not ideal but works for the leaderboard
                        copier_key = f"username_{copier_username}"
                        stats = player_stats[copier_key]
                        stats['username'] = copier_username
                        stats['total_drawings'] += 1
                        if copy_votes > 0:
                            stats['successful_copies'] += 1
                            stats['total_points'] += copy_votes * 150

            # Count games played per player (approximate)
            for player_key in player_stats:
                # Rough estimate: each player plays in about 1/3 of logged games
                player_stats[player_key]['games_played'] = max(1, len(games_seen) // 3)

    except Exception as e:
        print(f"Error reading leaderboard data: {e}")
        return []

    # Convert to list and calculate derived stats
    leaderboard_list = []
    for player_id, stats in player_stats.items():
        if stats['username']:  # Only include players with actual usernames
            # Calculate success rates
            original_success_rate = (stats['successful_originals'] / max(1, stats['total_drawings'])) * 100
            copy_success_rate = (stats['successful_copies'] / max(1, stats['total_drawings'])) * 100

            leaderboard_list.append({
                'username': stats['username'],
                'games_played': stats['games_played'],
                'total_drawings': stats['total_drawings'],
                'successful_originals': stats['successful_originals'],
                'successful_copies': stats['successful_copies'],
                'total_points': stats['total_points'],
                'original_success_rate': round(original_success_rate, 1),
                'copy_success_rate': round(copy_success_rate, 1),
                'avg_points_per_game': round(stats['total_points'] / max(1, stats['games_played']), 1)
            })

    # Sort by total points (primary) and then by success rate
    leaderboard_list.sort(key=lambda x: (x['total_points'], x['avg_points_per_game']), reverse=True)

    return leaderboard_list[:50]  # Top 50 players


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))

    logger.info(f"Starting Pixel Plagiarist server on port {port}")
    logger.info(f"Debug mode: {'enabled' if CONSTANTS['debug_mode'] else 'disabled'}")
    logger.info(f"Testing mode: {'enabled' if CONSTANTS['testing_mode'] else 'disabled'}")

    if 'DYNO' in os.environ:
        logger.info("Running on Heroku - game will be available at your app URL")
    else:
        logger.info(f"Game will be available at http://localhost:{port}")

    # Ensure there's always a default room available on startup
    try:
        game_state_sh.ensure_default_room()
        logger.info("Default $10 room created on server startup")
    except Exception as e:
        logger.error(f"Failed to create default room on startup: {e}")

    # Start the server
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=CONSTANTS['debug_mode']
    )
