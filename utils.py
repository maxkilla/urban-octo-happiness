import re

def sanitize_filename(filename):
    """Remove illegal characters for filenames."""
    return re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', filename)

# Add more utility functions here as needed 