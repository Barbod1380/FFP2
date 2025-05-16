
#!/bin/bash

# run.sh - Script to start the Dash application

# Ensure the assets directory exists
mkdir -p assets

# Install requirements if needed
pip install -r requirements.txt

# Run the application
python app.py
