#!/usr/bin/env python3
"""
Chip Organizer - A PyQt5 application for organizing chip images using classifier ontology.
"""

import sys
import os
from PyQt5.QtWidgets import QApplication
from chip_organizer import ChipOrganizerApp

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Chip Organizer")
    app.setApplicationVersion("1.0")
    
    # Create and show the main window
    window = ChipOrganizerApp()
    window.show()
    
    # Start the event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()