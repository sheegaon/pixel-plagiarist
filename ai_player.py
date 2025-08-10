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
from util.logging_utils import info_log, setup_logging

# Global shutdown flag for clean exit
shutdown_event = threading.Event()

setup_logging(file_root='ai_player')


def safe_print(message):
    """
    Print messages safely, handling potential Unicode errors.

    Parameters
    ----------
    message : str
        The message to print
    """
    try:
        info_log(message)
    except UnicodeEncodeError:
        # Fallback for environments that don't support certain characters
        message = message.encode('utf-8', errors='replace').decode('utf-8', errors='replace')
        info_log(message)


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
        self.connected = False  # Track connection state

        # AI configuration
        self.auto_join_delay = random.uniform(1, 3)  # Random delay before joining
        self.response_delay_range = (0.5, 2.0)  # Random response timing
        self.drawing_complexity = "simple"  # Can be enhanced later

        # Socket.IO client with Mac-specific configuration
        import platform
        if platform.system() == 'Darwin':  # macOS
            # Use specific transport and connection settings for macOS
            self.sio = socketio.Client(
                reconnection=True,
                reconnection_attempts=5,
                reconnection_delay=1,
                reconnection_delay_max=5,
                logger=False,
                engineio_logger=False
            )
        else:
            self.sio = socketio.Client()
        self.setup_event_handlers()

        # Pending timers to cancel if needed
        self.pending_timers = []

        safe_print(f"🤖 AI Player '{self.name}' initialized")

    def setup_event_handlers(self):
        """Set up Socket.IO event handlers for game communication."""

        @self.sio.event
        def connect():
            self.connected = True
            import platform
            platform_info = f" (on {platform.system()})"
            safe_print(f"🔗 {self.name} connected to server{platform_info}")

            # Add a small delay to ensure the connection is fully established
            def request_rooms():
                self.looking_for_room = True
                safe_print(f"📡 {self.name}: Requesting room list after connection")
                success = self.safe_emit('request_room_list')
                if not success:
                    safe_print(f"⚠️ {self.name}: Failed to request room list, retrying...")
                    self.schedule_action(self.find_existing_room, delay=2.0)

            # Use longer delay on macOS to ensure connection is fully stable
            delay = 1.0 if platform.system() == 'Darwin' else 0.5
            self.schedule_action(request_rooms, delay=delay)

        @self.sio.event
        def disconnect():
            self.connected = False
            safe_print(f"❌ {self.name} disconnected from server")
            # Cancel any pending timers when disconnected
            self.cancel_pending_timers()

        @self.sio.on('room_list_updated')
        def on_room_list_updated(data):
            """Handle room list response from server."""
            self.available_rooms = data['rooms']
            safe_print(f"📋 {self.name}: Received room list with {len(self.available_rooms)} rooms")

            # Log room details for debugging
            for room in self.available_rooms:
                room_info = f"Room {room['room_id']}: {room['player_count']}/{room['max_players']} players, phase: {room['phase']}"
                if 'players' in room:
                    human_count = sum(1 for p in room['players'] if not is_ai_player(p['username']))
                    room_info += f", humans: {human_count}"
                safe_print(f"  📊 {room_info}")

            # Only try to join if we're actively looking for a room
            if self.looking_for_room:
                safe_print(f"🎯 {self.name}: Looking for room, will attempt to join")
                self.schedule_action(self.try_join_available_room, delay=0.5)
            else:
                safe_print(f"⏸️ {self.name}: Not looking for room, ignoring room list")

        @self.sio.on('room_created')
        def on_room_created(data):
            """Handle room creation response - AI should not create rooms."""
            safe_print(f"⚠️ {self.name}: Unexpected room creation event received")

        @self.sio.on('joined_room')
        def on_joined_room(data):
            """Handle successful room join."""
            self.room_id = data['room_id']
            self.player_id = data['player_id']
            self.looking_for_room = False  # Stop looking once we've joined
            safe_print(f"✅ {self.name} joined room {self.room_id} as player {self.player_id}")

            # Check if this room has human players after joining
            self.schedule_action(self.check_room_for_humans, delay=1.0)

        @self.sio.on('join_room_error')
        def on_join_room_error(data):
            """Handle room join failures."""
            error_msg = data.get('message', 'Unknown error')
            safe_print(f"❌ {self.name}: Failed to join room - {error_msg}")

            # Reset state and try again
            self.room_id = None
            self.player_id = None
            self.looking_for_room = True

            # Try finding a different room after a delay
            self.schedule_action(self.find_existing_room, delay=3.0)

        @self.sio.on('players_updated')
        def on_players_updated(data):
            """Handle player list updates in the current room."""
            if self.room_id:
                safe_print(f"👥 {self.name}: Player list updated in room {self.room_id}")
                # Check if we still have human players when the player list changes
                self.schedule_action(self.check_current_room_for_humans, data['players'], delay=0.5)

        @self.sio.on('room_left')
        def on_room_left(data):
            """Handle leaving a room."""
            if data.get('success'):
                safe_print(f"🚪 {self.name}: Successfully left room {self.room_id}")
                self.room_id = None
                self.player_id = None
                self.game_phase = "waiting"
                # Start looking for a new room with human players
                self.schedule_action(self.find_existing_room, delay=2.0)
            else:
                safe_print(f"❌ {self.name}: Failed to leave room - {data.get('message')}")

        @self.sio.on('game_started')
        def on_game_started(data):
            """Handle game start."""
            self.game_phase = "drawing"
            self.current_prompt = data['prompt']
            safe_print(f"🎮 {self.name}: Game started! Prompt: '{self.current_prompt}'")
            self.schedule_action(self.draw_original)

        @self.sio.on('phase_changed')
        def on_phase_changed(data):
            """Handle game phase transitions."""
            self.game_phase = data['phase']
            safe_print(f"🔄 {self.name}: Phase changed to {self.game_phase}")

            if self.game_phase == "drawing":
                self.schedule_action(self.draw_original)
            # Copying phase handled by copying_assignment event

        @self.sio.on('copying_assignment')
        def on_copying_assignment(data):
            """Handle copying phase assignments."""
            self.copying_targets = data['targets']
            safe_print(f"🎨 {self.name}: Received {len(self.copying_targets)} drawings to copy")
            self.schedule_action(self.copy_drawings)

        @self.sio.on('voting_round')
        def on_voting_round(data):
            """Handle voting phase."""
            self.voting_drawings = data['drawings']
            safe_print(f"🗳️ {self.name}: Voting on {len(self.voting_drawings)} drawings")
            self.schedule_action(self.vote_randomly)

        @self.sio.on('voting_round_excluded')
        def on_voting_round_excluded(data):
            """Handle when AI is excluded from voting (drew or copied in the set)."""
            safe_print(f"⏭️ {self.name}: Excluded from voting - {data['reason']}")

        @self.sio.on('game_results')
        def on_game_results(data):
            """Handle game end and results."""
            safe_print(f"🏆 {self.name}: Game finished!")
            final_balances = data.get('final_balances', {})
            final_tokens = final_balances.get(self.player_id, 0)
            safe_print(f"💰 {self.name}: Final tokens: {final_tokens}")

            # Reset state and look for new rooms to join
            self.room_id = None
            self.player_id = None
            self.game_phase = "waiting"
            self.current_prompt = None
            self.copying_targets = []
            self.voting_drawings = []

            safe_print(f"🔄 {self.name}: Game ended, resetting state and looking for new room")
            self.schedule_action(self.find_existing_room, delay=2.0)

        @self.sio.on('game_ended_early')
        def on_game_ended_early(data):
            """Handle early game end."""
            safe_print(f"⏹️ {self.name}: Game ended early - {data.get('reason', 'Unknown reason')}")

            # Reset state and look for new rooms to join
            self.room_id = None
            self.player_id = None
            self.game_phase = "waiting"
            self.current_prompt = None
            self.copying_targets = []
            self.voting_drawings = []

            safe_print(f"🔄 {self.name}: Early game end, resetting state and looking for new room")
            self.schedule_action(self.find_existing_room, delay=2.0)

        @self.sio.on('error')
        def on_error(data):
            """Handle server errors."""
            error_msg = data.get('message', 'Unknown error')
            safe_print(f"❌ {self.name}: Server error - {error_msg}")

            # If room not found, try again after delay
            if 'Room not found' in error_msg or 'full' in error_msg.lower():
                self.schedule_action(self.find_existing_room, delay=10.0)

    def safe_emit(self, event, data=None):
        """
        Safely emit Socket.IO events, only if connected.

        Parameters
        ----------
        event : str
            Event name to emit
        data : dict, optional
            Data to send with the event

        Returns
        -------
        bool
            True if emission was successful, False otherwise
        """
        # Check our own connection state first, then socketio's state
        if not self.connected:
            safe_print(f"⚠️ {self.name}: Cannot emit '{event}' - not connected")
            return False
            
        if not self.sio.connected:
            safe_print(f"⚠️ {self.name}: Cannot emit '{event}' - socketio not connected")
            # Update our state to match socketio's state
            self.connected = False
            return False

        try:
            if data is None:
                self.sio.emit(event)
            else:
                self.sio.emit(event, data)
            return True
        except Exception as e:
            safe_print(f"❌ {self.name}: Failed to emit '{event}' - {e}")
            return False

    def cancel_pending_timers(self):
        """Cancel all pending timers to prevent actions after disconnect."""
        for timer in self.pending_timers:
            if timer.is_alive():
                timer.cancel()
        self.pending_timers.clear()

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

        # Check if we should stop before scheduling
        if self.should_stop or shutdown_event.is_set():
            return

        def safe_action():
            # Double-check before executing
            if not self.should_stop and not shutdown_event.is_set():
                try:
                    action(*args)
                except Exception as e:
                    safe_print(f"❌ {self.name}: Error executing scheduled action - {e}")

        timer = threading.Timer(delay, safe_action)
        self.pending_timers.append(timer)
        timer.start()

    def find_existing_room(self):
        """
        Request room list from server to find available rooms.
        Only executes if connected.
        """
        if not self.connected:
            self.connect_to_server()
            return

        self.looking_for_room = True  # Set flag to indicate active search
        success = self.safe_emit('request_room_list')
        if not success:
            # Retry after a delay if emission failed
            self.schedule_action(self.find_existing_room, delay=5.0)

    def check_room_for_humans(self):
        """
        Check if the current room has human players after joining.
        If no human players are found, leave the room.
        """
        if not self.room_id or not self.connected:
            return

        safe_print(f"🔍 {self.name}: Checking room {self.room_id} for human players...")
        # Request current room list to get updated player information
        self.safe_emit('request_room_list')

    def check_current_room_for_humans(self, players):
        """
        Check if the current room still has human players based on player list update.
        Leave the room if only AI players remain.

        Parameters
        ----------
        players : Iterable
            List of current players in the room
        """
        if not self.room_id:
            # Not in a room, nothing to check
            return

        human_players = []
        ai_players = []

        for player in players:
            username = player['username']
            if is_ai_player(username):
                ai_players.append(username)
            else:
                human_players.append(username)

        safe_print(
            f"👥 {self.name}: Room {self.room_id} has {len(human_players)} human players and "
            f"{len(ai_players)} AI players")
        safe_print(f"   Humans: {human_players}")
        safe_print(f"   AIs: {ai_players}")

        if len(human_players) == 0:
            # Only leave if game is in progress - stay in waiting rooms to be available
            if self.game_phase != "waiting":
                safe_print(f"🚪 {self.name}: Leaving room {self.room_id} - no humans and game active")
                self.leave_room()
            else:
                safe_print(f"⏳ {self.name}: No humans in waiting room {self.room_id}, but staying available")
        else:
            safe_print(f"✅ {self.name}: Staying in room {self.room_id} - found {len(human_players)} human player(s)")

    def leave_room(self):
        """
        Leave the current room and start looking for a new one with human players.
        """
        if self.room_id and self.game_phase == "waiting" and self.connected:
            safe_print(f"🚪 {self.name}: Leaving room {self.room_id} to find humans...")
            self.looking_for_room = True
            self.safe_emit('leave_room')
        else:
            safe_print(f"❌ {self.name}: Cannot leave room - either not in a room, game in progress, or not connected")

    def try_join_available_room(self):
        """
        Try to join one of the available rooms from the server's room list.
        Prioritizes rooms that are waiting for players and contain human players.
        """
        safe_print(f"🎲 {self.name}: Attempting to join available room...")

        if not self.connected:
            safe_print(f"⚠️ {self.name}: Cannot join room - not connected")
            return

        if not self.available_rooms:
            safe_print(f"📭 {self.name}: No available rooms found, will retry search...")
            self.looking_for_room = False  # Stop looking temporarily
            # Try again after a delay
            self.schedule_action(self.find_existing_room, delay=10.0)
            return

        # Filter rooms by basic suitability - must be waiting and have space
        suitable_rooms = [room for room in self.available_rooms
                          if (room['phase'] == 'waiting' and
                              room['player_count'] < room['max_players'])]

        safe_print(f"🔍 {self.name}: Found {len(suitable_rooms)} suitable rooms out of {len(self.available_rooms)} total")

        if suitable_rooms:
            # Prioritize rooms with human players, but also consider empty rooms
            rooms_with_humans = [room for room in suitable_rooms if has_human_players(room)]
            empty_or_ai_rooms = [room for room in suitable_rooms if not has_human_players(room)]

            if rooms_with_humans:
                # Prefer rooms with human players, closest to starting
                best_room = max(rooms_with_humans, key=lambda r: r['player_count'])
                safe_print(f"🎯 {self.name}: Found room with humans, joining that")
            elif empty_or_ai_rooms:
                # No rooms with humans, but join empty/AI rooms to make them available
                best_room = max(empty_or_ai_rooms, key=lambda r: r['player_count'])
                safe_print(f"🤖 {self.name}: No humans found, joining empty/AI room to wait for humans")
            else:
                safe_print(f"🚫 {self.name}: No suitable rooms found, will retry...")
                self.looking_for_room = False
                self.schedule_action(self.find_existing_room, delay=15.0)
                return

            room_id = best_room['room_id']
            human_count = sum(1 for p in best_room.get('players', []) if not is_ai_player(p['username']))

            safe_print(f"🎯 {self.name}: Attempting to join room {room_id} "
                       f"({best_room['player_count']}/{best_room['max_players']} players, "
                       f"{human_count} humans)")

            success = self.safe_emit('join_room', {
                'room_id': room_id,
                'username': self.name
            })

            if success:
                safe_print(f"📤 {self.name}: Join room request sent successfully")
            else:
                safe_print(f"❌ {self.name}: Failed to send join room request")
                self.schedule_action(self.find_existing_room, delay=5.0)
        else:
            safe_print(f"🚫 {self.name}: No suitable rooms found, will retry...")
            self.looking_for_room = False  # Stop looking temporarily
            # Try again after a longer delay
            self.schedule_action(self.find_existing_room, delay=15.0)

    def draw_original(self):
        """
        Draw an original artwork for the current prompt.

        Now includes shape variety and basic prompt awareness.
        """
        if not self.connected:
            safe_print(f"⚠️ {self.name}: Cannot draw - not connected")
            return

        safe_print(f"✏️ {self.name}: Drawing original artwork for '{self.current_prompt}'")

        # Choose shape based on prompt and variety
        chosen_shape = choose_drawing_shape(self.current_prompt)
        safe_print(f"🎨 {self.name}: Chose to draw a {chosen_shape}")

        drawing_data = self.create_simple_drawing(chosen_shape)

        self.safe_emit('submit_original', {
            'drawing_data': drawing_data  # Fixed: use 'drawing_data' not 'drawing'
        })

    def copy_drawings(self):
        """
        Copy assigned original drawings.

        Now includes shape variety for copies.
        """
        if not self.connected:
            safe_print(f"⚠️ {self.name}: Cannot copy - not connected")
            return

        for target in self.copying_targets:
            target_id = target['target_id']
            safe_print(f"🎨 {self.name}: Copying drawing from player {target_id}")

            # Use variety for copies too - could analyze original in the future
            chosen_shape = choose_drawing_shape()
            safe_print(f"🎨 {self.name}: Chose to copy with a {chosen_shape}")
            copy_data = self.create_simple_drawing(chosen_shape)

            self.safe_emit('submit_copy', {
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
        if not self.connected:
            safe_print(f"⚠️ {self.name}: Cannot vote - not connected")
            return

        if self.voting_drawings:
            chosen_drawing = random.choice(self.voting_drawings)
            drawing_id = chosen_drawing['id']
            safe_print(f"🗳️ {self.name}: Voting for drawing {drawing_id}")

            self.safe_emit('submit_vote', {'drawing_id': drawing_id})

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
        try:
            # Create blank canvas with white background
            width, height = 400, 300
            image = Image.new('RGB', (width, height), 'white')
            draw = ImageDraw.Draw(image)

            # Add some randomness to position and size
            margin = 50
            x1 = random.randint(margin, width - margin)
            y1 = random.randint(margin, height - margin)
            x2 = random.randint(margin, width - margin)
            y2 = random.randint(margin, height - margin)

            # Use black color for all shapes to ensure visibility
            color = 'black'
            line_width = 8

            # Draw based on shape type
            if shape == "X":
                # Draw an X
                draw.line([(margin, margin), (width - margin, height - margin)], fill=color, width=line_width)
                draw.line([(margin, height - margin), (width - margin, margin)], fill=color, width=line_width)
            elif shape == "O":
                # Draw a circle outline
                draw.ellipse([margin, margin, width - margin, height - margin], outline=color, width=line_width)
            elif shape == "line":
                # Draw a random line
                draw.line([(x1, y1), (x2, y2)], fill=color, width=line_width)
            elif shape == "circle":
                # Draw a filled circle
                circle_size = min(width, height) // 3
                center_x, center_y = width // 2, height // 2
                draw.ellipse([center_x - circle_size, center_y - circle_size,
                              center_x + circle_size, center_y + circle_size], fill=color)
            elif shape == "square":
                # Draw a filled square
                square_size = min(width, height) // 3
                center_x, center_y = width // 2, height // 2
                draw.rectangle([center_x - square_size, center_y - square_size,
                                center_x + square_size, center_y + square_size], fill=color)
            elif shape == "triangle":
                # Draw a triangle
                center_x, center_y = width // 2, height // 2
                size = min(width, height) // 3
                draw.polygon([
                    (center_x, center_y - size),  # top point
                    (center_x - size, center_y + size),  # bottom left
                    (center_x + size, center_y + size)  # bottom right
                ], fill=color)
            else:
                # Default: simple X (guaranteed to be visible)
                draw.line([(margin, margin), (width - margin, height - margin)], fill=color, width=line_width)
                draw.line([(margin, height - margin), (width - margin, margin)], fill=color, width=line_width)

            # Convert to base64 with proper error handling
            buffer = io.BytesIO()
            image.save(buffer, format='PNG', optimize=False)  # Don't optimize to avoid issues
            buffer.seek(0)
            image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

            # Verify the image data is valid before returning
            if len(image_data) < 100:  # Too small to be a valid image
                raise ValueError("Generated image data too small")

            result = f"data:image/png;base64,{image_data}"
            safe_print(f"✅ {PixelPlagiaristAI.__name__}: Created {shape} drawing ({len(image_data)} bytes)")
            return result

        except Exception as e:
            safe_print(f"⚠️ Error creating {shape} drawing: {e}")
            # Return a guaranteed working fallback
            return PixelPlagiaristAI.create_guaranteed_fallback()

    @staticmethod
    def create_guaranteed_fallback():
        """
        Create a guaranteed working fallback drawing.
        This uses the most basic PIL operations to ensure it always works.

        Returns
        -------
        str
            Base64-encoded PNG image data for a simple black square
        """
        try:
            # Create minimal image with guaranteed visible content
            width, height = 400, 300
            image = Image.new('RGB', (width, height), 'white')
            draw = ImageDraw.Draw(image)

            # Draw a simple black square in the center - guaranteed to be visible
            center_x, center_y = width // 2, height // 2
            size = 50
            draw.rectangle([center_x - size, center_y - size, center_x + size, center_y + size],
                           fill='black', outline='black')

            # Convert to base64
            buffer = io.BytesIO()
            image.save(buffer, format='PNG')
            image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')

            result = f"data:image/png;base64,{image_data}"
            safe_print(f"✅ Fallback: Created guaranteed black square ({len(image_data)} bytes)")
            return result

        except Exception as e:
            safe_print(f"❌ Even guaranteed fallback failed: {e}")
            # Last resort: return a minimal valid base64 PNG with visible content
            # This is a 1x1 black pixel PNG encoded in base64
            return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChAI9jU77zgAAAABJRU5ErkJggg=="

    def connect_to_server(self):
        """Connect to the game server with Mac-specific handling."""
        import platform

        # On macOS, use 127.0.0.1 instead of localhost to avoid DNS issues
        host = self.host
        if platform.system() == 'Darwin' and self.host == 'localhost':
            host = '127.0.0.1'
            safe_print(f"🍎 {self.name}: On macOS, using 127.0.0.1 instead of localhost")

        url = f"{'https' if self.use_ssl else 'http'}://{host}:{self.port}"
        safe_print(f"🚀 {self.name}: Connecting to {url}")

        max_retries = 3 if platform.system() == 'Darwin' else 1
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    safe_print(f"🔄 {self.name}: Connection attempt {attempt + 1}/{max_retries}")
                    time.sleep(attempt * 2)  # Exponential backoff

                self.sio.connect(url, wait_timeout=10)
                safe_print(f"✅ {self.name}: Successfully connected to server")
                return True
            except Exception as e:
                safe_print(f"❌ {self.name}: Connection attempt {attempt + 1} failed - {e}")
                if attempt == max_retries - 1:
                    safe_print(f"💥 {self.name}: All connection attempts failed")
                    return False

        return False

    def disconnect(self):
        """Disconnect from the server."""
        self.connected = False
        self.cancel_pending_timers()  # Cancel all pending actions
        if self.sio.connected:
            self.sio.disconnect()
            safe_print(f"👋 {self.name}: Disconnected")

    def run(self):
        """Main execution loop for the AI player."""
        if self.connect_to_server():
            safe_print(f"🤖 {self.name}: AI player is running...")
            self.running = True
            try:
                # Keep the AI running with properly interruptible loop
                while self.running and not self.should_stop and not shutdown_event.is_set():
                    time.sleep(0.1)  # Use regular sleep for better interrupt handling
            except KeyboardInterrupt:
                safe_print(f"\n⏹️ {self.name}: Shutting down...")
            finally:
                self.running = False
                self.should_stop = True
                self.disconnect()
        else:
            safe_print(f"💥 {self.name}: Failed to start AI player")

    def stop(self):
        """Stop the AI player gracefully."""
        self.should_stop = True
        self.running = False
        self.disconnect()


def is_ai_player(username):
    """Detect whether a username belongs to an AI player."""
    if not username:
        return False
    return (username.startswith('AI_') or
            'Bot' in username or
            username.startswith('AI ') or
            username.endswith('_AI') or
            username.startswith('AI Player') or
            username.startswith('TestBot'))


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
        safe_print(f"🚀 Spawning {args.count} AI players...")
        ais = []
        threads = []

        def cleanup_ais():
            """Clean up all AI players."""
            safe_print(f"\n⏹️ Shutting down all AI players...")
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
            safe_print(f"🤖 {args.count} AI players running. Press Ctrl+C to stop.")
            # Wait for shutdown event or threads to complete
            while not shutdown_event.is_set() and any(t.is_alive() for t in threads):
                time.sleep(0.1)
        except KeyboardInterrupt:
            safe_print(f"\n⏹️ Received Ctrl+C, shutting down...")
            shutdown_event.set()
        finally:
            # Ensure cleanup happens
            cleanup_ais()
            # Wait a bit for threads to finish
            for thread in threads:
                thread.join(timeout=2.0)


if __name__ == "__main__":
    main()
