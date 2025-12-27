# Peloton to Garmin Sync (Python)

This project is a Python port of the [Peloton-to-Garmin C# project](https://github.com/philosowaffle/peloton-to-garmin/). Unlike the original, this project is just a command-line application that can be run as a background service or as a periodic job. It automatically downloads Peloton workout data and uploads it to Garmin Connect.

## Configuration & First Run

This application uses a `config.toml` file for configuration.

**Important: Garmin 2FA**
If your Garmin account has Two-Factor Authentication (2FA) enabled, the script cannot log in automatically on the first run. You must run the script manually once in an interactive terminal to enter the 2FA code. This will generate authentication tokens and save them to config.toml, which allow future background runs (Docker/Systemd) to work without prompts.

### Manual Auth Steps (Virtual Environment)
To perform the one-time manual authentication:

1. **Create and activate a virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install the project dependencies**:
   ```bash
   pip install -e .
   ```

3. **Run the script**:
   ```bash
   # Ensure config.toml is present and filled out with your credentials
   python src/p2g/main.py
   ```
   Follow the prompts to enter your 2FA code. Once successfully authenticated, the tokens will be saved to your configuration, and you can proceed with Docker or Systemd deployment.

4. **Cleanup**:
   After authentication is complete, you can remove the virtual environment:
   ```bash
   deactivate
   rm -rf .venv
   ```

---

# Deployment Guide for Linux

This guide describes how to deploy the application on Linux using either **Docker** or **Systemd**.

## Method 1: Docker

This method isolates the application and its dependencies.

### Prerequisites
- Docker and Docker Compose installed.

### Setup

1. **Configuration**:
   - Edit the `config.toml` file in the project directory to add your credentials.
   - See "Configuration & First Run" above.

2. **Run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```
   
   This will:
   - Build the container.
   - Mount your `config.toml` (so the app can read it and write updated tokens to it).
   - Mount `p2g_output/` to persist your downloaded FIT files.
   
3. **Running in Background**:
   To run as a background service (daemon mode):
   ```bash
   docker-compose up -d
   ```

### Environment Variables
You can override configuration values using environment variables. The mapping uses double underscores `__` for nested values.

Example `docker-compose.yml` snippet:
```yaml
    environment:
      - P2G_Peloton__Email=myemail@example.com
      - P2G_Peloton__Password=mypassword
```

---

## Method 2: Systemd Service

This method runs the application as a user-level background service, scheduled by a Systemd timer.

### Setup

1. **Run the deployment script**:
   ```bash
   chmod +x deploy_linux.sh
   ./deploy_linux.sh
   ```
   
   This script will:
   - Create a Python virtual environment in `.venv`.
   - Install all dependencies.
   - Generate `p2g.service` and `p2g.timer` in `~/.config/systemd/user/`.

2. **Enable and Start**:
   The script will verify the files, but you need to enable the timer manually to avoid accidental scheduling:
   
   ```bash
   systemctl --user enable --now p2g.timer
   ```
   
   This will run the sync **every 6 hours** and **15 minutes after boot**.

3. **Manual Run**:
   To force a run immediately:
   ```bash
   systemctl --user start p2g.service
   ```

4. **View Logs**:
   ```bash
   journalctl --user -u p2g -f
   ```

### Uninstalling
To remove the service:
```bash
systemctl --user stop p2g.timer
systemctl --user disable p2g.timer
rm ~/.config/systemd/user/p2g.service
rm ~/.config/systemd/user/p2g.timer
systemctl --user daemon-reload
```
