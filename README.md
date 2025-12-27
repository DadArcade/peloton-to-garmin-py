# Peloton to Garmin Sync (Python)

A Python port of the [Peloton-to-Garmin C# project](https://github.com/philosowaffle/peloton-to-garmin/) for automatically syncing Peloton workouts to Garmin Connect. This tool works as a command-line application or background service.

## Quick Start & Auth

**Configuration**: Create `config.toml` with your credentials.

**Initial Authentication**: If using Garmin 2FA, you must run the script manually once to generate authentication tokens.

```bash
# 1. Setup Environment
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Run Sync (Enter 2FA code if prompted)
python src/p2g/main.py

# 3. Cleanup (Optional)
deactivate
rm -rf .venv
```

## Deployment (Linux)

### Method 1: Docker (Recommended)
Isolates dependencies. Edit `config.toml` then run:

```bash
# Run in background (Daemon)
docker-compose up -d

# Run in foreground (Debug/First Run)
docker-compose up --build
```
*Data persisted in `./p2g_output`.*

### Method 2: Systemd Service
Installs as a user-level background service (runs every 6 hours).

```bash
# Install & Enable every 6 hours sync
chmod +x deploy_linux.sh
./deploy_linux.sh
systemctl --user enable --now p2g.timer

# Check Logs
journalctl --user -u p2g -f
```

## Configuration
Settings are loaded from `config.toml`. You can override them with environment variables (using `__` for nesting):
```yaml
environment:
  - P2G_Peloton__Email=myemail@example.com
  - P2G_Peloton__Password=mypassword
```
