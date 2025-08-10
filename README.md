# Pixel Plagiarist
**Draw - Copy - Deceive**

A multiplayer web-based drawing game where players create original artwork, copy each other's drawings, and vote to identify the originals.

## Game Overview

**Pixel Plagiarist** is a social deduction game that combines creativity with strategy. Players draw original artwork based on prompts, attempt to copy other players' drawings, and then vote to identify which drawings are originals versus copies.

### How to Play

1. **Login**: Choose a username or log in with Google
2. **Join a Room**: Choose a room with a specified prize pool level
3. **Draw Original**: Create an artwork based on the given prompt
4. **Copy Others**: Study and recreate other players' drawings
5. **Vote**: Identify which drawings are originals in a series of voting rounds
6. **Win Tokens**: Earn _Bit_ tokens for successful deception and accurate voting

## Detailed Gameplay

### Game Phases

**Pixel Plagiarist** follows a structured 5-phase gameplay cycle:

#### 1. Room Setup
- Each player receives a starting balance of 1000 Bits
- Players join rooms with various stakes and entry fees:
  - Bronze: 100 stake + 5 entry fees
  - Silver: 250 stake + 10 entry fees
  - Gold: 1000 stake + 20 entry fees
- Stakes are collected into a prize pool distributed based on performance
- The entry fee is required to join the game but does not contribute to the prize pool

#### 2. Original Drawing Phase
- Each player receives a unique drawing prompt (e.g., "Cat wearing a hat", "Flying book")
- Players create original artwork using HTML5 canvas tools (brush, eraser)
- Drawings are submitted privately - other players cannot see them yet
- Auto-submission occurs if time expires to prevent game stalls
- Game proceeds to the next phase once all players have submitted their drawings

#### 3. Copying Phase
- System randomly assigns each player 1-2 other players' original drawings to copy
- Players are shown their assigned drawings for a 5-second viewing period
- Players recreate their assigned drawings from memory
- "View Again" button allows 5-second re-examination of original
- Goal: Make copies which will fool other players into thinking they are originals
- Auto-submission occurs if time expires to prevent game stalls
- Repeat copying phase if there are at least 4 players in the room
- Game proceeds to the next drawing or phase once all players have submitted their drawings

#### 4. Voting Phase
- Drawings are grouped into sets mixing originals with copies
- Players vote to identify which drawing in each set is the original
- **Voting Exclusions**: Players cannot vote on sets containing their own work
- Multiple voting rounds ensure all players get fair evaluation

#### 5. Results & Scoring
- Final scores calculated based on deception success and voting accuracy
- Token redistribution from prize pool based on performance
- Detailed breakdown of each round's results displayed

### Scoring System

The scoring system rewards both artistic deception and detective skills:

#### **Artist Points**
- **+100 points** for each vote your original drawing receives
- **+150 points** for each vote your copy receives (others think it's original)

#### **Voter Points**
- **+25 points** for correctly identifying an original drawing

#### **Token Distribution**
- The prize pool (sum of all stakes) is distributed proportionally based on scores
- Each drawing set is evaluated independently

#### **Strategic Considerations**
- **Copy Quality**: Better copies fool more voters but are harder to create
- **Artistic Style**: Consistent style helps copies blend with originals
- **Voting Psychology**: Consider what other players might find believable
- **Risk Management**: Balance copying accuracy with time management

## Additional Features

#### **Content Moderation**
- Players can flag inappropriate drawings during any game phase
- Flagged content is logged with reporter and creator information
- Review system for maintaining game quality

#### **Configurable Timers**
- Timers can be configured via `config.json` file for different game speeds
- Auto-submission prevents indefinite game stalls
- Phases end early if all players have submitted their drawings or have voted

#### **Room Management**
- Automatic room creation ensures games are always available
- Countdown system starts games when minimum players (3) join
- Maximum 12 players per room for optimal gameplay balance

## Core Features

### Gameplay
- **Real-time multiplayer**: Up to 12 players per room
- **Dynamic prompts**: Varied drawing challenges from curated prompt list
- **Multi-phase voting**: Each player gets one original, 1-2 copies, and at least one vote
- **Live drawing**: Simple HTML5 Canvas with only a brush tool and undo button

### User Experience
- **Responsive design**: Works on desktop, tablet, and mobile devices
- **Intuitive interface**: Clean, accessible UI with mobile-friendly design
- **Real-time feedback**: Instant updates via WebSocket connections
- **Auto-submission**: Prevents game stalls with automatic submissions
- **Content moderation**: Player reporting system for inappropriate content

### Technical Features
- **Scalable architecture**: Room-based game instances
- **Robust error handling**: Graceful degradation and recovery
- **Session management**: Persistent player state across connections
- **Performance optimized**: Efficient canvas rendering and data transfer

## Technical Stack

- **Backend**: Python Flask with Socket.IO
- **Frontend**: Vanilla JavaScript with modular architecture  
- **Canvas**: HTML5 Canvas API for drawing functionality
- **Communication**: WebSocket-based real-time messaging
- **Deployment**: Heroku-ready with Gunicorn WSGI server

## Installation & Setup

### Local Development
```bash
# Clone the repository
git clone <repository-url>
cd pixel_plagiarist

# Install dependencies
pip install -r requirements.txt

# Run the development server
python server.py
```

The game will be available at `http://localhost:5000`

### Environment Variables
- `PORT`: Server port (default: 5000)
- `FLASK_ENV`: Set to 'development' for debug mode
- `DEBUG_MODE`: Set to 'true' to enable detailed logging

### Deployment

The application is configured for Heroku deployment with the included `Procfile` and `runtime.txt`. For other platforms, ensure the WSGI server is properly configured.

## Development

### AI Players
The included `ai_player.py` script can be used to add automated players for testing:
```bash
python ai_player.py --count 3
```

### Game Configuration
Modify `util/config.json` to adjust:
- Timer durations for each phase
- Min/max number of players per room
- Points for receiving each type of vote and for voting accuracy
- Entry fees and prize pool levels
- Starting balance for each player

## Project Structure
```
pixel_plagiarist/
├── server.py              # Main Flask application
├── ai_player.py           # AI player for testing
├── game_logic/            # Core game logic modules
├── socket_handlers/       # WebSocket event handlers
├── static/                # Frontend assets
│   ├── js/                # JavaScript modules
│   ├── css/               # Stylesheets
│   └── images/            # Game assets
├── templates/             # HTML templates for rendering
└── util/                  # Utility functions and configuration
```
