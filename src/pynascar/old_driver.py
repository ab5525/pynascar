from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional, List
import unicodedata
import pandas as pd
import re
import math
import time
import numpy as np

from .caching import load_df, load_schedule, load_drivers_df, save_drivers_df
from .codes import NAME_MAPPINGS
from .schedule import Schedule
from .race import Race

def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def normalize_driver_name(name: Optional[str]) -> Optional[str]:
    if name is None or pd.isna(name):
        return None
    s = _strip_accents(str(name))
    # Remove symbols: *, #, (i)
    s = s.replace("#", "").replace("*", "")
    s = re.sub(r"\(\s*i\s*\)", "", s, flags=re.IGNORECASE)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    # Apply known mappings
    s = NAME_MAPPINGS.get(s, s)
    return s

@dataclass
class Driver:
    """Simplified driver class that works with new Race structure."""
    driver_id: int
    name: Optional[str] = None
    team: Optional[str] = None
    car_number: Optional[str] = None
    manufacturer: Optional[str] = None
    race_data: Dict[int, Dict] = field(default_factory=dict)  # race_id -> race metrics
    season_stats: pd.Series = field(default_factory=lambda: pd.Series(dtype="float64"))
    pit_stops_df: pd.DataFrame = field(default_factory=lambda: pd.DataFrame())

    def add_race_data(self, race: Race, race_id: int) -> None:
        """Extract and store all driver data from a Race object."""
        
        if not hasattr(race, 'driver_data') or not hasattr(race.driver_data, 'drivers'):
            print(f"DEBUG: No driver_data available for race {race_id}")

        # Get basic driver info from results
        if not race.results.results.empty:
            driver_row = race.results.results[race.results.results['driver_id'] == self.driver_id]
            if not driver_row.empty:
                row = driver_row.iloc[0]
                # new_name = normalize_driver_name(row.get('driver_name')) if 'driver_name' in row.index else None
                # if new_name:
                #     self.name = new_name
                #     print("there was a new name:", new_name)
                self.name = self.name
                self.team = self.team or row.get('team')
                self.car_number = self.car_number or str(row.get('driver_number', ''))
                self.manufacturer = self.manufacturer or row.get('manufacturer')


        # Collect all race metrics
        race_metrics = {
            'race_id': race_id,
            'driver_name': self.name,
            'team': self.team,
            'car_number': self.car_number,
            'manufacturer': self.manufacturer
        }

        # Get basic driver info from results (robust id matching)
        res = getattr(race.results, 'results', pd.DataFrame())
        if isinstance(res, pd.DataFrame) and not res.empty and 'driver_id' in res.columns:
            res = res.copy()
            res['_driver_id_num'] = pd.to_numeric(res['driver_id'], errors='coerce')
            this_id = pd.to_numeric(pd.Series([self.driver_id]), errors='coerce').iloc[0]
            driver_row = res[res['_driver_id_num'] == this_id]

            if not driver_row.empty:
                row = driver_row.iloc[0]
                new_name = normalize_driver_name(row.get('driver_name')) if 'driver_name' in row.index else None
                if new_name:
                    self.name = new_name
                    race_metrics['driver_name'] = new_name

                team_val = row.get('team')
                if pd.notna(team_val) and str(team_val).strip():
                    self.team = team_val
                    race_metrics['team'] = team_val

                num_val = row.get('driver_number', row.get('car_number'))
                if pd.notna(num_val) and str(num_val).strip():
                    self.car_number = str(num_val)
                    race_metrics['car_number'] = str(num_val)

                man_val = row.get('manufacturer')
                if pd.notna(man_val) and str(man_val).strip():
                    self.manufacturer = man_val
                    race_metrics['manufacturer'] = man_val

                race_metrics.update({
                    'finishing_position': row.get('finishing_position'),
                    'starting_position': row.get('starting_position'),
                    'laps_completed': row.get('laps_completed'),
                    'points': row.get('points'),
                    'playoff_points': row.get('playoff_points'),
                    'qualifying_position': row.get('qualifying_position'),
                    'qualifying_speed': row.get('qualifying_speed'),
                    'closing_position': row.get('closing_position'),
                    'leader_laps': row.get('leader_laps') if 'leader_laps' in row.index else row.get('lead_laps')
                })

        # Stage results
        for stage_num in [1, 2, 3]:
            stage_df = getattr(race.results, f'stage_{stage_num}', pd.DataFrame())
            if isinstance(stage_df, pd.DataFrame) and not stage_df.empty:
                stage_row = stage_df[stage_df['driver_id'] == self.driver_id]
                if not stage_row.empty:
                    s = stage_row.iloc[0]
                    race_metrics[f'stage{stage_num}_position'] = (
                        s.get('finishing_position', s.get('position', s.get('pos')))
                    )
                    race_metrics[f'stage{stage_num}_points'] = s.get('points')

        # Driver stats
        if hasattr(race, 'driver_data') and isinstance(race.driver_data.drivers, pd.DataFrame) and not race.driver_data.drivers.empty:
            stats_row = race.driver_data.drivers[race.driver_data.drivers['driver_id'] == self.driver_id]
            if not stats_row.empty:
                row = stats_row.iloc[0]
                for col in [
                    'mid_position', 'closing_position', 'closing_laps_diff', 'best_position',
                    'worst_position', 'avg_position', 'fast_laps', 'top15_laps',
                    'passes_green_flag', 'quality_passes', 'lead_laps', 'rating', 'passed_green_flag'
                ]:
                    if col in row.index:
                        race_metrics[col] = row[col]

        # Advanced driver stats
        adv_df = getattr(race.driver_data, 'driver_stats_advanced', pd.DataFrame())
        if isinstance(adv_df, pd.DataFrame) and not adv_df.empty:
            adv_row = adv_df[adv_df['driver_id'] == self.driver_id]
            if not adv_row.empty:
                row = adv_row.iloc[0]
                for col in row.index:
                    if col != 'driver_id':
                        race_metrics[col] = row[col]
            else:
                print(f"DEBUG: Driver {self.driver_id} not found in advanced driver stats")
        else:
            print(f"DEBUG: Advanced driver stats DataFrame is empty")

        # Lap times analysis
        laps_df = getattr(race.telemetry, 'lap_times', pd.DataFrame())
        if isinstance(laps_df, pd.DataFrame) and not laps_df.empty and not race.results.results.empty:
            map_num_to_id = (
                race.results.results[["driver_number", "driver_id"]]
                .dropna()
                .assign(driver_number=race.results.results["driver_number"].astype(str))
                .drop_duplicates(subset=["driver_number"], keep="first")
                .set_index("driver_number")["driver_id"]
            )
            working_df = laps_df.copy()
            if {"Number", "lap_speed", "Lap"}.issubset(working_df.columns):
                working_df["driver_number"] = working_df["Number"].astype(str)
                working_df["driver_id"] = working_df["driver_number"].map(map_num_to_id)
                working_df["lap_speed"] = pd.to_numeric(working_df["lap_speed"], errors="coerce")
                dlaps = working_df[working_df["driver_id"] == self.driver_id]
                if not dlaps.empty:
                    race_metrics["avg_lap_speed"] = dlaps["lap_speed"].mean()
                    race_metrics["fastest_lap"] = dlaps["lap_speed"].max()
                    race_metrics["total_laps"] = pd.to_numeric(dlaps["Lap"], errors="coerce").max()

        # Pit stops analysis
        # Pit stops analysis: map to driver_id using results, then compute metrics
        pits_df = getattr(race.telemetry, 'pit_stops', pd.DataFrame())
        res = getattr(race.results, 'results', pd.DataFrame())
        self.add_pit_stops(pits_df, res, race_id)
        if not self.pit_stops_df.empty:
            d = self.pit_stops_df[self.pit_stops_df["race_id"] == race_id]
            if not d.empty:
                race_metrics["total_pit_stops"] = len(d)
                # common column for pit time (adjust if your schema differs)
                pit_time_col = "pit_time" if "pit_time" in d.columns else ("Pit Time" if "Pit Time" in d.columns else None)
                if pit_time_col:
                    race_metrics["avg_pit_time"] = pd.to_numeric(d[pit_time_col], errors="coerce").mean()

        self.race_data[race_id] = race_metrics
    
    def add_pit_stops(self, pit: pd.DataFrame, res: pd.DataFrame, race_id: int) -> None:
        """Map pit stops to driver_id using results and append to self.pit_stops_df."""
        if not isinstance(pit, pd.DataFrame) or pit.empty:
            return
        if not isinstance(res, pd.DataFrame) or res.empty:
            return

        # Accept either 'driver' or 'driver_name' from results
        driver_col = 'driver' if 'driver' in res.columns else ('driver_name' if 'driver_name' in res.columns else None)
        if "Driver" not in pit.columns or driver_col is None or "driver_id" not in res.columns:
            return

        # Build name map from results, stripping symbols for matching
        def _clean_name(name):
            if pd.isna(name):
                return None
            cleaned = str(name).strip()
            cleaned = re.sub(r'^[*#†‡§¶\s]+', '', cleaned)
            cleaned = re.sub(r'[*#†‡§¶\s]+$', '', cleaned)
            cleaned = re.sub(r'\s*\([^)]*\)\s*$', '', cleaned)
            return cleaned.strip()

        # Known variant mappings
        name_mappings = {
            "Daniel Suárez": "Daniel Suarez",
            "John H. Nemechek": "John Hunter Nemechek",
            "Ricky Stenhouse Jr": "Ricky Stenhouse Jr.",
        }

        def _normalize_name(name):
            cleaned = _clean_name(name)
            if cleaned in name_mappings:
                return name_mappings[cleaned]
            return cleaned

        # Create clean name maps from results (include number/manufacturer when present)
        res_cols = [driver_col, "driver_id"]
        if "driver_number" in res.columns:
            res_cols.append("driver_number")
        if "manufacturer" in res.columns:
            res_cols.append("manufacturer")
        res_clean = res[res_cols].dropna(subset=[driver_col, "driver_id"]).copy()
        res_clean["clean_name"] = res_clean[driver_col].apply(_normalize_name)

        name_to_id = res_clean.drop_duplicates("clean_name").set_index("clean_name")["driver_id"]
        name_to_num = res_clean.drop_duplicates("clean_name").set_index("clean_name")["driver_number"] if "driver_number" in res_clean.columns else None
        name_to_man = res_clean.drop_duplicates("clean_name").set_index("clean_name")["manufacturer"] if "manufacturer" in res_clean.columns else None

        # Map pit stops to driver_id + enrich with car_number/manufacturer
        working_df = pit.copy()
        working_df["clean_driver"] = working_df["Driver"].apply(_normalize_name)
        working_df["driver_id"] = working_df["clean_driver"].map(name_to_id)

        # car_number: prefer mapping from results
        if name_to_num is not None:
            working_df["car_number"] = working_df["clean_driver"].map(name_to_num).astype("string")
        # manufacturer: prefer pit's Manufacturer, else fallback to results
        if "Manufacturer" in working_df.columns:
            working_df["manufacturer"] = working_df["Manufacturer"]
        elif name_to_man is not None:
            working_df["manufacturer"] = working_df["clean_driver"].map(name_to_man)

        # Drop duplicate pit rows if any
        working_df = working_df.drop_duplicates()

        res_df = working_df[working_df["driver_id"] == self.driver_id].copy()
        if res_df.empty:
            return

        res_df["race_id"] = race_id
        # Ensure consistent types
        if "car_number" in res_df.columns:
            res_df["car_number"] = res_df["car_number"].astype("string")

        self.pit_stops_df = (
            pd.concat([self.pit_stops_df, res_df], ignore_index=True)
            if not self.pit_stops_df.empty else res_df
        )
        # Final de-dup across races too
        self.pit_stops_df = self.pit_stops_df.drop_duplicates()

    def compute_season_stats(self) -> None:
        """Compute season-level statistics from race data."""
        if not self.race_data:
            return

        df = pd.DataFrame(list(self.race_data.values()))
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        # Basic averages
        self.season_stats = df[numeric_cols].mean()
        
        # Special calculations
        self.season_stats['total_races'] = len(self.race_data)
        self.season_stats['total_points'] = df['points'].sum() if 'points' in df else 0
        self.season_stats['total_playoff_points'] = df['playoff_points'].sum() if 'playoff_points' in df else 0
        self.season_stats['wins'] = (df['finishing_position'] == 1).sum() if 'finishing_position' in df else 0
        self.season_stats['top5s'] = (df['finishing_position'] <= 5).sum() if 'finishing_position' in df else 0
        self.season_stats['top10s'] = (df['finishing_position'] <= 10).sum() if 'finishing_position' in df else 0

    def get_race_summary(self, race_id: int) -> Optional[Dict]:
        """Get summary for a specific race."""
        return self.race_data.get(race_id)

    def to_dict(self) -> Dict:
        """Convert driver to dictionary for DataFrame creation."""
        # Fallback name/team from accumulated race_data if self.* are None
        if self.name is None or self.team is None:
            if self.race_data:
                rd = pd.DataFrame(self.race_data.values())
                if self.name is None and 'driver_name' in rd.columns:
                    nn = rd['driver_name'].dropna()
                    if not nn.empty:
                        self.name = normalize_driver_name(nn.iloc[0])
                if self.team is None and 'team' in rd.columns:
                    tt = rd['team'].dropna()
                    if not tt.empty:
                        self.team = tt.mode().iloc[0]

        # Provide commonly used season aggregates (non-prefixed for plotting)
        avg_lap_speed = np.nan
        if self.race_data:
            rd = pd.DataFrame(self.race_data.values())
            if 'avg_lap_speed' in rd.columns and rd['avg_lap_speed'].notna().any():
                avg_lap_speed = float(rd['avg_lap_speed'].mean())

        return {
            'driver_id': self.driver_id,
            'driver_name': self.name,
            'team': self.team,
            'car_number': self.car_number,
            'manufacturer': self.manufacturer,
            'avg_lap_speed': avg_lap_speed,
            **{f"season_{k}": v for k, v in self.season_stats.items()}
        }


@dataclass
class DriversData:
    """Simplified container for season driver data."""
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
        """Build DriversData for a season using new Race structure."""
        instance = cls(year=year, series_id=series_id)

        # Get schedule and finished races
        schedule = Schedule(year, series_id)
        finished_races = schedule.get_finished_races()
        if finished_races is None or finished_races.empty:
            print(f"DEBUG: No finished races found for {year}-{series_id}")
            return instance

        race_id_col = 'race_id' if 'race_id' in finished_races.columns else ('id' if 'id' in finished_races.columns else None)
        if race_id_col is None:
            print(f"DEBUG: Finished races missing race_id column. Columns: {list(finished_races.columns)}")
            return instance

        race_ids = pd.to_numeric(finished_races[race_id_col], errors='coerce').dropna().astype(int).tolist()
        instance.race_ids = race_ids
        print(f"DEBUG: Found {len(race_ids)} finished races")

        for race_id in race_ids:
            try:
                # If cache-only, ensure results exist in cache then run
                results_cached = load_df("results", year=year, series_id=series_id, race_id=race_id)
                if (results_cached is None or results_cached.empty) and use_cache_only:
                    print(f"DEBUG: Skipping race {race_id} (cache only, no cached results)")
                    continue

                reload = reload_cache or (results_cached is None or results_cached.empty)
                if reload:
                    print(f"DEBUG: Fetching race {race_id} (reload={reload})")
                else:
                    print(f"DEBUG: Loading race {race_id} from cache")

                race = Race(year, series_id, race_id, live=False, reload=reload)
                if reload and sleep_seconds > 0:
                    time.sleep(sleep_seconds)

                # Extract driver IDs from results
                res = getattr(race.results, 'results', pd.DataFrame())
                if not isinstance(res, pd.DataFrame) or res.empty or 'driver_id' not in res.columns:
                    print(f"DEBUG: Race {race_id} results empty or missing driver_id")
                    continue

                driver_ids = pd.to_numeric(res['driver_id'], errors='coerce').dropna().astype(int).unique()
                # Pre-fill minimal identity info to name/team where possible
                for driver_id in driver_ids:
                    if driver_id not in instance.drivers:
                        instance.drivers[driver_id] = Driver(driver_id=driver_id)
                    instance.drivers[driver_id].add_race_data(race, race_id)

            except Exception as e:
                print(f"Error processing race {race_id}: {e}")
                continue

        # Compute season statistics for all drivers
        for driver in instance.drivers.values():
            driver.compute_season_stats()

        return instance

    def to_dataframe(self, min_participation: float = 0.2) -> pd.DataFrame:
        """Convert to DataFrame with season statistics."""
        if not self.drivers:
            return pd.DataFrame()

        rows = [driver.to_dict() for driver in self.drivers.values()]
        df = pd.DataFrame(rows)

        # Normalize names; then backfill any remaining null identity per driver_id
        if 'driver_name' in df.columns:
            df['driver_name'] = df['driver_name'].apply(normalize_driver_name)
            df['driver_name'] = df.groupby('driver_id')['driver_name'].transform(
                lambda s: s.dropna().iloc[0] if s.notna().any() else np.nan
            )
        if 'team' in df.columns:
            df['team'] = df.groupby('driver_id')['team'].transform(
                lambda s: s.dropna().iloc[0] if s.notna().any() else np.nan
            )

        # Rank by average lap speed across season (for plotting)
        if 'avg_lap_speed' in df.columns and df['avg_lap_speed'].notna().any():
            df['avg_speed_rank'] = df['avg_lap_speed'].rank(ascending=False, method='min')

        # Apply minimum participation filter
        if min_participation > 0 and self.race_ids:
            min_races = max(1, math.ceil(min_participation * len(self.race_ids)))
            df = df[df['season_total_races'].fillna(0) >= min_races]

        return df

    def get_driver(self, driver_id: int) -> Optional[Driver]:
        """Get specific driver."""
        return self.drivers.get(driver_id)

    def race_dataframe(self, race_id: int) -> pd.DataFrame:
        """Get DataFrame for a specific race."""
        rows = []
        for driver in self.drivers.values():
            race_data = driver.get_race_summary(race_id)
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
        
        if 'driver_name' in df.columns:
            df['driver_name'] = df['driver_name'].apply(normalize_driver_name)

        # Compatibility/derivatives
        if 'lead_laps' in df.columns and 'leader_laps' not in df.columns:
            df['leader_laps'] = df['lead_laps']

        if 'avg_lap_speed' in df.columns:
            df['avg_speed_rank'] = df['avg_lap_speed'].rank(ascending=False, method='min')
            max_s, min_s = df['avg_lap_speed'].max(), df['avg_lap_speed'].min()
            df['norm_speed'] = 1.0 if max_s == min_s else (df['avg_lap_speed'] - min_s) / (max_s - min_s)

        return df

    def driver_season_dataframe(self, driver_id: int) -> pd.DataFrame:
        """Get all race data for a specific driver."""
        
        driver = self.drivers.get(driver_id)
        if not driver or not driver.race_data:
            print("no data")
            return pd.DataFrame()

        rows = []
        for race_id, race_data in driver.race_data.items():
            row = {
                'driver_id': driver_id,
                'driver_name': driver.name,
                'team': driver.team,
                'car_number': driver.car_number,
                'manufacturer': driver.manufacturer,
                **race_data
            }
            rows.append(row)

        return pd.DataFrame(rows).sort_values('race_id').reset_index(drop=True)
    
    def all_races_dataframe(self) -> pd.DataFrame:
        """Combine all races for all drivers into a single DataFrame."""
        if not self.race_ids:
            return pd.DataFrame()
        frames = [self.race_dataframe(r) for r in self.race_ids]
        frames = [f for f in frames if f is not None and not f.empty]
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)