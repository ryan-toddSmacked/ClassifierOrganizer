"""
Constants and configuration values for the Chip Organizer application.
"""

# Supported image file extensions
SUPPORTED_FORMATS = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tif', '.tiff']

# Application settings
APP_NAME = "ChipOrganizer"
APP_DISPLAY_NAME = "Chip Organizer"
MIN_WINDOW_WIDTH = 1000
MIN_WINDOW_HEIGHT = 700

# File list widget
FILE_LIST_MAX_WIDTH = 250

# UI Colors (RGB tuples)
COLOR_LABELED = (144, 238, 144)  # Light green for labeled images
COLOR_UNLABELED = (255, 182, 193)  # Light pink for unlabeled images
COLOR_CURRENT = (173, 216, 230)  # Light blue for current image

# Progress file
DEFAULT_PROGRESS_FILENAME = "chip_organizer_progress.json"

# CSV Export
CSV_HEADER = ["label", "parent", "description"]
