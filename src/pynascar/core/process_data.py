from typing import List, Dict, Any, Optional,Tuple
import pandas as pd
import re 
from ..codes import FLAG_CODE

class NASCARDataProcessor:
    """ 
    Handles incoming data, any transformation and cleaning.
    """

    # Make sure data is passed in as data.get('weekend_race', [])[0]
    @staticmethod
    def process_race_data(data: Dict[str, Any]) -> pd.DataFrame:
        """
        Process race data and return a DataFrame.
        """
        if not data:
            return pd.DataFrame()
        
        results = data.get('results', [])

        driver_results = []
        for i in results:
            driver_results.append({
                'driver_id': i.get('driver_id'),
                'driver_name': i.get('driver_fullname'),
                'car_number': i.get('car_number'),
                'manufacturer': i.get('car_make'),
                'sponsor': i.get('sponsor'),
                'team': i.get('team_name'),
                'team_id': i.get('team_id'),
                'qualifying_order': i.get('qualifying_order'),
                'qualifying_position': i.get('qualifying_position'),
                'qualifying_speed': i.get('qualifying_speed'),
                'starting_position': i.get('starting_position'),
                'finishing_position': i.get('finishing_position'),                    
                'laps_completed': i.get('laps_completed'),
                'points': i.get('points_earned'),
                'playoff_points': i.get('playoff_points_earned'),
                })

        return pd.DataFrame(driver_results)
    
    @staticmethod
    def process_caution_data(data: Dict[str, Any]) -> pd.DataFrame:

        if not data:
            return pd.DataFrame()
        
        caution_segments = data.get('caution_segments', [])
        caution_rows = []
        for i in caution_segments:
                caution_rows.append({
                    'start_lap': i.get('start_lap'),
                    'end_lap': i.get('end_lap'),
                    'caution_type': i.get('reason'),
                    'comment': i.get('comment'),
                    'flag_state': i.get('flag_state'),
                })
        return pd.DataFrame(caution_rows)
    
    @staticmethod
    def process_leader_data(data:Dict[str, Any]) -> pd.DataFrame:

        if not data:
            return pd.DataFrame()
        
        leaders = data.get('race_leaders', [])
        leader_list = []
        for i in leaders:
                leader_list.append({
                    'start_lap': i.get('start_lap'),
                    'end_lap': i.get('end_lap'),
                    'driver_name': None,
                    'car_number': i.get('car_number')
                })
        return pd.DataFrame(leader_list)

    @staticmethod
    def process_stage_data(data:Dict[str, Any],stage_number:int) -> pd.DataFrame:

        if not data:
            return pd.DataFrame()
        stages = data.get('results', [])

        stage_results = []
        for result in stages:
            stage_results.append({
                'driver_id': result.get('driver_id'),
                'driver_name': result.get('driver_fullname'),
                'car_number': result.get('car_number'),
                'stage_number': stage_number,
                'position': result.get('finishing_position'),
                'stage_points': result.get('stage_points'),
            })
        
        return pd.DataFrame(stage_results)
    
    # weekend_runs = data.get('weekend_runs', [])
    @staticmethod
    def process_practice_qualifying_data(data: List[Dict]) -> Tuple[pd.DataFrame, pd.DataFrame]:

        if not data:
            return pd.DataFrame(), pd.DataFrame()

        practice_res = []
        quali_res = []
        for event in data:
            name = (event.get('run_name') or '').lower()
            for run in event.get('results', []):
                if "practice" in name:
                    practice_res.append({
                        'driver_id': run.get('driver_id'),
                        'driver_name': run.get('driver_name'),
                        'manufacturer': run.get('manufacturer'),
                        'practice_name': name,
                        'position': run.get('finishing_position'),
                        'lap_time': run.get('best_lap_time'),
                        'speed': run.get('best_lap_speed'),
                        'total_laps': run.get('laps_completed'),
                        'delta_to_leader': run.get('delta_leader')
                    })

                if "pole_qualifying" in name:
                    quali_res.append({
                        'driver_id': run.get('driver_id'),
                        'driver_name': run.get('driver_name'),
                        'manufacturer': run.get('manufacturer'),
                        'position': run.get('finishing_position'),
                        'lap_time': run.get('best_lap_time'),
                        'speed': run.get('best_lap_speed'),
                        'total_laps': run.get('laps_completed'),
                        'delta_to_leader': run.get('delta_leader')
                    })

        practice_data = pd.DataFrame(practice_res) if practice_res else pd.DataFrame()
        practice_data['practice_number'] = practice_data['practice_name'].apply(lambda x: _parse_practice_quali_number(x, practice=True)) if not practice_data.empty else None
        practice_data = practice_data.sort_values(by='position') if not practice_data.empty else pd.DataFrame()

        qualifying_data = pd.DataFrame(quali_res) if quali_res else pd.DataFrame()
        qualifying_data['qualifying_number'] = qualifying_data['qualifying_name'].apply(lambda x: _parse_practice_quali_number(x, practice=False)) if not qualifying_data.empty else None
        qualifying_data = qualifying_data.sort_values(by='position') if not qualifying_data.empty else pd.DataFrame()
        return practice_data, qualifying_data

    @staticmethod
    def process_laps_data(data: Dict[str, Any]) -> pd.DataFrame:
        if not data:
            return pd.DataFrame()
        
        lap_times = []
        for i in data['laps']:
                driver = i.get('FullName')
                number = i.get('Number')
                manufacturer = i.get('Manufacturer')
                for j in i.get('Laps', []):
                    lap_times.append({
                        'driver_name': driver,
                        'car_number': number,
                        'manufacturer': manufacturer,
                        'Lap': j.get('Lap'),
                        'lap_time': j.get('LapTime'),
                        'lap_speed': j.get('LapSpeed'),
                        'position': j.get('RunningPos'),
                    })
        laps = pd.DataFrame(lap_times)
        laps['Lap'] = pd.to_numeric(laps['Lap'], errors='coerce').astype('Int64')
        laps['lap_time'] = pd.to_timedelta(laps['lap_time'], errors='coerce')
        laps['lap_speed'] = pd.to_numeric(laps['lap_speed'], errors='coerce')

        return laps

    @staticmethod
    def process_pit_stops(data: List[Dict[str, Any]]) -> pd.DataFrame:
        stops = []
        for i in data:
            stops.append({
                'driver_name': i.get('driver_name'),
                'lap': i.get('lap_count'),
                'manufacturer': i.get('vehicle_manufacturer'),
                'pit_in_flag_status': i.get('pit_in_flag_status'),
                'pit_out_flag_status': i.get('pit_out_flag_status'),
                'pit_in_race_time': i.get('pit_in_race_time'),
                'pit_out_race_time': i.get('pit_out_race_time'),
                'total_duration': i.get('total_duration'),
                'box_stop_race_time': i.get('box_stop_race_time'),
                'box_leave_race_time': i.get('box_leave_race_time'),
                'pit_stop_duration': i.get('pit_stop_duration'),
                'in_travel_duration': i.get('in_travel_duration'),
                'out_travel_duration': i.get('out_travel_duration'),
                'pit_stop_type': i.get('pit_stop_type'),
                'left_front_tire_changed': i.get('left_front_tire_changed'),
                'left_rear_tire_changed': i.get('left_rear_tire_changed'),
                'right_front_tire_changed': i.get('right_front_tire_changed'),
                'right_rear_tire_changed': i.get('right_rear_tire_changed'),
                'previous_lap_time': i.get('previous_lap_time'),
                'next_lap_time': i.get('next_lap_time'),
                'pit_in_rank': i.get('pit_in_rank'),
                'pit_out_rank': i.get('pit_out_rank'),
                'positions_gained_lost': i.get('positions_gained_lost'),
            })

        return pd.DataFrame(stops)
    
    @staticmethod
    def process_event_notes_data(data: Dict[str, Any]) -> pd.DataFrame:
        if not data:
            return pd.DataFrame()

        events = []
        laps = data.get('laps')
        for k,v in laps.items():
                for j in v:
                    events.append({
                        'Lap': k,
                        'Flag_State': j.get('FlagState'),
                        'Flag': None,
                        'note': j.get('Note'),
                        #'note_id': j.get('NoteID'),
                        'driver_ids': j.get('DriverIDs'),
                    })
        lap_events = pd.DataFrame(events) if events else pd.DataFrame()
        if not lap_events.empty:
            lap_events['Flag'] = lap_events['Flag_State'].map(FLAG_CODE)
    
        return pd.DataFrame(lap_events)
    
    @staticmethod
    def process_driver_data(data: Dict[str, Any]) -> pd.DataFrame:
        drivers = data[0].get('drivers', [])
        driver_list = []
        for i in drivers:
            driver_list.append({
                'driver_id': i.get('driver_id'),
                'driver_name': None,
                'start_position': i.get('start_ps'),
                'mid_position': i.get('mid_ps'),
                'position': i.get('ps'),
                'closing_position': i.get('closing_ps'),
                'closing_laps_diff': i.get('closing_laps_diff'),
                'best_position': i.get('best_ps'),
                'worst_position': i.get('worst_ps'),
                'avg_position': i.get('avg_ps'),
                'passes_green_flag': i.get('passes_gf'),
                'passing_diff': i.get('passing_diff'),
                'passed_green_flag': i.get('passed_gf'),
                'quality_passes': i.get('quality_passes'),
                'fast_laps': i.get('fast_laps'),
                'top15_laps': i.get('top15_laps'),
                'lead_laps': i.get('lead_laps'),
                'laps': i.get('laps'),
                'rating': i.get('rating'),
            })
        return pd.DataFrame(driver_list)
    
    @staticmethod
    def process_adv_driver_data(data: Dict[str,Any]) -> pd.DataFrame:
        vehicles = data.get('vehicles', [])
        driver_stats_advanced = []
        for vehicle in vehicles:
            driver = vehicle.get('driver', {})
            driver_stats_advanced.append({
                'driver_id': driver.get('driver_id'),
                'driver_name': driver.get('full_name'),
                'car_number': vehicle.get('vehicle_number'),
                'manufacturer': vehicle.get('vehicle_manufacturer'),
                'sponsor_name': vehicle.get('sponsor_name'),
                'best_lap': vehicle.get('best_lap'),
                'best_lap_speed': vehicle.get('best_lap_speed'),
                'best_lap_time': vehicle.get('best_lap_time'),
                'laps_position_improved': vehicle.get('laps_position_improved'),
                "fastest_laps_run": vehicle.get("fastest_laps_run"),
                'passes_made': vehicle.get('passes_made'),
                "times_passed": vehicle.get("times_passed"),
                'passing_differential': vehicle.get('passing_differential'),
                "quality_passes": vehicle.get("quality_passes"),
                'position_differential_last_10_percent': vehicle.get('position_differential_last_10_percent'),
            })
        return pd.DataFrame(driver_stats_advanced)


def _parse_practice_quali_number(name: str, practice: bool = True) -> int:
        """Infer practice round number from run name, fallback to sequence."""
        n = (name or "").lower()
        if 'final' in n:
            return 2
        m = re.search(r'practice\s*(\d+)', n) if practice else re.search(r'round\s*(\d+)', n)
        if m:
            return int(m.group(1))
        else:
            return 0