# src/race.py

import pandas as pd
import requests
import warnings
from .codes import FLAG_CODE

#https://cf.nascar.com/cacher/2023/2/5314/lap-times.json

class Race:
    def __init__(self, year, series_id,race_id=None,live=False):
        # Initialize race metadata
        self.year = year
        self.live = live
        self.series_id = series_id
        self.race_id = race_id
        self.entrants = None
        self.superspeedway = None
        self.winner = None
        self.data = {}

        # Practice and Qualifying.
        # This may be moved
        self.practice_data = pd.DataFrame()
        self.qualifying_data = pd.DataFrame()

        # Race Data
        self.name = None
        self.laps = None
        self.pit_stops = None
        self.events = None
        self.results = None
        self.cautions = None
        self.lead_changes = None
        self.lead_change_data = None
        self.start_time = None
        self.race_time = None
        self.end_time = None
        self.distance = None
        self.lap_count = None
        self.drivers = pd.DataFrame()

        # Stage Results. Currently shows only the top 10
        self.stage_1_results = None
        self.stage_2_results = None
        self.stage_3_results = None
        self.s1_lap_count = None
        self.s2_lap_count = None
        self.s3_lap_count = None

        # Initialize the race data
        self.fetch_laps()
        self.get_pit_stops()
        self.fetch_events()
        self.get_race_data()
        self.get_driver_stats()

    def get_race_data(self):
        """
        Fetch data for the race
        """   
        if self.live:
            url = f"https://cf.nascar.com/cacher/live/series_{self.series_id}/{self.race_id}/weekend-feed.json"
        else:
            url = f"https://cf.nascar.com/cacher/{self.year}/{self.series_id}/{self.race_id}/weekend-feed.json"

        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            weekend = data.get('weekend_race', [])[0]
            weekend_runs = data.get('weekend_runs', [])

            self.race_time = weekend.get('total_race_time')
            self.distance = weekend.get('scheduled_distance')
            self.lap_count = weekend.get('scheduled_laps')
            self.s1_lap_count = weekend.get('stage_1_laps')
            self.s2_lap_count = weekend.get('stage_2_laps')
            self.s3_lap_count = weekend.get('stage_3_laps')
            self.entrants = weekend.get('number_of_cars_in_field')
            self.superspeedway = weekend.get('restrictor_plate')

            
            results = weekend.get('results', [])
            cautions = weekend.get('caution_segments', [])
            leaders = weekend.get('race_leaders', [])
            stages = weekend.get('stage_results', [])

            driver_res = []
            cautions = []
            leader_list = []
            stage_1 = []
            stage_2 = []
            stage_3 = []

            for i in results:
                driver_res.append({
                    'driver_id': i.get('driver_id'),
                    'driver': i.get('driver_fullname'),
                    'driver_number': i.get('car_number'),
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
            self.results = pd.DataFrame(driver_res)

            for i in cautions:
                cautions.append({
                    'start_lap': i.get('start_lap'),
                    'end_lap': i.get('end_lap'),
                    'caution_type': i.get('reason'),
                    'comment': i.get('comment'),
                    'flag_state': i.get('flag_state'),
                })

            self.cautions = pd.DataFrame(cautions) if cautions else pd.DataFrame()
            self.cautions['Flag'] = self.cautions['flag_state'].map(FLAG_CODE) if not self.cautions.empty else None
            self.cautions['duration'] = self.cautions['end_lap'] - self.cautions['start_lap'] if not self.cautions.empty else None

            for i in leaders:
                leader_list.append({
                    'start_lap': i.get('start_lap'),
                    'end_lap': i.get('end_lap'),
                    'driver_name': None,
                    'car_number': i.get('car_number')
                })

            try:
                self.lead_changes = len(leader_list) - 1 if leader_list else 0
                self.lead_change_data = pd.DataFrame(leader_list) if leader_list else pd.DataFrame()
                self.lead_change_data['driver_name'] = self.lead_change_data['car_number'].map(self.results.set_index('driver_number')['driver']) if not self.lead_change_data.empty else None
            except Exception as e:
                print(f"Error processing lead changes: {e}")
            
            for i in stages:
                if i.get('stage_number') == 1:
                    for j in i.get('results', []):
                        stage_1.append({
                            'driver_id': j.get('driver_id'),
                            'driver_name': j.get('driver_fullname'),
                            'car_number': j.get('car_number'),
                            'position': j.get('finishing_position'),
                            'stage_points': j.get('stage_points'),
                        })
                elif i.get('stage_number') == 2:
                    for j in i.get('results', []):
                        stage_2.append({
                            'driver_id': j.get('driver_id'),
                            'driver_name': j.get('driver_fullname'),
                            'car_number': j.get('car_number'),
                            'position': j.get('finishing_position'),
                            'stage_points': j.get('stage_points'),
                        })
                elif i.get('stage_number') == 3:
                    for j in i.get('results', []):
                        stage_3.append({
                            'driver_id': j.get('driver_id'),
                            'driver_name': j.get('driver_fullname'),
                            'car_number': j.get('car_number'),
                            'position': j.get('finishing_position'),
                            'stage_points': j.get('stage_points'),
                        })

            self.stage_1_results = pd.DataFrame(stage_1) if stage_1 else pd.DataFrame()
            self.stage_2_results = pd.DataFrame(stage_2) if stage_2 else pd.DataFrame()
            self.stage_3_results = pd.DataFrame(stage_3) if stage_3 else pd.DataFrame()

            for i in weekend_runs:
                if 'practice' in i.get('run_name').lower():
                    if 'practice 1' in i.get('run_name').lower():
                        p1 = self.get_practice_results(i)
                        p1['practice_number'] = 1
                        self.practice_data = p1
                    if 'practice 2' in i.get('run_name').lower():
                        p2 = self.get_practice_results(i)
                        p2['practice_number'] = 2
                        self.practice_data = pd.concat([self.practice_data, p2], ignore_index=True)
                    if 'practice 3' in i.get('run_name').lower():
                        p3 = self.get_practice_results(i)
                        p3['practice_number'] = 3
                        self.practice_data = pd.concat([self.practice_data, p3], ignore_index=True)
                    if 'final practice' in i.get('run_name').lower():
                        final_practice = self.get_practice_results(i)
                        # Any final will be 4
                        final_practice['practice_number'] = 4
                        self.practice_data = pd.concat([self.practice_data, final_practice], ignore_index=True)
                    else:
                        self.practice_data = pd.concat([self.practice_data, self.get_practice_results(i)], ignore_index=True)

                elif 'pole qualifying' in i.get('run_name').lower():
                    # print(f"Qualifying run found: {i.get('run_name')}")
                    if 'round 1' in i.get('run_name').lower():
                        run1 = self.get_qualifying_results(i)
                        run1['qualifying_round'] = 1
                        self.qualifying_data = pd.concat([self.qualifying_data, run1], ignore_index=True) if not self.qualifying_data.empty else run1
                    if 'final round' in i.get('run_name').lower():
                        final_round = self.get_qualifying_results(i)
                        final_round['qualifying_round'] = 2
                        self.qualifying_data = pd.concat([self.qualifying_data, final_round], ignore_index=True) if not self.qualifying_data.empty else final_round
                    else: 
                        ukr = self.get_qualifying_results(i)
                        ukr['qualifying_round'] = None
                        self.qualifying_data = pd.concat([self.qualifying_data, ukr], ignore_index=True) if not self.qualifying_data.empty else ukr

        else:
            print(f"Failed to retrieve race data: {response.status_code}")

    def fetch_laps(self):
        """Fetch lap times for the specified race ID."""
        if self.live:
            url = f"https://cf.nascar.com/cacher/live/series_{self.series_id}/{self.race_id}/lap-times.json"
        else:
            url = f"https://cf.nascar.com/cacher/{self.year}/{self.series_id}/{self.race_id}/lap-times.json"

        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            self.data = data
            lap_times = []
            
            for i in data['laps']:
                driver = i.get('FullName')
                number = i.get('Number')
                manufacturer = i.get('Manufacturer')
                for j in i.get('Laps', []):
                    lap_times.append({
                        'Driver': driver,
                        'Number': number,
                        'Manufacturer': manufacturer,
                        'Lap': j.get('Lap'),
                        'lap_time': j.get('LapTime'),
                        'lap_speed': j.get('LapSpeed'),
                        'position': j.get('RunningPos'),
                    })
            self.laps = pd.DataFrame(lap_times)
            self.laps['Lap'] = self.laps['Lap'].astype(int)
            self.laps['lap_time'] = pd.to_timedelta(self.laps['lap_time'])
            self.laps['lap_speed'] = self.laps['lap_speed'].astype(float)
        else:
            print(f"Failed to retrieve lap data: {response.status_code}")
            print(f"url: {url}")

    def get_pit_stops(self):
        """Get pit stop information for the race."""
        if self.live:
            url = f"https://cf.nascar.com/cacher/live/series_{self.series_id}/{self.race_id}/live-pit-data.json"
        else:
            url = f"https://cf.nascar.com/cacher/{self.year}/{self.series_id}/{self.race_id}/live-pit-data.json"

        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            stops = []
            for i in data:
                stops.append({
                    'Driver': i.get('driver_name'),
                    'Lap': i.get('lap_count'),
                    'Manufacturer': i.get('vehicle_manufacturer'),
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
            # store both list and a DataFrame for convenience
            self.pit_stops = pd.DataFrame(stops) if stops else pd.DataFrame()
        else:
            print(f"Failed to retrieve pit stop data: {response.status_code}")
            print(f"url: {url}")

    def fetch_events(self):
        """ Fetch lap events and flags"""
        if self.live:
            url = f"https://cf.nascar.com/cacher/live/series_{self.series_id}/{self.race_id}/lap-notes.json"
        else:
            url = f"https://cf.nascar.com/cacher/{self.year}/{self.series_id}/{self.race_id}/lap-notes.json"

        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
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
            self.events = pd.DataFrame(events) if events else pd.DataFrame()
            if not self.events.empty:
                self.events['Flag'] = self.events['Flag_State'].map(FLAG_CODE)

        else:
            print(f"Failed to retrieve lap events: {response.status_code}")
            print(f"url: {url}")

    def get_practice_results(self, run: dict) -> pd.DataFrame:
        results = run.get('results', [])
        practice_res = []
        for i in results:
            practice_res.append({
                'driver_id': i.get('driver_id'),
                'driver_name': i.get('driver_name'),
                'manufacturer': i.get('manufacturer'),
                'position': i.get('finishing_position'),
                'lap_time': i.get('best_lap_time'),
                'speed': i.get('best_lap_speed'),
                'total_laps': i.get('laps_completed'),
                'delta_to_leader': i.get('delta_leader')
            })

        practice_data = pd.DataFrame(practice_res) if practice_res else pd.DataFrame()
        practice_data['practice_number'] = run.get('practice_number', 1)
        practice_data = practice_data.sort_values(by='position') if not practice_data.empty else pd.DataFrame()
        return practice_data

    def get_qualifying_results(self, run:dict) -> pd.DataFrame:
        results = run.get('results', [])
        quali_res = []
        for i in results:
            quali_res.append({
                'driver_id': i.get('driver_id'),
                'driver_name': i.get('driver_name'),
                'manufacturer': i.get('manufacturer'),
                'position': i.get('finishing_position'),
                'lap_time': i.get('best_lap_time'),
                'speed': i.get('best_lap_speed'),
                'total_laps': i.get('laps_completed'),
                'delta_to_leader': i.get('delta_leader')
            })
        qualifying_data = pd.DataFrame(quali_res) if quali_res else pd.DataFrame()
        qualifying_data['qualifying_round'] = None
        qualifying_data = qualifying_data.sort_values(by='position') if not qualifying_data.empty else pd.DataFrame()
        return qualifying_data

    def get_practice(self, round: int) -> pd.DataFrame:
        """Return practice data for a specific round."""
        data = self.practice_data[self.practice_data['practice_number'] == round] if not self.practice_data.empty else pd.DataFrame()
        return data

    def get_qualifying(self, round: int) -> pd.DataFrame:
        """Return qualifying data for a specific round."""
        data = self.qualifying_data[self.qualifying_data['qualifying_round'] == round] if not self.qualifying_data.empty else pd.DataFrame()
        return data
    
    def get_driver_stats(self):
        #https://cf.nascar.com/loopstats/prod/2023/2/5314.json
        url = f"https://cf.nascar.com/loopstats/prod/{self.year}/{self.series_id}/{self.race_id}.json"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()

            # Data comes in array
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
            
            self.drivers = pd.DataFrame(driver_list) if driver_list else pd.DataFrame()
            self.drivers['driver_name'] = self.drivers['driver_id'].map(self.results.set_index('driver_id')['driver']) if not self.drivers.empty else None