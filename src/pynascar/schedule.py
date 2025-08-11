# src/pynascar/schedule.py
import warnings
import pandas as pd
import requests

# endpoint for race list
#https://cf.nascar.com/cacher/2023/race_list_basic.json

class Schedule:
    '''
    
    Class to handle fetching and storing race data for a specific year and series ID.
    Attributes:
        year (int): The year of the race season.
        series_id (int): The ID of the NASCAR series (1 for Cup Series, 2 for Xfinity, 3 for Truck Series).
        
    '''
    
    def __init__(self, year, series_id):
        self.year = year
        self.series_id = series_id
        self.races = []
        self.data = pd.DataFrame()
        self.fetch_races()     

    def fetch_races(self):
        """Fetch the race list for the specified year and series ID."""
        url = f"https://cf.nascar.com/cacher/{self.year}/race_list_basic.json"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            # Filter the races by series ID
            race_list = data[f'series_{self.series_id}']
            self.races = [race for race in race_list if race['series_id'] == self.series_id]
            self.data = pd.DataFrame(self.races)
        else:
            warnings.warn(f"Failed to fetch race list: {response.status_code}")
    
    def get_completed_races(self):
        """Return a list of completed races."""
        return self.data[self.data['winner_driver_id'].notna()]['race_name'].tolist()
    
    def get_remaining_races(self):
        """Return a list of remaining races."""
        return self.data[self.data['winner_driver_id'].isna()]['race_name'].tolist()
            

    