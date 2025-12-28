import os
import re
import math
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from fit_tool.fit_file_builder import FitFileBuilder
from fit_tool.profile.messages.file_id_message import FileIdMessage
from fit_tool.profile.messages.event_message import EventMessage
from fit_tool.profile.messages.sport_message import SportMessage
from fit_tool.profile.messages.record_message import RecordMessage
from fit_tool.profile.messages.session_message import SessionMessage
from fit_tool.profile.messages.training_file_message import TrainingFileMessage
from fit_tool.profile.messages.zones_target_message import ZonesTargetMessage
from fit_tool.profile.messages.user_profile_message import UserProfileMessage
from fit_tool.profile.messages.device_info_message import DeviceInfoMessage
from fit_tool.profile.messages.activity_message import ActivityMessage
from fit_tool.profile.messages.workout_message import WorkoutMessage
from fit_tool.profile.messages.lap_message import LapMessage
from fit_tool.profile.messages.workout_step_message import WorkoutStepMessage
from fit_tool.profile.messages.set_message import SetMessage
from fit_tool.profile.profile_type import (
    Sport, SubSport, FileType, Event, EventType, Manufacturer,
    SetType, Intensity, WorkoutStepDuration, WorkoutStepTarget, LapTrigger,
    DisplayPower, HrZoneCalc, PwrZoneCalc, SourceType, Activity
)

from .exercise_mapping import STRENGTH_EXERCISE_MAPPINGS, IGNORED_PELOTON_EXERCISES, is_rest

class FitConverter:
    METERS_PER_MILE = 1609.34

    def __init__(self, output_dir: str = "p2g_output"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def convert(self, workout: Dict[str, Any], performance: Dict[str, Any], 
                segments: Optional[Dict[str, Any]] = None, 
                user_data: Optional[Dict[str, Any]] = None,
                title: Optional[str] = None) -> str:
        workout_id = workout["id"]
        start_time_ts = workout["start_time"]
        end_time_ts = workout.get("end_time") or (start_time_ts + performance.get("duration", 0))
        
        # Determine sport
        discipline = workout.get("fitness_discipline", "cycling")
        sport = self._get_garmin_sport(workout)
        sub_sport = self._get_garmin_sub_sport(workout)


        builder = FitFileBuilder()

        if not title:
            ride = workout.get("ride") or {}
            ride_title = ride.get("title") or workout.get("id")
            instructor = (ride.get("instructor") or {}).get("name")
            if not instructor:
                provider = ride.get("content_provider")
                if provider and provider.lower() == "entertainment":
                    instructor = "ENTERTAINMENT"
                # You could add others here if needed

            if instructor and instructor not in ["ENTERTAINMENT", "JUST RIDE"]:
                title = f"{ride_title} with {instructor}"
            else:
                title = ride_title

        # Determine filename
        # Format: YYYYMMDD_HHMMSS_WorkoutName_ID.fit
        dt = datetime.fromtimestamp(start_time_ts, tz=timezone.utc)
        ts_str = dt.strftime("%Y%m%d_%H%M%S")
        
        # Sanitize title: only alphanumeric and underscores
        safe_title = re.sub(r'[^a-zA-Z0-9]', '_', title)
        # Remove consecutive underscores
        safe_title = re.sub(r'_+', '_', safe_title).strip('_')
        
        file_name = f"{ts_str}_{safe_title}_{workout_id}.fit"
        # Truncate to 251 + .fit = 255 chars max
        if len(file_name) > 255:
            file_name = file_name[:251] + ".fit"
        
        file_path = os.path.join(self.output_dir, file_name)

        # 1. FileID Message
        file_id_msg = FileIdMessage()
        file_id_msg.type = FileType.ACTIVITY
        
        # Product IDs matching C# GarminDevices
        if sport == Sport.CYCLING:
            file_id_msg.manufacturer = 89 # Tacx
            file_id_msg.product = 20533 # TacxTrainingAppWin
        elif sport == Sport.ROWING:
            file_id_msg.manufacturer = 1 # Garmin
            file_id_msg.product = 3943 # Epix
        else:
            file_id_msg.manufacturer = 1 # Garmin
            file_id_msg.product = 2691 # FR935
            
        file_id_msg.serial_number = 12345
        file_id_msg.time_created = int(start_time_ts * 1000)
        builder.add(file_id_msg)

        # 2. Event Message (Timer Start)
        event_msg = EventMessage()
        event_msg.timestamp = int(start_time_ts * 1000)
        event_msg.event = Event.TIMER
        event_msg.event_type = EventType.START
        event_msg.data = 0
        event_msg.event_group = 0
        builder.add(event_msg)

        # 3. Device Info Message
        device_info_msg = DeviceInfoMessage()
        device_info_msg.timestamp = int(start_time_ts * 1000)
        if sport == Sport.CYCLING:
            device_info_msg.manufacturer = 89
            device_info_msg.product = 20533
            device_info_msg.product_name = "TacxTrainingAppWin"
        elif sport == Sport.ROWING:
            device_info_msg.manufacturer = 1
            device_info_msg.product = 3943
            device_info_msg.product_name = "Epix"
        else:
            device_info_msg.manufacturer = 1
            device_info_msg.product = 2691
            device_info_msg.product_name = "Forerunner 935"
        device_info_msg.serial_number = 12345
        device_info_msg.device_index = 0
        device_info_msg.source_type = SourceType.LOCAL
        builder.add(device_info_msg)

        # 4. User Profile Message
        user_profile_msg = UserProfileMessage()
        if user_data:
            user_profile_msg.weight = self._convert_weight_to_kg(user_data.get("weight") or 0, "lbs")
        user_profile_msg.power_setting = DisplayPower.PERCENT_FTP
        builder.add(user_profile_msg)

        # 5. Sport Message
        sport_msg = SportMessage()
        sport_msg.sport = sport
        sport_msg.sub_sport = sub_sport
        builder.add(sport_msg)

        # 6. Zones Target Message
        zones_msg = ZonesTargetMessage()
        if sport == Sport.CYCLING:
            ftp = self._get_cycling_ftp(workout, user_data)
            if ftp:
                zones_msg.functional_threshold_power = ftp
                zones_msg.pwr_calc_type = PwrZoneCalc.PERCENT_FTP
        
        max_hr = self._get_user_max_hr(performance, user_data)
        if max_hr:
            zones_msg.max_heart_rate = max_hr
            zones_msg.hr_calc_type = HrZoneCalc.PERCENT_MAX_HR
        builder.add(zones_msg)

        # 7. Training File Message
        training_msg = TrainingFileMessage()
        training_msg.timestamp = int(start_time_ts * 1000)
        training_msg.time_created = int(start_time_ts * 1000)
        training_msg.manufacturer = file_id_msg.manufacturer
        training_msg.product = file_id_msg.product
        training_msg.serial_number = file_id_msg.serial_number
        training_msg.type = FileType.WORKOUT
        builder.add(training_msg)

        # 8. Records (Bread and butter)
        self._add_metrics(builder, performance, workout, sport)

        # 9. Laps / Segments / Steps
        lap_count = 0
        if sub_sport == SubSport.STRENGTH_TRAINING:
            exercises = self._get_workout_exercises(workout, segments)
            # Strength sets are not laps
            self._add_strength_sets(builder, exercises, start_time_ts)
            lap_count = 0 
        else:
            # Check for structured workout steps (targets)
            steps_and_laps = self._get_workout_steps_and_laps(performance, start_time_ts, sport, sub_sport)
            if steps_and_laps:
                for step, lap in steps_and_laps:
                    builder.add(step)
                    builder.add(lap)
                lap_count = len(steps_and_laps)
            else:
                laps = self._get_laps(performance, start_time_ts, sport, sub_sport, segments)
                for lap in laps:
                    builder.add(lap)
                lap_count = len(laps)

        # 11. Workout Message (Naming)
        if title:
            wkt_msg = WorkoutMessage()
            wkt_msg.workout_name = title
            wkt_msg.sport = sport
            wkt_msg.sub_sport = sub_sport
            wkt_msg.capabilities = 32 # Match C#
            builder.add(wkt_msg)

        # 12. Session Message
        session_msg = self._get_session_msg(workout, performance, sport, sub_sport, start_time_ts, end_time_ts, lap_count, title, user_data)
        ftp = self._get_cycling_ftp(workout, user_data)
        if ftp:
            session_msg.threshold_power = ftp
        builder.add(session_msg)

        # 13. Activity Message
        activity_msg = ActivityMessage()
        activity_msg.timestamp = int(end_time_ts * 1000)
        if title:
            activity_msg.name = title
        
        # Add local timestamp (offset from UTC)
        now = datetime.now()
        utcnow = datetime.now(timezone.utc)
        offset = (now.replace(tzinfo=None) - utcnow.replace(tzinfo=None)).total_seconds()
        # FIT local_timestamp is uint32 (seconds since epoch)
        activity_msg.local_timestamp = int(end_time_ts + offset)
        
        activity_msg.num_sessions = 1
        activity_msg.type = Activity.MANUAL
        activity_msg.event = Event.ACTIVITY
        activity_msg.event_type = EventType.STOP
        builder.add(activity_msg)

        fit_file = builder.build()
        fit_file.to_file(file_path)

        return file_path

    def _add_metrics(self, builder: FitFileBuilder, performance: Dict[str, Any], workout: Dict[str, Any], sport: Sport):
        metrics = performance.get("metrics") or []
        hr_data = self._get_metric_values(metrics, "heart_rate")
        power_data = self._get_metric_values(metrics, "output")
        cadence_data = self._get_metric_values(metrics, "cadence") if sport != Sport.ROWING else self._get_metric_values(metrics, "stroke_rate")
        speed_data = self._get_metric_values(metrics, "speed") or self._get_metric_values(metrics, "split_pace") or self._get_metric_values(metrics, "pace")
        resistance_data = self._get_metric_values(metrics, "resistance")
        elevation_data = self._get_metric_values(metrics, "altitude")
        incline_data = self._get_metric_values(metrics, "incline")
        
        # GPS
        location_data = performance.get("location_data") or []
        coords = []
        for ld in location_data:
            if ld:
                coords.extend(ld.get("coordinates") or [])

        start_time_ts = workout["start_time"]
        seconds = performance.get("seconds_since_pedaling_start", [])
        
        total_distance = 0.0
        last_elapsed = 0
        
        for i, elapsed in enumerate(seconds):
            record = RecordMessage()
            record.timestamp = int((start_time_ts + elapsed) * 1000)
            
            # Calculate accumulated distance
            if speed_data and i < len(speed_data):
                s_unit = self._get_metric_unit(metrics, "speed") or self._get_metric_unit(metrics, "pace") or "mph"
                speed_mps = self._convert_to_mps(speed_data[i], s_unit)
                record.speed = speed_mps
                
                # Assume 1 second intervals if not specified, or use diff
                interval = elapsed - last_elapsed
                if interval > 0:
                    total_distance += speed_mps * interval
                
            record.distance = total_distance
            last_elapsed = elapsed
            
            if hr_data and i < len(hr_data):
                record.heart_rate = int(hr_data[i])
            if power_data and i < len(power_data):
                record.power = int(power_data[i])
            if cadence_data and i < len(cadence_data):
                record.cadence = int(cadence_data[i])
            
            if resistance_data and i < len(resistance_data):
                # 0-100 to 0-254
                record.resistance = int(254 * (resistance_data[i] / 100.0))
            
            if elevation_data and i < len(elevation_data):
                record.altitude = self._convert_to_meters(elevation_data[i], self._get_metric_unit(metrics, "altitude") or "ft")
            
            if incline_data and i < len(incline_data):
                record.grade = float(incline_data[i])
            
            if coords and i < len(coords):
                record.position_lat = self._convert_degrees_to_semicircles(coords[i].get("lat"))
                record.position_long = self._convert_degrees_to_semicircles(coords[i].get("lng"))
            
            builder.add(record)

    def _get_session_msg(self, workout: Dict[str, Any], performance: Dict[str, Any], 
                         sport: Sport, sub_sport: SubSport, 
                         start_time_ts: float, end_time_ts: float, lap_count: int, 
                         title: str = None, user_data: Optional[Dict[str, Any]] = None) -> SessionMessage:
        summary_data = workout.get("summary") or {}
        performance_summaries = performance.get("summaries") or []
        metrics = performance.get("metrics") or []
        
        session = SessionMessage()
        if title:
            session.name = title

        session.timestamp = int(end_time_ts * 1000)
        session.start_time = int(start_time_ts * 1000)
        duration = performance.get("duration", 0)
        session.total_elapsed_time = duration
        session.total_timer_time = duration
        
        # Calories
        calories_summary = next((s for s in performance_summaries if s.get("slug") in ["calories", "total_calories"]), None)
        calories = 0
        if calories_summary:
            calories = calories_summary.get("value") or 0
        else:
            calories = summary_data.get("calories") or summary_data.get("total_calories") or 0
        session.total_calories = int(calories)
        
        # Distance
        distance_summary = next((s for s in performance_summaries if s.get("slug") == "distance"), None)
        distance_meters = 0.0
        if distance_summary:
            distance_meters = self._convert_to_meters(distance_summary.get("value") or 0, distance_summary.get("display_unit") or "mi")
        else:
            distance_meters = (summary_data.get("distance") or 0) * self.METERS_PER_MILE
            
        session.total_distance = distance_meters

        # Elevation
        elevation_summary = next((s for s in performance_summaries if s.get("slug") == "elevation"), None)
        if elevation_summary:
            elevation_meters = self._convert_to_meters(elevation_summary.get("value") or 0, elevation_summary.get("display_unit") or "ft")
            session.total_ascent = int(elevation_meters)
        
        # Power
        output_metric = next((m for m in metrics if m.get("slug") == "output"), {})
        # Check both avg_output and avg_power since Peloton tags vary
        session.avg_power = int(output_metric.get("average_value") or summary_data.get("avg_output") or summary_data.get("avg_power") or 0)
        session.max_power = int(output_metric.get("max_value") or summary_data.get("max_output") or summary_data.get("max_power") or 0)
        session.total_work = int(workout.get("total_work") or summary_data.get("total_work") or 0)
        
        # Speed
        speed_metric = next((m for m in metrics if m.get("slug") in ["speed", "split_pace", "pace"]), {})
        if speed_metric:
            unit = speed_metric.get("display_unit") or "mph"
            session.avg_speed = self._convert_to_mps(speed_metric.get("average_value") or 0, unit)
            session.max_speed = self._convert_to_mps(speed_metric.get("max_value") or 0, unit)
            session.enhanced_avg_speed = session.avg_speed
            session.enhanced_max_speed = session.max_speed

        # Grade
        grade_metric = next((m for m in metrics if m.get("slug") == "incline"), {})
        if grade_metric:
            session.avg_grade = float(grade_metric.get("average_value") or 0)
            session.max_pos_grade = float(grade_metric.get("max_value") or 0)
        
        # Cadence
        cad_slug = "cadence" if sport != Sport.ROWING else "stroke_rate"
        cad_metric = next((m for m in metrics if m.get("slug") == cad_slug), {})
        session.avg_cadence = int(cad_metric.get("average_value") or summary_data.get("avg_cadence") or summary_data.get("avg_stroke_rate") or 0)
        session.max_cadence = int(cad_metric.get("max_value") or summary_data.get("max_cadence") or summary_data.get("max_stroke_rate") or 0)
        
        session.max_cad_list = [session.max_cadence]
        
        session.sport = sport
        session.sub_sport = sub_sport
        session.num_laps = lap_count
        
        # Power Zones (Match C# rules for summaties, but fix threshold for Garmin display)
        ftp = self._get_cycling_ftp(workout, user_data)
        
        # HEURISTIC: If Running and FTP is clearly just the cycling fallback (low),
        # use avg power to guess a realistic running threshold for Garmin's zones.
        if sport == Sport.RUNNING and (not ftp or ftp < session.avg_power):
            ftp = int(session.avg_power / 0.85)

        if ftp:
            session.threshold_power = ftp
            
            # C# ONLY includes the explicit 7-zone summary table for Cycling with specific workout FTP
            if sport == Sport.CYCLING:
                ftp_info = workout.get("ftp_info")
                if ftp_info and ftp_info.get("ftp", 0) > 0:
                    power_metric = next((m for m in metrics if m.get("slug") == "output"), {})
                    power_values = power_metric.get("values") or []
                    if power_values:
                        p_zones = self._calculate_power_zones(ftp)
                        
                        pwr_zone_durations = [0] * 7
                        for val in power_values:
                            if val is None: continue
                            for idx, (low, high) in enumerate(p_zones):
                                if low <= val <= high:
                                    pwr_zone_durations[idx] += 1
                                    break
                        
                        session.time_in_power_zone = [int(d) for d in pwr_zone_durations]

        # HR (Manual calculation using % Max HR to avoid buggy Peloton data)
        hr_metric = next((m for m in metrics if m.get("slug") == "heart_rate"), {})
        session.avg_heart_rate = int(hr_metric.get("average_value") or summary_data.get("avg_heart_rate") or 0)
        
        # Get Max HR for zone boundaries
        max_hr = self._get_user_max_hr(performance, user_data)
        if not max_hr:
             max_hr = int(hr_metric.get("max_value") or summary_data.get("max_heart_rate") or 0)
        session.max_heart_rate = max_hr

        raw_hr_values = hr_metric.get("values") or []
        # Find the most accurate duration (active workout time)
        # Garmin/C# usually aim for the 'official' duration which might be 1812 for a 30m ride
        v_watch = workout.get("total_video_watch_time_seconds") or workout.get("v2_total_video_watch_time_seconds")
        official_duration = workout.get("ride", {}).get("duration") or workout.get("duration") or summary_data.get("duration")
        # HEURISTIC: If watch time exists and is close to samples, it might be the right anchor
        workout_duration = int(official_duration or v_watch or performance.get("duration", 0))
        
        # Clip HR values to duration to match C# logic
        if workout_duration > 0 and len(raw_hr_values) > workout_duration:
            # We usually skip the FIRST N samples (intro/lead-in)
            hr_values = raw_hr_values[-workout_duration:]
        else:
            hr_values = raw_hr_values

        if hr_values and max_hr > 0:
            # 1. Try to use boundaries from the metric definition (most ride-specific)
            hr_zones_def = hr_metric.get("zones") or []
            b = []
            if hr_zones_def:
                for i in range(1, 6):
                    z = next((zd for zd in hr_zones_def if zd.get("slug") == f"zone{i}"), None)
                    if z:
                        # Ensure it's BPM, not Power (Power floors are usually 0, 114, 132 etc)
                        val = int(z.get("min_value") or 0)
                        if val < 50 and i > 1: # Clearly not BPM, fallback
                            b = []
                            break
                        b.append(val)
            
            # 2. Fallback to standard 50-90% calculation if metric zones are suspect/missing
            if not b or len(b) < 5:
                # Use standard Peloton/Garmin integer boundaries based on percentage of Max HR
                def p_floor(p, m): return int(p * m + 0.5)
                b = [p_floor(p, max_hr) for p in [0.5, 0.6, 0.7, 0.8, 0.9]]
            
            durations = [0] * 6
            for val in hr_values:
                if val is None: continue
                # Bucketing samples based on floor boundaries
                if val >= b[4]: durations[5] += 1
                elif val >= b[3]: durations[4] += 1
                elif val >= b[2]: durations[3] += 1
                elif val >= b[1]: durations[2] += 1
                elif val >= b[0]: durations[1] += 1
                else: durations[0] += 1
            
            session.time_in_hr_zone = durations
        else:
            # Fallback if no HR data or Max HR
            hr_zones_def = hr_metric.get("zones") or []
            if hr_zones_def:
                dt = [0] * 5
                for i in range(1, 6):
                    zone = next((z for z in hr_zones_def if z.get("slug") == f"zone{i}"), None)
                    if zone:
                        dt[i-1] = int(float(zone.get("duration") or 0))
                session.time_in_hr_zone = [0] + dt

        return session

    def _calculate_power_zones(self, ftp: float) -> List[tuple]:
        return [
            (0, 0.55 * ftp),         # Zone 1
            (0.56 * ftp, 0.75 * ftp),  # Zone 2
            (0.76 * ftp, 0.90 * ftp),  # Zone 3
            (0.91 * ftp, 1.05 * ftp),  # Zone 4
            (1.06 * ftp, 1.20 * ftp),  # Zone 5
            (1.21 * ftp, 1.50 * ftp),  # Zone 6
            (1.51 * ftp, 9999)        # Zone 7
        ]

    def _get_workout_steps_and_laps(self, performance: Dict[str, Any], start_time_ts: float, 
                                     sport: Sport, sub_sport: SubSport) -> List[tuple]:
        # Extract cadence targets
        target_metrics = (performance.get("target_performance_metrics") or {}).get("target_graph_metrics") or []
        cadence_target = next((m for m in target_metrics if m.get("type") == "cadence"), None)
        
        if not cadence_target or "graph_data" not in cadence_target or not cadence_target["graph_data"]:
            return []

        graph_data = cadence_target["graph_data"]
        lower_targets = graph_data.get("lower", [])
        upper_targets = graph_data.get("upper", [])
        seconds = performance.get("seconds_since_pedaling_start", [])
        
        if not seconds:
            return []

        steps_and_laps = []
        prev_lower = -1
        prev_upper = -1
        step_index = 0
        duration = 0
        lap_distance = 0.0
        
        # We need speed data to calculate lap distance
        metrics = performance.get("metrics", [])
        speed_data = self._get_metric_values(metrics, "speed") or self._get_metric_values(metrics, "split_pace")
        speed_unit = self._get_metric_unit(metrics, "speed") or "mph"

        current_step = None
        current_lap = None

        for i, elapsed in enumerate(seconds):
            idx = int(elapsed) # graph_data is usually second-indexed
            curr_lower = lower_targets[idx] if idx < len(lower_targets) else 0
            curr_upper = upper_targets[idx] if idx < len(upper_targets) else 0
            
            if curr_lower != prev_lower or curr_upper != prev_upper:
                # Finish previous step
                if current_step and current_lap:
                    current_step.duration_value = duration * 1000 # ms
                    current_lap.total_elapsed_time = duration
                    current_lap.total_timer_time = duration
                    current_lap.timestamp = int((start_time_ts + elapsed) * 1000)
                    current_lap.total_distance = lap_distance
                    steps_and_laps.append((current_step, current_lap))
                    
                    step_index += 1
                    duration = 0
                    lap_distance = 0.0

                # Start new step
                current_step = WorkoutStepMessage()
                current_step.message_index = step_index
                current_step.duration_type = WorkoutStepDuration.TIME
                current_step.target_type = WorkoutStepTarget.CADENCE
                current_step.custom_target_value_low = int(curr_lower)
                current_step.custom_target_value_high = int(curr_upper)
                current_step.intensity = Intensity.ACTIVE if curr_upper > 60 else Intensity.REST
                
                current_lap = LapMessage()
                current_lap.start_time = int((start_time_ts + elapsed) * 1000)
                current_lap.message_index = step_index
                current_lap.event = Event.LAP
                current_lap.lap_trigger = LapTrigger.TIME
                current_lap.sport = sport
                current_lap.sub_sport = sub_sport

                prev_lower = curr_lower
                prev_upper = curr_upper

            # Increment duration and distance AFTER step transition logic
            duration += 1
            if speed_data and i < len(speed_data):
                lap_distance += self._convert_to_mps(speed_data[i], speed_unit) # Simplified 1s interval

        # Final step
        if current_step and current_lap:
            current_step.duration_value = duration * 1000
            current_lap.total_elapsed_time = duration
            current_lap.total_timer_time = duration
            current_lap.timestamp = int((start_time_ts + seconds[-1]) * 1000)
            current_lap.total_distance = lap_distance
            steps_and_laps.append((current_step, current_lap))

        return steps_and_laps

    def _get_laps(self, performance: Dict[str, Any], start_time_ts: float, 
                  sport: Sport, sub_sport: SubSport, 
                  segments: Optional[Dict[str, Any]] = None) -> List[LapMessage]:
        if segments and segments.get("segment_list"):
            return self._get_laps_from_segments(segments, start_time_ts, sport, sub_sport)
        
        # Try distance-based laps mirroring C# logic
        dist_laps = self._get_laps_from_distance(performance, start_time_ts, sport, sub_sport)
        if dist_laps:
            return dist_laps

        # Final fallback to one lap
        lap = LapMessage()
        lap.start_time = int(start_time_ts * 1000)
        lap.timestamp = int((start_time_ts + performance.get("duration", 0)) * 1000)
        lap.total_elapsed_time = performance.get("duration", 0)
        lap.total_timer_time = performance.get("duration", 0)
        lap.sport = sport
        lap.sub_sport = sub_sport
        return [lap]

    def _get_laps_from_segments(self, segments: Dict[str, Any], start_time_ts: float, 
                                sport: Sport, sub_sport: SubSport) -> List[LapMessage]:
        laps = []
        for i, seg in enumerate(segments["segment_list"]):
            lap = LapMessage()
            offset = seg.get("start_time_offset", 0)
            length = seg.get("length", 0)
            lap.start_time = int((start_time_ts + offset) * 1000)
            lap.timestamp = int((start_time_ts + offset + length) * 1000)
            lap.total_elapsed_time = length
            lap.total_timer_time = length
            lap.message_index = i
            lap.sport = sport
            lap.sub_sport = sub_sport
            laps.append(lap)
        return laps

    def _get_laps_from_distance(self, performance: Dict[str, Any], start_time_ts: float, 
                                sport: Sport, sub_sport: SubSport) -> List[LapMessage]:
        metrics = performance.get("metrics") or []
        speed_data = self._get_metric_values(metrics, "speed") or self._get_metric_values(metrics, "split_pace") or self._get_metric_values(metrics, "pace")
        if not speed_data:
            return []

        speed_unit = self._get_metric_unit(metrics, "speed") or self._get_metric_unit(metrics, "pace") or "mph"
        # Mirror C# lap distances: 1000m for metric, 500m for rowing, 1600m for imperial
        if sport == Sport.ROWING:
            lap_meters = 500
        elif "km" in speed_unit.lower() or "kph" in speed_unit.lower():
            lap_meters = 1000
        else:
            lap_meters = 1600 # Close enough to 1 mile, following C#
            
        hr_data = self._get_metric_values(metrics, "heart_rate") or []
        pow_data = self._get_metric_values(metrics, "output") or []
        cad_data = self._get_metric_values(metrics, "cadence") or self._get_metric_values(metrics, "stroke_rate") or []
        seconds = performance.get("seconds_since_pedaling_start", [])
        
        laps = []
        current_lap = None
        lap_dist = 0.0
        lap_dur = 0
        
        # Aggregates
        h_sum = h_max = h_cnt = 0
        p_sum = p_max = p_cnt = 0
        c_sum = c_max = c_cnt = 0
        
        last_elapsed = 0
        for i, elapsed in enumerate(seconds):
            if current_lap is None:
                current_lap = LapMessage()
                current_lap.start_time = int((start_time_ts + elapsed) * 1000)
                current_lap.message_index = len(laps)
                current_lap.sport = sport
                current_lap.sub_sport = sub_sport
                lap_dist = 0.0
                lap_dur = 0
                h_sum = h_max = h_cnt = 0
                p_sum = p_max = p_cnt = 0
                c_sum = c_max = c_cnt = 0

            interval = elapsed - last_elapsed
            if interval > 0:
                s_val = speed_data[i] if i < len(speed_data) and speed_data[i] is not None else 0
                mps = self._convert_to_mps(s_val, speed_unit)
                lap_dist += mps * interval
                lap_dur += interval
                
                if i < len(hr_data) and hr_data[i]:
                    h_sum += hr_data[i]; h_max = max(h_max, hr_data[i]); h_cnt += 1
                if i < len(pow_data) and pow_data[i]:
                    p_sum += pow_data[i]; p_max = max(p_max, pow_data[i]); p_cnt += 1
                if i < len(cad_data) and cad_data[i]:
                    c_sum += cad_data[i]; c_max = max(c_max, cad_data[i]); c_cnt += 1

            last_elapsed = elapsed
            
            # Check for lap completion
            if lap_dist >= lap_meters or i == len(seconds) - 1:
                current_lap.timestamp = int((start_time_ts + elapsed) * 1000)
                current_lap.total_elapsed_time = lap_dur
                current_lap.total_timer_time = lap_dur
                current_lap.total_distance = lap_dist
                if lap_dur > 0:
                    current_lap.avg_speed = lap_dist / lap_dur
                if h_cnt > 0:
                    current_lap.avg_heart_rate = int(h_sum / h_cnt)
                    current_lap.max_heart_rate = int(h_max)
                if p_cnt > 0:
                    current_lap.avg_power = int(p_sum / p_cnt)
                    current_lap.max_power = int(p_max)
                if c_cnt > 0:
                    current_lap.avg_cadence = int(c_sum / c_cnt)
                    current_lap.max_cadence = int(c_max)
                
                laps.append(current_lap)
                current_lap = None
                
        return laps

    def _add_strength_sets(self, builder: FitFileBuilder, exercises: List[Dict[str, Any]], start_time_ts: float) -> int:
        added_sets = 0
        for ex in exercises:
            peloton_id = ex["id"]
            is_rest_flag = is_rest(peloton_id)
            mapping = None
            
            if not is_rest_flag:
                mapping = STRENGTH_EXERCISE_MAPPINGS.get(peloton_id)
                if not mapping:
                    # Skip unmapped exercises to match C# behavior
                    continue
            
            set_msg = SetMessage()
            
            # Times are in ms for fit_tool properties (based on field offsets)
            start_ms = int((start_time_ts + ex["start_offset_seconds"]) * 1000)
            duration_s = ex["duration_seconds"]
            
            set_msg.start_time = start_ms
            set_msg.duration = duration_s
            set_msg.message_index = added_sets
            set_msg.workout_step_index = added_sets
            
            if is_rest_flag:
                set_msg.set_type = SetType.REST.value
            else:
                set_msg.set_type = SetType.ACTIVE.value
                # GarminExercise stores ints
                set_msg.category = [mapping.category.value]
                set_msg.category_subtype = [mapping.name.value]
            
            reps = int(ex.get("reps", 0))
            if reps <= 0 and ex.get("duration_seconds", 0) > 0:
                # Fallback: estimate reps based on duration (e.g. 3s per rep)
                reps = int(ex["duration_seconds"] / 3)
            set_msg.repetitions = reps
            
            if ex.get("weight"):
                 # value is in lbs or kg from JSON. Convert to KG.
                w_val = self._convert_weight_to_kg(ex["weight"]["value"], ex["weight"]["unit"])
                set_msg.weight = w_val
                # C# does not set weight_display_unit
                # set_msg.weight_display_unit = 1
            
            builder.add(set_msg)
            added_sets += 1
        return added_sets



    def _get_workout_exercises(self, workout: Dict[str, Any], segments: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        exercises = []

        # 1. From Movement Tracker
        mtd = workout.get("movement_tracker_data") or workout.get("Movement_Tracker_Data") or {}
        cmsd = mtd.get("completed_movements_summary_data") or mtd.get("Completed_Movements_Summary_Data") or {}
        tracked = cmsd.get("repetition_summary_data") or cmsd.get("Repetition_Summary_Data") or []
        for rep in tracked:
            weight_list = rep.get("weight") or rep.get("Weight") or []
            weight_item = weight_list[0] if weight_list else {}
            weight_data = weight_item.get("weight_data") or weight_item.get("Weight_Data") or {}
            
            w_unit = weight_data.get("weight_unit") or weight_data.get("Weight_Unit")
            w_value = weight_data.get("weight_value") or weight_data.get("Weight_Value") or 0
            
            # Handle potential casing differences and field names (Completed_Number vs Completed_Reps)
            reps = rep.get("completed_reps") or rep.get("Completed_Reps") or rep.get("completed_number") or rep.get("Completed_Number") or 0
            
            exercises.append({
                "id": rep.get("movement_id") or rep.get("Movement_Id"),
                "name": rep.get("movement_name") or rep.get("Movement_Name"),
                "start_offset_seconds": rep.get("offset") if rep.get("offset") is not None else rep.get("Offset", 0),
                "duration_seconds": rep.get("length") if rep.get("length") is not None else rep.get("Length", 0),
                "reps": reps,
                "weight": {
                    "unit": w_unit,
                    "value": w_value
                }
            })
        

        # 2. From Segments if not already there
        segment_list = None
        if segments:
            # The /details endpoint returns { "segments": { "segment_list": [...] } }
            # But it can also vary. Let's be robust.
            if isinstance(segments, list):
                segment_list = segments
            else:
                # Try common paths
                segment_obj = segments.get("segments") or segments.get("Segments")
                if not segment_obj:
                    # Maybe it's in ride object
                    ride_obj = segments.get("ride") or segments.get("Ride") or {}
                    segment_obj = ride_obj.get("segments") or ride_obj.get("Segments")
                
                if not segment_obj:
                    segment_obj = segments
                
                if isinstance(segment_obj, list):
                    segment_list = segment_obj
                else:
                    segment_list = segment_obj.get("segment_list") or segment_obj.get("Segment_List") or segment_obj.get("segments")
        
        # Fallback to workout['ride']['segments'] if nothing found yet? 
        # Actually segments is already passed in from main.py which did the fetching.
            
        if segment_list:
            for i, seg in enumerate(segment_list):
                # Try multiple naming conventions for sub-segments
                sub_segments = (
                    seg.get("sub_segments_v2") or 
                    seg.get("SubSegments_V2") or 
                    seg.get("subsegments_v2") or 
                    seg.get("Subsegments_V2") or 
                    seg.get("sub_segments") or 
                    seg.get("SubSegments") or 
                    []
                )
                for j, sub in enumerate(sub_segments):
                    offset = sub.get("offset") if sub.get("offset") is not None else sub.get("Offset", 0)
                    movements = sub.get("movements") or sub.get("Movements") or []
                    
                    for k, move in enumerate(movements):
                        move_id = move.get("id") or move.get("Id")
                        if move_id in IGNORED_PELOTON_EXERCISES:
                            continue

                        # Avoid duplicates
                        if any(e["id"] == move_id and e["start_offset_seconds"] == offset for e in exercises):
                            continue
                        
                        move_count = len(movements) if movements else 1
                        length = sub.get("length") if sub.get("length") is not None else sub.get("Length", 0)
                        rounds = sub.get("rounds") if sub.get("rounds") is not None else sub.get("Rounds", 0)

                        exercises.append({
                            "id": move_id,
                            "name": move.get("name") or move.get("Name"),
                            "start_offset_seconds": offset,
                            "duration_seconds": length // move_count,
                            "reps": rounds
                        })

        
        exercises.sort(key=lambda x: x["start_offset_seconds"])
        return exercises

    def _get_cycling_ftp(self, workout: Dict[str, Any], user_data: Optional[Dict[str, Any]]) -> Optional[int]:
        ftp = None
        ftp_info = workout.get("ftp_info") or {}
        if ftp_info and ftp_info.get("ftp", 0) > 0:
            ftp = ftp_info.get("ftp")
            if ftp_info.get("ftp_source") == "ftp_manual_source":
                ftp = int(round(ftp * 0.95))
        
        if (ftp is None or ftp <= 0) and user_data:
            source = user_data.get("cycling_ftp_source")
            if source == "ftp_manual_source":
                ftp = int(round((user_data.get("cycling_ftp") or 0) * 0.95))
            elif source == "ftp_workout_source":
                ftp = user_data.get("cycling_workout_ftp")
            
            if (ftp is None or ftp <= 0):
                ftp = user_data.get("estimated_cycling_ftp")
            
        return ftp

    def _get_user_max_hr(self, performance: Dict[str, Any], user_data: Optional[Dict[str, Any]] = None) -> Optional[int]:
        # 1. Check user_data (keys are often lowercase in Peloton responses)
        if user_data:
            possible_keys = ["customized_max_heart_rate", "Customized_Max_Heart_Rate", 
                             "estimated_max_heart_rate", "Estimated_Max_Heart_Rate",
                             "default_max_heart_rate", "Default_Max_Heart_Rate"]
            for key in possible_keys:
                max_hr = user_data.get(key)
                if max_hr:
                    return int(max_hr)

        # 2. Check performance metrics
        hr_metric = next((m for m in (performance.get("metrics") or []) if m.get("slug") == "heart_rate"), {})
        zones = hr_metric.get("zones") or []
        zone5 = next((z for z in zones if z.get("slug") == "zone5"), None)
        if zone5:
            m_val = zone5.get("max_value")
            if m_val:
                return int(m_val)
        
        # 3. Check summary
        summary = performance.get("summary") or {}
        p_max = summary.get("max_heart_rate")
        if p_max:
            return int(p_max)

        # Final Fallback to standard 178
        return 178

    # Helper methods
    def _get_metric_values(self, metrics: List[Dict], slug: str) -> Optional[List[float]]:
        for m in metrics:
            if m.get("slug") == slug:
                return m.get("values")
        return None

    def _get_metric_unit(self, metrics: List[Dict], slug: str) -> Optional[str]:
        for m in metrics:
            if m.get("slug") == slug:
                return m.get("display_unit")
        return None

    def _convert_to_mps(self, value: float, unit: str) -> float:
        if value is None or not isinstance(value, (int, float)):
            return 0.0
        if value <= 0: return 0.0
        if unit == "mph":
            return (value * self.METERS_PER_MILE) / 3600.0
        if unit == "kph":
            return (value * 1000.0) / 3600.0
        
        # Handle Pace (min/km, min/mi)
        low_unit = unit.lower()
        if "min/km" in low_unit:
            return 1000.0 / (value * 60.0) if value > 0 else 0.0
        if "min/mi" in low_unit or "min/mile" in low_unit:
            return self.METERS_PER_MILE / (value * 60.0) if value > 0 else 0.0
            
        return value

    def _convert_to_meters(self, value: float, unit: str) -> float:
        if unit == "ft":
            return value * 0.3048
        if unit == "mi":
            return value * self.METERS_PER_MILE
        if unit == "km":
            return value * 1000.0
        return value

    def _convert_weight_to_kg(self, value: float, unit: str) -> float:
        if unit == "lbs":
            return value * 0.453592
        return value

    def _convert_degrees_to_semicircles(self, degrees: float) -> int:
        if degrees is None: return 0
        return int(degrees * (pow(2, 31) / 180.0))

    def _get_garmin_sport(self, workout: Dict[str, Any]) -> Sport:
        discipline = workout.get("fitness_discipline", "").lower()
        if "cycling" in discipline or "bike_bootcamp" in discipline:
            return Sport.CYCLING
        if "running" in discipline or "walking" in discipline:
            return Sport.RUNNING
        if "rowing" in discipline or "caesar" in discipline:
            return Sport.ROWING
        # Cardio, Circuit, Strength, Stretching, Yoga, Meditation
        return Sport.TRAINING

    def _get_garmin_sub_sport(self, workout: Dict[str, Any]) -> SubSport:
        discipline = str(workout.get("fitness_discipline", "")).lower()
        is_outdoor = workout.get("is_outdoor", False)
        
        if is_outdoor:
            return SubSport.GENERIC
            
        if "cycling" in discipline or "bike_bootcamp" in discipline:
            return SubSport.INDOOR_CYCLING
        if "running" in discipline or "walking" in discipline:
            return SubSport.TREADMILL
        if "strength" in discipline:
            return SubSport.STRENGTH_TRAINING
        if "cardio" in discipline or "circuit" in discipline:
            return SubSport.CARDIO_TRAINING
        if "stretching" in discipline:
            return SubSport.FLEXIBILITY_TRAINING
        if "yoga" in discipline:
            return SubSport.YOGA
        if "meditation" in discipline:
            return SubSport.GENERIC  # BREATHING is missing in fit_tool
        if "rowing" in discipline or "caesar" in discipline:
            return SubSport.INDOOR_ROWING
        return SubSport.GENERIC
