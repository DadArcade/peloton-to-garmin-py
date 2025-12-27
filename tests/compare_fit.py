import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from fit_tool.fit_file import FitFile
from fit_tool.profile.messages.set_message import SetMessage

def dump_fit_sets(file_path):
    print(f"\n--- Analyzing {os.path.basename(file_path)} ---")
    try:
        fit_file = FitFile.from_file(file_path)
    except Exception as e:
        print(f"Failed to parse: {e}")
        return

    messages = fit_file.records
    set_msgs = [m for m in messages if isinstance(m.message, SetMessage)]
    
    print(f"Total Messages: {len(messages)}")
    print(f"Set Messages: {len(set_msgs)}")
    
    for i, record in enumerate(set_msgs):
        msg = record.message
        print(f"Set {i}:")
        # Print all fields present in the message
        # We access the fields directly via the helper methods or internal dictionary if needed
        # fit_tool messages usually have properties.
        
        # We'll rely on the object's string representation or manually check specific fields
        print(f"  Timestamp: {getattr(msg, 'timestamp', 'N/A')}")
        print(f"  StartTime: {getattr(msg, 'start_time', 'N/A')}")
        print(f"  Duration: {getattr(msg, 'duration', 'N/A')}")
        print(f"  Repetitions: {getattr(msg, 'repetitions', 'N/A')}")
        print(f"  Weight: {getattr(msg, 'weight', 'N/A')}")
        print(f"  SetType: {getattr(msg, 'set_type', 'N/A')}")
        print(f"  Category: {getattr(msg, 'category', 'N/A')}")
        print(f"  CategorySubtype: {getattr(msg, 'category_subtype', 'N/A')}")
        print(f"  MessageIndex: {getattr(msg, 'message_index', 'N/A')}")
        print(f"  WktStepIndex: {getattr(msg, 'workout_step_index', 'N/A')}")

    # Also check the ORDER. Are sets at the end?
    if set_msgs:
        first_set_index = messages.index(set_msgs[0])
        last_set_index = messages.index(set_msgs[-1])
        print(f"First Set Message Index in File: {first_set_index}")
        print(f"Last Set Message Index in File: {last_set_index}")
        print(f"Total Records: {len(messages)}")


def main():
    base_dir = Path("python-client/p2g_output")
    c_sharp_file = base_dir / "cf0447504e9d41ed80f24628dc8ad653_10_min_Core_Strength_with_Ben_Alldis.fit"
    python_file = base_dir / "peloton_cf0447504e9d41ed80f24628dc8ad653.fit"
    
    dump_fit_sets(str(c_sharp_file))
    dump_fit_sets(str(python_file))

if __name__ == "__main__":
    main()
