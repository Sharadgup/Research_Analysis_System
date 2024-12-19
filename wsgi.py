import sys
import os

# Add your project directory to the sys.path
project_home = '/workspaces/Research_Analysis_System (main)'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Create the uploads folder if it doesn't exist
os.makedirs(os.path.join(project_home, 'uploads'), exist_ok=True)

# Import your app from app.py
from app import app as app