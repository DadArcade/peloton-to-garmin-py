from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import os

# Mocking the garmin_fit_sdk structure based on typical FIT SDK patterns
# In a real environment, these would be imported from the library
try:
    from garmin_fit_sdk import Encode, Stream, Message, Field
except ImportError:
    # Fallback or placeholder if library structure differs
    pass

class FitConverter:
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def convert(self, workout: Dict[str, Any], performance: Dict[str, Any]) -> str:
        workout_id = workout["id"]
        start_time = datetime.fromtimestamp(workout["start_time"], tz=timezone.utc)
        
        # Determine sport
        discipline = workout.get("fitness_discipline", "cycling")
        sport = self._get_garmin_sport(discipline)
        sub_sport = self._get_garmin_sub_sport(discipline)

        file_name = f"peloton_{workout_id}.fit"
        file_path = os.path.join(self.output_dir, file_name)

        # FIT SDK Encoding (Conceptual)
        # 1. Create Messages
        messages = []

        # FileID Message
        messages.append({
            "name": "file_id",
            "fields": {
                "type": 4,  # Activity
                "manufacturer": 1,  # Garmin
                "product": 0,
                "serial_number": 12345,
                "time_created": start_time
            }
        })

        # Sport Message
        messages.append({
            "name": "sport",
            "fields": {
                "sport": sport,
                "sub_sport": sub_sport
            }
        })

        # Record Messages (The bread and butter)
        metrics = performance.get("metrics", [])
        hr_data = self._get_metric(metrics, "heart_rate")
        power_data = self._get_metric(metrics, "output")
        cadence_data = self._get_metric(metrics, "cadence")
        
        seconds = performance.get("seconds_since_pedaling_start", [])
        for i, elapsed in enumerate(seconds):
            record = {
                "name": "record",
                "fields": {
                    "timestamp": datetime.fromtimestamp(workout["start_time"] + elapsed, tz=timezone.utc),
                    "heart_rate": hr_data[i] if hr_data and i < len(hr_data) else None,
                    "power": power_data[i] if power_data and i < len(power_data) else None,
                    "cadence": cadence_data[i] if cadence_data and i < len(cadence_data) else None,
                }
            }
            # Clean None fields
            record["fields"] = {k: v for k, v in record["fields"].items() if v is not None}
            messages.append(record)

        # Session Message
        summary = workout.get("summary", {})
        messages.append({
            "name": "session",
            "fields": {
                "timestamp": datetime.fromtimestamp(workout["end_time"], tz=timezone.utc),
                "start_time": start_time,
                "total_elapsed_time": workout.get("duration", 0),
                "total_timer_time": workout.get("duration", 0),
                "total_calories": summary.get("calories", 0),
                "total_distance": summary.get("distance", 0) * 1609.34, # Miles to Meters
                "avg_power": summary.get("avg_output", 0),
                "max_power": summary.get("max_output", 0),
                "avg_heart_rate": summary.get("avg_heart_rate", 0),
                "max_heart_rate": summary.get("max_heart_rate", 0),
                "sport": sport,
                "sub_sport": sub_sport
            }
        })

        # Activity Message
        messages.append({
            "name": "activity",
            "fields": {
                "timestamp": datetime.fromtimestamp(workout["end_time"], tz=timezone.utc),
                "num_sessions": 1,
                "type": 0, # Manual
                "event": 26, # Activity
                "event_type": 1, # Stop
            }
        })

        # Write to file (Implementation depends on the exact garmin-fit-sdk API)
        # Note: This is an abstraction. The real SDK might use encoder.write(messages)
        # or specific message objects.
        print(f"Generating FIT file for workout {workout_id}...")
        
        # Placeholder for real encoding logic
        with open(file_path, "wb") as f:
             # In a real implementation:
             # stream = Stream.from_file(f)
             # encoder = Encode(stream)
             # encoder.write(messages)
             f.write(b"FIT placeholder content") # Placeholder

        return file_path

    def _get_metric(self, metrics: List[Dict], slug: str) -> Optional[List[float]]:
        for m in metrics:
            if m.get("slug") == slug:
                return m.get("values")
        return None

    def _get_garmin_sport(self, discipline: str) -> int:
        mapping = {
            "cycling": 2,
            "running": 1,
            "swimming": 5,
            "strength": 20,
            "walking": 11,
            "yoga": 28,
        }
        return mapping.get(discipline.lower(), 0) # Generic

    def _get_garmin_sub_sport(self, discipline: str) -> int:
        # Simplified sub-sport mapping
        if "cycling" in discipline.lower():
            return 2 # Indoor Cycling
        return 0 # Generic
