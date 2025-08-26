import pandas as pd
import requests
from dataclasses import dataclass 
from typing import Dict, List, Optional, Union,Any

@dataclass
class NASCARConfig:
    """ Basic config for API """
    base_url:str = "https://cf.nascar.com/cacher"
    live_url:str = "https://cf.nascar.com/cacher/live"
    loop_stats_url: str = "https://cf.nascar.com/loopstats/prod"
    default_timeout:int = 60
    retry_attempts:int = 2

class NascarAPI:
    """ 
    Client for NASCAR API data
    If new endpoints are discovered, they should be added here. 
    """
    def __init__(self, config: NASCARConfig = NASCARConfig()):
        self.config = config

    def _make_request(self,url:str) -> Optional[Dict[Any,Any]]:
        try:
            response = requests.get(url,timeout=self.config.default_timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to fetch data for {url}. Error: {e}")
            return None
    
    def get_race_data(self,year:int,series_id:int,race_id:int, live:bool = False) -> Optional[Dict]:
        """ Make Request for Race weekend data"""
        if live:
            url = f"{self.config.live_url}/series_{series_id}/{race_id}/weekend-feed.json"
        else:
            url = f"{self.config.base_url}/{year}/{series_id}/{race_id}/weekend-feed.json"
        return self._make_request(url)

    def get_lap_time_data(self,year:int,series_id:int,race_id:int, live:bool = False) -> Optional[Dict]:
        """ Make Request for Lap time data"""
        if live:
            url = f"{self.config.live_url}/series_{series_id}/{race_id}/lap-times.json"
        else:
            url = f"{self.config.base_url}/{year}/{series_id}/{race_id}/lap-times.json"
        return self._make_request(url)

    def get_pit_stop_data(self,year:int,series_id:int,race_id:int, live:bool = False) -> Optional[Dict]:
        """ Make Request for Pit stop data"""
        if live:
            url = f"{self.config.live_url}/series_{series_id}/{race_id}/live-pit-data.json"
        else:
            url = f"{self.config.base_url}/{year}/{series_id}/{race_id}/live-pit-data.json"
        return self._make_request(url)
    
    def get_event_notes_data(self,year:int,series_id:int,race_id:int, live:bool = False) -> Optional[Dict]:
        """ Make Request for Event notes data"""
        if live:
            url = f"{self.config.live_url}/series_{series_id}/{race_id}/lap-notes.json"
        else:
            url = f"{self.config.base_url}/{year}/{series_id}/{race_id}/lap-notes.json"
        return self._make_request(url)

    def get_driver_stat_data(self,year:int,series_id:int,race_id:int) -> Optional[Dict]:
        """ Make Request for Driver statistics data"""
        url = f"{self.config.loop_stats_url}/{year}/{series_id}/{race_id}.json"
        return self._make_request(url)

    def get_advanced_driver_stat_data(self,year:int,series_id:int,race_id:int) -> Optional[Dict]:
        """ Make Request for Driver statistics data"""
        url = f"{self.config.live_url}/series_{series_id}/{race_id}/live-feed.json"
        return self._make_request(url)
    
    def get_schedule(self,year:int):
        """Make requests for race schedule data"""
        url = f"{self.config.base_url}/{year}/race_list_basic.json"
        return self._make_request(url)