#!/bin/bash
# FileSqueeze One-Click Installer for Linux
# Run with: bash install.sh
# Or download and run: curl -sSL https://nyjc.app/filesqueeze/install | bash

set -e

# Default values
INSTALL_DIR="$HOME/FileSqueeze"
BRANCH="main"
REPO_URL="https://github.com/yourusername/filesqueeze.git"
FORCE=false
SKIP_DEPS=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --install-dir)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --branch)
            BRANCH="$2"
            shift 2
            ;;
        --repo)
            REPO_URL="$2"
            shift 2
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --skip-deps)
            SKIP_DEPS=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Functions
status() {
    echo -e "${GREEN}==>${NC} $1"
}

error() {
    echo -e "${RED}==> ERROR:${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}==> WARNING:${NC} $1"
}

# Welcome message
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${CYAN}  FileSqueeze Installer for Linux${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
status "Welcome to FileSqueeze!"
echo "  This installer will:"
echo "  - Check for Python 3.11+"
echo "  - Install Poetry (if needed)"
echo "  - Clone FileSqueeze repository"
echo "  - Install dependencies"
echo "  - Detect FFmpeg, Ghostscript, Tesseract"
echo "  - Generate configuration file"
echo ""

# Check if installation directory exists
if [ -d "$INSTALL_DIR" ]; then
    if [ "$FORCE" = false ]; then
        error "Installation directory already exists: $INSTALL_DIR\nUse --force to reinstall."
    fi
    status "Removing existing installation (force reinstall)..."
    rm -rf "$INSTALL_DIR"
fi

# Create installation directory
status "Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

# Check Python installation
status "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    error "Python 3 not found. Please install Python 3.11+:
  Ubuntu/Debian: sudo apt-get install python3.11 python3-pip
  Fedora: sudo dnf install python3.11
  Arch: sudo pacman -S python"
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "  ${GRAY}Found: Python $PYTHON_VERSION${NC}"

# Check Python version
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    error "Python 3.11+ required. Found: $PYTHON_VERSION"
fi

# Check pip installation
if ! command -v pip3 &> /dev/null; then
    error "pip3 not found. Please install python3-pip"
fi

# Check Poetry installation
status "Checking Poetry installation..."
if ! command -v poetry &> /dev/null; then
    echo -e "  ${YELLOW}Poetry not found. Installing...${NC}"
    status "Installing Poetry..."

    # Download Poetry installer
    curl -sSL https://install.python-poetry.org | python3 -

    # Add Poetry to PATH
    export PATH="$HOME/.local/bin:$PATH"

    # Verify installation
    if ! command -v poetry &> /dev/null; then
        error "Poetry installation failed. Please install manually:
  curl -sSL https://install.python-poetry.org | python3 -"
    fi

    POETRY_VERSION=$(poetry --version)
    echo -e "  ${GRAY}Poetry installed: $POETRY_VERSION${NC}"
else
    POETRY_VERSION=$(poetry --version)
    echo -e "  ${GRAY}Found: $POETRY_VERSION${NC}"
fi

# Clone repository
status "Cloning FileSqueeze repository..."
if ! git clone --branch "$BRANCH" --depth 1 "$REPO_URL" "$INSTALL_DIR/repo"; then
    error "Failed to clone repository. Please check your internet connection and Git installation."
fi
cd "$INSTALL_DIR/repo"
echo -e "  ${GRAY}Repository cloned successfully${NC}"

# Install dependencies
if [ "$SKIP_DEPS" = false ]; then
    status "Installing dependencies (this may take a few minutes)..."
    if ! poetry install; then
        error "Failed to install dependencies."
    fi
    echo -e "  ${GRAY}Dependencies installed successfully${NC}"
else
    status "Skipping dependency installation (--skip-deps)" "${YELLOW}"
fi

# Detect binaries and generate config
status "Detecting FFmpeg, Ghostscript, and Tesseract..."
poetry run python -m filesqueeze detect || warn "Binary detection had issues"

# Generate configuration
status "Generating configuration file..."
if poetry run python -m filesqueeze init-config --output "$INSTALL_DIR/filesqueeze.toml"; then
    echo -e "  ${GRAY}Configuration created: $INSTALL_DIR/filesqueeze.toml${NC}"
else
    warn "Config generation failed. You can create it manually."
fi

# Create start scripts
status "Creating start scripts..."

# Watch mode script
cat > "$INSTALL_DIR/start-watch.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/repo"
poetry run python -m filesqueeze service
EOF
chmod +x "$INSTALL_DIR/start-watch.sh"

# Compress single file script
cat > "$INSTALL_DIR/compress-file.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/repo"
read -p "Enter file path: " FILEPATH
poetry run python -m filesqueeze compress "$FILEPATH"
EOF
chmod +x "$INSTALL_DIR/compress-file.sh"

echo -e "  ${GRAY}Start scripts created in $INSTALL_DIR${NC}"

# Create systemd service (optional)
status "Creating systemd service file..."
cat > "$HOME/.config/systemd/user/filesqueeze.service" << EOF
[Unit]
Description=FileSqueeze Compression Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR/repo
ExecStart=$(which poetry) run python -m filesqueeze service
Restart=on-failure

[Install]
WantedBy=default.target
EOF

echo -e "  ${GRAY}Systemd service created: ~/.config/systemd/user/filesqueeze.service${NC}"
echo -e "  ${GRAY}To enable: systemctl --user enable filesqueeze.service${NC}"
echo -e "  ${GRAY}To start: systemctl --user start filesqueeze.service${NC}"

# Success message
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${CYAN}Installation directory:${NC} $INSTALL_DIR"
echo ""
echo -e "${YELLOW}Quick Start:${NC}"
echo "  1. Edit config: nano $INSTALL_DIR/filesqueeze.toml"
echo "  2. Start service: cd $INSTALL_DIR/repo && poetry run python -m filesqueeze service"
echo "  3. Or use systemd: systemctl --user start filesqueeze.service"
echo ""
echo -e "${YELLOW}Commands:${NC}"
echo "  Start service:      poetry run python -m filesqueeze service"
echo "  Watch mode:         poetry run python -m filesqueeze watch"
echo "  Compress file:      poetry run python -m filesqueeze compress <file>"
echo "  Batch process:      poetry run python -m filesqueeze scan"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Edit: $INSTALL_DIR/filesqueeze.toml"
echo "  Set input/output directories"
echo "  Configure log location"
echo ""
echo -e "${GREEN}Thank you for installing FileSqueeze!${NC}"
echo ""

# Offer to start service
read -p "Start FileSqueeze service now? (Y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    status "Starting FileSqueeze service..."
    cd "$INSTALL_DIR/repo"
    poetry run python -m filesqueeze service
fi
