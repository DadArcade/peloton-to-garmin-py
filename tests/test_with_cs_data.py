import json
import sys
import os
import pytest
from pathlib import Path

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from p2g.convert import FitConverter

def normalize_keys(obj):
    """Recursively lowercase all keys in a dictionary."""
    if isinstance(obj, dict):
        return {k.lower(): normalize_keys(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [normalize_keys(i) for i in obj]
    else:
        return obj

def get_test_files():
    # Local data directory
    data_dir = Path(__file__).parent / "data/p2g_workouts"
    if not data_dir.exists():
        return []
    return list(data_dir.glob("*.json"))

@pytest.mark.parametrize("json_path", get_test_files(), ids=lambda p: p.name)
def test_conversion_parity(json_path: Path):
    """Test that the Python converter can handle C# workout JSON exports."""
    try:
        with open(json_path, 'r', encoding='utf-8-sig') as f:
            data = json.load(f)
    except Exception as e:
        pytest.fail(f"Failed to load JSON {json_path.name}: {e}")
    
    # Normalize keys to match Python's snake_case expectation
    normalized = normalize_keys(data)
    
    workout = normalized.get("workout") or {}
    performance = normalized.get("workoutsamples") or {}
    user_data = normalized.get("userdata") or {}
    
    # Prepare segments (Python expects a dict with 'segment_list')
    segments = {"segment_list": performance.get("segment_list", [])}
    
    # Use a temporary output directory for tests
    output_dir = Path(__file__).parent / "output"
    os.makedirs(output_dir, exist_ok=True)
    
    converter = FitConverter(output_dir=str(output_dir))
    
    file_path = converter.convert(
        workout=workout,
        performance=performance,
        segments=segments,
        user_data=user_data,
        title=workout.get("name")
    )
    
    assert os.path.exists(file_path)
    assert os.path.getsize(file_path) > 0

if __name__ == "__main__":
    # If run directly as a script, still work
    for f in get_test_files():
        print(f"Testing {f.name}...")
        test_conversion_parity(f)
