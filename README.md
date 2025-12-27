# Deployment Guide for Linux

This guide describes how to deploy the Peloton to Garmin Sync (`p2g-python`) application on Linux using either **Docker** or **Systemd**.

## Method 1: Docker (Recommended)

This method isolates the application and its dependencies.

### Prerequisites
- Docker and Docker Compose installed.

### Setup

1. **Configuration**:
   - Ensure you have a `config.toml` file in the project directory.
   - If you haven't authenticated yet, it is easiest to run the script locally once to generate the tokens, or provide credentials via environment variables.

2. **Run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```
   
   This will:
   - Build the container.
   - Mount your `config.toml` (so the app can read it and write updated tokens to it).
   - Mount `p2g_output/` to persist your downloaded FIT files.
   
3. **Running in Background**:
   To run as a background service:
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

## Method 2: Systemd Service (Native)

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
