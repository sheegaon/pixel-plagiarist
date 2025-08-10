#!/usr/bin/env python3
"""
Pixel Plagiarist - Multiplayer Drawing Game Server
A real-time multiplayer drawing game where players draw originals, copy others' drawings, and vote.

This is the main entry point for the Pixel Plagiarist server.

Debug Mode
----------
Set TESTING_MODE=true as an environment variable to enable accelerated gameplay for testing:
- All timers reduced to 5 seconds (countdown, drawing, copying, voting)
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
from util.db import initialize_database, get_leaderboard
from socket_handlers import setup_socket_handlers
from socket_handlers.game_state import GAME_STATE_SH

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
logger = setup_logging(file_root='server')

# Set up Socket.IO event handlers
setup_socket_handlers(socketio)

# Initialize database on startup
try:
    initialize_database()
    print("Database initialized successfully")
except Exception as e:
    print(f"Failed to initialize database: {e}")
    # Continue running but log the error
    pass


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

    # Get leaderboard data from database
    leaderboard_data = get_leaderboard()
    return render_template('leaderboard.html',
                           user=session['user'],
                           leaderboard=leaderboard_data)


@app.route('/api/player/balance/<username>')
def get_player_balance(username):
    """Get current player balance from database"""
    if 'user' not in session:
        return {'error': 'Not authenticated'}, 401
    
    try:
        from util.db import get_player_stats
        player_stats = get_player_stats(username)
        if player_stats:
            return {'balance': player_stats['balance']}
        else:
            return {'balance': CONSTANTS['INITIAL_BALANCE']}
    except Exception as e:
        logger.error(f"Error getting player balance: {e}")
        return {'error': 'Database error'}, 500


@app.route('/api/player/stats/<username>')
def get_player_stats_route(username):
    """Get comprehensive player statistics"""
    if 'user' not in session:
        return {'error': 'Not authenticated'}, 401
    
    try:
        from util.db import get_player_stats
        stats = get_player_stats(username)
        if stats:
            return dict(stats)
        else:
            return {'error': 'Player not found'}, 404
    except Exception as e:
        logger.error(f"Error getting player stats: {e}")
        return {'error': 'Database error'}, 500


@app.route('/api/player/balance/<username>', methods=['POST'])
def update_player_balance_route(username):
    """Update player balance in database"""
    if 'user' not in session:
        return {'error': 'Not authenticated'}, 401
    
    try:
        data = request.get_json()
        new_balance = data.get('balance')
        
        if new_balance is None:
            return {'error': 'Balance not provided'}, 400
        
        from util.db import update_player_balance
        success = update_player_balance(username, new_balance)
        
        if success:
            return {'success': True, 'balance': new_balance}
        else:
            return {'error': 'Failed to update balance'}, 500
            
    except Exception as e:
        logger.error(f"Error updating player balance: {e}")
        return {'error': 'Database error'}, 500


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
        GAME_STATE_SH.ensure_default_room()
    except Exception as e:
        logger.error(f"Failed to create default room on startup: {e}")

    # Start the server
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=CONSTANTS['debug_mode'],
        allow_unsafe_werkzeug=os.getenv('WERKZEUG_ALLOW_ASYNC_UNSAFE', 'false').lower() == 'true',
        use_reloader=os.getenv('USE_RELOADER', 'true').lower() == 'true'
    )
