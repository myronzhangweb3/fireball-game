#!/bin/bash

echo "Building macOS executable with PyInstaller..."

# Ensure PyInstaller is installed
pip install -r requirements.txt

# Run PyInstaller
pyinstaller --onefile \
            --windowed \
            --name "FireballGame" \
            --add-data "game:game" \
            --add-data "game/assets:game/assets" \
            --hidden-import "mediapipe" \
            --hidden-import "cv2" \
main.py

echo "Build complete. The executable can be found in the 'dist' directory."
