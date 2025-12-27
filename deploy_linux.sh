#!/bin/bash
set -e

# Check if running as root
if [ "$EUID" -eq 0 ]; then
  echo "Error: Please do not run this script as root (sudo). Run it as your regular user to install the user-level systemd service."
  exit 1
fi

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed. Please install Python 3."
    exit 1
fi

# Check if venv module is available
if ! python3 -m venv --help > /dev/null 2>&1; then
    echo "Error: python3-venv is not installed. Please install it (e.g., sudo apt install python3-venv)."
    exit 1
fi

# Configure DBUS variables for headless/VM environments
if [ -z "$XDG_RUNTIME_DIR" ]; then
    export XDG_RUNTIME_DIR="/run/user/$(id -u)"
fi

if [ -z "$DBUS_SESSION_BUS_ADDRESS" ]; then
    export DBUS_SESSION_BUS_ADDRESS="unix:path=${XDG_RUNTIME_DIR}/bus"
fi

# Check if the systemd user bus is accessible
if [ ! -S "${XDG_RUNTIME_DIR}/bus" ]; then
    echo "Warning: Systemd user bus socket not found at ${XDG_RUNTIME_DIR}/bus."
    echo "This often happens in headless environments or if you haven't logged in."
    echo "Try enabling lingering for your user to keep the user manager running:"
    echo "  sudo loginctl enable-linger $USER"
    echo "Then log out and back in, or reboot."
    # Proceeding, but systemctl might fail
fi

# Deployment script for p2g-python on Linux using Systemd

INSTALL_DIR="$(pwd)"
VENV_DIR="$INSTALL_DIR/.venv"
SERVICE_NAME="p2g"
USER_SYSTEMD_DIR="$HOME/.config/systemd/user"

echo "Deploying P2G-Python to run as a user-level Systemd service."
echo "Installation Directory: $INSTALL_DIR"

# 1. Create Virtual Env
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    # Use --system-site-packages to inherit setuptools/pip from system if missing in restricted repo
    python3 -m venv --system-site-packages "$VENV_DIR"
fi

# 2. Install Dependencies
echo "Installing dependencies..."

# Ensure pip is installed in the venv (sometimes missing on Debian/Ubuntu)
if [ ! -x "$VENV_DIR/bin/pip" ]; then
    echo "pip binary not found in venv. Attempting to bootstrap with ensurepip..."
    "$VENV_DIR/bin/python" -m ensurepip --default-pip || true
fi

"$VENV_DIR/bin/python" -m pip install --upgrade pip

# Manually install dependencies to bypass build system (setuptools) issues
echo "Installing runtime dependencies directly..."
"$VENV_DIR/bin/python" -m pip install httpx pydantic pydantic-settings garmin-fit-sdk python-dotenv beautifulsoup4 oauthlib fit-tool

# 3. Generate Systemd Service File
mkdir -p "$USER_SYSTEMD_DIR"

SERVICE_FILE="$USER_SYSTEMD_DIR/$SERVICE_NAME.service"
TIMER_FILE="$USER_SYSTEMD_DIR/$SERVICE_NAME.timer"

echo "Generating $SERVICE_FILE..."
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Peloton to Garmin Sync Service
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONPATH=$INSTALL_DIR/src
ExecStart=$VENV_DIR/bin/python -m p2g.main
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
EOF

# 4. Generate Systemd Timer File
echo "Generating $TIMER_FILE..."
cat > "$TIMER_FILE" <<EOF
[Unit]
Description=Timer for Peloton to Garmin Sync
Requires=$SERVICE_NAME.service

[Timer]
# Run 15 minutes after boot
OnBootSec=15min
# Run every 6 hours
OnUnitActiveSec=6h
Persistent=true

[Install]
WantedBy=timers.target
EOF

# 5. Reload Systemd
echo "Reloading systemd user daemon..."
systemctl --user daemon-reload

echo "--------------------------------------------------------"
echo "Deployment files created."
echo ""
echo "To enable and start the timer (runs every 6h):"
echo "  systemctl --user enable --now $SERVICE_NAME.timer"
echo ""
echo "To run the sync manually once:"
echo "  systemctl --user start $SERVICE_NAME.service"
echo ""
echo "To check logs:"
echo "  journalctl --user -u $SERVICE_NAME"
echo "--------------------------------------------------------"
