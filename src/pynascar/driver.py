from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, List
import pandas as pd
import math
import time

from .caching import load_df, load_drivers_df, save_drivers_df
from .schedule import Schedule
from .race import Race

@dataclass
class Driver:
    """Streamlined driver class with clean, normalized data."""
    driver_id: int
    name: Optional[str] = None
    team: Optional[str] = None
    car_number: Optional[str] = None
    manufacturer: Optional[str] = None
    race_data: Dict[int, Dict] = field(default_factory=dict)  # race_id -> metrics
    pit_stops_df: pd.DataFrame = field(default_factory=pd.DataFrame)

    def add_race_data(self, race: Race, race_id: int) -> None:
        """Extract all driver data from a Race object."""
        race_metrics = {'race_id': race_id}

        # Basic results and driver info
        self._add_results_data(race, race_metrics)
        
        # Stage results  
        self._add_stage_data(race, race_metrics)
        
        # Driver performance stats
        self._add_driver_stats(race, race_metrics)
        
        # Lap analysis
        self._add_lap_analysis(race, race_metrics)
        
        # Pit stops
        self._add_pit_data(race, race_id, race_metrics)

        # Store with current driver info
        race_metrics.update({
            'driver_name': self.name,
            'team': self.team,
            'car_number': self.car_number,
            'manufacturer': self.manufacturer
        })
        self.race_data[race_id] = race_metrics

    def _add_results_data(self, race: Race, race_metrics: dict) -> None:
        """Add basic results data and update driver info."""
        res = race.results.results
        if res.empty or 'driver_id' not in res.columns:
            return

        driver_row = res[res['driver_id'] == self.driver_id]
        if driver_row.empty:
            return

        row = driver_row.iloc[0]
        
        # Update driver info from latest race data
        for attr, col in [('name', 'driver_name'), ('team', 'team'), 
                         ('car_number', 'car_number'), ('manufacturer', 'manufacturer')]:
            val = row.get(col)
            if pd.notna(val) and str(val).strip():
                setattr(self, attr, val)

        # Add race results (all already normalized in race.py)
        for col in ['finishing_position', 'starting_position', 'laps_completed', 
                   'points', 'playoff_points', 'qualifying_position', 'qualifying_speed']:
            race_metrics[col] = row.get(col)

    def _add_stage_data(self, race: Race, race_metrics: dict) -> None:
        """Add stage results (already have race_id and driver_id)."""
        for stage_num in [1, 2, 3]:
            stage_df = getattr(race.results, f'stage_{stage_num}', pd.DataFrame())
            if not stage_df.empty and 'driver_id' in stage_df.columns:
                stage_row = stage_df[stage_df['driver_id'] == self.driver_id]
                if not stage_row.empty:
                    s = stage_row.iloc[0]
                    race_metrics[f'stage{stage_num}_position'] = s.get('finishing_position', s.get('position'))
                    race_metrics[f'stage{stage_num}_points'] = s.get('points')

    def _add_driver_stats(self, race: Race, race_metrics: dict) -> None:
        """Add driver performance stats (already normalized)."""
        if not hasattr(race, 'driver_data'):
            return
            
        # Basic driver stats
        if hasattr(race.driver_data, 'drivers') and not race.driver_data.drivers.empty:
            stats_row = race.driver_data.drivers[race.driver_data.drivers['driver_id'] == self.driver_id]
            if not stats_row.empty:
                row = stats_row.iloc[0]
                for col in row.index:
                    if col not in ['driver_id', 'race_id', 'driver_name'] and pd.notna(row[col]):
                        race_metrics[col] = row[col]

        # Advanced stats
        adv_df = getattr(race.driver_data, 'driver_stats_advanced', pd.DataFrame())
        if not adv_df.empty and 'driver_id' in adv_df.columns:
            adv_row = adv_df[adv_df['driver_id'] == self.driver_id]
            if not adv_row.empty:
                row = adv_row.iloc[0]
                for col in row.index:
                    if col not in ['driver_id', 'race_id', 'driver_name'] and pd.notna(row[col]):
                        race_metrics[col] = row[col]

    def _add_lap_analysis(self, race: Race, race_metrics: dict) -> None:
        """Add lap-based metrics (already has driver_id mapping)."""
        laps_df = race.telemetry.lap_times.copy()
        if laps_df.empty or 'driver_id' not in laps_df.columns:
            return

        # Filter to this driver (driver_id already mapped in race.py)
        driver_laps = laps_df[laps_df['driver_id'] == self.driver_id]
        if driver_laps.empty:
            return

        # Calculate basic metrics
        race_metrics.update({
            "avg_lap_speed": driver_laps["lap_speed"].mean(),
            "fastest_lap": driver_laps["lap_speed"].max(),
            "total_laps": driver_laps["Lap"].max()
        })
        
        # Leader laps calculation
        laps_df["lap_speed_max"] = laps_df.groupby("Lap")["lap_speed"].transform("max")
        leader_laps = (driver_laps["lap_speed"] == laps_df.loc[driver_laps.index, "lap_speed_max"]).sum()
        race_metrics["leader_laps"] = int(leader_laps)
        
        # Average speed rank
        laps_df["speed_rank"] = laps_df.groupby("Lap")["lap_speed"].rank(ascending=False, method="min")
        race_metrics["avg_speed_rank"] = laps_df[laps_df["driver_id"] == self.driver_id]["speed_rank"].mean()

    def _add_pit_data(self, race: Race, race_id: int, race_metrics: dict) -> None:
        """Add pit stop data (already has driver_id and race_id)."""
        pit_df = race.telemetry.pit_stops
        if pit_df.empty or 'driver_id' not in pit_df.columns:
            return

        # Filter to this driver (driver_id already mapped in race.py)
        driver_pits = pit_df[pit_df["driver_id"] == self.driver_id].copy()
        if not driver_pits.empty:
            # Store pit stops (race_id already added in race.py)
            self.pit_stops_df = pd.concat([self.pit_stops_df, driver_pits], ignore_index=True)
            
            # Add race metrics
            race_metrics["total_pit_stops"] = len(driver_pits)
            
            # Find pit time column and calculate average
            pit_time_cols = ["pit_time", "Pit Time", "total_duration"]
            pit_time_col = next((c for c in pit_time_cols if c in driver_pits.columns), None)
            if pit_time_col:
                race_metrics["avg_pit_time"] = pd.to_numeric(driver_pits[pit_time_col], errors="coerce").mean()

    def compute_season_stats(self) -> pd.Series:
        """Compute season-level statistics."""
        if not self.race_data:
            return pd.Series(dtype="float64")

        df = pd.DataFrame(list(self.race_data.values()))
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        # Basic averages
        stats = df[numeric_cols].mean()
        
        # Special calculations
        stats['total_races'] = len(self.race_data)
        
        if 'points' in df.columns:
            stats['total_points'] = df['points'].sum()
        if 'playoff_points' in df.columns:
            stats['total_playoff_points'] = df['playoff_points'].sum()
        if 'finishing_position' in df.columns:
            stats['wins'] = (df['finishing_position'] == 1).sum()
            stats['top5s'] = (df['finishing_position'] <= 5).sum()
            stats['top10s'] = (df['finishing_position'] <= 10).sum()
        if 'leader_laps' in df.columns:
            stats['total_leader_laps'] = df['leader_laps'].sum()
        if 'passes_green_flag' in df.columns:
            stats['total_passes_green_flag'] = df['passes_green_flag'].sum()
        if 'passed_green_flag' in df.columns:
            stats['total_passed_green_flag'] = df['passed_green_flag'].sum()

        return stats

    def to_dict(self) -> Dict:
        """Convert to dictionary for DataFrame creation."""
        season_stats = self.compute_season_stats()

        return {
            'driver_id': self.driver_id,
            'driver_name': self.name,
            'team': self.team,
            'car_number': self.car_number,
            'manufacturer': self.manufacturer,
            **season_stats.to_dict()
        }


@dataclass
class DriversData:
    """Streamlined container for season driver data."""
    year: int
    series_id: int
    drivers: Dict[int, Driver] = field(default_factory=dict)
    race_ids: List[int] = field(default_factory=list)

    @classmethod
    def build(
        cls,
        year: int,
        series_id: int,
        use_cache_only: bool = True,
        sleep_seconds: int = 10,
        reload_cache: bool = False
    ) -> 'DriversData':
        """Build DriversData for a season."""
        instance = cls(year=year, series_id=series_id)

        # Get finished races
        schedule = Schedule(year, series_id)
        finished_races = schedule.get_finished_races()
        if finished_races is None or finished_races.empty:
            return instance

        race_id_col = 'race_id' if 'race_id' in finished_races.columns else 'id'
        race_ids = pd.to_numeric(finished_races[race_id_col], errors='coerce').dropna().astype(int).tolist()
        instance.race_ids = race_ids

        # Process each race
        for race_id in race_ids:
            try:
                # Check cache first
                results_cached = load_df("results", year=year, series_id=series_id, race_id=race_id)
                if (results_cached is None or results_cached.empty) and use_cache_only:
                    continue

                should_reload = reload_cache or (results_cached is None or results_cached.empty)
                race = Race(year, series_id, race_id, live=False, reload=should_reload)
                
                if should_reload and sleep_seconds > 0:
                    time.sleep(sleep_seconds)

                # Process drivers from results (driver_id already clean)
                res = race.results.results
                if res.empty or 'driver_id' not in res.columns:
                    continue

                driver_ids = pd.to_numeric(res['driver_id'], errors='coerce').dropna().astype(int).unique()
                
                for driver_id in driver_ids:
                    if driver_id not in instance.drivers:
                        instance.drivers[driver_id] = Driver(driver_id=driver_id)
                    instance.drivers[driver_id].add_race_data(race, race_id)

            except Exception as e:
                print(f"Error processing race {race_id}: {e}")
                continue

        return instance

    def to_dataframe(self, min_participation: float = 0.2) -> pd.DataFrame:
        """Convert to season summary DataFrame."""
        if not self.drivers:
            return pd.DataFrame()

        rows = [driver.to_dict() for driver in self.drivers.values()]
        df = pd.DataFrame(rows)

        # Apply minimum participation filter
        if min_participation > 0 and self.race_ids:
            min_races = max(1, math.ceil(min_participation * len(self.race_ids)))
            df = df[df['total_races'].fillna(0) >= min_races]

        return df

    def race_dataframe(self, race_id: int) -> pd.DataFrame:
        """Get DataFrame for a specific race."""
        rows = []
        for driver in self.drivers.values():
            race_data = driver.race_data.get(race_id)
            if race_data:
                rows.append({
                    'driver_id': driver.driver_id,
                    'driver_name': driver.name,
                    'team': driver.team,
                    'car_number': driver.car_number,
                    'manufacturer': driver.manufacturer,
                    **race_data
                })
        
        df = pd.DataFrame(rows)
        if df.empty:
            return df

        # Add normalized speed
        if 'avg_lap_speed' in df.columns and df['avg_lap_speed'].notna().any():
            max_speed, min_speed = df['avg_lap_speed'].max(), df['avg_lap_speed'].min()
            if max_speed != min_speed:
                df['norm_speed'] = (df['avg_lap_speed'] - min_speed) / (max_speed - min_speed)
            else:
                df['norm_speed'] = 1.0

        return df

    def all_races_dataframe(self) -> pd.DataFrame:
        """Get all races combined into single DataFrame."""
        if not self.race_ids:
            return pd.DataFrame()
            
        frames = [self.race_dataframe(race_id) for race_id in self.race_ids]
        frames = [f for f in frames if not f.empty]
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    def driver_season_dataframe(self, driver_id: int) -> pd.DataFrame:
        """Get all race data for a specific driver."""
        driver = self.drivers.get(driver_id)
        if not driver or not driver.race_data:
            return pd.DataFrame()

        rows = []
        for race_id, race_data in sorted(driver.race_data.items()):
            rows.append({
                'driver_id': driver_id,
                'driver_name': driver.name,
                'team': driver.team,
                'car_number': driver.car_number,
                'manufacturer': driver.manufacturer,
                **race_data
            })

        return pd.DataFrame(rows)

    def get_driver(self, driver_id: int) -> Optional[Driver]:
        """Get specific driver."""
        return self.drivers.get(driver_id)

    def driver_pit_stops(self, driver_id: int, race_id: Optional[int] = None) -> pd.DataFrame:
        """Get pit stops for a driver."""
        driver = self.drivers.get(driver_id)
        if not driver or driver.pit_stops_df.empty:
            return pd.DataFrame()
            
        df = driver.pit_stops_df.copy()
        if race_id is not None:
            df = df[df['race_id'] == race_id]
        return df