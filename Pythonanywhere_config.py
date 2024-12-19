import os

# Configuration for PythonAnywhere
class Config:
    # Set the upload folder path
    UPLOAD_FOLDER = '/workspaces/Research_Analysis_System/uploads'
    
    # Ensure the upload folder exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    # Set allowed extensions
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}
    
    # Debug mode should be False in production
    DEBUG = False

# Update your app.py to use this configuration
def configure_app(app):
    app.config.from_object(Config)