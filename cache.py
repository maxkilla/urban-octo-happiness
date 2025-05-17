import json
import os
import time

def load_cache(filename, max_age=86400):
    """Load cache from filename if not older than max_age seconds. Return None if expired or missing."""
    if not os.path.exists(filename):
        return None
    if time.time() - os.path.getmtime(filename) > max_age:
        return None
    with open(filename, 'r') as f:
        return json.load(f)

def save_cache(filename, data):
    """Save data to filename as JSON."""
    with open(filename, 'w') as f:
        json.dump(data, f) 