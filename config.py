# Configuration and constants for Pixel Plagiarist server
import os
import csv

# Game Constants
CONSTANTS = {
    'initial_balance': 100,
    'max_players': 12,
    'blank_image_penalty': 0.05,
    'non_voting_penalty': 0.02,
    'debug_mode': os.environ.get('DEBUG_MODE', 'true').lower() == 'true',
    'testing_mode': os.environ.get('TESTING_MODE', 'false').lower() == 'true'
}


def get_timer_config():
    """
    Get timer configuration from environment variables.
    
    Returns a dictionary of timer values in seconds. If TESTING_MODE is enabled,
    all timers are set to 5 seconds for rapid testing. Otherwise, uses environment
    variables or sensible defaults.
    
    Returns
    -------
    dict
        Dictionary containing timer values:
        - countdown: Time to wait for more players before starting
        - betting: Time allowed for placing bets
        - drawing: Time allowed for drawing original artwork
        - copying: Time allowed for copying other players' drawings
        - voting: Time allowed per voting round
    """
    if CONSTANTS['testing_mode']:
        print("🧪 TESTING MODE ENABLED - All timers set to 5 seconds")
        return {
            'countdown': 5,
            'betting': 5,
            'drawing': 5,
            'copying': 5,
            'voting': 5
        }

    return {
        'countdown': int(os.environ.get('COUNTDOWN_TIMER', 20)),
        'betting': int(os.environ.get('BETTING_TIMER', 10)),
        'drawing': int(os.environ.get('DRAWING_TIMER', 60)),
        'copying': int(os.environ.get('COPYING_TIMER', 60)),
        'voting': int(os.environ.get('VOTING_TIMER', 30))
    }


def load_prompts():
    """
    Load drawing prompts from the prompts.csv file.
    
    Reads prompts from a CSV file with a 'prompt' column header. If the file
    is missing or corrupted, falls back to a basic set of prompts to ensure
    the game can still function.
    
    Returns
    -------
    list of str
        A list of drawing prompts loaded from the CSV file. Each prompt is
        a string describing what players should draw (e.g., "Cat wearing a hat").
        Returns fallback prompts if the CSV file cannot be read.
        
    Notes
    -----
    The function handles various error conditions:
    - FileNotFoundError: CSV file doesn't exist
    - Empty file or no valid prompts
    - General parsing errors
    
    All errors result in fallback prompts being returned to keep the game functional.
    """
    prompts = []
    prompts_file = os.path.join(os.path.dirname(__file__), 'prompts.csv')
    fallback_prompts = ["Cat wearing a hat", "Flying book", "Sad rain cloud"]

    try:
        with open(prompts_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['prompt'].strip():  # Skip empty rows
                    prompts.append(row['prompt'].strip())

        if not prompts:
            print("Warning: No prompts found in prompts.csv, using fallback prompts")
            return fallback_prompts

        print(f"Loaded {len(prompts)} prompts from prompts.csv")
        return prompts

    except FileNotFoundError:
        print("Warning: prompts.csv not found, using fallback prompts")
        return fallback_prompts
    except Exception as e:
        print(f"Error loading prompts: {e}, using fallback prompts")
        return fallback_prompts


# Load configurations at module import
TIMER_CONFIG = get_timer_config()
PROMPTS = load_prompts()
