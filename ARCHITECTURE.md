# Pixel Plagiarist Architecture

## Overview

Pixel Plagiarist is built with a modular, event-driven architecture that separates concerns between game logic, user interface, and network communication. The system is designed for scalability, maintainability, and real-time multiplayer performance.

## System Architecture

### High-Level Design

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client Web    │    │   Flask Server  │    │   Game Logic    │
│   Application   │◄──►│   + Socket.IO   │◄──►│   Engine        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Frontend       │    │  WebSocket      │    │  Room           │
│  Modules        │    │  Handlers       │    │  Management     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Component Layers

1. **Presentation Layer**: HTML/CSS/JavaScript frontend
2. **Communication Layer**: WebSocket-based real-time messaging
3. **Application Layer**: Flask web server with Socket.IO
4. **Business Logic Layer**: Game rules, state management, and scoring
5. **Data Layer**: In-memory session storage and configuration

## Backend Architecture

### Modular Game Logic

The backend uses a modular architecture with specialized components for each aspect of the game:

#### Core Game State (`game_logic/game_state.py`)
- **Room Management**: Creates and manages game room instances
- **Player Management**: Tracks player states, balances, and actions
- **Phase Coordination**: Orchestrates transitions between game phases
- **State Validation**: Ensures game rules are enforced consistently

#### Phase-Specific Modules
- **Timer (`timer.py`)**: Manages countdown timers and phase transitions
- **Betting Phase (`betting_phase.py`)**: Handles stake collection and validation
- **Drawing Phase (`drawing_phase.py`)**: Manages original artwork submission
- **Copying Phase (`copying_phase.py`)**: Handles copy assignments and submissions
- **Voting Phase (`voting_phase.py`)**: Creates voting sets and processes votes
- **Scoring Engine (`scoring_engine.py`)**: Calculates scores and distributes tokens

#### Socket Handler System (`socket_handlers/`)
- **Connection Handlers**: Manage client connections and disconnections
- **Room Handlers**: Handle room creation, joining, and leaving
- **Game Handlers**: Process in-game actions like betting, drawing, voting
- **Admin Handlers**: Administrative functions and debugging
- **Centralized State**: Shared game state management across handlers

### Data Flow

1. **Client Action**: Player performs action (join room, draw, vote)
2. **WebSocket Event**: Action sent to server via Socket.IO
3. **Validation**: Server validates action against current game state
4. **State Update**: Game logic updates room state if action is valid
5. **Broadcast**: Updated state broadcast to all players in room
6. **UI Update**: Clients update interface based on received state

## Frontend Architecture

### Module System

The frontend uses a modular architecture with clear separation of concerns:

#### Core Modules

**Main Application** (`main.js`)
- Application orchestration and lifecycle management
- Module initialization and dependency resolution
- Global error handling and resource cleanup
- Development debugging utilities

**Game Manager** (`game-manager.js`)
- Game state coordination and phase transitions
- Delegates to specialized managers for specific functionality
- Handles socket event routing and state synchronization

#### Specialized Managers

**Room Manager** (`room-manager.js`)
- Room creation, joining, and listing
- Player list management
- Room state display and updates

**Player Manager** (`player-manager.js`)
- Player identification and balance tracking
- Player list rendering and updates

**Game State Manager** (`game-state-manager.js`)
- Current phase tracking and timer management
- Game data storage and retrieval

**Betting Manager** (`betting-manager.js`)
- Stake selection and bet placement
- Betting interface management

**Drawing Manager** (`drawing-manager.js`)
- Original drawing phase coordination
- Canvas integration and submission

**Copying Manager** (`copying-manager.js`)
- Copy assignment handling and viewing phase
- Copy submission and progress tracking

**Voting Manager** (`voting-manager.js`)
- Voting interface and option selection
- Vote submission and exclusion handling

**Results Manager** (`results-manager.js`)
- Final results display and scoring breakdown

**UI Manager** (`ui-manager.js`)
- Screen transitions and modal management
- Timer displays and countdown functionality
- Message notifications and error display

**Socket Handler** (`socket-handler.js`)
- WebSocket connection management
- Event emission and reception handling
- Connection state monitoring

**Drawing Canvas** (`drawing-canvas.js`)
- HTML5 Canvas drawing functionality
- Tool management (brush, eraser)
- Stroke recording and image export

### Event-Driven Communication

The frontend uses an event-driven architecture where:
- Socket events trigger state changes
- UI components react to state updates
- User interactions emit appropriate events
- Error conditions are handled gracefully

## Game Flow Architecture

### Phase Management

The game progresses through distinct phases, each managed by specialized components:

1. **Waiting Phase**: Room setup and player joining
2. **Betting Phase**: Players wager tokens on their performance
3. **Drawing Phase**: Original artwork creation
4. **Copying Phase**: Viewing and recreating other players' art
5. **Voting Phase**: Multiple rounds of original identification
6. **Results Phase**: Score calculation and final standings

### State Synchronization

- **Authoritative Server**: Server maintains canonical game state
- **Client Prediction**: Clients can optimistically update for responsiveness
- **Conflict Resolution**: Server state always takes precedence
- **Reconnection Handling**: Players can rejoin games in progress

## Data Models

### Room Object
```python
{
    'room_id': str,
    'players': dict,
    'phase': str,
    'created_at': datetime,
    'min_stake': int,
    'max_players': int,
    'drawing_sets': list,
    'votes': dict,
    'original_drawings': dict,
    'copied_drawings': dict
}
```

### Player Object
```python
{
    'id': str,
    'username': str,
    'balance': int,
    'stake': int,
    'connected': bool,
    'has_drawn_original': bool,
    'completed_copies': int,
    'votes_cast': int,
    'has_bet': bool
}
```

### Drawing Set Object
```python
{
    'original_id': str,
    'drawings': [
        {
            'id': str,
            'player_id': str,
            'type': str,  # 'original' or 'copy'
            'drawing': str,  # base64 image data
            'target_id': str  # for copies only
        }
    ]
}
```

## Security Considerations

### Input Validation
- All client inputs validated on server side
- Drawing data size limits enforced
- Player action validation against game rules
- Content moderation through player reporting

### Game Integrity
- Server-authoritative game state prevents cheating
- Player actions validated against current phase
- Timing enforced server-side to prevent manipulation
- Phase transition guards prevent duplicate operations

### Network Security
- WebSocket connections use secure protocols in production
- Rate limiting on client actions
- Session validation for all operations
- Graceful handling of malicious or malformed requests

## Performance Optimization

### Backend Performance
- **Modular Design**: Specialized components for efficient processing
- **In-Memory Storage**: Fast access to game state
- **Event-Driven Processing**: Non-blocking I/O operations
- **Resource Cleanup**: Automatic cleanup of completed games

### Frontend Performance
- **Modular Loading**: Components loaded as needed
- **Canvas Optimization**: Efficient drawing operations
- **Memory Management**: Proper cleanup prevents memory leaks
- **Network Efficiency**: Minimal data transfer and batching

### Scalability Features
- **Room Isolation**: Games are independent and scalable
- **Stateless Design**: Easy horizontal scaling potential
- **Connection Management**: Handles multiple concurrent games
- **Resource Limits**: Prevents resource exhaustion

## Error Handling Strategy

### Phase Validation
- All user actions validated against current game phase
- Duplicate operation prevention at both frontend and backend
- Graceful handling of invalid state transitions

### Client-Side Error Handling
- **Network Failures**: Automatic reconnection attempts
- **Invalid States**: Graceful degradation and user notification
- **Resource Errors**: Cleanup and recovery procedures
- **User Errors**: Clear feedback and correction guidance

### Server-Side Error Handling  
- **Connection Drops**: Game state preservation and recovery
- **Invalid Requests**: Validation and appropriate error responses
- **Resource Limits**: Graceful handling of capacity constraints
- **System Errors**: Comprehensive logging and monitoring

## Development and Debugging

### Testing Support
- **Testing Mode**: Accelerated timers (5 seconds) for rapid testing
- **AI Players**: Automated players for testing multiplayer scenarios
- **Debug Logging**: Comprehensive logging with configurable verbosity

### Monitoring Tools
- **Performance Metrics**: Client-side performance monitoring
- **State Inspection**: Runtime game state examination
- **Network Analysis**: WebSocket message tracking
- **Error Tracking**: Comprehensive error logging and reporting

This modular architecture provides a solid foundation for real-time multiplayer gaming while maintaining code quality, performance, and scalability.