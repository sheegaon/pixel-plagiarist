# Pixel Plagiarist

A multiplayer web-based drawing game where players create original artwork, copy each other's drawings, and vote to identify the originals.

## Game Overview

**Pixel Plagiarist** is a social deduction game that combines creativity with strategy. Players draw original artwork based on prompts, attempt to copy other players' drawings, and then vote to identify which drawings are originals versus copies.

### How to Play

1. **Join or Create a Room**: Enter a room code or create a room with a minimum betting stake
2. **Place Your Bet**: Wager tokens on your ability to fool other players
3. **Draw Original**: Create an artwork based on the given prompt
4. **Copy Others**: Study and recreate other players' drawings
5. **Vote**: Identify which drawings are originals in a series of voting rounds
6. **Win Tokens**: Earn tokens for successful deception and accurate voting

## Detailed Gameplay

### Game Phases

**Pixel Plagiarist** follows a structured 6-phase gameplay cycle:

#### 1. Room Setup & Betting Phase
- Players join rooms with configurable minimum stakes ($10, $25, or $100)
- Each player receives a starting balance of $100
- Players must wager at least the room's minimum stake to participate
- Stakes are collected into a prize pool distributed based on performance

#### 2. Original Drawing Phase
- Each player receives a unique drawing prompt (e.g., "Cat wearing a hat", "Flying book")
- Players create original artwork using HTML5 canvas tools (brush, eraser)
- Drawings are submitted privately - other players cannot see them yet
- Auto-submission occurs if time expires to prevent game stalls

#### 3. Copying Assignment & Viewing Phase
- System randomly assigns each player 1-2 other players' drawings to copy
- Players are shown their assigned drawings for a brief viewing period

#### 4. Copying Phase
- Players recreate their assigned drawings from memory
- "View Again" button allows 5-second re-examination of original
- Goal: Make copies so accurate they're indistinguishable from originals
- Multiple copying rounds if assigned multiple targets

#### 5. Voting Phase
- Drawings are grouped into sets mixing originals with copies
- Players vote to identify which drawing in each set is the original
- **Voting Exclusions**: Players cannot vote on sets containing their own work
- Multiple voting rounds ensure all players get fair evaluation

#### 6. Results & Scoring
- Final scores calculated based on deception success and voting accuracy
- Token redistribution from prize pool based on performance
- Detailed breakdown of each round's results displayed

### Scoring System

The scoring system rewards both artistic deception and detective skills:

#### **Deception Points** (Being a Successful Plagiarist)
- **+100 points** for each vote your original drawing receives
- **+150 points** for each vote your copy receives (others think it's original)

#### **Detection Points** (Being a Good Detective)
- **+25 points** for correctly identifying an original drawing

#### **Token Distribution**
- The prize pool (sum of all stakes) is distributed proportionally based on scores
- Prize pool contributions are taken equally from all participating artists in the set
- Excess stakes are returned to players
- Disconnected or inactive players forfeit a portion of their excess stakes, which are redistributed to active players

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
- Timers can be configured for different game speeds
- Auto-submission prevents indefinite game stalls

#### **Room Management**
- Automatic room creation ensures games are always available
- Countdown system starts games when minimum players (3) join
- Maximum 12 players per room for optimal gameplay balance

## Strategy Tips

### For Drawing Originals
- Keep designs simple enough to be copyable but distinctive enough to be memorable
- Consider what details might be hard to reproduce from memory
- Balance uniqueness with believability

### For Making Copies
- Focus on key distinctive elements rather than perfect reproduction
- Use the "View Again" button strategically for complex details
- Remember that convincing copies often fool voters better than perfect ones

### For Voting
- Look for subtle inconsistencies in line quality, proportions, or style
- Consider which drawing shows more confidence in execution
- Remember that copies often lack the spontaneity of originals

## Core Features

### Gameplay
- **Real-time multiplayer**: Up to 12 players per room
- **Dynamic prompts**: Varied drawing challenges from curated prompt list
- **Betting system**: Token-based wagering adds strategic depth
- **Multi-phase voting**: Multiple rounds ensure balanced scoring
- **Live drawing**: HTML5 Canvas with brush and eraser tools

### User Experience
- **Responsive design**: Works on desktop, tablet, and mobile devices
- **Intuitive interface**: Clean, accessible UI with keyboard navigation
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
- `TESTING_MODE`: Set to 'true' to enable accelerated timers for testing
- `DEBUG_MODE`: Set to 'true' to enable detailed logging

### Deployment

The application is configured for Heroku deployment with the included `Procfile` and `runtime.txt`. For other platforms, ensure the WSGI server is properly configured.

## Development

### Testing Mode
Enable testing mode with accelerated timers:
```bash
TESTING_MODE=true python server.py
```

This reduces all game phase timers to 5 seconds for rapid testing and development.

### AI Players
The included `ai_player.py` script can be used to add automated players for testing:
```bash
python ai_player.py --count 3
```

### Game Configuration
Modify `util/config.json` to adjust:
- Timer durations for each phase
- Min/max number of players per room
- Betting stakes and token distribution rules

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
