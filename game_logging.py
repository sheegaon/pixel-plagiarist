import os
import csv
import threading
from datetime import datetime
from logging_utils import debug_log

# Global lock for thread-safe file writing
_log_lock = threading.Lock()

def log_game_summary(room_id, drawing_sets, votes, players, player_prompts):
    """
    Log game summary information to a global log file.
    
    Parameters
    ----------
    room_id : str
        The room ID for this game
    drawing_sets : list
        List of drawing sets from the game
    votes : dict
        Vote data indexed by set
    players : dict
        Player information
    player_prompts : dict
        Prompts assigned to each player
    """
    log_dir = os.path.join(os.path.dirname(__file__), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, 'game_summary.csv')
    
    # Check if file exists to determine if we need headers
    file_exists = os.path.exists(log_file)
    
    with _log_lock:
        try:
            with open(log_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write headers if file is new
                if not file_exists:
                    writer.writerow([
                        'timestamp', 'room_id', 'set_index', 'prompt', 
                        'original_player_username', 'original_player_id',
                        'first_copier_username', 'second_copier_username',
                        'original_votes', 'first_copy_votes', 'second_copy_votes'
                    ])
                
                timestamp = datetime.now().isoformat()
                
                # Write one row per drawing set
                for set_index, drawing_set in enumerate(drawing_sets):
                    original_id = drawing_set['original_id']
                    original_username = players.get(original_id, {}).get('username', 'Unknown')
                    original_prompt = player_prompts.get(original_id, 'Unknown')
                    
                    # Find copiers
                    copiers = []
                    for drawing in drawing_set['drawings']:
                        if drawing['type'] == 'copy':
                            copier_username = players.get(drawing['player_id'], {}).get('username', 'Unknown')
                            copiers.append(copier_username)
                    
                    # Pad copiers list to exactly 2 entries
                    while len(copiers) < 2:
                        copiers.append('')
                    
                    # Count votes for each drawing
                    set_votes = votes.get(set_index, {})
                    vote_counts = {}
                    
                    for drawing in drawing_set['drawings']:
                        drawing_id = drawing['id']
                        vote_counts[drawing_id] = sum(1 for vote in set_votes.values() if vote == drawing_id)
                    
                    # Get vote counts (original first, then copies in order)
                    original_drawing_id = f"original_{original_id}"
                    original_votes = vote_counts.get(original_drawing_id, 0)
                    
                    copy_votes = []
                    for drawing in drawing_set['drawings']:
                        if drawing['type'] == 'copy':
                            copy_votes.append(vote_counts.get(drawing['id'], 0))
                    
                    # Pad copy votes to exactly 2 entries
                    while len(copy_votes) < 2:
                        copy_votes.append(0)
                    
                    writer.writerow([
                        timestamp, room_id, set_index, original_prompt,
                        original_username, original_id,
                        copiers[0], copiers[1],
                        original_votes, copy_votes[0], copy_votes[1]
                    ])
                    
        except Exception as e:
            debug_log("Error writing game summary log", None, room_id, {'error': str(e)})

def log_flagged_image(room_id, image_data, drawer_username, drawer_id, reporter_username, reporter_id, phase):
    """
    Save flagged images to the flagged_images folder with metadata.
    
    Parameters
    ----------
    room_id : str
        The room ID where the image was flagged
    image_data : str
        Base64 image data
    drawer_username : str
        Username of who drew the image
    drawer_id : str
        Player ID of who drew the image  
    reporter_username : str
        Username of who reported the image
    reporter_id : str
        Player ID of who reported the image
    phase : str
        Game phase when image was flagged (copying/voting)
    """
    flagged_dir = os.path.join(os.path.dirname(__file__), 'flagged_images')
    os.makedirs(flagged_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename_base = f"{timestamp}_{room_id}_{drawer_id}"
    
    with _log_lock:
        try:
            # Save image data
            import base64
            import re
            
            # Extract base64 data (remove data:image/png;base64, prefix if present)
            if image_data.startswith('data:image'):
                image_data = re.sub(r'^data:image/[^;]+;base64,', '', image_data)
            
            image_path = os.path.join(flagged_dir, f"{filename_base}.png")
            with open(image_path, 'wb') as f:
                f.write(base64.b64decode(image_data))
            
            # Save metadata
            metadata_path = os.path.join(flagged_dir, f"{filename_base}_metadata.txt")
            with open(metadata_path, 'w', encoding='utf-8') as f:
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Room ID: {room_id}\n")
                f.write(f"Phase: {phase}\n")
                f.write(f"Drawer Username: {drawer_username}\n")
                f.write(f"Drawer ID: {drawer_id}\n")
                f.write(f"Reporter Username: {reporter_username}\n")
                f.write(f"Reporter ID: {reporter_id}\n")
            
            debug_log("Image flagged and saved", reporter_id, room_id, {
                'drawer': drawer_username,
                'phase': phase,
                'filename': filename_base
            })
            
        except Exception as e:
            debug_log("Error saving flagged image", reporter_id, room_id, {'error': str(e)})