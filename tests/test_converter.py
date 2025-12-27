import os
import pytest
from datetime import datetime, timezone
from p2g.convert import FitConverter
from fit_tool.fit_file import FitFile
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.messages.activity_message import ActivityMessage
from fit_tool.profile.messages.workout_message import WorkoutMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.set_message import SetMessage
from fit_tool.profile.profile_type import ExerciseCategory

def test_cycling_conversion(tmp_path):
    output_dir = str(tmp_path / "test_output")
    os.makedirs(output_dir, exist_ok=True)
    converter = FitConverter(output_dir)
    
    workout = {
        "id": "cycling_test",
        "start_time": datetime.now(timezone.utc).timestamp(),
        "fitness_discipline": "cycling",
        "summary": {
            "avg_output": 200,
            "max_output": 300,
            "avg_heart_rate": 150,
            "max_heart_rate": 180,
            "avg_cadence": 90,
            "calories": 500,
            "distance": 0.35, # miles
        },
        "total_work": 12345,
        "ftp_info": {"ftp": 250}
    }
    
    performance = {
        "duration": 60,
        "seconds_since_pedaling_start": [0, 30, 60],
        "metrics": [
            {"slug": "heart_rate", "values": [140, 150, 160], "zones": [{"slug": "zone1", "duration": 10}, {"slug": "zone2", "duration": 50}]},
            {"slug": "output", "values": [180, 200, 220]},
            {"slug": "cadence", "values": [85, 90, 95], "display_unit": "rpm"},
            {"slug": "speed", "values": [20, 21, 22], "display_unit": "mph", "average_value": 21, "max_value": 22}
        ]
    }
    
    segments = {
        "segment_list": [
            {"start_time_offset": 0, "length": 30, "name": "Warmup"},
            {"start_time_offset": 30, "length": 30, "name": "Effort"}
        ]
    }
    
    path = converter.convert(workout, performance, segments, title="Test Ride Name")
    
    # Read back and verify
    fit = FitFile.from_file(path)
    messages = [r.message for r in fit.records]
    
    records = [m for m in messages if isinstance(m, RecordMessage)]
    laps = [m for m in messages if isinstance(m, LapMessage)]
    sessions = [m for m in messages if isinstance(m, SessionMessage)]
    activities = [m for m in messages if isinstance(m, ActivityMessage)]
    workouts = [m for m in messages if isinstance(m, WorkoutMessage)]
    
    assert len(records) == 3
    assert len(laps) == 2
    assert len(sessions) == 1
    assert len(activities) == 1
    assert len(workouts) == 1
    
    assert workouts[0].workout_name == "Test Ride Name"
    
    session = sessions[0]
    assert session.avg_power == 200
    assert abs(session.time_in_hr_zone[0] - 10.0) < 0.1
    assert any(t > 0 for t in session.time_in_power_zone)
    
    # Verify Distance and Speed
    assert session.avg_speed > 0
    assert session.total_distance > 0
    assert session.total_work == 12345
    assert records[0].distance >= 0
    assert records[-1].distance > 0
    
    margin = 100
    assert abs(records[-1].distance - session.total_distance) < margin

def test_strength_conversion(tmp_path):
    output_dir = str(tmp_path / "test_output")
    os.makedirs(output_dir, exist_ok=True)
    converter = FitConverter(output_dir)
    
    workout = {
        "id": "strength_test",
        "start_time": datetime.now(timezone.utc).timestamp(),
        "fitness_discipline": "strength",
        "summary": {"calories": 100}
    }
    
    performance = {
        "duration": 60,
        "seconds_since_pedaling_start": [0, 60],
        "metrics": []
    }
    
    segments = {
        "segment_list": [
            {
                "start_time_offset": 0, 
                "length": 60, 
                "sub_segments_v2": [
                    {
                        "offset": 0,
                        "length": 60,
                        "rounds": 10,
                        "movements": [{"id": "01251235527748368069f9dc898aadf3", "name": "Arnold Press"}]
                    }
                ]
            }
        ]
    }
    
    path = converter.convert(workout, performance, segments)
    
    fit = FitFile.from_file(path)
    messages = [r.message for r in fit.records]
    sets = [m for m in messages if isinstance(m, SetMessage)]
    
    assert len(sets) == 1
    assert sets[0].repetitions == 10
    
    # Check category
    category_values = [c if isinstance(c, int) else c.value for r in fit.records if isinstance(r.message, SetMessage) for c in r.message.category]
    assert ExerciseCategory.SHOULDER_PRESS.value in category_values
