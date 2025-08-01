# Logging utilities for Pixel Plagiarist server
import logging
from util.config import CONSTANTS


def setup_logging():
    """
    Configure logging for the application.
    
    Returns
    -------
    logging.Logger
        Configured logger instance
    """
    import os
    from datetime import datetime
    
    # Configure logging
    log_folder = os.path.join(os.getcwd(), 'logs')
    os.makedirs(log_folder, exist_ok=True)
    log_file_path = os.path.join(log_folder, f'pixel_plagiarist_{datetime.now():%Y-%m-%d_%H%M%S}.log')
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
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
        log_parts = [message]

        if player_id:
            log_parts.append(f"Player: {player_id}")
        if room_id:
            log_parts.append(f"Room: {room_id}")
        if extra_data:
            log_parts.append(f"Data: {extra_data}")

        logger = logging.getLogger(__name__)
        logger.info(" | ".join(log_parts))