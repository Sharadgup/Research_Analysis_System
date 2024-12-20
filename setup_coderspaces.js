import { existsSync, mkdirSync, writeFileSync } from 'fs';
// Create .devcontainer/devcontainer.json
const devcontainerConfig = {
  "name": "Python Flask App",
  "image": "mcr.microsoft.com/devcontainers/python:3.8",
  "forwardPorts": [5000],
  "postCreateCommand": "pip install -r requirements.txt",
  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance"
      ]
    }
  }
};

// Create requirements.txt
const requirements = `
Flask==2.0.1
Werkzeug==2.0.1
PyPDF2==3.0.1
python-docx==0.8.11
nltk==3.6.3
beautifulsoup4==4.9.3
requests==2.26.0
`;

// Create setup script
console.log("Setting up GitHub Codespaces configuration...");

// Create .devcontainer directory if it doesn't exist
if (!existsSync('.devcontainer')) {
  mkdirSync('.devcontainer');
  console.log("Created .devcontainer directory");
}

// Write devcontainer.json
writeFileSync(
  '.devcontainer/devcontainer.json',
  JSON.stringify(devcontainerConfig, null, 2)
);
console.log("Created devcontainer.json");

// Write requirements.txt
writeFileSync('requirements.txt', requirements.trim());
console.log("Created requirements.txt");

// Create uploads directory
if (!existsSync('uploads')) {
  mkdirSync('uploads');
  console.log("Created uploads directory");
}

console.log("\nTo fix the 404 error:");
console.log("1. Add these configuration files to your repository");
console.log("2. Rebuild your codespace (Command Palette -> Codespaces: Rebuild Container)");
console.log("3. When the container is ready, run:");
console.log("   python -m flask run --host=0.0.0.0");
console.log("\nYour app will be available at:");
console.log("https://[codespace-name]-5000.preview.app.github.dev");