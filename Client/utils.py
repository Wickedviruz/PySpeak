from datetime import datetime

def log_message(console, message):
    timestamp = datetime.now().strftime('%H:%M:%S')
    console.append(f"{timestamp} - {message}")