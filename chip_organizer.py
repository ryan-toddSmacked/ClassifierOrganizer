"""
Main application window for the Chip Organizer.
"""

import os
import json
import shutil
from pathlib import Path
from typing import List, Optional, Dict, Set
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QFileDialog, QMessageBox, QListWidget, QSplitter,
    QGroupBox, QCheckBox, QScrollArea, QInputDialog, QListWidgetItem,
    QGridLayout, QFrame, QShortcut
)
from PyQt5.QtCore import Qt, QSettings, QSize
from PyQt5.QtGui import QPixmap, QImage, QColor, QBrush, QKeySequence
from dialogs import RemoveLabelDialog, AddLabelDialog
from utils import find_image_files, parse_labels_from_text, get_categories_from_ontology, format_category_label
from constants import (
    SUPPORTED_FORMATS, APP_NAME, APP_DISPLAY_NAME, 
    MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT, FILE_LIST_MAX_WIDTH,
    COLOR_LABELED, COLOR_UNLABELED, COLOR_CURRENT
)


class ClickableImageLabel(QLabel):
    """A clickable image label for grid view."""
    
    def __init__(self, image_path: Path, app_instance):
        super().__init__()
        self.image_path = image_path
        self.app_instance = app_instance
        self.is_selected = False
        self.is_labeled = False
        self.setFrameStyle(QFrame.Box)
        self.setLineWidth(3)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(150, 150)
        self.setMaximumSize(200, 200)
        self.setScaledContents(False)
        self.update_border()
    
    def mousePressEvent(self, event):
        """Handle mouse click to label image with selected category."""
        if self.app_instance and hasattr(self.app_instance, 'on_image_clicked'):
            self.app_instance.on_image_clicked(self)
        super().mousePressEvent(event)
    
    def set_labeled(self, labeled: bool):
        """Mark this image as labeled."""
        self.is_labeled = labeled
        self.update_border()
    
    def update_border(self):
        """Update border color based on state."""
        if self.is_labeled and hasattr(self, 'assigned_category') and self.assigned_category:
            # Use category color if available
            color_hex = None
            try:
                color_hex = self.app_instance.category_colors.get(self.assigned_category)
            except Exception:
                color_hex = None

            if color_hex:
                c = QColor(color_hex)
                r, g, b, _ = c.getRgb()
                self.setStyleSheet(f"QLabel {{ border: 3px solid {color_hex}; background-color: rgba({r}, {g}, {b}, 60); }}")
            else:
                self.setStyleSheet("QLabel { border: 3px solid green; background-color: rgba(0, 255, 0, 0.2); }")
        else:
            self.setStyleSheet("QLabel { border: 3px solid gray; }")


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
        
        # Grid state
        self.grid_size: tuple = (8, 4)  # columns x rows (configurable)
        self.grid_start_index: int = 0
        self.grid_labels: Dict[ClickableImageLabel, Path] = {}
        self.current_category: Optional[str] = None  # Currently selected category for labeling
        self.zoom_level: float = 1.0  # Zoom level (1.0 = 100%)
        # Category -> hex color mapping for labeled borders
        self.category_colors: Dict[str, str] = {}
        
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
        
        # Grid dimension settings
        grid_size_label = QLabel("Grid:")
        toolbar_layout.addWidget(grid_size_label)
        
        self.cols_input = QInputDialog()
        self.cols_btn = QPushButton(f"{self.grid_size[0]}×{self.grid_size[1]}")
        self.cols_btn.clicked.connect(self.configure_grid_size)
        self.cols_btn.setToolTip("Configure grid dimensions (columns × rows)")
        toolbar_layout.addWidget(self.cols_btn)
        
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
        
        # Center - Grid view display
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        
        # Grid container with scroll
        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        self.grid_scroll.setWidget(self.grid_container)
        center_layout.addWidget(self.grid_scroll)
        
        # Grid controls
        grid_controls = QHBoxLayout()
        
        # Zoom controls
        zoom_label = QLabel("Zoom:")
        grid_controls.addWidget(zoom_label)
        
        self.zoom_out_btn = QPushButton("-")
        self.zoom_out_btn.setMaximumWidth(30)
        self.zoom_out_btn.setToolTip("Zoom Out (Ctrl+-)")
        self.zoom_out_btn.clicked.connect(self.zoom_out)
        grid_controls.addWidget(self.zoom_out_btn)
        
        self.zoom_level_label = QLabel("100%")
        self.zoom_level_label.setMinimumWidth(50)
        self.zoom_level_label.setAlignment(Qt.AlignCenter)
        grid_controls.addWidget(self.zoom_level_label)
        
        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setMaximumWidth(30)
        self.zoom_in_btn.setToolTip("Zoom In (Ctrl++)")
        self.zoom_in_btn.clicked.connect(self.zoom_in)
        grid_controls.addWidget(self.zoom_in_btn)
        
        self.zoom_reset_btn = QPushButton("Reset")
        self.zoom_reset_btn.setMaximumWidth(60)
        self.zoom_reset_btn.setToolTip("Reset Zoom (Ctrl+0)")
        self.zoom_reset_btn.clicked.connect(self.zoom_reset)
        grid_controls.addWidget(self.zoom_reset_btn)
        
        grid_controls.addSpacing(20)
        
        self.cycle_labeled_btn = QPushButton("Cycle Labeled Images")
        self.cycle_labeled_btn.clicked.connect(self.cycle_labeled_images)
        self.cycle_labeled_btn.setToolTip("Replace labeled images with new unlabeled ones")
        grid_controls.addWidget(self.cycle_labeled_btn)
        
        grid_controls.addStretch()
        center_layout.addLayout(grid_controls)
        
        # Classification status indicator
        self.status_indicator = QLabel("Status: Select a category from the right panel, then click images to label them")
        self.status_indicator.setAlignment(Qt.AlignCenter)
        self.status_indicator.setStyleSheet(
            "QLabel { padding: 8px; font-weight: bold; background-color: #e0e0e0; border: 2px solid #999; border-radius: 4px; }"
        )
        center_layout.addWidget(self.status_indicator)
        
        splitter.addWidget(center_widget)
        
        # Right side - Ontology categories
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        ontology_group = QGroupBox("Classification Categories")
        ontology_layout = QVBoxLayout(ontology_group)
        
        # Add sort checkbox
        self.sort_labels_checkbox = QCheckBox("Sort labels alphabetically")
        self.sort_labels_checkbox.setChecked(False)
        self.sort_labels_checkbox.stateChanged.connect(self.update_category_list)
        ontology_layout.addWidget(self.sort_labels_checkbox)
        
        self.category_list = QListWidget()
        self.category_list.itemClicked.connect(self.classify_current_image)
        # Add spacing between items to prevent misclicks
        self.category_list.setSpacing(3)
        # Style items to look like buttons with borders (removed green selection)
        self.category_list.setStyleSheet("""
            QListWidget::item {
                padding: 6px;
                margin: 1px 2px;
                border: 2px solid #2196F3;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item:hover {
                background-color: #e3f2fd;
                border-color: #1976D2;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                border-color: #1976D2;
                color: black;
            }
        """)
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
        
        # Setup keyboard shortcuts for zoom
        self.zoom_in_shortcut = QShortcut(QKeySequence("Ctrl++"), self)
        self.zoom_in_shortcut.activated.connect(self.zoom_in)
        
        self.zoom_out_shortcut = QShortcut(QKeySequence("Ctrl+-"), self)
        self.zoom_out_shortcut.activated.connect(self.zoom_out)
        
        self.zoom_reset_shortcut = QShortcut(QKeySequence("Ctrl+0"), self)
        self.zoom_reset_shortcut.activated.connect(self.zoom_reset)
        
        self.update_ui_state()
    
    def on_file_list_clicked(self, item):
        """Handle clicking on a file in the file list."""
        # In grid-only mode, file list is informational only
        pass
    
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
        self.grid_start_index = 0
        
        # Display grid
        self.display_grid()
        
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
        
        # Sort alphabetically if checkbox is checked
        if hasattr(self, 'sort_labels_checkbox') and self.sort_labels_checkbox.isChecked():
            categories = sorted(categories, key=lambda x: str(x).lower())
        
        for category in categories:
            # Ensure a stable color for each category (generate if missing)
            if category not in self.category_colors:
                # Generate a hue from the category name hash for deterministic colors
                hue = abs(hash(category)) % 360
                color = QColor.fromHsv(hue, 200, 255)
                self.category_colors[category] = color.name()

            label = format_category_label(category)
            item = QListWidgetItem(label)
            # Use a pale background based on category color for the list item
            item.setBackground(QBrush(QColor(self.category_colors[category]).lighter(150)))
            self.category_list.addItem(item)
    
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
        """No longer used in grid-only mode. Kept for compatibility."""
        pass
    
    def classify_current_image(self, item):
        """Set the current category for labeling when user selects from list."""
        self.current_category = item.text()
        
        # Update current classification display
        self.current_classification_label.setText(f"Selected Category: {self.current_category}")
        self.current_classification_label.setStyleSheet(
            "QLabel { padding: 10px; background-color: #cce5ff; border: 2px solid #007bff; font-weight: bold; }"
        )
        
        # Update status to guide user
        self.status_indicator.setText(f"Ready to label | Click images to mark as '{self.current_category}'")
        self.status_indicator.setStyleSheet(
            "QLabel { padding: 8px; font-weight: bold; background-color: #cce5ff; border: 2px solid #007bff; border-radius: 4px; }"
        )
    
    def configure_grid_size(self):
        """Allow user to configure grid dimensions."""
        cols, ok1 = QInputDialog.getInt(
            self, "Grid Columns", 
            "Number of columns:", 
            self.grid_size[0], 1, 20, 1
        )
        
        if not ok1:
            return
        
        rows, ok2 = QInputDialog.getInt(
            self, "Grid Rows", 
            "Number of rows:", 
            self.grid_size[1], 1, 20, 1
        )
        
        if not ok2:
            return
        
        # Update grid size
        self.grid_size = (cols, rows)
        self.cols_btn.setText(f"{cols}×{rows}")
        
        # Reset to start and redisplay
        self.grid_start_index = 0
        if self.image_files:
            self.display_grid()
    
    def display_grid(self):
        """Display images in grid layout."""
        # Clear existing grid
        for i in reversed(range(self.grid_layout.count())):
            self.grid_layout.itemAt(i).widget().setParent(None)
        
        self.grid_labels.clear()
        
        if not self.image_files:
            return
        
        cols, rows = self.grid_size
        images_per_page = cols * rows
        
        # Get unlabeled images starting from grid_start_index
        unlabeled_images = [
            img for img in self.image_files
            if img.name not in self.classifications
        ]
        
        if not unlabeled_images:
            self.status_indicator.setText("All images labeled!")
            self.status_indicator.setStyleSheet(
                "QLabel { padding: 8px; font-weight: bold; background-color: #90EE90; border: 2px solid #4CAF50; border-radius: 4px; }"
            )
            return
        
        # Display images in grid
        for idx in range(images_per_page):
            row = idx // cols
            col = idx % cols
            
            img_idx = self.grid_start_index + idx
            if img_idx >= len(unlabeled_images):
                break
            
            image_path = unlabeled_images[img_idx]
            
            # Calculate sizes based on zoom level
            base_size = 180
            zoomed_size = int(base_size * self.zoom_level)
            
            # Create clickable image label
            img_widget = ClickableImageLabel(image_path, self)
            
            # Apply zoom to widget size constraints
            img_widget.setMinimumSize(int(150 * self.zoom_level), int(150 * self.zoom_level))
            img_widget.setMaximumSize(int(200 * self.zoom_level), int(200 * self.zoom_level))
            
            # Check if already labeled and set assigned_category for correct border color
            if image_path.name in self.classifications:
                img_widget.assigned_category = self.classifications[image_path.name]
                img_widget.set_labeled(True)
            else:
                img_widget.assigned_category = None
            
            # Load and display image
            pixmap = QPixmap(str(image_path))
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(zoomed_size, zoomed_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                img_widget.setPixmap(scaled_pixmap)
            
            # Add filename label below image
            container = QWidget()
            container_layout = QVBoxLayout(container)
            container_layout.addWidget(img_widget)
            
            filename_label = QLabel(image_path.name)
            filename_label.setAlignment(Qt.AlignCenter)
            filename_label.setWordWrap(True)
            filename_label.setMaximumWidth(int(200 * self.zoom_level))
            font_size = max(8, int(10 * self.zoom_level))  # Scale font but keep minimum readable
            filename_label.setStyleSheet(f"QLabel {{ font-size: {font_size}px; }}")
            container_layout.addWidget(filename_label)
            
            # Attach filename label and container to widget for easy updates when cycling
            img_widget.filename_label = filename_label
            img_widget.container = container

            self.grid_layout.addWidget(container, row, col)
            self.grid_labels[img_widget] = image_path
        
        # Update status
        labeled_count = len(self.classifications)
        total_count = len(self.image_files)
        showing = min(images_per_page, len(unlabeled_images) - self.grid_start_index)
        self.status_indicator.setText(
            f"Showing {showing} unlabeled images | Total: {labeled_count}/{total_count} labeled"
        )
        self.status_indicator.setStyleSheet(
            "QLabel { padding: 8px; font-weight: bold; background-color: #e0e0e0; border: 2px solid #999; border-radius: 4px; }"
        )
    
    def on_image_clicked(self, image_widget):
        """Label image immediately when clicked."""
        if not self.current_category:
            QMessageBox.warning(
                self, "No Category Selected",
                "Please select a category from the right panel first."
            )
            return
        
        # Get the image path
        image_path = self.grid_labels.get(image_widget)
        if not image_path:
            return
        
        # Label the image
        self.classifications[image_path.name] = self.current_category
        # annotate widget so its border can reflect category color
        image_widget.assigned_category = self.current_category
        image_widget.set_labeled(True)
        
        # Update all displays
        self.update_file_list()
        self.update_statistics()
        self.update_ui_state()
        
        # Update status
        labeled_count = len(self.classifications)
        total_count = len(self.image_files)
        self.status_indicator.setText(
            f"✓ Labeled as '{self.current_category}' | Total: {labeled_count}/{total_count} labeled"
        )
        self.status_indicator.setStyleSheet(
            "QLabel { padding: 8px; font-weight: bold; color: white; background-color: #28a745; border: 2px solid #1e7e34; border-radius: 4px; }"
        )
    
    def cycle_labeled_images(self):
        """Cycle the entire grid to the next alphabetical batch of unlabeled images.
        Labeled images are removed from the master `self.image_files` so they do not
        reappear; cycling continues page-by-page until all images are labeled.
        """
        if not self.image_files:
            return

        # Remove already labeled images from the master list so they don't show again
        self.image_files = [img for img in self.image_files if img.name not in self.classifications]

        # Build an alphabetical list of remaining (unlabeled) images
        unlabeled_images = sorted(self.image_files, key=lambda p: p.name.lower())

        if not unlabeled_images:
            QMessageBox.information(self, "All Labeled", "All images have been labeled.")
            return

        cols, rows = self.grid_size
        images_per_page = cols * rows

        # Reset start if beyond range
        if self.grid_start_index >= len(unlabeled_images):
            self.grid_start_index = 0

        start = self.grid_start_index

        # Build the page images and wrap-around if necessary so the grid stays full
        if len(unlabeled_images) <= images_per_page:
            # fewer images than grid -> show them all (grid will be partially empty)
            page_images = unlabeled_images[:]
            end = start + len(page_images)
        else:
            end = start + images_per_page
            if end <= len(unlabeled_images):
                page_images = unlabeled_images[start:end]
            else:
                # wrap to the beginning to fill the page
                wrap_count = end - len(unlabeled_images)
                page_images = unlabeled_images[start:]
                page_images.extend(unlabeled_images[0:wrap_count])

        # Iterate current grid widgets and set them to the page images (or clear if none)
        widgets = list(self.grid_labels.keys())
        for i, widget in enumerate(widgets):
            if i < len(page_images):
                new_image = page_images[i]
                self.grid_labels[widget] = new_image
                pixmap = QPixmap(str(new_image))
                if not pixmap.isNull():
                    # Respect zoom level when rendering
                    zoomed_size = int(180 * getattr(self, 'zoom_level', 1.0))
                    widget.setPixmap(pixmap.scaled(zoomed_size, zoomed_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                widget.assigned_category = None
                widget.set_labeled(False)
                if hasattr(widget, 'filename_label'):
                    widget.filename_label.setText(new_image.name)
            else:
                # No image available for this slot: clear display
                widget.clear()
                widget.assigned_category = None
                widget.set_labeled(False)
                if hasattr(widget, 'filename_label'):
                    widget.filename_label.setText("")
                if widget in self.grid_labels:
                    del self.grid_labels[widget]

        # Advance page (wrap if needed when there are >= page sized images)
        if len(unlabeled_images) >= images_per_page:
            self.grid_start_index = (start + images_per_page) % len(unlabeled_images)
        else:
            # keep at 0 when fewer than one page remains
            self.grid_start_index = 0

        # Update UI
        self.update_file_list()
        self.update_statistics()
        self.update_ui_state()

        total_unlabeled = len(unlabeled_images)
        shown_count = len(page_images)
        self.status_indicator.setText(f"Showing {shown_count} of {total_unlabeled} unlabeled images (page start {start + 1})")
    
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
            
            # Reload images from source directory using utility function
            self.image_files = find_image_files(self.source_directory, SUPPORTED_FORMATS)
            
            # Update UI
            self.update_category_list()
            self.display_grid()
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
    
    def zoom_in(self):
        """Zoom in the grid view."""
        self.zoom_level = min(self.zoom_level + 0.25, 3.0)  # Max 300%
        self.apply_zoom()
    
    def zoom_out(self):
        """Zoom out the grid view."""
        self.zoom_level = max(self.zoom_level - 0.25, 0.25)  # Min 25%
        self.apply_zoom()
    
    def zoom_reset(self):
        """Reset zoom to 100%."""
        self.zoom_level = 1.0
        self.apply_zoom()
    
    def apply_zoom(self):
        """Apply the current zoom level to the grid."""
        # Update zoom label
        self.zoom_level_label.setText(f"{int(self.zoom_level * 100)}%")
        
        # Redisplay the grid with new zoom level
        self.display_grid()
    
    def update_ui_state(self):
        """Update the enabled/disabled state of UI elements."""
        has_images = bool(self.image_files)
        has_ontology = bool(self.ontology)
        
        self.save_progress_btn.setEnabled(has_images)
        self.export_btn.setEnabled(bool(self.classifications))
        self.cycle_labeled_btn.setEnabled(has_images)
    
    def restore_session(self):
        """Restore the last session if available."""
        # This could auto-load the last progress file or directory
        pass
    
    def resizeEvent(self, event):
        """Handle window resize events."""
        super().resizeEvent(event)
        # Grid layout handles resizing automatically
