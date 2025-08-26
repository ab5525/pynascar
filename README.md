## PyNASCAR

###### This is obviously not associated with NASCAR and is an unofficial project

## Overview

`pynascar` is a Python package for nascar race data acquisition and hopefully analysis

## Installation

Install via pip

```bash
pip install pynascar
```

updates will be made regularly until all public API endpoints are hit


## Quickstart

You can use this package to obtain data from the schedule or from any existing or live race including lap times, pit stop laps and times, all in race flags and all race control messages.

```python
from pynascar import Schedule, Race, set_options, get_settings
from pynascar.driver import DriversData

# Enable local caching for faster repeated runs
set_options(cache_enabled=True, cache_dir=".cache/", df_format="parquet")
print(get_settings())  # verify settings

# Series: 1=Cup, 2=Xfinity, 3=Trucks
year = 2025
series_id = 1
race_id = 5577  # replace with a valid race id

# Schedules
schedule = Schedule(year, series_id)
schedule.data.head()

# Race data (use reload=True to force network fetch even if cached)
race = Race(year, series_id, race_id, reload=True)
race.telemetry.lap_times.head()
race.telemetry.pit_stops.head()
race.events.head()
# Example result subset (if available):
# race.results.stage_1

# Driver season aggregates
dd = DriversData.build(2025, 1, use_cache_only=False)
summary = dd.to_dataframe()
summary.sort_values("season_avg_position").head()
```

## Available Classes

Ill replace this with proper documentation if anyone cares. Just leave an issue. 

### Schedule
```python
schedule = Schedule(year, series_id)
```
```
# DataFrames:
schedule.data - Complete race schedule
  Columns: race_id, race_name, race_date, track_name, series_id, winner_driver_id, scheduled_at, track_type, plus other race metadata

# Methods:
schedule.get_finished_races() - Completed races DataFrame
schedule.get_remaining_races() - Upcoming races DataFrame  
schedule.most_recent_race() - Single row with latest completed race
schedule.next_race() - Single row with next scheduled race
```

### Race
```python
race = Race(year, series_id, race_id, reload=False)
```
```
# Results DataFrames:
race.results.results - Main race results
  Columns: driver_id, driver_name, car_number, manufacturer, sponsor, team, team_id, qualifying_order, qualifying_position, qualifying_speed, starting_position, finishing_position, laps_completed, points, playoff_points

race.results.stage_1 - Stage 1 results (when available)
race.results.stage_2 - Stage 2 results (when available)
race.results.stage_3 - Stage 3 results (when available)
  Columns: driver_id, driver_name, car_number, stage_number, position, stage_points

race.results.cautions - Caution periods
  Columns: start_lap, end_lap, caution_type, comment, flag_state

race.results.lead_changes - Race leaders by lap
  Columns: start_lap, end_lap, driver_name, car_number

race.results.practice - Practice session results
  Columns: driver_id, driver_name, manufacturer, practice_name, position, lap_time, speed, total_laps, delta_to_leader, practice_number

race.results.qualifying - Qualifying results
  Columns: driver_id, driver_name, manufacturer, qualifying_name, position, lap_time, speed, total_laps, delta_to_leader, qualifying_number

# Telemetry DataFrames:
race.telemetry.lap_times - Lap-by-lap timing data
  Columns: driver_name, car_number, manufacturer, Lap, lap_time, lap_speed, position, driver_id

race.telemetry.pit_stops - Pit stop data
  Columns: driver_name, lap, manufacturer, pit_in_flag_status, pit_out_flag_status, pit_in_race_time, pit_out_race_time, total_duration, box_stop_race_time, box_leave_race_time, pit_stop_duration, in_travel_duration, out_travel_duration, pit_stop_type, left_front_tire_changed, left_rear_tire_changed, right_front_tire_changed, right_rear_tire_changed, previous_lap_time, next_lap_time, pit_in_rank, pit_out_rank, positions_gained_lost, driver_id, car_number

race.telemetry.events - Race events and flags
  Columns: Lap, Flag_State, Flag, note, driver_ids

# Driver Statistics DataFrames:
race.driver_data.drivers - Basic driver statistics
  Columns: driver_id, driver_name, start_position, mid_position, position, closing_position, closing_laps_diff, best_position, worst_position, avg_position, passes_green_flag, passing_diff, passed_green_flag, quality_passes, fast_laps, top15_laps, lead_laps, laps, rating

race.driver_data.driver_stats_advanced - Advanced driver statistics
  Columns: driver_id, driver_name, car_number, manufacturer, sponsor_name, best_lap, best_lap_speed, best_lap_time, laps_position_improved, fastest_laps_run, passes_made, times_passed, passing_differential, quality_passes, position_differential_last_10_percent
```

### DriversData
```python
dd = DriversData.build(year, series_id, use_cache_only=False)
```
```
# DataFrames:
dd.to_dataframe() - Season summary for all drivers
  Columns: driver_id, driver_name, team, car_number, manufacturer, total_races, total_points, total_playoff_points, wins, top5s, top10s, total_leader_laps, total_passes_green_flag, total_passed_green_flag, plus averages of all race metrics

dd.race_dataframe(race_id) - Single race data for all drivers
  Columns: All race metrics for specific race including driver_id, driver_name, team, car_number, manufacturer, race_id, finishing_position, starting_position, points, stage_points, avg_lap_speed, fastest_lap, pit_stops, etc.

dd.all_races_dataframe() - All races combined for all drivers
  Columns: Same as race_dataframe() but for all races in the season

dd.driver_season_dataframe(driver_id) - All races for a specific driver
  Columns: Same as race_dataframe() but filtered to one driver across all races

dd.driver_pit_stops(driver_id, race_id=None) - Pit stops for specific driver
  Columns: Same as race.telemetry.pit_stops but filtered to specific driver, optionally by race

# Individual Driver Access:
dd.get_driver(driver_id) - Returns Driver object with race_data dict and pit_stops_df
```


## Documentation

Series IDs:
1 - Cup
2 - Xfinity
3 - Trucks


## Data Output Examples

### Schedule
Example output:

| race_id | series_id | race_season | race_name                      | track_name                        | date_scheduled        | track_type     |
|---------|-----------|-------------|--------------------------------|-----------------------------------|-----------------------|----------------|
| 5546    | 1         | 2025        | DAYTONA 500                    | Daytona International Speedway    | 2025-02-16T14:30:00  | superspeedway |
| 5547    | 1         | 2025        | Ambetter Health 400            | Atlanta Motor Speedway            | 2025-02-23T15:00:00  | intermediate  |
| 5551    | 1         | 2025        | EchoPark Automotive Grand Prix | Circuit of The Americas           | 2025-03-02T15:30:00  | road course   |


---

### Race Laps

| driver_name   | car_number | manufacturer | lap | lap_time | lap_speed | position |
|---------------|------------|--------------|-----|----------|-----------|----------|
| Kyle Busch    | 8          | Chv          | 53  | 26.06s   | 115.95    | 25       |
| Zane Smith    | 38         | Frd          | 16  | 26.07s   | 115.94    | 24       |
| Austin Cindric| 2          | Frd          | 17  | 29.31s   |  89.47    | 29       |

---

### Pit Stops

| driver_name         | lap | manufacturer | total_duration | pit_stop_type | car_number |
|---------------------|-----|--------------|----------------|---------------|------------|
| Ryan Blaney         | 0   | Frd          | 25.04s         | OTHER         | 12         |
| Shane Van Gisbergen | 0   | Chv          | 24.85s         | OTHER         | 88         |
| Chase Briscoe       | 0   | Tyt          | 25.10s         | OTHER         | 19         |

---

### Race Events

| lap | flag_state | flag    | note                                        |
|-----|------------|---------|---------------------------------------------|
| 0   | 8          | Warm Up | To the rear: #5, #6, #7, #35, #48, ...     |
| 1   | 1          | Green   | #19 leads the field to the green...         |
| 3   | 1          | Green   | #19, #23, #2 get single file in front...    |
| 5   | 1          | Green   | #77 reports fuel pressure issues...         |

---

### Race Driver Data

| driver_name          | start_position | avg_position | best_position | worst_position | fast_laps | lead_laps | rating |
|----------------------|----------------|--------------|---------------|----------------|-----------|-----------|--------|
| Shane Van Gisbergen  | 2              | 4.04         | 1             | 23             | 18        | 38        | 143.72 |

---

## Visualizations (Examples)

Below are example plots that can be generated with the package an example of that is in the examples folder:

- **Average Speed per Driver**
![Plotlot](figures/2025_Season_Average_Lap_Speed_Overall.png)

- **Average Position Difference**
![Plot](figures/2025_Average_Closing_Laps_Passing_Difference.png)

- **Quality Passes per race**
![Placeholder plot](figures/2025_Average_Quality_Passes_Per_Race.png)

## TODO

| #   | Item                              | Progress                    | Notes                                                                   |
| --- | --------------------------------- | --------------------------- | ----------------------------------------------------------------------- |
| 1   | Add Caching                       | ![90%](https://progress-bar.xyz/90) | Works. Needs to prevent writing when no data                            |
| 2   | Add Driver Stats                  | ![100%](https://progress-bar.xyz/100) | Collected for stats. Works but is inefficient. Names need to be in sync |
| 3   | Add Lap Stats                     | ![80%](https://progress-bar.xyz/80) | Laps exist within Race. Will add functions to analyze                   |
| 3   | Add Pit Stats                     | ![70%](https://progress-bar.xyz/70) | Pits exist within Race and Driver. Will add functions to analyze        |
| 4   | Add tests                         | ![0%](https://progress-bar.xyz/0) | No work done                                                            |
| 5   | Add Laps from Practice/Qualifying | ![0%](https://progress-bar.xyz/0)  | This end point may not exist                                            |

## Acknowledgements

A few redditors found and plotted some of the routes a few years ago which is where i started with this:

https://github.com/ooohfascinating/NascarApi