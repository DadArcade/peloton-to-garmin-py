from .config import load_settings
from .peloton import PelotonClient
from .garmin import GarminClient
from .convert import FitConverter
import sys
import os

def main():
    config_path = "configuration.local.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    print(f"Loading configuration from {config_path}...")
    try:
        settings = load_settings(config_path)
    except Exception as e:
        print(f"Error loading settings: {e}")
        sys.exit(1)

    # 1. Peloton
    print("Authenticating with Peloton...")
    peloton = PelotonClient(settings)
    try:
        peloton.authenticate()
    except Exception as e:
        print(f"Peloton authentication failed: {e}")
        sys.exit(1)

    # 2. Garmin
    garmin = None
    if settings.Garmin.Upload:
        print("Authenticating with Garmin...")
        garmin = GarminClient(settings)
        try:
            garmin.authenticate()
        except Exception as e:
            print(f"Garmin authentication failed: {e}")
            sys.exit(1)

    # 3. Fetch Workouts
    num_to_fetch = settings.Peloton.NumWorkoutsToDownload
    print(f"Fetching last {num_to_fetch} workouts from Peloton...")
    workouts = peloton.get_recent_workouts(limit=num_to_fetch)

    converter = FitConverter(output_dir="p2g_output")

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

        print(f"Processing workout: {w.get('title')} ({workout_id})")
        
        # Fetch detailed metrics
        details = peloton.get_workout_details(workout_id)
        performance = peloton.get_performance_graph(workout_id)

        # Convert to FIT
        try:
            fit_path = converter.convert(details, performance)
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

if __name__ == "__main__":
    main()
