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
        
        socketHandler.emit('create_room', {
            min_stake: parseInt(minStake),
            username: gameManager.username
        });
        uiManager.showSuccess('Creating room...');
    }

    joinRoom(roomId = null) {
        const data = {
            username: gameManager.username
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
                    <span class="room-players">${room.player_count}/${room.max_players} players</span>
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
}