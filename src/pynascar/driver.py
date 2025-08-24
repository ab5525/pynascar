# Largely placeholder file
# Created with some initial structure. Plans to refactor and simplify
# I prefer the use of initializers generally
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
import time
import pandas as pd
import math

from .caching import load_df, load_schedule, load_drivers_df, save_drivers_df
from .schedule import Schedule
from .race import Race

def _nanmean(values):
    s = pd.to_numeric(values, errors="coerce").dropna()
    return float(s.mean()) if not s.empty else None

def _nansum(values):
    s = pd.to_numeric(values, errors="coerce").dropna()
    return float(s.sum()) if not s.empty else None

def _nanmedian(values):
    s = pd.to_numeric(values, errors="coerce").dropna()
    return float(s.median()) if not s.empty else None

def _drop_avg_columns(df: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(df, pd.DataFrame) or df.empty:
        return df
    drop_cols = [c for c in df.columns if c.startswith("avg_")]
    return df.drop(columns=drop_cols, errors="ignore")

def _filter_by_race(df: pd.DataFrame, race_id: int) -> pd.DataFrame:
    """Safe filter by race_id; returns empty DataFrame if column missing."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()
    if "race_id" not in df.columns:
        return pd.DataFrame()
    return df.loc[df["race_id"] == race_id]

@dataclass
class Driver:
    driver_id: int
    name: Optional[str] = None
    team: Optional[str] = None
    car_number: Optional[str] = None
    manufacturer: Optional[str] = None
    stats_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    adv_stats_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    averages: pd.Series = field(default_factory=lambda: pd.Series(dtype="float64"))
    results_rows: pd.DataFrame = field(default_factory=pd.DataFrame)
    stage_rows: pd.DataFrame = field(default_factory=pd.DataFrame)
    lap_speed_summary: pd.DataFrame = field(default_factory=pd.DataFrame)
    pit_stops_df: pd.DataFrame = field(default_factory=pd.DataFrame)

    def _merge_cols_for_race(self, df: pd.DataFrame, race_id: int, cols: list, row: dict) -> bool:
        sub = _filter_by_race(df, race_id)
        if sub.empty:
            return False
        s0 = sub.iloc[0]
        added = False
        for c in cols:
            if c in s0.index and pd.notna(s0[c]):
                row[c] = s0[c]
                added = True
        return added

    def _pit_aggregates_for_race(self, race_id: int) -> pd.DataFrame:
        p = _filter_by_race(self.pit_stops_df, race_id)
        if p.empty:
            return pd.DataFrame()
        data = {
            "race_id": race_id,
            "total_pit_stops": int(len(p)),
            "avg_total_duration": _nanmean(p["total_duration"]) if "total_duration" in p.columns else None,
            "avg_pit_stop_duration": _nanmean(p["pit_stop_duration"]) if "pit_stop_duration" in p.columns else None,
            "avg_in_travel_duration": _nanmean(p["in_travel_duration"]) if "in_travel_duration" in p.columns else None,
            "avg_out_travel_duration": _nanmean(p["out_travel_duration"]) if "out_travel_duration" in p.columns else None,
            "avg_positions_gained_lost": _nanmean(p["positions_gained_lost"]) if "positions_gained_lost" in p.columns else None,
        }
        return pd.DataFrame([data])

    def get_race_row(self, race_id: int) -> Optional[dict]:
        row = {
            "race_id": race_id,
            "driver_id": self.driver_id,
            "driver_name": self.name,
            "team": self.team,
        }
        found_any = False

        # Deterres_df participation
        r = _filter_by_race(self.results_rows, race_id)
        participated = False
        if not r.empty:
            r0 = r.iloc[0]
            laps_c = pd.to_numeric(r0.get("laps_completed"), errors="coerce")
            fin_pos = pd.to_numeric(r0.get("finishing_position"), errors="coerce")
            participated = (pd.notna(fin_pos)) or (pd.notna(laps_c) and laps_c > 0)
        if not participated and not _filter_by_race(self.lap_speed_summary, race_id).empty:
            participated = True
        if not participated and not _filter_by_race(self.pit_stops_df, race_id).empty:
            participated = True
        if not participated and not _filter_by_race(self.stage_rows, race_id).empty:
            participated = True
        if not participated:
            return None

        # Results merge
        found_any |= self._merge_cols_for_race(
            self.results_rows, race_id,
            [
                "qualifying_position", "qualifying_speed", "points", "playoff_points",
                "laps_completed", "starting_position", "finishing_position",
                "manufacturer", "car_number",
            ],
            row,
        )
        if "car_number" not in row and not r.empty and "driver_number" in r.columns:
            dn = r.iloc[0].get("driver_number")
            if pd.notna(dn):
                row["car_number"] = str(dn); found_any = True

        # Loop/advanced stats merge
        wanted_cols = [
            "mid_position", "closing_position", "closing_laps_diff",
            "best_position", "worst_position", "avg_position",
            "passes_green_flag", "passing_diff", "passed_green_flag",
            "quality_passes", "fast_laps", "top15_laps",
        ]
        found_any |= self._merge_cols_for_race(self.stats_df, race_id, wanted_cols, row)
        found_any |= self._merge_cols_for_race(self.adv_stats_df, race_id, wanted_cols, row)

        # No closing_position fallback

        # Backfill identifiers
        if "manufacturer" not in row and self.manufacturer is not None:
            row["manufacturer"] = self.manufacturer
        if "car_number" not in row and self.car_number is not None:
            row["car_number"] = self.car_number

        # Stage results
        row["stage1_position"] = 0; row["stage1_points"] = 0.0
        row["stage2_position"] = 0; row["stage2_points"] = 0.0
        s = _filter_by_race(self.stage_rows, race_id)
        if not s.empty and "stage" in s.columns:
            s1 = s.loc[s["stage"] == 1]
            if not s1.empty:
                r1 = s1.iloc[0]
                pos1 = pd.to_numeric(r1.get("position"), errors="coerce")
                pts1 = pd.to_numeric(r1.get("stage_points"), errors="coerce")
                row["stage1_position"] = int(pos1) if pd.notna(pos1) and int(pos1) <= 10 else 0
                row["stage1_points"] = float(pts1) if pd.notna(pts1) and row["stage1_position"] > 0 else 0.0
                found_any = True
            s2 = s.loc[s["stage"] == 2]
            if not s2.empty:
                r2 = s2.iloc[0]
                pos2 = pd.to_numeric(r2.get("position"), errors="coerce")
                pts2 = pd.to_numeric(r2.get("stage_points"), errors="coerce")
                row["stage2_position"] = int(pos2) if pd.notna(pos2) and int(pos2) <= 10 else 0
                row["stage2_points"] = float(pts2) if pd.notna(pts2) and row["stage2_position"] > 0 else 0.0
                found_any = True

        # Lap-speed summary merge
        found_any |= self._merge_cols_for_race(
            self.lap_speed_summary, race_id,
            ["leader_laps", "avg_speed_rank", "laps_completed_pct", "avg_lap_speed", "norm_speed"],
            row,
        )

        # Pit aggregates merge
        pit_agg = self._pit_aggregates_for_race(race_id)
        found_any |= self._merge_cols_for_race(
            pit_agg, race_id,
            ["total_pit_stops", "avg_total_duration", "avg_pit_stop_duration",
             "avg_in_travel_duration", "avg_out_travel_duration", "avg_positions_gained_lost"],
            row,
        )

        # Ensure all requested keys are present
        ensure = wanted_cols + [
            "manufacturer", "car_number",
            "leader_laps", "avg_speed_rank", 'avg_lap_speed','norm_speed', "laps_completed_pct",
            "total_pit_stops", "avg_total_duration", "avg_pit_stop_duration",
            "avg_in_travel_duration", "avg_out_travel_duration", "avg_positions_gained_lost",
            "qualifying_position", "qualifying_speed", "points", "playoff_points",
            "laps_completed", "starting_position", "finishing_position",
            "stage1_position", "stage1_points", "stage2_position", "stage2_points",
        ]
        for c in ensure:
            if c not in row:
                row[c] = None

        return row

    def add_stats(self, df: pd.DataFrame) -> None:
        if df is None or df.empty or "driver_id" not in df.columns:
            return
        rows = df[df["driver_id"] == self.driver_id]
        if rows.empty:
            return
        self.stats_df = pd.concat([self.stats_df, rows], ignore_index=True) if not self.stats_df.empty else rows.copy()
        if self.name is None and "driver_name" in rows.columns:
            n = rows["driver_name"].dropna()
            if not n.empty:
                self.name = str(n.iloc[0])

    def add_adv_stats(self, df: pd.DataFrame) -> None:
        if df is None or df.empty or "driver_id" not in df.columns:
            return
        rows = df[df["driver_id"] == self.driver_id]
        if rows.empty:
            return
        self.adv_stats_df = pd.concat([self.adv_stats_df, rows], ignore_index=True) if not self.adv_stats_df.empty else rows.copy()
        if self.name is None and "driver_name" in rows.columns:
            n = rows["driver_name"].dropna()
            if not n.empty:
                self.name = str(n.iloc[0])

    # add results-derived fields
    def add_results(self, res: pd.DataFrame, race_id: int) -> None:
        if not isinstance(res, pd.DataFrame) or res.empty or "driver_id" not in res.columns:
            return
        row = res[res["driver_id"] == self.driver_id]
        if row.empty:
            return

        # Skip non-starters (DNQ/DNS): no finishing_position and no laps completed
        try:
            r0 = row.iloc[0]
            laps_c = pd.to_numeric(r0.get("laps_completed"), errors="coerce")
            fin_pos = pd.to_numeric(r0.get("finishing_position"), errors="coerce")
            started = (pd.notna(fin_pos)) or (pd.notna(laps_c) and laps_c > 0)
            if not started:
                return
        except Exception:
            pass

        cols = [c for c in (
            "qualifying_position",
            "qualifying_speed",
            "points",
            "playoff_points",
            "laps_completed",
            "starting_position",
            "finishing_position",
            "driver",
            "team",
            "manufacturer",
            "driver_number",
        ) if c in row.columns]
        take = row[cols].copy()
        take = take.assign(race_id=race_id)
        if "driver_number" in take.columns and "car_number" not in take.columns:
            with pd.option_context('mode.chained_assignment', None):
                take["car_number"] = take["driver_number"].astype(str)
        self.results_rows = pd.concat([self.results_rows, take], ignore_index=True) if not self.results_rows.empty else take
        if self.name is None and "driver" in row.columns:
            n = row["driver"].dropna()
            if not n.empty:
                self.name = str(n.iloc[0])
        if self.team is None and "team" in row.columns:
            t = row["team"].dropna()
            if not t.empty:
                self.team = str(t.iloc[0])
        if self.car_number is None and "driver_number" in row.columns:
            dn = row["driver_number"].dropna()
            if not dn.empty:
                self.car_number = str(dn.iloc[0])
        if self.manufacturer is None and "manufacturer" in row.columns:
            m = row["manufacturer"].dropna()
            if not m.empty:
                self.manufacturer = str(m.iloc[0])

    # add stage 1/2 results (position, stage_points)
    def add_stage_results(self, stage1: Optional[pd.DataFrame], stage2: Optional[pd.DataFrame], race_id: int) -> None:
        frames = []
        if isinstance(stage1, pd.DataFrame) and not stage1.empty and "driver_id" in stage1.columns:
            r = stage1[stage1["driver_id"] == self.driver_id]
            if not r.empty:
                r = r[[c for c in ("position", "stage_points") if c in r.columns]].copy().assign(stage=1, race_id=race_id)
                frames.append(r)
        if isinstance(stage2, pd.DataFrame) and not stage2.empty and "driver_id" in stage2.columns:
            r = stage2[stage2["driver_id"] == self.driver_id]
            if not r.empty:
                r = r[[c for c in ("position", "stage_points") if c in r.columns]].copy().assign(stage=2, race_id=race_id)
                frames.append(r)
        if frames:
            add = pd.concat(frames, ignore_index=True)
            self.stage_rows = pd.concat([self.stage_rows, add], ignore_index=True) if not self.stage_rows.empty else add

    # compute leader_laps, avg_speed_rank, laps_completed_pct from laps cache
    def add_laps_for_race(self, laps: pd.DataFrame, res: pd.DataFrame, race_id: int) -> None:
        if not isinstance(laps, pd.DataFrame) or laps.empty:
            return
        if not isinstance(res, pd.DataFrame) or res.empty:
            return
        if "driver_number" not in res.columns or "driver_id" not in res.columns:
            return
        map_num_to_id = (
            res[["driver_number", "driver_id"]]
            .dropna()
            .assign(driver_number=res["driver_number"].astype(str))
            .drop_duplicates(subset=["driver_number"], keep="first")
            .set_index("driver_number")["driver_id"]
        )
        working_df = laps.copy()
        if "Number" not in working_df.columns or "lap_speed" not in working_df.columns or "Lap" not in working_df.columns:
            return
        working_df["driver_number"] = working_df["Number"].astype(str)
        working_df["lap_speed"] = pd.to_numeric(working_df["lap_speed"], errors="coerce")
        working_df["Lap"] = pd.to_numeric(working_df["Lap"], errors="coerce").astype("Int64")
        working_df["driver_id"] = working_df["driver_number"].map(map_num_to_id)
        working_df = working_df.dropna(subset=["driver_id", "Lap", "lap_speed"])
        if working_df.empty:
            return
        
        # Get lap ranks
        working_df["lap_speed_max"] = working_df.groupby("Lap")["lap_speed"].transform("max")
        working_df["lap_speed_rank"] = working_df.groupby("Lap")["lap_speed"].rank(ascending=False, method="min")
        
        # Get the avg speed for the race
        working_df['avg_lap_speed'] = working_df.groupby('driver_id')['lap_speed'].transform('mean')
        working_df['normalized_lap_speed'] = working_df['avg_lap_speed'] / working_df['avg_lap_speed'].max() * 100

        res_df = working_df[working_df["driver_id"] == self.driver_id]
        if res_df.empty:
            return
        
        leader_laps = int((res_df["lap_speed"] == res_df["lap_speed_max"]).sum())
        avg_rank = float(res_df["lap_speed_rank"].mean())
        total_race_laps = int(working_df["Lap"].max()) if working_df["Lap"].notna().any() else None
        laps_completed = int(res_df["Lap"].count())
        laps_pct = (laps_completed / total_race_laps) if total_race_laps and total_race_laps > 0 else None
        avg_speed = float(res_df["normalized_lap_speed"].mean())
        norm_speed = float(res_df["normalized_lap_speed"].mean())
        summary = pd.DataFrame([{
            "race_id": race_id,
            "leader_laps": leader_laps,
            "avg_speed_rank": avg_rank,
            "laps_completed_pct": laps_pct,
            "avg_lap_speed": avg_speed,
            "norm_speed": norm_speed
        }])
        self.lap_speed_summary = pd.concat([self.lap_speed_summary, summary], ignore_index=True) if not self.lap_speed_summary.empty else summary

    # collect pit stop rows and map to driver_id via results
    def add_pit_stops(self, pit: pd.DataFrame, res: pd.DataFrame, race_id: int) -> None:
        if not isinstance(pit, pd.DataFrame) or pit.empty:
            return
        if not isinstance(res, pd.DataFrame) or res.empty:
            return
        if "Driver" not in pit.columns or "driver" not in res.columns or "driver_id" not in res.columns:
            return

        # Build name map from results, stripping symbols for matching
        def _clean_name(name):
            if pd.isna(name):
                return None
            import re
            cleaned = str(name).strip()
            cleaned = re.sub(r'^[*#†‡§¶\s]+', '', cleaned)
            cleaned = re.sub(r'[*#†‡§¶\s]+$', '', cleaned)
            cleaned = re.sub(r'\s*\([^)]*\)\s*$', '', cleaned)
            return cleaned.strip()

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
        res_cols = ["driver", "driver_id"]
        if "driver_number" in res.columns:
            res_cols.append("driver_number")
        if "manufacturer" in res.columns:
            res_cols.append("manufacturer")
        res_clean = res[res_cols].dropna(subset=["driver", "driver_id"]).copy()
        res_clean["clean_name"] = res_clean["driver"].apply(_normalize_name)

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

        res_df = working_df[working_df["driver_id"] == self.driver_id].copy()
        if res_df.empty:
            return

        res_df["race_id"] = race_id
        # Ensure consistent types
        if "car_number" in res_df.columns:
            res_df["car_number"] = res_df["car_number"].astype("string")
        self.pit_stops_df = pd.concat([self.pit_stops_df, res_df], ignore_index=True) if not self.pit_stops_df.empty else res_df

    def total_races(self) -> int:
        race_count = len(self.results_rows)
        return race_count
        
    
    def compute_averages(self) -> None:
        data_parts = []
        if not self.stats_df.empty:
            data_parts.append(self.stats_df.select_dtypes(include=["number"]))
        if not self.adv_stats_df.empty:
            data_parts.append(self.adv_stats_df.select_dtypes(include=["number"]))
        if not data_parts:
            self.averages = pd.Series(dtype="float64")
            return

        merged = pd.concat(data_parts, axis=1)
        self.averages = merged.mean(numeric_only=True)

        # Stats-based helpers
        if not self.stats_df.empty:
            if "position" in self.stats_df.columns:
                self.averages["avg_finish_position"] = _nanmean(self.stats_df["position"])
            if "start_position" in self.stats_df.columns:
                self.averages["avg_start_position"] = _nanmean(self.stats_df["start_position"])
            if "rating" in self.stats_df.columns:
                self.averages["avg_rating"] = _nanmean(self.stats_df["rating"])
            if "fast_laps" in self.stats_df.columns:
                self.averages["avg_fast_laps"] = _nanmean(self.stats_df["fast_laps"])

        # Results-derived metrics
        if isinstance(self.results_rows, pd.DataFrame) and not self.results_rows.empty:
            for col, out_name in [
                ("qualifying_position", "avg_qualifying_position"),
                ("qualifying_speed", "avg_qualifying_speed"),
                ("points", "avg_points"),
                ("playoff_points", "avg_playoff_points"),
            ]:
                if col in self.results_rows.columns:
                    self.averages[out_name] = _nanmean(self.results_rows[col])

        # Stage metrics
        if isinstance(self.stage_rows, pd.DataFrame) and not self.stage_rows.empty:
            for stage in (1, 2):
                sub = self.stage_rows[self.stage_rows.get("stage") == stage]
                if not sub.empty:
                    if "stage_points" in sub.columns:
                        self.averages[f"avg_stage{stage}_points"] = _nanmean(sub["stage_points"])
                    if "position" in sub.columns:
                        self.averages[f"avg_stage{stage}_position"] = _nanmean(sub["position"])

        # Lap-speed summary metrics
        if isinstance(self.lap_speed_summary, pd.DataFrame) and not self.lap_speed_summary.empty:
            if "leader_laps" in self.lap_speed_summary.columns:
                self.averages["lap_speed_leader_laps_total"] = _nansum(self.lap_speed_summary["leader_laps"])
            if "avg_speed_rank" in self.lap_speed_summary.columns:
                self.averages["avg_speed_rank"] = _nanmean(self.lap_speed_summary["avg_speed_rank"])
            if "laps_completed_pct" in self.lap_speed_summary.columns:
                self.averages["avg_laps_completed_pct"] = _nanmean(self.lap_speed_summary["laps_completed_pct"])
            if "avg_lap_speed" in self.lap_speed_summary.columns:
                self.averages["avg_lap_speed"] = _nanmean(self.lap_speed_summary["avg_lap_speed"])
            if "norm_speed" in self.lap_speed_summary.columns:
                self.averages["avg_norm_speed"] = _nanmean(self.lap_speed_summary["norm_speed"])
        # ...existing code...

        # Pit stop totals and averages
        if isinstance(self.pit_stops_df, pd.DataFrame) and not self.pit_stops_df.empty:
            self.averages["total_pit_stops"] = int(len(self.pit_stops_df))
            for col, out_name in [
                # ("pit_in_race_time", "avg_pit_in_race_time"),
                # ("pit_out_race_time", "avg_pit_out_race_time"),
                ("total_duration", "avg_total_duration"),
                # ("box_stop_race_time", "avg_box_stop_race_time"),
                # ("box_leave_race_time", "avg_box_leave_race_time"),
                ("pit_stop_duration", "avg_pit_stop_duration"),
                ("in_travel_duration", "avg_in_travel_duration"),
                ("out_travel_duration", "avg_out_travel_duration"),
                ("positions_gained_lost", "avg_positions_gained_lost"),
            ]:
                if col in self.pit_stops_df.columns:
                    self.averages[out_name] = _nanmean(self.pit_stops_df[col])

        self.averages["total_races"] = self.total_races()


@dataclass
class DriversData:
    year: int
    series_id: int
    drivers: Dict[int, Driver] = field(default_factory=dict)
    summary_cache: Optional[pd.DataFrame] = None
    per_race_cache: Optional[pd.DataFrame] = None
    season_race_ids: list[int] = field(default_factory=list)

    @classmethod
    def build(
        cls,
        year: int,
        series_id: int,
        use_cache_only: bool = True,
        sleep_seconds: int = 10,
        use_drivers_cache: bool = True,
        reload_drivers_cache: bool = False,
    ):
        """
        Build DriversData for a season (cache-first):
        - Load schedule from cache; only fetch if allowed and missing.
        - Use only finished races from the schedule.
        - For each finished race, load cached driver_stats and driver_stats_advanced.
        - If both missing and fetching allowed, fetch, then re-load from cache (sleep between fetches).
        - Optionally use/save season-level drivers caches (summary and per-race).
        """
        out = cls(year=year, series_id=series_id)

        if use_drivers_cache and not reload_drivers_cache:
            summary = load_drivers_df(year=year, series_id=series_id, name="summary")
            per_race = load_drivers_df(year=year, series_id=series_id, name="per_race")
            if isinstance(summary, pd.DataFrame) and not summary.empty:
                out.summary_cache = summary
                out.per_race_cache = per_race if isinstance(per_race, pd.DataFrame) and not per_race.empty else None
                if isinstance(out.per_race_cache, pd.DataFrame) and "race_id" in out.per_race_cache.columns:
                    out.season_race_ids = (
                        pd.to_numeric(out.per_race_cache["race_id"], errors="coerce")
                        .dropna().astype(int).unique().tolist()
                    )
                else:
                    sched_df = load_schedule(year=year, series_id=series_id)
                    if isinstance(sched_df, pd.DataFrame) and not sched_df.empty and "race_id" in sched_df.columns:
                        now = pd.Timestamp.now(tz="UTC")
                        if "winner_driver_id" in sched_df.columns:
                            finished_df = sched_df[sched_df["winner_driver_id"].notna()]
                        elif "scheduled_at" in sched_df.columns:
                            finished_df = sched_df[pd.to_datetime(sched_df["scheduled_at"], errors="coerce", utc=True) <= now]
                        else:
                            finished_df = sched_df
                        out.season_race_ids = (
                            pd.to_numeric(finished_df["race_id"], errors="coerce")
                            .dropna().astype(int).unique().tolist()
                        )
                return out

        # Schedule: prefer cache
        sched_df = load_schedule(year=year, series_id=series_id)
        if (sched_df is None or sched_df.empty) and not use_cache_only:
            sched = Schedule(year, series_id)
            sched_df = sched.data

        if sched_df is None or sched_df.empty or "race_id" not in sched_df.columns:
            return out

        cached_sched = load_schedule(year=year, series_id=series_id)
        if (cached_sched is None or cached_sched.empty):
            if use_cache_only:
                return out
            sched = Schedule(year, series_id)            # may fetch, then cache
        else:
            sched = Schedule(year, series_id)            # loads from cache, no API hit

        finished_df = sched.get_finished_races()
        if finished_df is None or finished_df.empty or "race_id" not in finished_df.columns:
            return out

        race_ids = finished_df["race_id"].dropna().astype(int).tolist()
        out.season_race_ids = race_ids
        if not race_ids:
            return out
        
        if not race_ids:
            return out

        for race_id in race_ids:
            stats = load_df("driver_stats", year=year, series_id=series_id, race_id=race_id)
            adv = load_df("driver_stats_advanced", year=year, series_id=series_id, race_id=race_id)
            res = load_df("results", year=year, series_id=series_id, race_id=race_id)
            stage1 = load_df("stage_1_results", year=year, series_id=series_id, race_id=race_id)
            stage2 = load_df("stage_2_results", year=year, series_id=series_id, race_id=race_id)
            laps = load_df("laps", year=year, series_id=series_id, race_id=race_id)
            pit = load_df("pit_stops", year=year, series_id=series_id, race_id=race_id)

            if (stats is None or (isinstance(stats, pd.DataFrame) and stats.empty)) and \
               (adv is None or (isinstance(adv, pd.DataFrame) and adv.empty)):
                if use_cache_only:
                    continue
                Race(year, series_id, race_id, live=False)
                time.sleep(sleep_seconds)
                stats = load_df("driver_stats", year=year, series_id=series_id, race_id=race_id)
                adv = load_df("driver_stats_advanced", year=year, series_id=series_id, race_id=race_id)
                res = load_df("results", year=year, series_id=series_id, race_id=race_id)
                stage1 = load_df("stage_1_results", year=year, series_id=series_id, race_id=race_id)
                stage2 = load_df("stage_2_results", year=year, series_id=series_id, race_id=race_id)
                laps = load_df("laps", year=year, series_id=series_id, race_id=race_id)
                pit = load_df("pit_stops", year=year, series_id=series_id, race_id=race_id)
                missing_stats = (stats is None or (isinstance(stats, pd.DataFrame) and stats.empty))
                missing_adv = (adv is None or (isinstance(adv, pd.DataFrame) and adv.empty))
                if missing_stats and missing_adv:
                    continue

            if isinstance(stats, pd.DataFrame) and not stats.empty and "race_id" not in stats.columns:
                stats = stats.copy()
                stats["race_id"] = race_id
            if isinstance(adv, pd.DataFrame) and not adv.empty and "race_id" not in adv.columns:
                adv = adv.copy()
                adv["race_id"] = race_id

            driver_ids = set()
            if isinstance(stats, pd.DataFrame) and not stats.empty and "driver_id" in stats.columns:
                driver_ids.update(stats["driver_id"].dropna().astype(int).unique().tolist())
            if isinstance(adv, pd.DataFrame) and not adv.empty and "driver_id" in adv.columns:
                driver_ids.update(adv["driver_id"].dropna().astype(int).unique().tolist())

            for did in sorted(driver_ids):
                d = out.drivers.get(did)
                if d is None:
                    d = Driver(driver_id=did)
                    out.drivers[did] = d
                if isinstance(stats, pd.DataFrame) and not stats.empty:
                    d.add_stats(stats)
                if isinstance(adv, pd.DataFrame) and not adv.empty:
                    d.add_adv_stats(adv)
                if isinstance(res, pd.DataFrame) and not res.empty:
                    d.add_results(res, race_id)
                if isinstance(stage1, pd.DataFrame) or isinstance(stage2, pd.DataFrame):
                    d.add_stage_results(stage1, stage2, race_id)
                if isinstance(laps, pd.DataFrame) and not laps.empty and isinstance(res, pd.DataFrame) and not res.empty:
                    d.add_laps_for_race(laps, res, race_id)
                if isinstance(pit, pd.DataFrame) and not pit.empty and isinstance(res, pd.DataFrame) and not res.empty:
                    d.add_pit_stops(pit, res, race_id)

        for d in out.drivers.values():
            d.compute_averages()

        if use_drivers_cache:
            try:
                summary_df = out.to_dataframe()
                if isinstance(summary_df, pd.DataFrame) and not summary_df.empty:
                    save_drivers_df(summary_df, year=year, series_id=series_id, name="summary")
                per_race_rows = []
                for rid in race_ids:
                    for drv in out.drivers.values():
                        r = drv.get_race_row(rid)
                        if r:
                            per_race_rows.append(r)
                if per_race_rows:
                    per_race_df = pd.DataFrame(per_race_rows)
                    save_drivers_df(per_race_df, year=year, series_id=series_id, name="per_race")
                    # Keep in memory so the notebook can inspect it right away
                    out.per_race_cache = per_race_df.copy()
            except Exception:
                pass

        return out

    def to_dataframe(self,min_participation: float = 0.2) -> pd.DataFrame:
        """One row per driver with averages."""
        season_total = len(self.season_race_ids) if self.season_race_ids else None

        if isinstance(self.summary_cache, pd.DataFrame) and not self.summary_cache.empty and not self.drivers:
            results_df = self.summary_cache.copy()

            if min_participation > 0:
                threshold = max(1, math.ceil(min_participation * season_total))
                results_df = results_df[results_df["total_races"].fillna(0).astype(int) >= threshold]
            return results_df

        rows = []
        for did, d in self.drivers.items():
            row = {
                "driver_id": did,
                "driver_name": d.name,
                "team": d.team,                   # <— include team
                "car_number": d.car_number,
                "manufacturer": d.manufacturer,
            }
            if isinstance(d.averages, pd.Series) and not d.averages.empty:
                row.update({str(k): v for k, v in d.averages.items()})
            rows.append(row)

        results_df = pd.DataFrame(rows)
        
        if min_participation > 0:
            threshold = max(1, math.ceil(min_participation * season_total))
            results_df = results_df[results_df["total_races"].fillna(0).astype(int) >= threshold]
        return results_df
    
    def race_dataframe(self, race_id: int) -> pd.DataFrame:
        # Keep per-race averages; only drop season-level total_races
        if isinstance(self.per_race_cache, pd.DataFrame) and not self.per_race_cache.empty and not self.drivers:
            df = self.per_race_cache[self.per_race_cache.get("race_id") == race_id].copy()
            df = df.drop(columns=["total_races"], errors="ignore")
            return df.reset_index(drop=True)
        rows = []
        for d in self.drivers.values():
            r = d.get_race_row(race_id)
            if r:
                rows.append(r)
        df = pd.DataFrame(rows).drop(columns=["total_races"], errors="ignore")
        return df.reset_index(drop=True)

    def driver_races(self, driver_id: int) -> pd.DataFrame:
        """
        Return one row per race for this driver with per-race metrics (includes per-race averages).
        """
        d = self.drivers.get(driver_id)
        if d is not None:
            race_ids = []
            if isinstance(d.results_rows, pd.DataFrame) and "race_id" in d.results_rows.columns:
                race_ids = (
                    pd.to_numeric(d.results_rows["race_id"], errors="coerce")
                    .dropna().astype(int).unique().tolist()
                )
            rows = []
            for rid in sorted(race_ids):
                r = d.get_race_row(rid)
                if r:
                    rows.append(r)
            return pd.DataFrame(rows).sort_values("race_id", ignore_index=True)
        if isinstance(self.per_race_cache, pd.DataFrame) and not self.per_race_cache.empty:
            df = self.per_race_cache[self.per_race_cache["driver_id"] == driver_id].copy()
            return df.sort_values("race_id", ignore_index=True)
        return pd.DataFrame()

    # NEW: raw pit stops for a specific driver (optionally for a single race)
    def driver_pit_stops(self, driver_id: int, race_id: Optional[int] = None) -> pd.DataFrame:
        """
        Return raw pit stop rows for driver_id across races (or a single race if race_id provided).
        Includes all columns from the pit_stops cache plus driver_id/driver_name/race_id.
        """
        d = self.drivers.get(driver_id)
        # Prefer in-memory driver store
        if d is not None and isinstance(d.pit_stops_df, pd.DataFrame) and not d.pit_stops_df.empty:
            df = d.pit_stops_df.copy()
            if race_id is not None:
                df = df[df.get("race_id") == race_id]
            if "driver_id" not in df.columns:
                df["driver_id"] = driver_id
            if "driver_name" not in df.columns:
                df["driver_name"] = d.name
            # Ensure normalized manufacturer field exists
            if "manufacturer" not in df.columns and "Manufacturer" in df.columns:
                df["manufacturer"] = df["Manufacturer"]
            # Order helpful columns first
            first = [c for c in ["race_id", "driver_id", "driver_name", "car_number", "manufacturer"] if c in df.columns]
            rest = [c for c in df.columns if c not in first]
            return df[first + rest].sort_values(["race_id"], ignore_index=True)

        # Fallback: build from race caches (best-effort)
        rows = []
        for rid in (self.season_race_ids or []):
            if race_id is not None and rid != race_id:
                continue
            pit = load_df("pit_stops", year=self.year, series_id=self.series_id, race_id=rid)
            res = load_df("results", year=self.year, series_id=self.series_id, race_id=rid)
            if not isinstance(pit, pd.DataFrame) or pit.empty or not isinstance(res, pd.DataFrame) or res.empty:
                continue
            if "driver" not in res.columns or "driver_id" not in res.columns or "Driver" not in pit.columns:
                continue
            name_to_id = res[["driver", "driver_id"]].dropna().drop_duplicates("driver").set_index("driver")["driver_id"]
            name_to_num = res[["driver", "driver_number"]].dropna().drop_duplicates("driver").set_index("driver")["driver_number"] if "driver_number" in res.columns else None
            name_to_man = res[["driver", "manufacturer"]].dropna().drop_duplicates("driver").set_index("driver")["manufacturer"] if "manufacturer" in res.columns else None

            working_df = pit.copy()
            working_df["driver_id"] = working_df["Driver"].map(name_to_id)
            working_df = working_df[working_df["driver_id"] == driver_id].copy()
            if working_df.empty:
                continue
            working_df["race_id"] = rid
            working_df["driver_name"] = working_df["Driver"]
            if name_to_num is not None:
                working_df["car_number"] = working_df["Driver"].map(name_to_num).astype("string")
            if "Manufacturer" in working_df.columns:
                working_df["manufacturer"] = working_df["Manufacturer"]
            elif name_to_man is not None:
                working_df["manufacturer"] = working_df["Driver"].map(name_to_man)
            rows.append(working_df)
        if rows:
            df = pd.concat(rows, ignore_index=True)
            first = [c for c in ["race_id", "driver_id", "driver_name", "car_number", "manufacturer"] if c in df.columns]
            rest = [c for c in df.columns if c not in first]
            return df[first + rest].sort_values(["race_id"], ignore_index=True)
        return pd.DataFrame()

    # NEW: raw pit stops for a race across all drivers
    def race_pit_stops(self, race_id: int) -> pd.DataFrame:
        """
        Return raw pit stop rows for a race_id across all drivers.
        Includes all columns from pit_stops cache plus driver_id/driver_name.
        """
        pit = load_df("pit_stops", year=self.year, series_id=self.series_id, race_id=race_id)
        res = load_df("results", year=self.year, series_id=self.series_id, race_id=race_id)
        if not isinstance(pit, pd.DataFrame) or pit.empty:
            return pd.DataFrame()
        df = pit.copy()
        # Map names to ids/numbers/manufacturer when possible
        if isinstance(res, pd.DataFrame) and not res.empty and "driver" in res.columns and "driver_id" in res.columns and "Driver" in df.columns:
            name_to_id = res[["driver", "driver_id"]].dropna().drop_duplicates("driver").set_index("driver")["driver_id"]
            df["driver_id"] = df["Driver"].map(name_to_id)
            if "driver_number" in res.columns:
                name_to_num = res[["driver", "driver_number"]].dropna().drop_duplicates("driver").set_index("driver")["driver_number"]
                df["car_number"] = df["Driver"].map(name_to_num).astype("string")
            if "manufacturer" in res.columns and "manufacturer" not in df.columns:
                name_to_man = res[["driver", "manufacturer"]].dropna().drop_duplicates("driver").set_index("driver")["manufacturer"]
                df["manufacturer"] = df["Driver"].map(name_to_man)
        # Normalize manufacturer field to lower-case column name as alias
        if "manufacturer" not in df.columns and "Manufacturer" in df.columns:
            df["manufacturer"] = df["Manufacturer"]
        if "driver_name" not in df.columns and "Driver" in df.columns:
            df["driver_name"] = df["Driver"]
        df["race_id"] = race_id
        first = [c for c in ["race_id", "driver_id", "driver_name", "car_number", "manufacturer"] if c in df.columns]
        rest = [c for c in df.columns if c not in first]
        return df[first + rest].reset_index(drop=True)