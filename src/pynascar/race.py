# src/race.py

import pandas as pd
import requests
import warnings
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from .codes import FLAG_CODE
from .caching import load_df, save_df
from .core.base_api import NascarAPI
from .core.process_data import NASCARDataProcessor


@dataclass
class RaceMetadata:
    """Race metadata container."""
    race_id: int
    year: int
    series_id: int
    name: Optional[str] = None
    distance: Optional[float] = None
    scheduled_laps: Optional[int] = None
    stage_1_laps: Optional[int] = None
    stage_2_laps: Optional[int] = None
    stage_3_laps: Optional[int] = None
    track_name: Optional[str] = None
    race_time: Optional[str] = None
    entrant_num: Optional[int] = None
    restrictor_plate: Optional[bool] = None
    winner: Optional[str] = None

@dataclass 
class RaceResults:
    """Container for race results data."""
    results: pd.DataFrame = field(default_factory=pd.DataFrame)
    stage_1: pd.DataFrame = field(default_factory=pd.DataFrame)
    stage_2: pd.DataFrame = field(default_factory=pd.DataFrame)
    stage_3: pd.DataFrame = field(default_factory=pd.DataFrame)
    cautions: pd.DataFrame = field(default_factory=pd.DataFrame)
    lead_changes: pd.DataFrame = field(default_factory=pd.DataFrame)
    practice: pd.DataFrame = field(default_factory=pd.DataFrame)
    qualifying: pd.DataFrame = field(default_factory=pd.DataFrame)

@dataclass
class RaceTelemetry:
    """Container for race telemetry data."""
    lap_times: pd.DataFrame = field(default_factory=pd.DataFrame)
    pit_stops: pd.DataFrame = field(default_factory=pd.DataFrame)
    events: pd.DataFrame = field(default_factory=pd.DataFrame)

class RaceDriverData:
    """Container for race telemetry data."""
    drivers: pd.DataFrame = field(default_factory=pd.DataFrame)
    driver_stats_advanced: pd.DataFrame = field(default_factory=pd.DataFrame)



class Race:
    def __init__(self, year, series_id,race_id=None,live=False,reload = False,api_client = None):
        self.metadata = RaceMetadata(race_id=race_id, year=year, series_id=series_id)
        self.api = api_client or NascarAPI()
        self.data_processor = NASCARDataProcessor()
        self.results = RaceResults()
        self.telemetry = RaceTelemetry()
        self.driver_data = RaceDriverData()
        self.reload = reload
        self.live = live

        # Initialize the race data
        self._load_race_data()

    def _load_race_data(self) -> None:
        self._load_results()
        self._load_telemetry()
        self._load_drivers()

    def _load_results(self):
        if (not self.live) and (not self.reload):
            print(f"Reading from Cache for {self.metadata.year}-{self.metadata.series_id}-{self.metadata.race_id}")

            cached_results = load_df("results", year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)
            cached_cautions = load_df("cautions", year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)
            cached_lead_changes = load_df("lead_changes", year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)
            cached_stage1 = load_df("stage_1_results", year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)
            cached_stage2 = load_df("stage_2_results", year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)
            cached_stage3 = load_df("stage_3_results", year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)

            if cached_results is not None:
                self.results.results = cached_results
                self.results.stage_1 = cached_stage1 if cached_stage1 is not None else pd.DataFrame()
                self.results.stage_2 = cached_stage2 if cached_stage2 is not None else pd.DataFrame()
                self.results.stage_3 = cached_stage3 if cached_stage3 is not None else pd.DataFrame()
                self.results.cautions = cached_cautions if cached_cautions is not None else pd.DataFrame()
                self.results.lead_changes = cached_lead_changes if cached_lead_changes is not None else pd.DataFrame()
                self.metadata.winner = self.results.results[self.results.results['finishing_position'] == 1]['driver'].values[0] if not self.results.results.empty else None
        
        print(f"Fetching Data for {self.metadata.year}-{self.metadata.series_id}-{self.metadata.race_id}")
        race_data = self.api.get_race_data(year = self.metadata.year, series_id = self.metadata.series_id,
                                           race_id=self.metadata.race_id, live=self.live)
        if not race_data:
            print(f"Failed to fetch race data for: {self.metadata.year}-{self.metadata.series_id}-{self.metadata.race_id}")
            return
        
        weekend_race = race_data.get('weekend_race', [])
        if weekend_race:
            race = weekend_race[0]
            self._update_metadata(race)
            self._process_race_results(race)
        weekend_runs = race_data.get('weekend_runs', [])
        if weekend_runs:
            self._process_weekend_run_results(weekend_runs)
        
    
    def _update_metadata(self, weekend_data: Dict) -> None:
        self.metadata.name = weekend_data.get('race_name')
        self.metadata.distance = weekend_data.get('scheduled_distance')
        self.metadata.scheduled_laps = weekend_data.get('scheduled_laps')
        self.metadata.race_time = weekend_data.get('total_race_time')
        self.metadata.stage_1_laps = weekend_data.get('stage_1_laps')
        self.metadata.stage_2_laps = weekend_data.get('stage_2_laps')
        self.metadata.stage_3_laps = weekend_data.get('stage_3_laps')
        self.metadata.entrant_num = weekend_data.get('number_of_cars_in_field')
        self.metadata.restrictor_plate = weekend_data.get('restrictor_plate')

    def _process_race_results(self,race_data:Dict) -> None:
        self.results.results = self.data_processor.process_race_data(race_data)
        self.results.cautions = self.data_processor.process_caution_data(race_data)
        self.results.lead_changes = self.data_processor.process_leader_data(race_data)
        self.results.lead_changes['driver_name'] = self.results.lead_changes['car_number'].map(self.results.results.set_index('driver_number')['driver']) if not self.results.lead_changes.empty else None
        self.metadata.winner = self.results.results[self.results.results['finishing_position'] == 1]['driver'].values[0] if not self.results.results.empty else None

        stages_data = race_data.get('stage_results', [])
        for stage_data in stages_data:
            stage_num = stage_data.get('stage_number')
            if stage_num in [1, 2, 3]:
                stage_df = self.data_processor.process_stage_data(stage_data, stage_num)
                setattr(self.results, f"stage_{stage_num}", stage_df)

        if not self.live:
            save_df("results", self.results.results, year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)
            save_df("cautions", self.results.cautions, year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)
            save_df("lead_changes", self.results.lead_changes, year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)
            save_df('stage_1_results', self.results.stage_1, year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)
            save_df('stage_2_results', self.results.stage_2, year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)
            # if self.results.stage_3 is not None:
            #     save_df('stage_3_results', self.results.stage_3, year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)

    def _process_weekend_run_results(self, run_data: Dict) -> None:
        practice, qualifying = self.data_processor.process_practice_qualifying_data(run_data)
        self.results.qualifying = qualifying
        self.results.practice = practice
        if not self.live:
            if not self.results.practice.empty:
                save_df("practice",  self.results.practice, year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)
            if not self.results.qualifying.empty:
                save_df("qualifying", self.results.qualifying, year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)

    def _load_telemetry(self):
        if (not self.live) and (not self.reload):
            cached_laps = load_df("laps", year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)
            self.telemetry.lap_times = cached_laps if cached_laps is not None else pd.DataFrame()
        else:
            self._fetch_lap_times()

        if (not self.live) and (not self.reload):
            cached_pit_stops = load_df("pit_stops", year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)
            self.telemetry.pit_stops = cached_pit_stops if cached_pit_stops is not None else pd.DataFrame()
        else:
            self._fetch_pit_stops()
        
        if (not self.live) and (not self.reload):
            cached_events = load_df("events", year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)
            self.telemetry.events = cached_events if cached_events is not None else pd.DataFrame()
        else:
            self._fetch_event_notes()

    def _fetch_lap_times(self):
        """Fetch lap times for the specified race ID."""
        lap_data = self.api.get_lap_time_data(year=self.metadata.year, series_id=self.metadata.series_id,
                                              race_id=self.metadata.race_id, live=self.live)
        if lap_data:
            self.telemetry.lap_times = self.data_processor.process_laps_data(lap_data)

        if not self.live:
            save_df("laps", self.telemetry.lap_times, year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)
    
    def _fetch_pit_stops(self):
        pit_data = self.api.get_pit_stop_data(
            self.metadata.year,
            self.metadata.series_id,
            self.metadata.race_id,
            self.live
        )
        if pit_data:
            self.telemetry.pit_stops = self.data_processor.process_pit_stops(pit_data)

        if not self.live:
            save_df("pit_stops", self.telemetry.pit_stops, year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)

    def _fetch_event_notes(self):
        """ Fetch lap events and flags"""
        event_data = self.api.get_event_notes_data(
            self.metadata.year,
            self.metadata.series_id,
            self.metadata.race_id,
            self.live
        )
        if event_data:
            self.telemetry.events = self.data_processor.process_event_notes_data(event_data)

        if not self.live:
            save_df("events", self.telemetry.events, year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)

    def _load_drivers(self):
        if (not self.live) and (not self.reload):
            cached_driver_stats = load_df("driver_stats", year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)
            self.driver_data.drivers = cached_driver_stats if cached_driver_stats is not None else pd.DataFrame()
        else:
            self._fetch_driver_stats()

        if (not self.live) and (not self.reload):
            cached_driver_stats_advanced = load_df("driver_stats_advanced", year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)
            self.driver_data.driver_stats_advanced = cached_driver_stats_advanced if cached_driver_stats_advanced is not None else pd.DataFrame()
        else:
            self._fetch_adv_driver_stats()

    def _fetch_driver_stats(self):
        driver_stats_data = self.api.get_driver_stat_data(
            self.metadata.year,
            self.metadata.series_id,
            self.metadata.race_id,
        )
        
        self.driver_data.drivers = self.data_processor.process_driver_data(driver_stats_data)

        if not self.driver_data.drivers.empty:
            name_map_df = (
                    self.results.results[['driver_id', 'driver']]
                    .dropna(subset=['driver_id', 'driver'])
                    .astype({'driver_id': 'Int64'})
                    .drop_duplicates(subset=['driver_id'], keep='first')
                )
            name_map = name_map_df.set_index('driver_id')['driver']
            self.driver_data.drivers['driver_name'] = self.driver_data.drivers['driver_id'].astype('Int64').map(name_map)
        if not self.live:
                save_df("driver_stats", self.driver_data.drivers, year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)
    
    def _fetch_adv_driver_stats(self):
        adv_driver_stats_data = self.api.get_advanced_driver_stat_data(
            self.metadata.year,
            self.metadata.series_id,
            self.metadata.race_id,
        )
        self.driver_data.driver_stats_advanced = self.data_processor.process_adv_driver_data(adv_driver_stats_data)
        if not self.live:
            save_df("driver_stats_advanced", self.driver_data.driver_stats_advanced, year=self.metadata.year, series_id=self.metadata.series_id, race_id=self.metadata.race_id)