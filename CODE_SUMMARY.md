# Summary of Code Modules in Pixel Plagiarist

# Overview of Socket Handlers

The socket handlers in Pixel Plagiarist form a modular, event-driven system built on Flask-SocketIO, designed to manage real-time multiplayer interactions in a drawing game. They separate concerns into distinct handler classes (Connection, Room, Game, Admin), all orchestrated through a centralized game state manager (`GameStateSH`). This architecture ensures scalability, easy debugging, and clear separation of logic: connections handle lifecycle events, rooms manage lobby operations, games process in-game actions, and admins provide oversight tools.

All handlers rely on the global `GAME_STATE_SH` instance (from `game_state.py`) for shared state access, avoiding direct coupling between handlers. Events are registered in `setup.py` via `socketio.on_event`, and most operations involve:
- Validating player/room existence.
- Updating state in `GAME_STATE_SH`.
- Emitting events to clients (e.g., via `emit` for targeted responses or broadcasts).
- Broadcasting global updates like room lists using `broadcast_room_list`.

For a new dev: This system is stateless per-handler but stateful via `GAME_STATE_SH`, so always check/modify state atomically to avoid race conditions (e.g., during disconnects). Debug with `debug_log` calls (from `util.logging_utils`), and test in `TESTING_MODE=true` for faster timers. Handlers are initialized with a `socketio` instance for emitting, but static methods (e.g., in ConnectionHandlers) don't need it if they don't emit.

Below, I'll break down each handler, their key methods, interdependencies, and data flows. I'll include code snippets, event names, and tips for extension.

#### 1. Centralized State Management: GameStateSH
This is the "glue" that ties all handlers together. It's a singleton-like class (`GAME_STATE_SH`) instantiated once in `game_state.py`.

- **Key Attributes**:
  - `GAMES`: Dict of `room_id` (str) to `GameStateGL` objects (from `game_logic/game_state.py`). Each `GameStateGL` holds room-specific state like players, phase ("waiting", "drawing", etc.), drawings, votes, and timers.
  - `PLAYERS`: Dict of `player_id` (str, typically `request.sid` from SocketIO) to `room_id`.

- **Core Methods** (used across handlers):
  - `get_game(room_id)`: Retrieves a `GameStateGL` instance.
  - `get_player_room(player_id)`: Gets a player's room.
  - `add_game(room_id, game)` / `remove_game(room_id)`: Manages rooms.
  - `add_player(player_id, room_id)` / `remove_player(player_id)`: Tracks player-room associations.
  - `ensure_default_room()`: Checks for a waiting Bronze-level room (min stake from `CONSTANTS['MIN_STAKE']`); creates one if none exists (UUID-generated `room_id`). Called on startup, connects, disconnects, and cleanups to guarantee at least one joinable room.
  - `check_and_create_default_room(socketio=None)`: Wrapper for `ensure_default_room()` that broadcasts updates if a new room is created.

- **Utilities** (exported in `__init__.py`):
  - `get_room_info()`: Returns a list of dicts for waiting rooms only, including `room_id`, `player_count`, `max_players`, `room_level()` (derived from stake), `phase`, `created_at`, and detailed `players` list (with IDs and usernames). Sorts newest first. Filters out non-waiting rooms to show only joinable lobbies.
  - `broadcast_room_list(socketio=None)`: Emits `'room_list_updated'` with rooms from `get_room_info()`. Uses provided `socketio` for background threads or global `emit` otherwise.

**Interdependency Note**: Every handler accesses `GAME_STATE_SH` for reads/writes. For example, disconnects remove players/rooms and call `ensure_default_room()` to maintain availability. If adding a new handler, always import `GAME_STATE_SH` and use its methods to avoid direct dict manipulation (prevents bugs like orphaned players).

**New Dev Tip**: If debugging state inconsistencies (e.g., player in `PLAYERS` but not in a game's `players`), use AdminHandlers' `debug_game_state` event to inspect totals and per-room details. State is in-memory only—no DB persistence for games—so restarts wipe everything.

#### 2. Handler Initialization and Registration (setup.py)
This module wires everything together. Called once in `server.py` via `setup_socket_handlers(socketio)`.

- **Process**:
  1. Instantiate handler classes: `ConnectionHandlers(socketio)`, `RoomHandlers(socketio)`, etc. (Most need `socketio` for emits; static methods don't.)
  2. Call `GAME_STATE_SH.ensure_default_room()` to bootstrap a default room.
  3. Register events with `socketio.on_event(event_name, handler_method)`.

- **Registered Events Table** (for quick reference):

| Category | Event Name | Handler Class | Method | Description |
|----------|------------|---------------|--------|-------------|
| Connection | `'connect'` | ConnectionHandlers | `handle_connect` | Logs connect, sends room list, creates default room if none. |
| Connection | `'disconnect'` | ConnectionHandlers | `handle_disconnect` | Removes player, cleans empty rooms, ensures default, broadcasts updates. |
| Connection | `'request_room_list'` | ConnectionHandlers | `handle_request_room_list` | Sends current room list. |
| Room | `'create_room'` | RoomHandlers | `handle_create_room` | Creates room, adds player, starts countdown if min players met. |
| Room | `'join_room'` | RoomHandlers | `handle_join_room` | Joins room, adds player, starts/continues countdown. |
| Room | `'leave_room'` | RoomHandlers | `handle_leave_room` | Leaves room (waiting/results only), cleans if empty, cancels countdown if below min. |
| Game | `'submit_original'` | GameHandlers | `handle_submit_original` | Submits original drawing to `drawing_phase`. |
| Game | `'submit_copy'` | GameHandlers | `handle_submit_copy` | Submits copy to `copying_phase`. |
| Game | `'submit_vote'` | GameHandlers | `handle_submit_vote` | Submits vote to `voting_phase`. |
| Game | `'request_review'` | GameHandlers | `handle_request_review` | Sends original drawing for 5s review. |
| Admin | `'debug_game_state'` | AdminHandlers | `handle_debug_game_state` | Emits debug info (games, players). |
| Admin | `'force_start_game'` | AdminHandlers | `handle_force_start_game` | Starts waiting game immediately. |
| Admin | `'cleanup_rooms'` | AdminHandlers | `handle_cleanup_rooms` | Removes empty rooms, ensures default. |

**New Dev Tip**: To add a new event (e.g., `'chat_message'`), create a new method in an existing handler or a new class, then register it in `setup.py`. Pass `socketio` if needed for emits. Test by emitting from client JS and watching server logs.

#### 3. ConnectionHandlers: Lifecycle Management
Handles client connect/disconnect and room list requests. Static methods, so no instance state.

- **handle_connect()**: 
  - Logs connect with `debug_log`.
  - Emits `'room_list_updated'` with current rooms.
  - If no rooms, calls `ensure_default_room()` and re-emits updated list.
  - Interacts with: `get_room_info()`, `GAME_STATE_SH.ensure_default_room()`, `broadcast_room_list` (indirectly).

- **handle_disconnect()**:
  - Gets `player_id = request.sid`.
  - If player in `PLAYERS`, gets room, removes from `PLAYERS` and game's `players`.
  - If room empty, removes game, ensures default, broadcasts room list.
  - If room not empty, emits `'players_updated'` to room and broadcasts room list.
  - Interacts with: `GAME_STATE_SH` (remove_player, remove_game), `broadcast_room_list`.

- **handle_request_room_list(data=None)**:
  - Simply emits `'room_list_updated'` with `get_room_info()`.

**Data Flow**: Connect triggers room list sync; disconnect cleans state and notifies all clients of changes. This ensures the home screen always shows accurate lobbies.

**New Dev Tip**: Disconnects can happen mid-game—game logic (`GameStateGL.remove_player`) handles phase-specific cleanup (e.g., abort if too few players). If adding reconnect logic, check `player_id` in `PLAYERS` on connect and re-join room.

#### 4. RoomHandlers: Lobby Operations
Manages room creation/joining/leaving. Instance methods use `self.socketio`.

- **handle_create_room(data)**:
  - Gets `player_id`, `username`, `stake`.
  - Generates `room_id` (UUID upper 8 chars).
  - Creates `GameStateGL(room_id, stake)`, adds to `GAMES`.
  - Adds player to game/`PLAYERS`, joins SocketIO room.
  - If min players met, starts countdown (`timer.start_joining_countdown`) or game if max.
  - Emits `'room_created'`, `'players_updated'` to room, broadcasts room list.
  - Interacts with: `GAME_STATE_SH` (add_game, add_player), `GameStateGL.add_player/start_game`, `broadcast_room_list`.

- **handle_join_room(data)**:
  - Similar to create: Validates room not full, adds to `PLAYERS`/game, joins SocketIO room.
  - Starts/continues countdown if min met; sends existing countdown to late joiners.
  - Emits `'joined_room'`, `'players_updated'`, broadcasts room list.
  - Interacts with: Same as create, plus timer checks.

- **handle_leave_room(data=None)**:
  - Validates in room and phase allows (waiting/results).
  - Removes from game/`PLAYERS`, leaves SocketIO room.
  - If empty, removes game, ensures default.
  - If below min and countdown active, cancels it (sets flag, emits `'countdown_cancelled'`).
  - Emits `'room_left'`, `'players_updated'`, broadcasts room list.
  - Interacts with: `GAME_STATE_SH` (remove_player/game), `broadcast_room_list`.

**Data Flow**: These update `GAMES`/`PLAYERS` and trigger game starts via timers in `GameStateGL`. Broadcasts keep all clients (even non-joined) synced on lobbies.

**New Dev Tip**: Room IDs are uppercase 8-char UUIDs—unique but short for UX. If extending (e.g., private rooms), add params to `data` and validate in `GameStateGL`.

#### 5. GameHandlers: In-Game Actions
Processes phase-specific submissions. All methods get `player_id = request.sid`, validate room/game, then delegate to `GameStateGL`'s phase objects (e.g., `drawing_phase.submit_drawing`).

- **handle_submit_original(data)**: Submits `drawing_data` to `drawing_phase`.
- **handle_submit_copy(data)**: Submits `drawing_data` for `target_id` to `copying_phase`.
- **handle_submit_vote(data)**: Submits `drawing_id` to `voting_phase`.
- **handle_request_review(data)**: If `target_id` valid, emits `'review_drawing'` with original (5s duration).

**Interacts with**: `GAME_STATE_SH` (get room/game), `GameStateGL` phases (which may emit progress updates via `socketio`).

**Data Flow**: These are player-initiated; server validates phase (implicit via `game.drawing_phase` etc.) and updates drawings/votes in `GameStateGL`. Phases handle broadcasts (e.g., all submissions complete → next phase).

**New Dev Tip**: Phases are in `game_logic/`—extend there for new actions. Drawings are base64 strings; enforce size limits to prevent abuse.

#### 6. AdminHandlers: Oversight Tools
For debugging/cleanup. Similar structure.

- **handle_debug_game_state(data=None)**: Emits totals and per-game info.
- **handle_force_start_game(data)**: Starts waiting game, logs as admin action.
- **handle_cleanup_rooms(data=None)**: Removes empty games, ensures default, broadcasts.

**Interacts with**: `GAME_STATE_SH` (iterates `GAMES`), `broadcast_room_list`.

**New Dev Tip**: These are admin-only—add auth if exposing publicly. Useful for monitoring; extend for metrics like active players.

#### 7. How Handlers Work Together: Interdependencies and Flows
- **Startup Flow**: `server.py` → `setup_socket_handlers` → registers events, ensures default room.
- **Player Join Flow**: Connect → room list → join_room → add to state → broadcast → countdown if ready → game start (delegates to `GameStateGL`).
- **Game Play Flow**: In-game events → game handlers → phase updates → broadcasts (via phases).
- **Disconnect Flow**: Disconnect → remove from state → clean room if empty → ensure default → broadcast.
- **Global Sync**: Any state change (join/leave/create/disconnect/cleanup) calls `broadcast_room_list` to update all clients.
- **Error Handling**: Most methods emit error messages (e.g., `'join_room_error'`); use `debug_log` for server-side tracing.
- **Thread Safety**: SocketIO handles concurrency; but for timers (background threads), pass `socketio` to `broadcast_room_list`.

**Potential Pitfalls for New Devs**:
- **Orphaned State**: Always pair add/remove (e.g., add_player with join_room).
- **Phase Locks**: Can't leave mid-game—enforced in leave_room.
- **Broadcast Overuse**: Only broadcast room list on changes; use room-specific emits for performance.
- **Extension Example**: To add a 'chat' handler, create `ChatHandlers`, register in setup.py, store messages in `GameStateGL`, emit to room.
- **Testing**: Use multiple browser tabs; enable `DEBUG_MODE=true` for logs. Simulate disconnects by closing tabs.

This setup keeps code organized—focus on one handler for specific features while relying on `GAME_STATE_SH` for cohesion. If adding complex logic, consider adding to `GameStateGL` first.

# Game Logic

This guide dives deeper into the game logic code, which is primarily housed in the `game_logic/` directory. The logic is modular, with a central game state manager coordinating specialized phase handlers, timers, and scoring. This architecture (detailed in `ARCHITECTURE.md`) ensures separation of concerns, scalability, and ease of maintenance.

The game is a real-time multiplayer experience built on Flask with Socket.IO for WebSocket communication. Game instances are room-based, supporting 3-12 players. Players stake tokens (Bits) into a prize pool, draw originals based on prompts, copy others' work, vote to identify originals, and earn rewards based on deception and detection skills. The code emphasizes server-authoritative state to prevent cheating, with client-side predictions for responsiveness.

Below, I'll break down the key modules, their classes, methods, and interactions. References to code snippets are illustrative; always check the source files for exact implementations.

## Core Structure and Entry Point

The `game_logic/__init__.py` file exports the main class:
```python
from .game_state import GameStateGL
__all__ = ['GameStateGL']
```
- `GameStateGL` is the central class for managing a single game room. All game logic revolves around instances of this class.

## Central Game State Management (`game_state.py`)

`GameStateGL` orchestrates the entire game flow. It initializes with a room ID, prize per player (stake), and entry fee. It tracks global state like players, phase, prompts, drawings, votes, and more.

### Key Attributes:
- `room_id`: Unique identifier for the game room.
- `players`: Dict of player data (ID, username, balance, stake, etc.).
- `phase`: Current game stage ("waiting", "drawing", "copying", "voting", "results", or "ended_early").
- `player_prompts`: Dict mapping players to unique drawing prompts (from `util/config.py`'s PROMPTS list).
- `original_drawings` / `copied_drawings`: Dicts storing base64-encoded image data.
- `drawing_sets`: List of sets for voting (each contains one original + copies).
- `votes`: Dict of votes per drawing set.
- `prize_per_player` / `entry_fee`: Configurable from constants; affects token economy.
- Modular components: Instances of `Timer`, `DrawingPhase`, `CopyingPhase`, `VotingPhase`, and `ScoringEngine` are attached here for phase-specific logic.

### Key Methods:
- `__init__(self, room_id, prize_per_player=CONSTANTS['MIN_STAKE'], entry_fee=CONSTANTS['ENTRY_FEE'])`: Sets up the room with defaults (e.g., max 12 players, min 3). Initializes empty states and modular handlers.
- `add_player(self, player_id, username)`: Adds a player if room isn't full and balance suffices. Deducts entry fee (stored in DB via `util/db.py`). Triggers countdown if min players reached. Returns True on success.
- `remove_player(self, player_id, socketio)`: Handles disconnection. Refunds stake if game not started; ends game early if below min players.
- `start_game(self, socketio)`: Called when countdown finishes or min players met. Deducts stakes, assigns unique prompts, transitions to "drawing" phase, and starts `DrawingPhase`.
- `end_game_early(self, socketio)`: Refunds stakes (minus entry fee) if insufficient players; records in DB.
- `room_level(self)`: Returns "Bronze", "Silver", or "Gold" based on stake level.

### Interactions:
- Relies on `util/db.py` for player data persistence (e.g., `get_or_create_player`, `update_player_balance`).
- Uses `socketio` to emit events like 'game_started' or 'game_ended_early'.
- Coordinates phase transitions by calling methods on attached phase handlers (e.g., `self.drawing_phase.start_phase(socketio)`).
- Logs extensively via `util/logging_utils.py`'s `debug_log`.

**Note**: Player balances are tracked in-memory for the session but synced to DB at key points (e.g., game end). Stakes contribute to a prize pool redistributed in scoring.

## Timer Management (`timer.py`)

The `Timer` class handles all timing, including countdowns and phase durations. Configured via `util/config.py`'s TIMER_CONFIG.

### Key Attributes:
- `game`: Reference to `GameStateGL`.
- Timers: `start_timer`, `countdown_timer`, `phase_timer` (threading.Timer instances).

### Key Methods:
- `start_joining_countdown(self, socketio)`: Starts a countdown (e.g., 30s) for player joining. Emits 'joining_countdown_started'. Prevents duplicates.
- `stop_joining_countdown(self)`: Cancels the joining timer.
- `start_phase_timer(self, socketio, seconds, callback)`: Starts a phase-specific timer; emits 'phase_timer'. Cancels existing timers first.
- `cancel_phase_timer(self)`: Stops the current phase timer.
- `_countdown_finished(self, socketio)`: Internal; calls `game.start_game(socketio)`.
- Static getters: `get_drawing_timer_duration()`, etc., return values from TIMER_CONFIG.

### Interactions:
- Uses `threading.Timer` for non-blocking delays.
- Emits Socket.IO events for client-side countdowns.
- Called by `GameStateGL` during phase starts (e.g., in `start_game`).

**Note**: In testing mode (env var TESTING_MODE=true), timers are shortened (e.g., to 5s) for rapid iteration.

## Drawing Phase (`drawing_phase.py`)

Handles the "drawing" phase where players create originals.

### Key Class: `DrawingPhase`
- Initialized with `game` reference.

### Key Methods:
- `start_phase(self, socketio)`: Sets phase to "drawing", deducts stakes if not already, emits 'phase_changed' with individual prompts, starts timer to transition to copying.
- `submit_drawing(self, player_id, drawing_data, socketio, check_early_advance=True)`: Validates phase/player/submission status. Stores base64 data in `game.original_drawings`. Marks player as drawn. Emits 'original_submitted'. Saves to log via `save_drawing`. Checks for early advance.
- `check_early_advance(self, socketio)`: If all players submitted, cancels timer, emits 'early_phase_advance', and starts copying phase.

### Interactions:
- Validates against game phase and player state.
- Uses `util/logging_utils.py` for debugging (e.g., image saving).
- Early advance prevents waiting if everyone finishes quickly.

## Copying Phase (`copying_phase.py`)

Manages "copying" phase: assigning targets, viewing, and submitting copies.

### Key Class: `CopyingPhase`
- Attributes: `phase_started`, `assignments_made`, `phase_start_time` (for min time checks).

### Key Methods:
- `start_phase(self, socketio)`: Sets phase, assigns tasks if not done, sends targets to players, starts timer to voting.
- `_assign_copying_tasks(self)`: Shuffles players; assigns 1-2 copy targets (cyclic, avoiding self). Sets `game.copy_assignments` and player 'copies_to_make'.
- `_send_copying_phase(self, socketio)`: Emits 'copying_phase' with target drawings (base64 from originals).
- `submit_drawing(self, player_id, target_id, drawing_data, socketio, check_early_advance=True)`: Validates, stores in `game.copied_drawings[player_id][target_id]`, increments completed copies. Emits 'copy_submitted'. Checks early advance.
- `check_early_advance(self, socketio)`: If all completed (with min 5s elapsed), advances to voting.
- `reset_for_new_game(self)`: Resets flags for new games.

### Interactions:
- Assignments ensure balanced copying (e.g., in 3-player game, each copies 1).
- Supports "View Again" (client-side, not in this code).
- Blank submissions handled in voting.

## Voting Phase (`voting_phase.py`)

Handles "voting" phase: creating sets, collecting votes, exclusions.

### Key Class: `VotingPhase`
- Attributes: `drawing_sets_created`, `current_set_started`, `set_start_time`.

### Key Methods:
- `start_phase(self, socketio)`: Sets phase, creates sets if not done, starts first set.
- `_create_drawing_sets(self)`: For each original, builds set with original + expected copies (uses BLANK_CANVAS if missing). Shuffles order. Stores in `game.drawing_sets`.
- `start_voting_on_set(self, socketio)`: If sets remain, emits 'voting_set' with anonymized drawings (IDs only, no player info). Starts timer to next set or results.
- `submit_vote(self, player_id, set_index, drawing_id, socketio)`: Validates eligibility (not own work), hasn't voted. Stores in `game.votes[set_index]`. Emits 'vote_cast'. Checks early advance.
- `validate_vote(self, player_id, drawing_id)`: Checks player in game, eligible (via `get_eligible_voters_for_set`), not voted, valid ID.
- `get_eligible_voters_for_set(self, drawing_set)`: All players except those who drew/copied in this set.
- `next_voting_set(self, socketio)`: Increments set index, starts next.
- `check_early_advance(self, socketio)`: If all eligible voted (with min 5s), advances.

### Interactions:
- Uses BLANK_CANVAS (hardcoded base64 white image) for missing copies.
- Exclusions prevent bias; eligible voters vary per set.
- Multiple sets ensure all originals are voted on.

## Scoring Engine (`scoring_engine.py`)

Final phase: Calculates scores, distributes tokens.

### Key Class: `ScoringEngine`
- Attribute: `results_calculated` (prevents duplicates).

### Key Methods:
- `calculate_results(self, socketio)`: If not done, sets phase to "results", processes each set, distributes tokens, logs summary, emits 'game_results' with balances/details.
- `calculate_drawing_set_scores(self, set_index)`: Counts votes per drawing. Awards: 100pts/vote for originals, 150pts/vote for copies. +25pts for correct voter guesses. Only for active players.
- `distribute_tokens(self, set_index, scores)`: Proportional to scores; total pool = sum stakes. (Code truncated in doc, but implies DB updates.)
- `_log_game_summary(self)`: (Truncated, but logs to global file.)
- `_record_game_completion(self)`: For each player, calculates stats (originals drawn, copies made, votes, correct votes, points), records via `util/db.py`.

### Additional Function:
- `is_blank_image(base64_data, ...)`: Uses PIL to check if image is all white/transparent. Logs/saves for debugging. Treats invalid as blank.

### Interactions:
- Only scores active players; skips disconnected.
- Emits detailed results for UI display.
- Integrates with DB for completion records.

## Overall Game Flow and Integration

1. **Room Creation/Joining**: `GameStateGL` instance created. Players added; countdown via `Timer`.
2. **Start Game**: Prompts assigned, `DrawingPhase` starts.
3. **Phase Transitions**: Each phase starts its timer; submissions trigger early advances. On timeout/advance: next phase (drawing -> copying -> voting -> results).
4. **End Game**: Scoring, DB sync, results emitted. New default room created.
5. **Error Handling**: Extensive validation/logging. Graceful disconnections.

**Debugging Tips**: Enable DEBUG_MODE env var. Use `ai_player.py` for testing. Check logs for `debug_log` outputs.

This covers the core logic. Review `socket_handlers/` for how these tie into WebSocket events, and `util/config.py` for tunables. If extending (e.g., new phases), add to `GameStateGL` and hook into flow. Questions? Refer to `ARCHITECTURE.md` for diagrams.

# Frontend JavaScript Summary

The frontend of Pixel Plagiarist is built with modular Vanilla JavaScript classes, focusing on real-time multiplayer drawing game mechanics. It handles UI views, game phases (waiting, drawing, copying, voting, results), player interactions, and Socket.IO communication. Managers delegate tasks to specialized classes, coordinated by `GameManager` and initialized in `main.js`. Global configs (e.g., `GameConfig`) from `util/config.json` control timers, balances, and canvas sizes. The code emphasizes state management, error handling, and resets for new games. Below is a file-by-file summary, including key classes, methods, and interactions.

#### `room-manager.js`: Manages room creation, joining, and listing.
- **Class**: `RoomManager`
- **Purpose**: Handles room operations, including creating/joining rooms with stakes, refreshing lists, and leaving. Tracks current room and list of active rooms.
- **Key Attributes**: `currentRoom` (string), `roomList` (array of room objects).
- **Key Methods**:
  - `createRoomWithStake(stake)`: Emits 'create_room' with stake and username; validates input.
  - `joinRoom(roomId)`: Emits 'join_room'; handles random or specific joins.
  - `joinRoomFromList(roomId)` / `joinRoomByCode()`: Variants for list clicks or code input.
  - `refreshRoomList()`: Requests room list via socket.
  - `updateRoomList(rooms)`: Renders room list HTML with clickable items (e.g., player count, level: Bronze/Silver/Gold).
  - `leaveRoom()`: Emits 'leave_room'.
  - `updateRoomDisplay(roomId)`: Updates UI room info.
  - `reset()`: Clears room data and UI.
- **Interactions**: Uses `socketHandler` for emits; `uiManager` for messages/modals. Gets username from `gameManager` or global `gameUserData`.
- **Notes**: Supports max players from config (default 12). Renders "no rooms" message if empty.

#### `results-manager.js`: Processes and displays game results.
- **Class**: `ResultsManager`
- **Purpose**: Handles final results, standings, and balance updates post-game.
- **Key Attributes**: `finalStandings` (sorted array of player objects with id, name, tokens).
- **Key Methods**:
  - `displayResults(data)`: Processes standings, shows 'results' view, renders UI, updates/saves balance.
  - `savePlayerBalance(balance)`: POSTs balance to `/api/player/balance/{username}`.
  - `processStandings(data)`: Maps/sorts balances by tokens descending.
  - `renderResultsInterface()`: Builds HTML grid with standings (ranks, crowns for #1) and "Return Home" button.
  - `generateStandingsHTML()`: Creates ranked list HTML, highlighting current player.
  - `reset()`: Clears standings and UI grid.
- **Interactions**: Uses `playerManager` for balance updates; `uiManager` for view switch. Fetches via API for persistence.
- **Notes**: Rounds tokens; highlights top 3 and current player.

#### `voting-manager.js`: Manages voting phase UI and submissions.
- **Class**: `VotingManager`
- **Purpose**: Displays voting sets, handles selections/submissions, and exclusions (e.g., can't vote on own work).
- **Key Attributes**: `selectedDrawingId`, `voteSubmitted`, `total_sets`, `set_index`, `drawings` (array).
- **Key Methods**:
  - `initializeVoting(data)`: Sets up view, displays interface, starts timer; hides submit button (auto-submits on select).
  - `displayVotingInterface(data)`: Renders instructions with prompt/set info.
  - `displayVotingOptions(drawings, observationOnly)`: Builds grid of images with flag buttons; adds click listeners for votes if not observation.
  - `selectAndSubmitVote(drawingId, element)`: Selects (highlights), emits 'submit_vote', disables further votes.
  - `handleVoteCast(data)`: Updates vote count UI.
  - `showExcludedVoting(data)`: Displays observation-only view for excluded players.
  - `reset()`: Clears state and resets UI elements.
- **Interactions**: Emits via `socketHandler`; uses `gameStateManager` for timers. Flags images for moderation.
- **Notes**: Auto-submits on selection; supports observation mode with no clicks.

#### `drawing-manager.js`: Handles original drawing phase.
- **Class**: `DrawingManager`
- **Purpose**: Manages prompt display, canvas submission, and auto-submit on timeout.
- **Key Attributes**: `currentPrompt`, `drawingSubmitted`, `timeRemaining`.
- **Key Methods**:
  - `initializeDrawing(data)`: Sets prompt, resets canvas/button, shows view, starts timer.
  - `submitDrawing()`: Validates phase, gets canvas data, emits 'submit_original', disables button.
  - `autoSubmitDrawing()`: Submits if not already done (even empty).
  - `reset()`: Clears prompt/state, resets UI.
- **Interactions**: Relies on global `drawingCanvas` for data/clear; `gameStateManager` for timers/phases.
- **Notes**: Validates against current phase to prevent out-of-phase submits.

#### `player-manager.js`: Tracks player data and balances.
- **Class**: `PlayerManager`
- **Purpose**: Manages player ID, balance, list updates, and loading from server.
- **Key Attributes**: `playerId`, `currentBalance` (starts at config INITIAL_BALANCE), `playerList`.
- **Key Methods**:
  - `loadPlayerBalance()`: Fetches balance from `/api/player/balance/{username}` on init.
  - `setPlayerId(id)` / `getPlayerId()`: ID management.
  - `setBalance(balance)` / `adjustBalance(amount)`: Updates value and UI.
  - `updateBalanceDisplay()`: Renders balance in UI.
  - `updatePlayerList(players)`: Builds HTML list with names, balances, ready indicators; highlights self.
  - `reset()`: Resets to defaults.
- **Interactions**: Uses global `gameUserData.username`; async fetch for persistence.
- **Notes**: Rounds balances; falls back to defaults on load failure.

#### `copying-manager.js`: Oversees copying phase, including targets and reviews.
- **Class**: `CopyingManager`
- **Purpose**: Handles multiple copy targets, submissions, "view again", and auto-submit.
- **Key Attributes**: `copyTargets` (array), `currentCopyIndex`, `submittedCopies`, `initialized`.
- **Key Methods**:
  - `initializeCopyingPhase(data)`: Sets targets if new, shows view, starts first copy; skips duplicates.
  - `startNextCopy()`: Renders current target UI with "View Again" button.
  - `submitCurrentCopy()`: Validates, gets canvas data, emits 'submit_copy', advances index.
  - `requestReview(targetId)`: Emits 'request_review' for 5s overlay.
  - `showReviewOverlay(drawingUrl, duration)`: Displays timed image overlay.
  - `autoSubmitRemainingCopies()`: Submits empty canvases for unfinished copies.
  - `reset()`: Clears state and UI.
- **Interactions**: Uses global `drawingCanvas` (copying variant); timers from config.
- **Notes**: Prevents re-init with same data; creates empty PNG for autosubmits.

#### `game-state-manager.js`: Tracks overall game phase and timers.
- **Class**: `GameStateManager`
- **Purpose**: Manages phase transitions, data storage, and global timers.
- **Key Attributes**: `currentPhase` (e.g., 'waiting'), `gameData`, `timeRemaining`, `timer`.
- **Key Methods**:
  - `setPhase(phase)`: Updates phase and UI display.
  - `setGameData(data)`: Merges game data.
  - `startTimer(duration)`: Starts countdown interval, updates UI.
  - `clearTimer()`: Stops interval.
  - `updateTimerDisplay()` / `updatePhaseDisplay()`: Renders time/phase.
  - `reset()`: Clears to defaults.
- **Interactions**: Used by phase managers for synchronization.
- **Notes**: Formats time as MM:SS; no phase-specific logic here.

#### `game-manager.js`: Central coordinator delegating to other managers.
- **Class**: `GameManager`
- **Purpose**: Initializes managers, delegates methods, handles socket events, resets game.
- **Key Attributes**: `username` (from global), `managersInitialized`.
- **Key Methods**:
  - `initializeManagers()`: Creates global instances (e.g., `roomManager`).
  - Delegation: e.g., `createRoomWithStake()` calls `roomManager`'s; similar for join/submit.
  - Socket handlers: e.g., `handleRoomCreated(data)` updates managers/views.
  - `returnHome()`: Leaves room, resets, reloads balance/room list.
  - `resetAllManagers()`: Calls reset on all.
  - `cleanup()`: Resets managers and clears UI.
- **Interactions**: Bridges socket events to managers; uses `uiManager` for views.
- **Notes**: Ensures single init; getters for compatibility.

#### `main.js`: Application entry point and orchestration.
- **Class**: `PixelPlagiarist`
- **Purpose**: Initializes everything: config load, modules, events, UI. Manages lifecycle.
- **Key Attributes**: `initialized`, `modules` (Map), `eventListeners` (array).
- **Key Methods**:
  - `init()`: Loads config, initializes modules (e.g., socket, canvas, managers), sets listeners/state.
  - `loadConfiguration()`: Fetches `util/config.json` variants, updates `GameConfig`.
  - `initializeModules()`: Sets up socket, asset manager, canvas, etc.
  - `setupEventListeners()`: Adds DOM/socket listeners for phases/actions.
  - `setupInitialState()`: Shows home, connects socket, requests rooms.
  - `reset()`: Cleans up and re-inits.
  - `getDebugInfo()`: Returns app state for debugging.
- **Interactions**: Creates global `pixelPlagiarist`; handles errors with fallback UI.
- **Notes**: Async init; debug mode for localhost. Truncated code suggests more event handling.

#### `ui-manager.js`: General UI utilities and view management.
- **Class**: `UIManager`
- **Purpose**: Handles views, messages, timers, modals, and responsive elements.
- **Key Attributes**: `timers` (Map of intervals), `currentView`.
- **Key Methods**:
  - `showView(viewName)`: Switches screens by ID/class.
  - `showError/Success(message)`: Displays timed messages.
  - `startTimer(elementId, seconds, callback)`: Countdown with UI update/expiry.
  - `clearAllTimers()`: Stops all.
  - Modal methods: e.g., `showJoinCodeModal()`, `hideModal(id)`.
  - `updateCanvasSize()`: Responsive canvas scaling.
  - `initResponsive()` / `setupKeyboardNavigation()`: Event setups.
  - `handleError(error)`: Logs and shows message.
- **Interactions**: Used universally for UI changes/timers.
- **Notes**: Supports loading states, keyboard (Esc/Enter), and element enable/disable.

**Overall Architecture Notes**: Modular delegation reduces coupling; globals (e.g., `gameManager`) allow access. Socket.IO drives state changes. Resets ensure clean new games. Config-driven for easy tweaks (timers, balances). For development, use `pixelPlagiarist.getDebugInfo()` in console.