"""
Dialog windows for the Chip Organizer application.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QListWidget, QTextEdit
)
from PyQt5.QtCore import Qt


class RemoveLabelDialog(QDialog):
    """Dialog for selecting multiple labels to remove."""
    
    def __init__(self, categories, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Remove Labels")
        self.setMinimumWidth(400)
        self.setMinimumHeight(400)
        
        self.selected_labels = []
        self._setup_ui(categories)
    
    def _setup_ui(self, categories):
        """Initialize the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel("Select labels to remove (Ctrl+Click for multiple):")
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # List widget with multi-selection
        self.label_list = QListWidget()
        self.label_list.setSelectionMode(QListWidget.MultiSelection)
        
        # Add all current labels
        for category in categories:
            self.label_list.addItem(str(category))
        
        layout.addWidget(self.label_list)
        
        # Note about classifications
        note = QLabel("Note: Removing labels will NOT remove existing classifications.")
        note.setStyleSheet("QLabel { color: #666; font-style: italic; }")
        note.setWordWrap(True)
        layout.addWidget(note)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self.accept)
        button_layout.addWidget(remove_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def get_selected_labels(self):
        """Return list of selected label names."""
        return [item.text() for item in self.label_list.selectedItems()]


class AddLabelDialog(QDialog):
    """Dialog for adding multiple labels at once."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Labels")
        self.setMinimumWidth(500)
        self.setMinimumHeight(350)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize the dialog UI."""
        layout = QVBoxLayout(self)
        
        # Instructions
        instructions = QLabel(
            "Enter labels to add (one per line):\n"
            "• Use dash '-' for hierarchy (e.g., 'Parent-Child-Grandchild')\n"
            "• Empty lines and duplicates will be skipped"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)
        
        # Multi-line text edit
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "Example:\n"
            "Microcontrollers\n"
            "Memory-DRAM-DDR4\n"
            "Processors-Intel-i7\n"
            "Sensors-Temperature"
        )
        layout.addWidget(self.text_edit)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add Labels")
        add_btn.clicked.connect(self.accept)
        button_layout.addWidget(add_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
    
    def get_labels_text(self):
        """Return the text from the text edit."""
        return self.text_edit.toPlainText()
