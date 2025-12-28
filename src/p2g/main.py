from .config import load_settings
from .peloton import PelotonClient
from .garmin import GarminClient
from .convert import FitConverter

import os
import argparse
import re
import time
from datetime import datetime, timezone

def run_sync(config_path):
    print(f"Loading configuration from {config_path}...")
    try:
        settings = load_settings(config_path)
    except Exception as e:
        print(f"Error loading settings: {e}")
        return

    # 1. Peloton
    print("Authenticating with Peloton...")
    peloton = PelotonClient(settings)
    try:
        peloton.authenticate()
    except Exception as e:
        print(f"Peloton authentication failed: {e}")
        return

    # 2. Garmin
    garmin = None
    if settings.Garmin.Upload:
        if settings.Garmin.Email and settings.Garmin.Password:
            print("Authenticating with Garmin...")
            garmin = GarminClient(settings, config_path=config_path)
            try:
                garmin.authenticate()
            except Exception as e:
                print(f"Garmin authentication failed: {e}")
                return
        else:
            print("Garmin upload enabled but credentials missing. Skipping upload and saving locally only.")

    # 3. Determine how many workouts to fetch based on backup
    backup_path = os.path.abspath(settings.Peloton.BackupFolder)
    os.makedirs(backup_path, exist_ok=True)
    
    # We only care about files that start with our date pattern YYYYMMDD_
    dated_fit_files = []
    date_pattern = re.compile(r"^(\d{8})_")
    
    for f in os.listdir(backup_path):
        if f.endswith(".fit") and date_pattern.match(f):
            dated_fit_files.append(f)
            
    dated_fit_files.sort(reverse=True)
    
    since_timestamp = None
    if dated_fit_files:
        latest_file = dated_fit_files[0]
        match = date_pattern.match(latest_file)
        if match:
            date_str = match.group(1)
            # Start of that day in UTC
            dt = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
            since_timestamp = dt.timestamp()
            print(f"Incremental sync: Scanning activities since {date_str}...")

    if since_timestamp:
        # Fetch a sufficient batch and filter
        all_recent = peloton.get_recent_workouts(limit=100)
        workouts = [w for w in all_recent if w["start_time"] >= since_timestamp]
    else:
        num_to_fetch = settings.Peloton.MaxWorkoutsToDownload
        print(f"No backup found. Fetching last {num_to_fetch} workouts...")
        workouts = peloton.get_recent_workouts(limit=num_to_fetch)

    print(f"Saving to {backup_path}.")
    converter = FitConverter(output_dir=backup_path)

    # Fetch user data once
    try:
        user_data = peloton.get_me()
    except Exception as e:
        print(f"Failed to fetch user data: {e}")
        user_data = {}

    for w in workouts:
        workout_id = w["id"]
        discipline = w.get("fitness_discipline")
        
        # Check exclusion
        if discipline in settings.Peloton.ExcludeWorkoutTypes:
            print(f"Skipping excluded workout type: {discipline} ({workout_id})")
            continue

        if w.get("status") != "COMPLETE":
            print(f"Skipping incomplete workout: {workout_id}")
            continue

        title = w.get("title") or w.get("name") or workout_id
        print(f"Processing workout: {title} ({workout_id})")
        
        # Fetch detailed metrics
        details = peloton.get_workout_details(workout_id)
        performance = peloton.get_performance_graph(workout_id)
        
        # Additional data for enhanced conversion
        segments = None
        ride = details.get("ride") or (details.get("workout") or {}).get("ride") or {}

        # 1️⃣ Try the ride ID (used for cycling/running classes)
        class_id = ride.get("id")

        # 2️⃣ If there is no ride ID, fall back to the **strength‑plan GUID**.
        if not class_id:
            overlay = details.get("strength_plan_overlay_metadata") or {}
            class_id = overlay.get("strength_plan_id") or details.get("strength_plan_id")

        if class_id and class_id != "00000000000000000000000000000000":
            try:
                segments = peloton.get_class_segments(class_id)
            except Exception as e:
                # 404 is common for non‑cycling/running or scenic classes
                if "404" not in str(e):
                    print(f"Failed to fetch segments for class {class_id}: {e}")

        # Convert to FIT
        try:
            fit_path = converter.convert(details, performance, segments, user_data)
            print(f"Saved: {os.path.basename(fit_path)}")
        except Exception as e:
            print(f"Failed to convert workout {workout_id}: {e}")
            continue

        # Upload to Garmin
        if garmin:
            try:
                garmin.upload_activity(fit_path)
            except Exception as e:
                print(f"Failed to upload workout {workout_id} to Garmin: {e}")

    print("Sync complete.")

def main():
    parser = argparse.ArgumentParser(description="Sync Peloton workouts to Garmin Connect.")
    parser.add_argument("-c", "--config", default="config.toml", help="Path to configuration file (default: config.toml). Contains Peloton and Garmin credentials.")
    parser.add_argument("--daemon", action="store_true", help="Run in daemon mode. The script will run continuously and sync periodically (useful for Docker/Systemd).")
    parser.add_argument("--interval", type=int, default=21600, help="Interval in seconds for daemon mode (default: 21600s / 6h).")
    args = parser.parse_args()

    config_path = args.config

    if args.daemon:
        print(f"Starting in daemon mode. Syncing every {args.interval} seconds.")
        while True:
            try:
                run_sync(config_path)
            except Exception as e:
                print(f"Global error during sync: {e}")
            
            print(f"Sleeping for {args.interval} seconds...")
            time.sleep(args.interval)
    else:
        run_sync(config_path)

if __name__ == "__main__":
    main()
