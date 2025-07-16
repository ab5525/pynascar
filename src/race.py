# src/race.py

import pandas as pd
import requests
import warnings

#https://cf.nascar.com/cacher/2023/2/5314/lap-times.json
#

class Race:
    def __init__(self, year, series_id,race_id=None):
        self.year = year
        self.series_id = series_id
        self.race_id = race_id
        self.name = None
        self.laps = None
        self.winner = None
        self.data = pd.DataFrame()
        self.laps = pd.DataFrame()
        self.test = None
        
    def fetch_laps(self):
        """Fetch lap times for the specified race ID."""
        url = f"https://cf.nascar.com/cacher/{self.year}/{self.series_id}/{self.race_id}/lap-times.json"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            self.data = data
            lap_times = []
            
            for i in data['laps']:
                driver = i['FullName']
                number = i['Number']
                manufacturer = i['Manufacturer']
                for j in i['Laps']:
                    lap_times = lap_times
                    lap_times.append({
                        'Driver': driver,
                        'Number': number,
                        'Manufacturer': manufacturer,
                        'Lap': j['Lap'],
                        'lap_time': j['LapTime'],
                        'lap_speed': j['LapSpeed'],
                        'position': j['RunningPos'],
                    })
            self.laps = pd.DataFrame(lap_times)
            self.laps['Lap'] = self.laps['Lap'].astype(int)
            self.laps['lap_time'] = pd.to_timedelta(self.laps['lap_time'])
            self.laps['lap_speed'] = self.laps['lap_speed'].astype(float)