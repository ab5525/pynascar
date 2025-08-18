# src/pynascar/schedule.py
import warnings
import pandas as pd
import requests
from .caching import load_schedule, save_schedule

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
        cached_schedule = load_schedule(year=self.year, series_id=self.series_id)
        if cached_schedule is not None:
            self.data = cached_schedule
            self.races = self.data.to_dict(orient="records")
            return

        url = f"https://cf.nascar.com/cacher/{self.year}/race_list_basic.json"
        response = requests.get(url)
        if response.status_code == 200:
            print(f"Fetching data for Year:{self.year} Series:{self.series_id}")
            data = response.json()
            # Filter the races by series ID
            race_list = data[f'series_{self.series_id}']
            self.races = [race for race in race_list if race['series_id'] == self.series_id]
            self.data = pd.DataFrame(self.races)
            if "race_date" in self.data.columns:
                self.data["scheduled_at"] = pd.to_datetime(
                        self.data["race_date"], errors="coerce", utc=True
                    )
            save_schedule(self.data, year=self.year, series_id=self.series_id)
        else:
            warnings.warn(f"Failed to fetch race list: {response.status_code}")
    
    def completed_races(self):
        """Return a list of completed races."""
        return self.get_finished_races()['race_name'].tolist(),self.get_finished_races()['race_id'].tolist()

    def remaining_races(self):
        """Return a list of remaining races."""
        return self.get_remaining_races()['race_name'].tolist(),self.get_remaining_races()['race_id'].tolist()

    def most_recent_race(self) -> pd.DataFrame:
        """Return a DataFrame with a single row for the most recent completed race."""
        return self.get_finished_races().head(1)
    
    def next_race(self) -> pd.DataFrame:
        """Return a DataFrame with a single row for the next scheduled race."""
        return self.get_remaining_races().head(1)

    def get_finished_races(self) -> pd.DataFrame:
        """
        Return a DataFrame with all completed races.
        """
        df = self.data.copy()
        if df.empty:
            return df

        now = pd.Timestamp.now(tz="UTC")
        completed = df["winner_driver_id"].notna() if "winner_driver_id" in df.columns else (df["scheduled_at"] <= now)
        df = df[completed]
        if df.empty:
            return df
        return df.sort_values("scheduled_at", ascending=False)
    
    def get_remaining_races(self) -> pd.DataFrame:
        """
        Return a DataFrame with all remaining races.
        """
        df = self.data.copy()
        if df.empty:
            return df

        now = pd.Timestamp.now(tz="UTC")
        remaining = df["winner_driver_id"].isna() if "winner_driver_id" in df.columns else (df["scheduled_at"] >= now)
        df = df[remaining]
        if df.empty:
            return df
        return df.sort_values("scheduled_at", ascending=True)

    