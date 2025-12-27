#!/bin/bash
set -e

# Check if running as root
if [ "$EUID" -eq 0 ]; then
  echo "Error: Please do not run this script as root (sudo). Run it as your regular user to install the user-level systemd service."
  exit 1
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
    python3 -m venv "$VENV_DIR"
fi

# 2. Install Dependencies
echo "Installing dependencies..."
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install .

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
