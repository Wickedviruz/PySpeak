import json

# Load configuration
def load_config(file='config.json'):
    try:
        with open(file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print("config file not found. A new one will be created.")
        return {}
    except json.JSONDecodeError as e:
        print(f"Failed to load config due to JSON decoding error: {str(e)}")
        return {}
config = load_config('config.json')