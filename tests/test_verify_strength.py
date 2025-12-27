import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from p2g.convert import FitConverter

def test_strength_extraction():
    # Use the local data copy
    base_path = Path(__file__).parent / "data/p2g_workouts/strength_guide_with_exercise.json"
    
    with open(base_path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
        
    # Do NOT normalize keys. Pass as is.
    workout = data.get("Workout") # PascalCase
    performance = data.get("WorkoutSamples") # PascalCase
    
    # Python converter requires dicts
    segments = {"segment_list": performance.get("Segment_List", [])}
    
    converter = FitConverter(output_dir="test_verify_strength_output")
    
    # We can invoke _get_workout_exercises directly to verify
    exercises = converter._get_workout_exercises(workout, segments)
    
    print(f"Extracted {len(exercises)} exercises.")
    for ex in exercises:
        print(f"ID: {ex['id']}, Name: {ex['name']}, Reps: {ex['reps']}, Duration: {ex['duration_seconds']}, Weight: {ex['weight']['value']}")

    # Validation
    assert len(exercises) > 0, "Should have extracted exercises"
    
    first_ex = exercises[0]
    # In JSON: Movement_Name="Wide Grip Overhead Press", Completed_Number=10, Offset=90, Length=30
    assert first_ex['name'] == "Wide Grip Overhead Press"
    assert first_ex['reps'] == 10
    assert first_ex['duration_seconds'] == 30
    assert first_ex['weight']['value'] == 10

if __name__ == "__main__":
    try:
        test_strength_extraction()
        print("Test PASSED")
    except Exception as e:
        print(f"Test FAILED: {e}")
        import traceback
        traceback.print_exc()
