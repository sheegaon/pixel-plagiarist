#!/usr/bin/env python3
"""
Pixel Plagiarist AI Player
Automated client that connects to the Pixel Plagiarist game server and plays autonomously.

This AI player can be used for testing game functionality without requiring multiple human players.
The AI performs basic actions: draws simple "X" marks and votes randomly.

Usage Examples
--------------
# Single AI player
python ai_player.py

# Multiple AI players with custom names
python ai_player.py --name "TestBot1" --host localhost --port 5000
python ai_player.py --name "TestBot2" --host localhost --port 5000

# Connect to remote server
python ai_player.py --name "AI_Player" --host your-app.herokuapp.com --port 443 --ssl

AI Enhancement Opportunities
----------------------------
Future improvements could include:
- More sophisticated drawing algorithms (basic shapes, patterns)
- Strategic voting based on drawing quality analysis
- Adaptive betting strategies based on game state
- Learning from previous games to improve performance
- Computer vision analysis of other players' drawings
"""

import os
import argparse
import random
import time
import threading
import base64
import io
import signal
import sys
import atexit
from PIL import Image, ImageDraw
import socketio

# Global shutdown flag for clean exit
shutdown_event = threading.Event()


def signal_handler(signum, frame):
    """Handle Ctrl+C and other termination signals."""
    print(f"\n⏹️ Received signal {signum}, shutting down AI players...")
    shutdown_event.set()
    sys.exit(0)


# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def choose_drawing_shape(prompt=""):
    """
    Choose what shape to draw based on variety and optional prompt awareness.

    Current implementation: Random shape selection with basic prompt hints.
    Enhancement opportunities:
    - More sophisticated prompt analysis
    - Context-aware shape selection
    - Learning from successful drawings

    Parameters
    ----------
    prompt : str
        The drawing prompt (optional for basic shape selection)

    Returns
    -------
    str
        Shape type to draw ("X", "O", "circle", "square", "triangle", "line")
    """
    # Available shapes for variety
    shapes = ["X", "O", "circle", "square", "triangle", "line"]

    # Basic prompt awareness - look for keywords
    prompt_lower = prompt.lower()

    # Simple keyword matching for shape suggestions
    if any(word in prompt_lower for word in ["circle", "ball", "round", "dot", "bubble"]):
        return "circle" if random.random() < 0.7 else random.choice(shapes)
    elif any(word in prompt_lower for word in ["square", "box", "cube", "block"]):
        return "square" if random.random() < 0.7 else random.choice(shapes)
    elif any(word in prompt_lower for word in ["triangle", "arrow", "point", "pyramid"]):
        return "triangle" if random.random() < 0.7 else random.choice(shapes)
    elif any(word in prompt_lower for word in ["line", "stick", "rod", "stripe"]):
        return "line" if random.random() < 0.7 else random.choice(shapes)
    elif any(word in prompt_lower for word in ["x", "cross", "plus", "mark"]):
        return "X" if random.random() < 0.7 else random.choice(shapes)
    else:
        # No keyword match, choose randomly
        return random.choice(shapes)


def has_human_players(room):
    """
    Check if a room contains any human players (non-AI players).

    AI players are identified by usernames that start with "AI_Player" or contain "Bot".

    Parameters
    ----------
    room : dict
        Room information dictionary containing player details

    Returns
    -------
    bool
        True if room has at least one human player, False otherwise
    """
    if 'players' not in room or not room['players']:
        return False

    for player in room['players']:
        username = player['username']
        # Check if this appears to be a human player (not an AI)
        if not is_ai_player(username):
            return True

    return False


class PixelPlagiaristAI:
    def __init__(self, name="AI_Player", host="localhost", port=5000, use_ssl=False):
        """
        Initialize AI player.
        
        Parameters
        ----------
        name : str
            Display name for the AI player
        host : str
            Server hostname or IP address
        port : int
            Server port number
        use_ssl : bool
            Whether to use SSL/HTTPS connection
        """
        self.name = name
        self.host = host
        self.port = port
        self.use_ssl = use_ssl

        # Game state
        self.room_id = None
        self.player_id = None
        self.game_phase = "waiting"
        self.current_prompt = None
        self.copying_targets = []
        self.voting_drawings = []
        self.available_rooms = []  # Store available rooms from server
        self.looking_for_room = False  # Flag to track if actively seeking a room

        # Control flags
        self.running = False
        self.should_stop = False

        # AI configuration
        self.auto_join_delay = random.uniform(1, 3)  # Random delay before joining
        self.response_delay_range = (0.5, 2.0)  # Random response timing
        self.drawing_complexity = "simple"  # Can be enhanced later

        # Socket.IO client
        self.sio = socketio.Client()
        self.setup_event_handlers()

        print(f"🤖 AI Player '{self.name}' initialized")

    def setup_event_handlers(self):
        """Set up Socket.IO event handlers for game communication."""

        @self.sio.event
        def connect():
            print(f"🔗 {self.name} connected to server")
            # Request room list immediately after connection and start looking for rooms
            self.looking_for_room = True
            self.sio.emit('request_room_list')

        @self.sio.event
        def disconnect():
            print(f"❌ {self.name} disconnected from server")

        @self.sio.on('room_list_updated')
        def on_room_list_updated(data):
            """Handle room list response from server."""
            self.available_rooms = data['rooms']
            print(f"📋 {self.name}: Received {len(self.available_rooms)} available rooms: {self.available_rooms}")

            # Only try to join if we're actively looking for a room
            if self.looking_for_room:
                self.schedule_action(self.try_join_available_room)
            else:
                print(f"📋 {self.name}: Not looking for a room")

        @self.sio.on('room_created')
        def on_room_created(data):
            """Handle room creation response - AI should not create rooms."""
            print(f"⚠️ {self.name}: Unexpected room creation event received")

        @self.sio.on('joined_room')
        def on_joined_room(data):
            """Handle successful room join."""
            self.room_id = data['room_id']
            self.player_id = data['player_id']
            self.looking_for_room = False  # Stop looking once we've joined
            print(f"✅ {self.name} joined room {self.room_id} as player {self.player_id}")

            # Check if this room has human players after joining
            self.schedule_action(self.check_room_for_humans, delay=1.0)

        @self.sio.on('players_updated')
        def on_players_updated(data):
            """Handle player list updates in the current room."""
            if self.room_id:
                print(f"👥 {self.name}: Player list updated in room {self.room_id}")
                # Check if we still have human players when the player list changes
                self.schedule_action(self.check_current_room_for_humans, data['players'], delay=0.5)

        @self.sio.on('room_left')
        def on_room_left(data):
            """Handle leaving a room."""
            if data.get('success'):
                print(f"🚪 {self.name}: Successfully left room {self.room_id}")
                self.room_id = None
                self.player_id = None
                self.game_phase = "waiting"
                # Start looking for a new room with human players
                self.schedule_action(self.find_existing_room, delay=2.0)
            else:
                print(f"❌ {self.name}: Failed to leave room - {data.get('message')}")

        @self.sio.on('game_started')
        def on_game_started(data):
            """Handle game start and betting phase."""
            self.game_phase = "betting"
            self.current_prompt = data['prompt']
            min_stake = data['min_stake']
            print(f"🎮 {self.name}: Game started! Prompt: '{self.current_prompt}'")

            # AI betting strategy (can be enhanced)
            self.schedule_action(self.place_bet, min_stake)

        @self.sio.on('phase_changed')
        def on_phase_changed(data):
            """Handle game phase transitions."""
            self.game_phase = data['phase']
            print(f"🔄 {self.name}: Phase changed to {self.game_phase}")

            if self.game_phase == "drawing":
                self.schedule_action(self.draw_original)
            # Copying phase handled by copying_assignment event

        @self.sio.on('copying_assignment')
        def on_copying_assignment(data):
            """Handle copying phase assignments."""
            self.copying_targets = data['targets']
            print(f"🎨 {self.name}: Received {len(self.copying_targets)} drawings to copy")
            self.schedule_action(self.copy_drawings)

        @self.sio.on('voting_round')
        def on_voting_round(data):
            """Handle voting phase."""
            self.voting_drawings = data['drawings']
            print(f"🗳️ {self.name}: Voting on {len(self.voting_drawings)} drawings")
            self.schedule_action(self.vote_randomly)

        @self.sio.on('voting_round_excluded')
        def on_voting_round_excluded(data):
            """Handle when AI is excluded from voting (drew or copied in the set)."""
            print(f"⏭️ {self.name}: Excluded from voting - {data['reason']}")

        @self.sio.on('game_results')
        def on_game_results(data):
            """Handle game end and results."""
            print(f"🏆 {self.name}: Game finished!")
            final_balance = data.get('final_balance', {})
            final_tokens = final_balance.get(self.player_id, 0)
            print(f"💰 {self.name}: Final tokens: {final_tokens}")

            # Stay connected and look for new rooms to join
            self.game_phase = "waiting"
            self.schedule_action(self.find_existing_room, delay=5.0)

        @self.sio.on('error')
        def on_error(data):
            """Handle server errors."""
            error_msg = data.get('message', 'Unknown error')
            print(f"❌ {self.name}: Server error - {error_msg}")

            # If room not found, try again after delay
            if 'Room not found' in error_msg or 'full' in error_msg.lower():
                self.schedule_action(self.find_existing_room, delay=10.0)

    def schedule_action(self, action, *args, delay=None):
        """
        Schedule an AI action with random delay for more human-like behavior.
        
        Parameters
        ----------
        action : callable
            Function to execute
        *args : tuple
            Arguments to pass to the action
        delay : float, optional
            Specific delay, otherwise uses random delay
        """
        if delay is None:
            delay = random.uniform(*self.response_delay_range)

        threading.Timer(delay, lambda: action(*args)).start()

    def find_existing_room(self):
        """
        Request room list from server to find available rooms.
        """
        print(f"🔍 {self.name}: Requesting available rooms from server...")
        self.looking_for_room = True  # Set flag to indicate active search
        self.sio.emit('request_room_list')

    def check_room_for_humans(self):
        """
        Check if the current room has human players after joining.
        If no human players are found, leave the room.
        """
        if not self.room_id:
            return

        print(f"🔍 {self.name}: Checking room {self.room_id} for human players...")
        # Request current room list to get updated player information
        self.sio.emit('request_room_list')

    def check_current_room_for_humans(self, players):
        """
        Check if the current room still has human players based on player list update.
        Leave the room if only AI players remain.
        
        Parameters
        ----------
        players : Iterable
            List of current players in the room
        """
        if not self.room_id or self.game_phase != "waiting":
            # Don't leave during active games
            return

        human_players = []
        ai_players = []

        for player in players:
            username = player['username']
            if is_ai_player(username):
                ai_players.append(username)
            else:
                human_players.append(username)

        print(
            f"👥 {self.name}: Room {self.room_id} has {len(human_players)} human players and "
            f"{len(ai_players)} AI players")
        print(f"   Humans: {human_players}")
        print(f"   AIs: {ai_players}")

        if len(human_players) == 0 and len(players) > 1:
            # Room has only AI players - leave it
            print(f"🚪 {self.name}: Leaving room {self.room_id} - no human players remaining")
            self.leave_room()
        elif len(human_players) > 0:
            print(f"✅ {self.name}: Staying in room {self.room_id} - found {len(human_players)} human player(s)")

    def leave_room(self):
        """
        Leave the current room and start looking for a new one with human players.
        """
        if self.room_id and self.game_phase == "waiting":
            print(f"🚪 {self.name}: Leaving room {self.room_id} to find humans...")
            self.looking_for_room = True
            self.sio.emit('leave_room')
        else:
            print(f"❌ {self.name}: Cannot leave room - either not in a room or game in progress")

    def try_join_available_room(self):
        """
        Try to join one of the available rooms from the server's room list.
        Prioritizes rooms that are waiting for players and contain human players.
        """
        if not self.available_rooms:
            print(f"📭 {self.name}: No available rooms found, waiting...")
            self.looking_for_room = False  # Stop looking temporarily
            # Try again after a delay
            self.schedule_action(self.find_existing_room, delay=10.0)
            return

        # Debug: Print detailed room information
        print(f"🔍 {self.name}: Analyzing {len(self.available_rooms)} available rooms:")
        for i, room in enumerate(self.available_rooms):
            player_names = [p['username'] for p in room.get('players', [])]
            has_humans = has_human_players(room)
            print(f"  Room {i + 1}: {room['room_id']} - Phase: {room['phase']}, "
                  f"Players: {room['player_count']}/{room['max_players']}, "
                  f"Has humans: {has_humans}, Players: {player_names}")

        # Filter rooms by suitability - must be waiting, have space, AND have human players
        suitable_rooms = [room for room in self.available_rooms
                          if (room['phase'] == 'waiting' and
                              room['player_count'] < room['max_players'] and
                              has_human_players(room))]

        print(f"🎯 {self.name}: Found {len(suitable_rooms)} suitable rooms with human players")

        if suitable_rooms:
            # Prefer rooms that are closest to starting (more players)
            best_room = max(suitable_rooms, key=lambda r: r['player_count'])
            room_id = best_room['room_id']

            print(f"🎯 {self.name}: Attempting to join room {room_id} "
                  f"({best_room['player_count']}/{best_room['max_players']} players) "
                  f"with human players")

            self.sio.emit('join_room', {
                'room_id': room_id,
                'username': self.name
            })
        else:
            print(f"⏳ {self.name}: No suitable rooms available (need rooms with human players)")
            self.looking_for_room = False  # Stop looking temporarily
            # Try again after a longer delay
            self.schedule_action(self.find_existing_room, delay=15.0)

    def place_bet(self, min_stake):
        """
        Place a bet during the betting phase.
        
        Current strategy: Always bet the minimum.
        Enhancement opportunity: Could implement more sophisticated betting
        strategies based on confidence, previous performance, etc.
        """
        stake = min_stake  # Simple strategy: always bet minimum
        print(f"💰 {self.name}: Placing bet of {stake} tokens")
        self.sio.emit('place_bet', {'stake': stake})

    def draw_original(self):
        """
        Draw an original artwork for the current prompt.
        
        Now includes shape variety and basic prompt awareness.
        """
        print(f"✏️ {self.name}: Drawing original artwork for '{self.current_prompt}'")

        # Choose shape based on prompt and variety
        chosen_shape = choose_drawing_shape(self.current_prompt)
        print(f"🎨 {self.name}: Chose to draw a {chosen_shape}")

        drawing_data = self.create_simple_drawing(chosen_shape)

        self.sio.emit('submit_drawing', {
            'drawing_data': drawing_data  # Fixed: use 'drawing_data' not 'drawing'
        })

    def copy_drawings(self):
        """
        Copy assigned original drawings.
        
        Now includes shape variety for copies.
        """
        for target in self.copying_targets:
            target_id = target['target_id']
            print(f"🎨 {self.name}: Copying drawing from player {target_id}")

            # Use variety for copies too - could analyze original in the future
            chosen_shape = choose_drawing_shape()
            print(f"🎨 {self.name}: Chose to copy with a {chosen_shape}")
            copy_data = self.create_simple_drawing(chosen_shape)

            self.sio.emit('submit_copy', {
                'target_id': target_id,
                'drawing_data': copy_data  # Fixed: use correct event and key names
            })

            # Small delay between copies for realism
            time.sleep(random.uniform(0.5, 1.5))

    def vote_randomly(self):
        """
        Cast a random vote during voting phase.
        
        Current implementation: Completely random selection.
        Enhancement opportunities:
        - Analyze drawing quality/complexity
        - Vote based on which drawing looks most "original" vs "copied"
        - Implement basic image comparison algorithms
        - Learn voting patterns from previous games
        - Consider drawing style consistency
        """
        if self.voting_drawings:
            chosen_drawing = random.choice(self.voting_drawings)
            drawing_id = chosen_drawing['id']
            print(f"🗳️ {self.name}: Voting for drawing {drawing_id}")

            self.sio.emit('submit_vote', {'drawing_id': drawing_id})

    @staticmethod
    def create_simple_drawing(shape="X"):
        """
        Create a simple drawing as base64-encoded image data.
        
        Current implementation: Basic shapes on white background.
        Enhancement opportunities:
        - More sophisticated drawing algorithms
        - Variable colors and styles
        - Pattern generation based on prompts
        - Basic geometric shape combinations
        
        Parameters
        ----------
        shape : str
            Type of shape to draw ("X", "O", "line", etc.)
            
        Returns
        -------
        str
            Base64-encoded PNG image data
        """
        # Create blank canvas
        width, height = 400, 400
        image = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(image)

        # Add some randomness to position and size
        margin = 50
        x1 = random.randint(margin, width - margin)
        y1 = random.randint(margin, height - margin)
        x2 = random.randint(margin, width - margin)
        y2 = random.randint(margin, height - margin)

        # Draw based on shape type
        if shape == "X":
            # Draw an X
            draw.line([(margin, margin), (width - margin, height - margin)], fill='black', width=8)
            draw.line([(margin, height - margin), (width - margin, margin)], fill='black', width=8)
        elif shape == "O":
            # Draw a circle
            draw.ellipse([margin, margin, width - margin, height - margin], outline='black', width=8)
        elif shape == "line":
            # Draw a random line
            draw.line([(x1, y1), (x2, y2)], fill='black', width=8)
        elif shape == "circle":
            # Draw a filled circle
            draw.ellipse([margin, margin, width - margin, height - margin], fill='black')
        elif shape == "square":
            # Draw a filled square
            draw.rectangle([margin, margin, width - margin, height - margin], fill='black')
        elif shape == "triangle":
            # Draw a triangle
            draw.polygon(
                [(width / 2, margin), (width - margin, height - margin), (margin, height - margin)], fill='black')
        else:
            # Default: simple X
            draw.line([(margin, margin), (width - margin, height - margin)], fill='black', width=8)
            draw.line([(margin, height - margin), (width - margin, margin)], fill='black', width=8)

        # Convert to base64
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return f"data:image/png;base64,{image_data}"

    def connect_to_server(self):
        """Connect to the game server."""
        url = f"{'https' if self.use_ssl else 'http'}://{self.host}:{self.port}"
        print(f"🚀 {self.name}: Connecting to {url}")

        try:
            self.sio.connect(url)
            return True
        except Exception as e:
            print(f"❌ {self.name}: Failed to connect - {e}")
            return False

    def disconnect(self):
        """Disconnect from the server."""
        if self.sio.connected:
            self.sio.disconnect()
            print(f"👋 {self.name}: Disconnected")

    def run(self):
        """Main execution loop for the AI player."""
        if self.connect_to_server():
            print(f"🤖 {self.name}: AI player is running...")
            self.running = True
            try:
                # Keep the AI running with properly interruptible loop
                while self.running and not self.should_stop and not shutdown_event.is_set():
                    time.sleep(0.1)  # Use regular sleep for better interrupt handling
            except KeyboardInterrupt:
                print(f"\n⏹️ {self.name}: Shutting down...")
            finally:
                self.running = False
                self.should_stop = True
                self.disconnect()
        else:
            print(f"💥 {self.name}: Failed to start AI player")

    def stop(self):
        """Stop the AI player gracefully."""
        self.should_stop = True
        self.running = False


def is_ai_player(username):
    """Detect whether a username belongs to an AI player."""
    return username.startswith('AI_') or 'Bot' in username or username.startswith('AI ') or username.endswith('_AI')


def main():
    """Main entry point with command line argument parsing."""
    parser = argparse.ArgumentParser(description='Pixel Plagiarist AI Player')
    parser.add_argument('--name', default=f"AI Player {random.randint(1000, 9999)}",
                        help='AI player display name')
    parser.add_argument('--host', default='localhost',
                        help='Game server hostname')
    parser.add_argument('--port', type=int, default=os.environ.get('PORT', 5000),
                        help='Game server port')
    parser.add_argument('--ssl', action='store_true',
                        help='Use SSL/HTTPS connection')
    parser.add_argument('--count', type=int, default=1,
                        help='Number of AI players to spawn')

    args = parser.parse_args()

    if args.count == 1:
        # Single AI player
        ai = PixelPlagiaristAI(args.name, args.host, args.port, args.ssl)
        ai.run()
    else:
        # Multiple AI players
        print(f"🚀 Spawning {args.count} AI players...")
        ais = []
        threads = []

        def cleanup_ais():
            """Clean up all AI players."""
            print(f"\n⏹️ Shutting down all AI players...")
            shutdown_event.set()
            for ai in ais:
                ai.stop()
                ai.disconnect()

        # Register cleanup function
        atexit.register(cleanup_ais)

        for i in range(args.count):
            # Use spaces instead of underscores in AI names
            ai_name = f"{args.name} {i + 1}" if args.name.endswith(
                str(random.randint(1000, 9999))) else f"{args.name} {i + 1}"
            ai = PixelPlagiaristAI(ai_name, args.host, args.port, args.ssl)
            ais.append(ai)

            # Run each AI in its own thread
            thread = threading.Thread(target=ai.run)
            thread.daemon = False  # Don't use daemon threads for clean shutdown
            threads.append(thread)
            thread.start()

            # Small delay between connections
            time.sleep(0.5)

        try:
            print(f"🤖 {args.count} AI players running. Press Ctrl+C to stop.")
            # Wait for shutdown event or threads to complete
            while not shutdown_event.is_set() and any(t.is_alive() for t in threads):
                time.sleep(0.1)
        except KeyboardInterrupt:
            print(f"\n⏹️ Received Ctrl+C, shutting down...")
            shutdown_event.set()
        finally:
            # Ensure cleanup happens
            cleanup_ais()
            # Wait a bit for threads to finish
            for thread in threads:
                thread.join(timeout=2.0)


if __name__ == "__main__":
    main()
