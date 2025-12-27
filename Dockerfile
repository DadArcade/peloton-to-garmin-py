# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies if any (none strictly required for core pure-python deps, 
# but sometimes git or build-essential are needed for certain wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy the current directory contents into the container at /app
COPY . /app

# Install the package
# We install in editable mode or standard mode. Standard is better for production.
RUN pip install --no-cache-dir .

# Create a volume for configuration and output
VOLUME /app/config
VOLUME /app/output

# Set environment variables
ENV P2G_Peloton__BackupFolder=/app/output
# We expect config.toml to be mounted at /app/config.toml or passed entirely via env vars

# Command to run the application
# Users can override this to run bash or other commands
ENTRYPOINT ["python", "-m", "p2g.main"]
CMD ["--config", "/app/config/config.toml"]
