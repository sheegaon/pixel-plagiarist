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

### Core Components

#### Game Logic Engine (`game_logic.py`)
- **Room Management**: Creates and manages game room instances
- **Game State Machine**: Handles phase transitions and timing
- **Player Management**: Tracks player states, balances, and actions
- **Scoring System**: Calculates points based on voting accuracy and deception
- **Validation**: Ensures game rules are enforced consistently

#### Socket Handlers (`socket_handlers.py`)
- **Event Processing**: Handles incoming WebSocket events from clients
- **Broadcasting**: Sends state updates to all players in a room
- **Authentication**: Validates player actions and permissions
- **Error Handling**: Manages connection issues and invalid requests

#### Configuration Management (`config.py`)
- **Game Parameters**: Centralizes timing, scoring, and gameplay settings
- **Environment Settings**: Manages development vs production configurations
- **Prompt Database**: Stores and manages drawing prompts

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

**PixelPlagiarist** (`main.js`)
- Application orchestration and lifecycle management
- Module initialization and dependency resolution
- Global error handling and resource cleanup
- Development debugging utilities

**GameManager** (`game-manager.js`)
- Game state management and phase transitions
- Player action coordination
- Room management and player lists
- Betting and scoring display

**UIManager** (`ui-manager.js`)
- Screen transitions and modal management
- Timer displays and countdown functionality
- Message notifications and error display
- Responsive design and accessibility features

**SocketHandler** (`socket-handler.js`)
- WebSocket connection management
- Event emission and reception
- Connection state monitoring
- Message queuing for offline resilience

**DrawingCanvas** (`drawing-canvas.js`)
- HTML5 Canvas drawing functionality
- Tool management (brush, eraser)
- Stroke recording and playback
- Image data export and submission

### Event-Driven Communication

The frontend uses an event-driven architecture where:
- Socket events trigger state changes
- UI components react to state updates
- User interactions emit appropriate events
- Error conditions are handled gracefully

### Resource Management

- **Memory Management**: Proper cleanup of event listeners and timers
- **Canvas Optimization**: Efficient drawing operations and image handling
- **Network Efficiency**: Minimal data transfer and connection reuse

## Game Flow Architecture

### Phase Management

The game progresses through distinct phases, each with specific behaviors:

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
    'phase_start_time': datetime,
    'settings': dict,
    'game_state': dict
}
```

### Player Object
```python
{
    'player_id': str,
    'username': str,
    'balance': int,
    'current_bet': int,
    'drawing_data': str,
    'votes': list,
    'score': int
}
```

### Drawing Object
```python
{
    'drawing_id': str,
    'player_id': str,
    'image_data': str,
    'is_original': bool,
    'prompt': str,
    'timestamp': datetime
}
```

## Security Considerations

### Input Validation
- All client inputs validated on server side
- Drawing data size limits enforced
- SQL injection prevention (though no SQL database used)
- XSS prevention in user-generated content

### Game Integrity
- Server-authoritative game state prevents cheating
- Player actions validated against game rules
- Timing enforced server-side to prevent manipulation
- Content moderation through player reporting system

### Network Security
- WebSocket connections use secure protocols in production
- Rate limiting on client actions
- Session validation for all operations
- Graceful handling of malicious or malformed requests

## Performance Optimization

### Backend Performance
- **In-Memory Storage**: Fast access to game state
- **Event-Driven Processing**: Non-blocking I/O operations
- **Connection Pooling**: Efficient WebSocket management
- **Resource Cleanup**: Automatic cleanup of completed games

### Frontend Performance
- **Lazy Loading**: Modules loaded as needed
- **Canvas Optimization**: Efficient drawing operations
- **Memory Management**: Proper cleanup prevents memory leaks
- **Network Efficiency**: Minimal data transfer and batching

### Scalability Features
- **Room Isolation**: Games are independent and scalable
- **Stateless Design**: Easy horizontal scaling potential
- **Connection Management**: Handles multiple concurrent games
- **Resource Limits**: Prevents resource exhaustion

## Error Handling Strategy

### Client-Side Error Handling
- **Network Failures**: Automatic reconnection attempts
- **Invalid States**: Graceful degradation and user notification
- **Resource Errors**: Cleanup and recovery procedures
- **User Errors**: Clear feedback and correction guidance

### Server-Side Error Handling  
- **Connection Drops**: Game state preservation and recovery
- **Invalid Requests**: Validation and appropriate error responses
- **Resource Limits**: Graceful handling of capacity constraints
- **System Errors**: Logging and monitoring integration

## Monitoring and Debugging

### Development Tools
- **Debug Mode**: Verbose logging and error reporting
- **Performance Metrics**: Client-side performance monitoring
- **State Inspection**: Runtime game state examination
- **Network Analysis**: WebSocket message tracking

### Production Monitoring
- **Error Logging**: Comprehensive error tracking and reporting
- **Performance Monitoring**: Response time and resource usage tracking
- **User Analytics**: Gameplay metrics and user behavior analysis
- **Health Checks**: System availability and performance monitoring

This architecture provides a solid foundation for real-time multiplayer gaming while maintaining code quality, performance, and scalability.