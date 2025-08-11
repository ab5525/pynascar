# src/race.py

import pandas as pd
import requests
import warnings
from .codes import FLAG_CODE

#https://cf.nascar.com/cacher/2023/2/5314/lap-times.json
#

class Race:
    def __init__(self, year, series_id,race_id=None,live=False):
        # Initialize race metadata
        self.year = year
        self.live = live
        self.series_id = series_id
        self.race_id = race_id

        # Race Data
        self.name = None
        self.laps = None
        self.pit_stops = None
        self.events = None
        self.start_time = None
        self.end_time = None
        self.winner = None
        self.data = {}
        self.fetch_laps()
        self.get_pit_stops()
        self.fetch_events()
        
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