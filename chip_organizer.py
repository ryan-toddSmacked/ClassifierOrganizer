"""
Main application window for the Chip Organizer.
"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Optional, Dict
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QMessageBox, QListWidget, QSplitter,
    QGroupBox, QCheckBox, QScrollArea, QInputDialog, QListWidgetItem
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QPixmap, QImage, QColor, QBrush
from dialogs import RemoveLabelDialog, AddLabelDialog
from utils import find_image_files, parse_labels_from_text, get_categories_from_ontology, format_category_label
from constants import (
    SUPPORTED_FORMATS, APP_NAME, APP_DISPLAY_NAME, 
    MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT, FILE_LIST_MAX_WIDTH,
    COLOR_LABELED, COLOR_UNLABELED, COLOR_CURRENT
)


class ChipOrganizerApp(QMainWindow):
    """Main application window for organizing chip images."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_DISPLAY_NAME)
        self.setMinimumSize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        
        # Application state
        self.image_files: List[Path] = []
        self.current_index: int = 0
        self.ontology: Dict = {}
        self.classifications: Dict[str, str] = {}  # filename -> category
        self.source_directory: Optional[Path] = None
        
        # Settings
        self.settings = QSettings(APP_NAME, APP_NAME)
        
        # Setup UI
        self.setup_ui()
        
        # Restore last session if available
        self.restore_session()
    
    def setup_ui(self):
        """Initialize the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Top toolbar
        toolbar_layout = QHBoxLayout()
        
        self.load_images_btn = QPushButton("Load Images")
        self.load_images_btn.clicked.connect(self.load_images)
        toolbar_layout.addWidget(self.load_images_btn)
        
        self.load_ontology_btn = QPushButton("Load Ontology (CSV)")
        self.load_ontology_btn.clicked.connect(self.load_ontology)
        toolbar_layout.addWidget(self.load_ontology_btn)
        
        self.save_progress_btn = QPushButton("Save Progress")
        self.save_progress_btn.clicked.connect(self.save_progress)
        toolbar_layout.addWidget(self.save_progress_btn)
        
        self.load_progress_btn = QPushButton("Load Progress")
        self.load_progress_btn.clicked.connect(self.load_progress)
        toolbar_layout.addWidget(self.load_progress_btn)
        
        self.export_btn = QPushButton("Export Sorted Images")
        self.export_btn.clicked.connect(self.export_images)
        toolbar_layout.addWidget(self.export_btn)
        
        # Export mode checkbox (compact)
        self.copy_mode_checkbox = QCheckBox("Copy mode")
        self.copy_mode_checkbox.setChecked(True)
        self.copy_mode_checkbox.setToolTip("Copy files (uncheck to move files)")
        toolbar_layout.addWidget(self.copy_mode_checkbox)
        
        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)
        
        # Splitter for main content
        splitter = QSplitter(Qt.Horizontal)
        
        # Left side - File list
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        file_list_label = QLabel("Loaded Files")
        file_list_label.setStyleSheet("QLabel { font-weight: bold; padding: 5px; }")
        left_layout.addWidget(file_list_label)
        
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.on_file_list_clicked)
        self.file_list.setMaximumWidth(FILE_LIST_MAX_WIDTH)
        left_layout.addWidget(self.file_list)
        
        splitter.addWidget(left_widget)
        
        # Center - Image display
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        
        # Image display area
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(600, 400)
        self.image_label.setStyleSheet("QLabel { background-color: #333; border: 2px solid #666; }")
        self.image_label.setScaledContents(False)
        
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.image_label)
        scroll_area.setWidgetResizable(True)
        center_layout.addWidget(scroll_area)
        
        # Image info
        self.info_label = QLabel("No image loaded")
        self.info_label.setStyleSheet("QLabel { padding: 5px; }")
        center_layout.addWidget(self.info_label)
        
        # Classification status indicator
        self.status_indicator = QLabel("Status: No image loaded")
        self.status_indicator.setAlignment(Qt.AlignCenter)
        self.status_indicator.setStyleSheet(
            "QLabel { padding: 8px; font-weight: bold; background-color: #e0e0e0; border: 2px solid #999; border-radius: 4px; }"
        )
        center_layout.addWidget(self.status_indicator)
        
        # Navigation and counter layout
        nav_layout = QHBoxLayout()
        self.prev_btn = QPushButton("← Previous")
        self.prev_btn.clicked.connect(self.previous_image)
        nav_layout.addWidget(self.prev_btn)
        
        # Image counter (replaces progress bar)
        self.counter_label = QLabel("0 / 0")
        self.counter_label.setAlignment(Qt.AlignCenter)
        self.counter_label.setStyleSheet(
            "QLabel { padding: 8px; font-size: 14px; font-weight: bold; background-color: #f5f5f5; border: 1px solid #ccc; border-radius: 4px; }"
        )
        nav_layout.addWidget(self.counter_label)
        
        self.next_btn = QPushButton("Next →")
        self.next_btn.clicked.connect(self.next_image)
        nav_layout.addWidget(self.next_btn)
        
        center_layout.addLayout(nav_layout)
        
        splitter.addWidget(center_widget)
        
        # Right side - Ontology categories
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        ontology_group = QGroupBox("Classification Categories")
        ontology_layout = QVBoxLayout(ontology_group)
        
        self.category_list = QListWidget()
        self.category_list.itemClicked.connect(self.classify_current_image)
        ontology_layout.addWidget(self.category_list)
        
        # Add/Remove label buttons
        label_buttons_layout = QHBoxLayout()
        
        self.add_label_btn = QPushButton("+ Add Label")
        self.add_label_btn.clicked.connect(self.add_label)
        label_buttons_layout.addWidget(self.add_label_btn)
        
        self.remove_label_btn = QPushButton("- Remove Label")
        self.remove_label_btn.clicked.connect(self.remove_label)
        label_buttons_layout.addWidget(self.remove_label_btn)
        
        ontology_layout.addLayout(label_buttons_layout)
        
        # Export labels button
        self.export_labels_btn = QPushButton("Export Labels to CSV")
        self.export_labels_btn.clicked.connect(self.export_labels_to_csv)
        ontology_layout.addWidget(self.export_labels_btn)
        
        # Current classification display
        self.current_classification_label = QLabel("Current: Not classified")
        self.current_classification_label.setStyleSheet(
            "QLabel { padding: 10px; background-color: #f0f0f0; border: 1px solid #ccc; }"
        )
        ontology_layout.addWidget(self.current_classification_label)
        
        right_layout.addWidget(ontology_group)
        
        # Statistics
        stats_group = QGroupBox("Statistics")
        stats_layout = QVBoxLayout(stats_group)
        self.stats_label = QLabel("No images loaded")
        self.stats_label.setWordWrap(True)
        stats_layout.addWidget(self.stats_label)
        right_layout.addWidget(stats_group)
        
        splitter.addWidget(right_widget)
        
        # Set splitter sizes (file list, image display, categories)
        splitter.setSizes([250, 650, 300])
        
        main_layout.addWidget(splitter)
        
        self.update_ui_state()
    
    def on_file_list_clicked(self, item):
        """Handle clicking on a file in the file list."""
        # Get the index from the list
        index = self.file_list.row(item)
        if 0 <= index < len(self.image_files):
            self.current_index = index
            self.display_current_image()
    
    def update_file_list(self):
        """Update the file list with current images and their status."""
        self.file_list.clear()
        
        for i, image_file in enumerate(self.image_files):
            filename = image_file.name
            is_labeled = filename in self.classifications
            
            # Create list item with indicator
            if is_labeled:
                category = self.classifications[filename]
                item_text = f"✓ {filename}"
                self.file_list.addItem(item_text)
                # Get the actual item that was just added
                list_item = self.file_list.item(self.file_list.count() - 1)
                list_item.setBackground(QBrush(QColor(*COLOR_LABELED)))
                list_item.setToolTip(f"Labeled: {category}")
            else:
                item_text = f"⚠ {filename}"
                self.file_list.addItem(item_text)
                list_item = self.file_list.item(self.file_list.count() - 1)
                list_item.setBackground(QBrush(QColor(*COLOR_UNLABELED)))
                list_item.setToolTip("Not labeled")
        
        # Highlight current image
        if 0 <= self.current_index < self.file_list.count():
            self.file_list.setCurrentRow(self.current_index)
    
    def load_images(self):
        """Load images from a selected directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Directory with Chip Images"
        )
        
        if not directory:
            return
        
        self.source_directory = Path(directory)
        
        # Find all supported image files using utility function
        self.image_files = find_image_files(self.source_directory, SUPPORTED_FORMATS)
        
        if not self.image_files:
            QMessageBox.warning(
                self, "No Images Found",
                f"No supported image files found in {directory}"
            )
            return
        
        self.current_index = 0
        self.classifications = {}
        self.display_current_image()
        self.update_statistics()
        self.update_ui_state()
        self.update_file_list()
        
        QMessageBox.information(
            self, "Images Loaded",
            f"Loaded {len(self.image_files)} images from {directory}"
        )
    
    def load_ontology(self):
        """Load ontology from a CSV file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Select Ontology CSV File", "", "CSV Files (*.csv);;All Files (*.*)"
        )
        
        if not filename:
            return
        
        try:
            # Read CSV file - each line is a category label
            # Labels can have hierarchical structure using dash delimiter (e.g., "Mammal-carnivore-cat")
            categories = []
            with open(filename, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):  # Skip empty lines and comments
                        categories.append(line)
            
            # Store as simple list
            self.ontology = {'categories': categories}
            
            # Update category list
            self.update_category_list()
            
            QMessageBox.information(
                self, "Ontology Loaded",
                f"Successfully loaded {len(categories)} categories from {os.path.basename(filename)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error Loading Ontology",
                f"Failed to load ontology: {str(e)}"
            )
    
    def update_category_list(self):
        """Update the category list widget from the ontology."""
        self.category_list.clear()
        
        if not self.ontology:
            return
        
        # Get categories using utility function
        categories = get_categories_from_ontology(self.ontology)
        
        for category in categories:
            label = format_category_label(category)
            self.category_list.addItem(label)
    
    def add_label(self):
        """Add new labels to the category list (supports multiple labels, one per line)."""
        # Initialize ontology if it doesn't exist
        if not self.ontology:
            self.ontology = {'categories': []}
        
        # Get current categories list
        categories = get_categories_from_ontology(self.ontology)
        
        # Show the add label dialog
        dialog = AddLabelDialog(self)
        if not dialog.exec_():
            return
        
        text = dialog.get_labels_text()
        if not text.strip():
            return
        
        # Parse labels
        result = parse_labels_from_text(text, categories)
        
        # Add new labels to ontology
        if isinstance(self.ontology, dict):
            if 'categories' not in self.ontology:
                self.ontology['categories'] = []
            self.ontology['categories'].extend(result['added'])
        elif isinstance(self.ontology, list):
            self.ontology.extend(result['added'])
        
        # Update the display
        if result['added']:
            self.update_category_list()
        
        # Show results
        message_parts = []
        
        if result['added']:
            message_parts.append(f"Successfully added {len(result['added'])} label(s):")
            for label in result['added'][:10]:  # Show first 10
                message_parts.append(f"  • {label}")
            if len(result['added']) > 10:
                message_parts.append(f"  ... and {len(result['added']) - 10} more")
        
        if result['duplicates']:
            message_parts.append(f"\nSkipped {len(result['duplicates'])} duplicate(s) (already exist):")
            for label in result['duplicates'][:5]:
                message_parts.append(f"  • {label}")
            if len(result['duplicates']) > 5:
                message_parts.append(f"  ... and {len(result['duplicates']) - 5} more")
        
        if result['skipped']:
            message_parts.append(f"\nSkipped {len(result['skipped'])} duplicate(s) in input")
        
        if not result['added'] and not result['duplicates'] and not result['skipped']:
            QMessageBox.information(
                self, "No Labels Added",
                "No valid labels were entered."
            )
        else:
            QMessageBox.information(
                self, "Add Labels Complete",
                "\n".join(message_parts)
            )
    
    def remove_label(self):
        """Remove labels via a multi-selection dialog."""
        # Get current categories
        categories = get_categories_from_ontology(self.ontology)
        
        if not categories:
            QMessageBox.warning(
                self, "No Labels",
                "No labels available to remove."
            )
            return
        
        # Show the remove label dialog
        dialog = RemoveLabelDialog(categories, self)
        if not dialog.exec_():
            return
        
        # Get selected labels
        labels_to_remove = dialog.get_selected_labels()
        
        if not labels_to_remove:
            QMessageBox.information(
                self, "No Selection",
                "No labels were selected for removal."
            )
            return
        
        # Confirm deletion
        label_list_str = "\n".join(f"  • {label}" for label in labels_to_remove)
        reply = QMessageBox.question(
            self, "Confirm Removal",
            f"Are you sure you want to remove {len(labels_to_remove)} label(s)?\n\n"
            f"{label_list_str}\n\n"
            "Note: This will NOT remove existing classifications using these labels.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return
        
        # Remove labels from ontology
        if isinstance(self.ontology, dict):
            if 'categories' in self.ontology:
                for label in labels_to_remove:
                    if label in self.ontology['categories']:
                        self.ontology['categories'].remove(label)
        
        # Update the display
        self.update_category_list()
        
        QMessageBox.information(
            self, "Labels Removed",
            f"Successfully removed {len(labels_to_remove)} label(s)."
        )
    
    def export_labels_to_csv(self):
        """Export current labels to a CSV file."""
        if not self.ontology:
            QMessageBox.warning(
                self, "No Labels",
                "No labels to export. Please load or create labels first."
            )
            return
        
        # Get filename from user
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export Labels to CSV", "", "CSV Files (*.csv);;All Files (*.*)"
        )
        
        if not filename:
            return
        
        try:
            # Get categories
            categories = []
            if isinstance(self.ontology, dict):
                if 'categories' in self.ontology:
                    categories = self.ontology['categories']
                elif 'classes' in self.ontology:
                    categories = list(self.ontology['classes'].keys())
                else:
                    categories = list(self.ontology.keys())
            elif isinstance(self.ontology, list):
                categories = self.ontology
            
            # Write to CSV
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("# Exported Labels from Chip Organizer\n")
                f.write(f"# Total labels: {len(categories)}\n\n")
                for category in categories:
                    if isinstance(category, dict):
                        label = category.get('label', category.get('name', str(category)))
                    else:
                        label = str(category)
                    f.write(f"{label}\n")
            
            QMessageBox.information(
                self, "Export Successful",
                f"Successfully exported {len(categories)} labels to:\n{os.path.basename(filename)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Export Error",
                f"Failed to export labels: {str(e)}"
            )
    
    def display_current_image(self):
        """Display the current image."""
        if not self.image_files or self.current_index >= len(self.image_files):
            self.image_label.setText("No image to display")
            self.info_label.setText("No image loaded")
            self.status_indicator.setText("Status: No image loaded")
            self.status_indicator.setStyleSheet(
                "QLabel { padding: 8px; font-weight: bold; background-color: #e0e0e0; border: 2px solid #999; border-radius: 4px; }"
            )
            self.counter_label.setText("0 / 0")
            return
        
        current_file = self.image_files[self.current_index]
        
        try:
            # Load and display image
            pixmap = QPixmap(str(current_file))
            
            # Scale to fit while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            
            # Update info
            file_size = current_file.stat().st_size / 1024  # KB
            self.info_label.setText(
                f"File: {current_file.name} | Size: {file_size:.1f} KB"
            )
            
            # Update counter (replaces progress bar)
            self.counter_label.setText(f"{self.current_index + 1} / {len(self.image_files)}")
            
            # Update current classification display
            current_class = self.classifications.get(current_file.name, None)
            if current_class:
                self.current_classification_label.setText(f"Current: {current_class}")
                self.current_classification_label.setStyleSheet(
                    "QLabel { padding: 10px; background-color: #d4edda; border: 1px solid #c3e6cb; }"
                )
                # Update status indicator - labeled
                self.status_indicator.setText("✓ LABELED")
                self.status_indicator.setStyleSheet(
                    "QLabel { padding: 8px; font-weight: bold; color: white; background-color: #28a745; border: 2px solid #1e7e34; border-radius: 4px; }"
                )
            else:
                self.current_classification_label.setText("Current: Not classified")
                self.current_classification_label.setStyleSheet(
                    "QLabel { padding: 10px; background-color: #f8d7da; border: 1px solid #f5c6cb; }"
                )
                # Update status indicator - not labeled
                self.status_indicator.setText("⚠ NOT LABELED")
                self.status_indicator.setStyleSheet(
                    "QLabel { padding: 8px; font-weight: bold; color: white; background-color: #dc3545; border: 2px solid #bd2130; border-radius: 4px; }"
                )
            
            # Update UI button states
            self.update_ui_state()
            
            # Highlight current file in list
            if 0 <= self.current_index < self.file_list.count():
                self.file_list.setCurrentRow(self.current_index)
            
        except Exception as e:
            self.image_label.setText(f"Error loading image: {str(e)}")
    
    def classify_current_image(self, item):
        """Classify the current image with the selected category."""
        if not self.image_files or self.current_index >= len(self.image_files):
            return
        
        category = item.text()
        current_file = self.image_files[self.current_index]
        self.classifications[current_file.name] = category
        
        self.current_classification_label.setText(f"Current: {category}")
        self.current_classification_label.setStyleSheet(
            "QLabel { padding: 10px; background-color: #d4edda; border: 1px solid #c3e6cb; }"
        )
        
        # Update status indicator immediately
        self.status_indicator.setText("✓ LABELED")
        self.status_indicator.setStyleSheet(
            "QLabel { padding: 8px; font-weight: bold; color: white; background-color: #28a745; border: 2px solid #1e7e34; border-radius: 4px; }"
        )
        
        self.update_statistics()
        self.update_ui_state()
        self.update_file_list()
        
        # Auto-advance to next image
        if self.current_index < len(self.image_files) - 1:
            self.next_image()
    
    def previous_image(self):
        """Go to the previous image."""
        if self.current_index > 0:
            self.current_index -= 1
            self.display_current_image()
    
    def next_image(self):
        """Go to the next image."""
        if self.current_index < len(self.image_files) - 1:
            self.current_index += 1
            self.display_current_image()
    
    def update_statistics(self):
        """Update the statistics display."""
        if not self.image_files:
            self.stats_label.setText("No images loaded")
            return
        
        total = len(self.image_files)
        classified = len(self.classifications)
        remaining = total - classified
        
        # Count by category
        category_counts = {}
        for category in self.classifications.values():
            category_counts[category] = category_counts.get(category, 0) + 1
        
        stats_text = f"Total Images: {total}\n"
        stats_text += f"Classified: {classified}\n"
        stats_text += f"Remaining: {remaining}\n\n"
        
        if category_counts:
            stats_text += "By Category:\n"
            for category, count in sorted(category_counts.items()):
                stats_text += f"  {category}: {count}\n"
        
        self.stats_label.setText(stats_text)
    
    def save_progress(self):
        """Save current progress to a JSON file."""
        if not self.image_files:
            QMessageBox.warning(self, "No Data", "No images loaded to save progress.")
            return
        
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save Progress", "", "JSON Files (*.json)"
        )
        
        if not filename:
            return
        
        try:
            progress_data = {
                'source_directory': str(self.source_directory),
                'current_index': self.current_index,
                'classifications': self.classifications,
                'ontology': self.ontology
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2)
            
            QMessageBox.information(
                self, "Progress Saved",
                f"Progress saved to {os.path.basename(filename)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error Saving Progress",
                f"Failed to save progress: {str(e)}"
            )
    
    def load_progress(self):
        """Load progress from a JSON file."""
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Progress", "", "JSON Files (*.json)"
        )
        
        if not filename:
            return
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            # Restore state
            self.source_directory = Path(progress_data['source_directory'])
            self.current_index = progress_data.get('current_index', 0)
            self.classifications = progress_data.get('classifications', {})
            self.ontology = progress_data.get('ontology', {})
            
            # Reload images from source directory
            # Use a set to avoid duplicates on case-insensitive file systems (Windows)
            image_files_set = set()
            for ext in self.SUPPORTED_FORMATS:
                image_files_set.update(self.source_directory.glob(f"*{ext}"))
                image_files_set.update(self.source_directory.glob(f"*{ext.upper()}"))
            
            self.image_files = sorted(list(image_files_set))
            
            # Update UI
            self.update_category_list()
            self.display_current_image()
            self.update_statistics()
            self.update_ui_state()
            self.update_file_list()
            
            QMessageBox.information(
                self, "Progress Loaded",
                f"Progress loaded from {os.path.basename(filename)}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error Loading Progress",
                f"Failed to load progress: {str(e)}"
            )
    
    def export_images(self):
        """Export classified images to organized directories."""
        if not self.classifications:
            QMessageBox.warning(
                self, "No Classifications",
                "No images have been classified yet."
            )
            return
        
        # Select output directory
        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory for Sorted Images"
        )
        
        if not output_dir:
            return
        
        output_path = Path(output_dir)
        copy_mode = self.copy_mode_checkbox.isChecked()
        operation = "copy" if copy_mode else "move"
        
        try:
            # Create category directories and copy/move files
            for filename, category in self.classifications.items():
                # Create category directory
                category_dir = output_path / category
                category_dir.mkdir(parents=True, exist_ok=True)
                
                # Find source file
                source_file = self.source_directory / filename
                dest_file = category_dir / filename
                
                # Copy or move file
                if copy_mode:
                    shutil.copy2(source_file, dest_file)
                else:
                    shutil.move(str(source_file), str(dest_file))
            
            QMessageBox.information(
                self, "Export Complete",
                f"Successfully {operation}ed {len(self.classifications)} images to {output_dir}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Export Error",
                f"Failed to export images: {str(e)}"
            )
    
    def update_ui_state(self):
        """Update the enabled/disabled state of UI elements."""
        has_images = bool(self.image_files)
        has_ontology = bool(self.ontology)
        
        self.prev_btn.setEnabled(has_images and self.current_index > 0)
        self.next_btn.setEnabled(has_images and self.current_index < len(self.image_files) - 1)
        self.save_progress_btn.setEnabled(has_images)
        self.export_btn.setEnabled(bool(self.classifications))
    
    def restore_session(self):
        """Restore the last session if available."""
        # This could auto-load the last progress file or directory
        pass
    
    def resizeEvent(self, event):
        """Handle window resize events."""
        super().resizeEvent(event)
        # Redisplay current image to scale properly
        if self.image_files and self.current_index < len(self.image_files):
            self.display_current_image()
