import os
import threading
from datetime import datetime
from util.logging_utils import debug_log

# Global lock for thread-safe file writing
_log_lock = threading.Lock()


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
