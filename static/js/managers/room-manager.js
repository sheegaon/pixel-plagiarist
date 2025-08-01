// Room management for Pixel Plagiarist
class RoomManager {
    constructor() {
        this.currentRoom = null;
        this.roomList = [];
    }

    createRoomWithStake(minStake) {
        if (!minStake || minStake <= 0) {
            uiManager.showError('Please enter a valid minimum stake');
            return;
        }
        
        const username = this.getUsername();
        socketHandler.emit('create_room', {
            min_stake: parseInt(minStake),
            username: username
        });
        uiManager.showSuccess('Creating room...');
    }

    joinRoom(roomId = null) {
        const username = this.getUsername();
        const data = {
            username: username
        };
        
        if (roomId) {
            data.room_id = roomId;
        }
        
        socketHandler.emit('join_room', data);
        uiManager.showSuccess('Joining room...');
    }

    joinRoomFromList(roomId) {
        this.joinRoom(roomId);
    }

    joinRoomByCode() {
        const roomCode = document.getElementById('roomCodeInputModal').value.trim();
        if (!roomCode) {
            uiManager.showError('Please enter a room code');
            return;
        }
        
        this.joinRoom(roomCode);
        uiManager.hideJoinCodeModal();
    }

    refreshRoomList() {
        socketHandler.requestRoomList();
    }

    get max_players() {
        return (window.GameConfig && window.GameConfig.MAX_PLAYERS) ? window.GameConfig.MAX_PLAYERS : 12;
    }

    updateRoomList(rooms) {
        this.roomList = rooms;
        const roomListElement = document.getElementById('roomList');
        if (!roomListElement) return;

        if (!rooms || rooms.length === 0) {
            roomListElement.innerHTML = '<p class="no-rooms">No active rooms found. Create one to get started!</p>';
            return;
        }

        roomListElement.innerHTML = rooms.map(room => `
            <div class="room-item clickable" data-room-id="${room.room_id}" title="Click to join room ${room.room_id}">
                <div class="room-info">
                    <span class="room-id">Room: ${room.room_id}</span>
                    <span class="room-players">${room.player_count}/${this.max_players} players</span>
                    <span class="room-stake">Min Stake: $${room.min_stake}</span>
                </div>
            </div>
        `).join('');

        // Add event listeners after creating the HTML
        const roomItems = roomListElement.querySelectorAll('.room-item.clickable');
        roomItems.forEach(item => {
            item.addEventListener('click', (e) => {
                const roomId = e.currentTarget.getAttribute('data-room-id');
                this.joinRoomFromList(roomId);
            });
        });
    }

    leaveRoom() {
        if (this.currentRoom) {
            socketHandler.emit('leave_room');
            this.currentRoom = null;
        }
    }

    updateRoomDisplay(roomId) {
        this.currentRoom = roomId;
        const roomInfo = document.getElementById('roomInfo');
        if (roomInfo) {
            roomInfo.textContent = roomId ? `Room: ${roomId}` : 'Room: -';
            if (roomId) {
                roomInfo.classList.remove('hidden');
            } else {
                roomInfo.classList.add('hidden');
            }
        }
    }

    getCurrentRoom() {
        return this.currentRoom;
    }

    setCurrentRoom(roomId) {
        this.currentRoom = roomId;
    }

    reset() {
        this.currentRoom = null;
        this.roomList = [];
        
        // Clear room display
        const roomInfo = document.getElementById('roomInfo');
        if (roomInfo) {
            roomInfo.textContent = 'Room: -';
        }
    }

    getUsername() {
        // Try to get username from gameManager first, then fallback to gameUserData
        if (window.gameManager && window.gameManager.username) {
            return window.gameManager.username;
        }
        
        // Fallback to the same source that GameManager uses
        return window.gameUserData ? window.gameUserData.username : 'Anonymous';
    }
}