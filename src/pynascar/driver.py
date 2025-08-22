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

    def get_race_row(self, race_id: int) -> Optional[dict]:
        row = {
            "race_id": race_id,
            "driver_id": self.driver_id,
            "driver_name": self.name,
            "team": self.team,
        }
        found_any = False

        # First, determine if the driver actually participated in this race
        participated = False
        r = None
        if isinstance(self.results_rows, pd.DataFrame) and not self.results_rows.empty:
            r = self.results_rows[self.results_rows.get("race_id") == race_id]
            if not r.empty:
                r0 = r.iloc[0]
                laps_c = pd.to_numeric(r0.get("laps_completed"), errors="coerce")
                fin_pos = pd.to_numeric(r0.get("finishing_position"), errors="coerce")
                # Consider "participated" if they have a classified finish or completed any lap
                participated = (pd.notna(fin_pos)) or (pd.notna(laps_c) and laps_c > 0)

        # Fallback evidence: any laps, pit stops, or stage results for this race
        if not participated and isinstance(self.lap_speed_summary, pd.DataFrame) and not self.lap_speed_summary.empty:
            participated = not self.lap_speed_summary[self.lap_speed_summary.get("race_id") == race_id].empty
        if not participated and isinstance(self.pit_stops_df, pd.DataFrame) and not self.pit_stops_df.empty:
            participated = not self.pit_stops_df[self.pit_stops_df.get("race_id") == race_id].empty
        if not participated and isinstance(self.stage_rows, pd.DataFrame) and not self.stage_rows.empty:
            participated = not self.stage_rows[self.stage_rows.get("race_id") == race_id].empty

        if not participated:
            return None

        # Results-derived fields (only after we know they participated)
        if r is not None and not r.empty:
            r = r.iloc[0]
            for col in (
                "qualifying_position",
                "qualifying_speed",
                "points",
                "playoff_points",
                "laps_completed",
                "starting_position",
                "finishing_position",
            ):
                if col in r.index:
                    row[col] = r[col]
                    found_any = True
            # Include manufacturer and car number when present in result row
            if "manufacturer" in r.index and pd.notna(r["manufacturer"]):
                row["manufacturer"] = r["manufacturer"]
            car = None
            if "car_number" in r.index and pd.notna(r["car_number"]):
                car = r["car_number"]
            elif "driver_number" in r.index and pd.notna(r["driver_number"]):
                car = r["driver_number"]
            if car is None and self.car_number is not None:
                car = self.car_number
            if car is not None:
                row["car_number"] = str(car)

        # Backfill only for display; do not change participation logic
        if "manufacturer" not in row or pd.isna(row.get("manufacturer")):
            if self.manufacturer is not None:
                row["manufacturer"] = self.manufacturer
        
        # Always include stage fields with 0 defaults (top-10 cutoff)
        row["stage1_position"] = 0
        row["stage1_points"] = 0.0
        row["stage2_position"] = 0
        row["stage2_points"] = 0.0

        # Stage 1/2 overrides when present and position <= 10
        if isinstance(self.stage_rows, pd.DataFrame) and not self.stage_rows.empty:
            s = self.stage_rows[self.stage_rows.get("race_id") == race_id]
            if not s.empty:
                s1 = s[s.get("stage") == 1]
                if not s1.empty:
                    r1 = s1.iloc[0]
                    pos1 = pd.to_numeric(r1.get("position"), errors="coerce")
                    pts1 = pd.to_numeric(r1.get("stage_points"), errors="coerce")
                    row["stage1_position"] = int(pos1) if pd.notna(pos1) and int(pos1) <= 10 else 0
                    row["stage1_points"] = float(pts1) if pd.notna(pts1) and row["stage1_position"] > 0 else 0.0
                    found_any = True
                s2 = s[s.get("stage") == 2]
                if not s2.empty:
                    r2 = s2.iloc[0]
                    pos2 = pd.to_numeric(r2.get("position"), errors="coerce")
                    pts2 = pd.to_numeric(r2.get("stage_points"), errors="coerce")
                    row["stage2_position"] = int(pos2) if pd.notna(pos2) and int(pos2) <= 10 else 0
                    row["stage2_points"] = float(pts2) if pd.notna(pts2) and row["stage2_position"] > 0 else 0.0
                    found_any = True

        # Lap speed summary: include per-race metrics
        if isinstance(self.lap_speed_summary, pd.DataFrame) and not self.lap_speed_summary.empty:
            l = self.lap_speed_summary[self.lap_speed_summary.get("race_id") == race_id]
            if not l.empty:
                l = l.iloc[0]
                for col in ("leader_laps", "avg_speed_rank", "laps_completed_pct"):
                    if col in l.index:
                        row[col] = l[col]
                        found_any = True

        # Pit stops: include per-race averages and total count
        row["total_pit_stops"] = 0
        if isinstance(self.pit_stops_df, pd.DataFrame) and not self.pit_stops_df.empty:
            p = self.pit_stops_df[self.pit_stops_df.get("race_id") == race_id]
            if isinstance(p, pd.DataFrame) and not p.empty:
                row["total_pit_stops"] = int(len(p))
                for col, out_name in [
                    ("total_duration", "avg_total_duration"),
                    ("pit_stop_duration", "avg_pit_stop_duration"),
                    ("in_travel_duration", "avg_in_travel_duration"),
                    ("out_travel_duration", "avg_out_travel_duration"),
                    ("positions_gained_lost", "avg_positions_gained_lost"),
                    # Optional columns if present in schema:
                    # ("pit_in_race_time", "avg_pit_in_race_time"),
                    # ("pit_out_race_time", "avg_pit_out_race_time"),
                    # ("box_stop_race_time", "avg_box_stop_race_time"),
                    # ("box_leave_race_time", "avg_box_leave_race_time"),
                ]:
                    if col in p.columns:
                        row[out_name] = _nanmean(p[col])
                        found_any = True

        return row if found_any else None

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
        work = laps.copy()
        if "Number" not in work.columns or "lap_speed" not in work.columns or "Lap" not in work.columns:
            return
        work["driver_number"] = work["Number"].astype(str)
        work["lap_speed"] = pd.to_numeric(work["lap_speed"], errors="coerce")
        work["Lap"] = pd.to_numeric(work["Lap"], errors="coerce").astype("Int64")
        work["driver_id"] = work["driver_number"].map(map_num_to_id)
        work = work.dropna(subset=["driver_id", "Lap", "lap_speed"])
        if work.empty:
            return
        work["lap_speed_max"] = work.groupby("Lap")["lap_speed"].transform("max")
        work["lap_speed_rank"] = work.groupby("Lap")["lap_speed"].rank(ascending=False, method="min")
        mine = work[work["driver_id"] == self.driver_id]
        if mine.empty:
            return
        leader_laps = int((mine["lap_speed"] == mine["lap_speed_max"]).sum())
        avg_rank = float(mine["lap_speed_rank"].mean())
        total_race_laps = int(work["Lap"].max()) if work["Lap"].notna().any() else None
        laps_completed = int(mine["Lap"].count())
        laps_pct = (laps_completed / total_race_laps) if total_race_laps and total_race_laps > 0 else None
        summary = pd.DataFrame([{
            "race_id": race_id,
            "leader_laps": leader_laps,
            "avg_speed_rank": avg_rank,
            "laps_completed_pct": laps_pct
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
        work = pit.copy()
        work["clean_driver"] = work["Driver"].apply(_normalize_name)
        work["driver_id"] = work["clean_driver"].map(name_to_id)

        # car_number: prefer mapping from results
        if name_to_num is not None:
            work["car_number"] = work["clean_driver"].map(name_to_num).astype("string")
        # manufacturer: prefer pit's Manufacturer, else fallback to results
        if "Manufacturer" in work.columns:
            work["manufacturer"] = work["Manufacturer"]
        elif name_to_man is not None:
            work["manufacturer"] = work["clean_driver"].map(name_to_man)

        mine = work[work["driver_id"] == self.driver_id].copy()
        if mine.empty:
            return

        mine["race_id"] = race_id
        # Ensure consistent types
        if "car_number" in mine.columns:
            mine["car_number"] = mine["car_number"].astype("string")
        self.pit_stops_df = pd.concat([self.pit_stops_df, mine], ignore_index=True) if not self.pit_stops_df.empty else mine

    def total_races(self) -> int:
        race_count = len(self.results_rows)
        return race_count
        
    
    def compute_averages(self) -> None:
        parts = []
        if not self.stats_df.empty:
            parts.append(self.stats_df.select_dtypes(include=["number"]))
        if not self.adv_stats_df.empty:
            parts.append(self.adv_stats_df.select_dtypes(include=["number"]))
        if not parts:
            self.averages = pd.Series(dtype="float64")
            return

        merged = pd.concat(parts, axis=1)
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
                self.averages["avg_lap_speed_rank"] = _nanmean(self.lap_speed_summary["avg_speed_rank"])
            if "laps_completed_pct" in self.lap_speed_summary.columns:
                self.averages["avg_laps_completed_pct"] = _nanmean(self.lap_speed_summary["laps_completed_pct"])

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

            work = pit.copy()
            work["driver_id"] = work["Driver"].map(name_to_id)
            work = work[work["driver_id"] == driver_id].copy()
            if work.empty:
                continue
            work["race_id"] = rid
            work["driver_name"] = work["Driver"]
            if name_to_num is not None:
                work["car_number"] = work["Driver"].map(name_to_num).astype("string")
            if "Manufacturer" in work.columns:
                work["manufacturer"] = work["Manufacturer"]
            elif name_to_man is not None:
                work["manufacturer"] = work["Driver"].map(name_to_man)
            rows.append(work)
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