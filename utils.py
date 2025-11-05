"""
Utility functions for the Chip Organizer application.
"""

from pathlib import Path
from typing import List, Set


def find_image_files(directory: Path, supported_formats: List[str]) -> List[Path]:
    """
    Find all image files in a directory with supported formats.
    
    Args:
        directory: Directory to search
        supported_formats: List of file extensions (e.g., ['.png', '.jpg'])
    
    Returns:
        Sorted list of image file paths (duplicates removed)
    """
    image_files_set: Set[Path] = set()
    
    for ext in supported_formats:
        # Search for both lowercase and uppercase extensions
        image_files_set.update(directory.glob(f"*{ext}"))
        image_files_set.update(directory.glob(f"*{ext.upper()}"))
    
    return sorted(list(image_files_set))


def parse_labels_from_text(text: str, existing_categories: List[str]) -> dict:
    """
    Parse labels from multi-line text input.
    
    Args:
        text: Multi-line text with one label per line
        existing_categories: List of already existing categories
    
    Returns:
        Dictionary with:
            - 'added': List of new labels to add
            - 'duplicates': List of labels that already exist
            - 'skipped': List of duplicate labels within the input
    """
    lines = text.split('\n')
    added_labels = []
    duplicate_labels = []
    skipped_labels = []
    
    for line in lines:
        label = line.strip()
        
        # Skip empty lines and comments
        if not label or label.startswith('#'):
            continue
        
        # Check if already exists in ontology
        if label in existing_categories:
            duplicate_labels.append(label)
            continue
        
        # Check if already in the list to be added
        if label in added_labels:
            skipped_labels.append(label)
            continue
        
        added_labels.append(label)
    
    return {
        'added': added_labels,
        'duplicates': duplicate_labels,
        'skipped': skipped_labels
    }


def get_categories_from_ontology(ontology) -> List[str]:
    """
    Extract categories list from various ontology structures.
    
    Args:
        ontology: Ontology dict, list, or other structure
    
    Returns:
        List of category strings
    """
    categories = []
    
    if isinstance(ontology, dict):
        if 'categories' in ontology:
            categories = ontology['categories']
        elif 'classes' in ontology:
            categories = list(ontology['classes'].keys())
        else:
            categories = list(ontology.keys())
    elif isinstance(ontology, list):
        categories = ontology
    
    return categories


def format_category_label(category) -> str:
    """
    Format a category for display.
    
    Args:
        category: Category object (dict, string, etc.)
    
    Returns:
        String label for display
    """
    if isinstance(category, dict):
        return category.get('label', category.get('name', str(category)))
    return str(category)
