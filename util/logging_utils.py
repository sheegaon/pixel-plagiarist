# Logging utilities for Pixel Plagiarist server
import logging
import os
import base64
from datetime import datetime
from util.config import CONSTANTS


def setup_logging():
    """
    Configure logging for the application.
    
    Returns
    -------
    logging.Logger
        Configured logger instance
    """
    # Configure logging
    log_folder = os.path.join(os.getcwd(), 'logs')
    os.makedirs(log_folder, exist_ok=True)
    log_file_path = os.path.join(log_folder, f'pixel_plagiarist_{datetime.now():%Y-%m-%d_%H%M%S}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file_path, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger(__name__)
    
    # Initialize debug mode logging
    if CONSTANTS['debug_mode']:
        logger.info("DEBUG MODE ENABLED - All user interactions will be logged")
    else:
        logger.info("Debug mode disabled - Set DEBUG_MODE=true to enable detailed logging")
    
    return logger


def save_drawing(image_data, player_id, room_id, image_type, target_id=None):
    """
    Save image data to logs/drawings/ folder for debugging purposes.
    
    Parameters
    ----------
    image_data : str
        Base64 encoded image data
    player_id : str
        ID of the player who submitted the image
    room_id : str
        ID of the room where the image was submitted
    image_type : str
        Type of image ('original' or 'copy')
    target_id : str, optional
        For copies, the ID of the original artist being copied
        
    Returns
    -------
    str or None
        Path to saved image file, or None if saving failed
    """
    try:
        # Create images directory if it doesn't exist
        images_folder = os.path.join(os.getcwd(), 'logs', 'drawings')
        os.makedirs(images_folder, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # microseconds to milliseconds
        if image_type == 'copy' and target_id:
            filename = f"{timestamp}_{room_id}_{player_id}_copy_of_{target_id}.png"
        else:
            filename = f"{timestamp}_{room_id}_{player_id}_{image_type}.png"
        
        filepath = os.path.join(images_folder, filename)
        
        # Extract and save image data
        if image_data and ',' in image_data:
            # Remove data URL prefix
            image_bytes = base64.b64decode(image_data.split(',')[1])
            with open(filepath, 'wb') as f:
                f.write(image_bytes)
            return filepath
        else:
            debug_log("Invalid image data format - cannot save", player_id, room_id, {
                'image_type': image_type, 'data_preview': str(image_data)[:100] if image_data else 'None'
            })
            return None
            
    except Exception as e:
        debug_log("Failed to save image to logs", player_id, room_id, {
            'error': str(e), 'image_type': image_type
        })
        return None


def debug_log(message, player_id=None, room_id=None, extra_data=None):
    """
    Log debug information if debug mode is enabled.

    Parameters
    ----------
    message : str
        The debug message to log
    player_id : str, optional
        Player ID associated with the action
    room_id : str, optional
        Room ID associated with the action
    extra_data : dict, optional
        Additional data to include in the log
    """
    if CONSTANTS['debug_mode']:
        log_parts = []

        if room_id:
            log_parts.append(f"Room: {room_id}")
        if player_id:
            log_parts.append(f"Player: {player_id}")
        log_parts.append(message)
        if extra_data:
            log_parts.append(f"Data: {extra_data}")

        logger = logging.getLogger(__name__)
        logger.info(" | ".join(log_parts))


def info_log(message):
    """
    Log debug information if debug mode is enabled.

    Parameters
    ----------
    message : str
        The message to log
    """
    logger = logging.getLogger(__name__)
    logger.info(message)
