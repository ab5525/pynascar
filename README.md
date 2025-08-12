## PyNASCAR

###### This is obviously not associated with NASCAR and is an unofficial project

## Overview

`pynascar` is a Python package for nascar race data acquisition. Read the [Full Documentation](https://github.com/ab5525) for all data functions and types.

## Installation

Install via pip

```bash
pip install pynascar
```

updates will be made regularly until all public API endpoints are hit

## Race Data Example:

You can use this package to obtain data from any existing or live race including lap times, pit stop laps and times, all in race flags and all race control messages. The full schedule as well.

```python
from pynascar import Schedule, Race

# Get the schedule for the current year
schedule = Schedule(year= 2025, series_id = 1)

# This function isnt currently added. Will be in v 0.1.1
race_info = schedule.get_most_recent_race()
race_data = Race(year = 2025, series_id = 2, race_id = 5546)


```

## Documentation

coming next

Series IDs:
1 - Cup
2 - Xfinity
3 - Trucks

schedule columns:

```python

Index(['race_id', 'series_id', 'race_season', 'race_name', 'race_type_id',
       'restrictor_plate', 'track_id', 'track_name', 'date_scheduled',
       'race_date', 'qualifying_date', 'tunein_date', 'scheduled_distance',
       'actual_distance', 'scheduled_laps', 'actual_laps', 'stage_1_laps',
       'stage_2_laps', 'stage_3_laps', 'number_of_cars_in_field',
       'pole_winner_driver_id', 'pole_winner_speed', 'number_of_lead_changes',
       'number_of_leaders', 'number_of_cautions', 'number_of_caution_laps',
       'average_speed', 'total_race_time', 'margin_of_victory', 'race_purse',
       'race_comments', 'attendance', 'infractions', 'schedule',
       'radio_broadcaster', 'television_broadcaster',
       'satellite_radio_broadcaster', 'master_race_id', 'inspection_complete',
       'playoff_round', 'is_qualifying_race', 'qualifying_race_no',
       'qualifying_race_id', 'has_qualifying', 'winner_driver_id',
       'pole_winner_laptime'],
      dtype='object')

```

Race Laps:

```python
race_data.laps
```

| 54   | Driver          | Car | Manufacturer | lap | time                      | speed   | Pos |
| ---- | --------------- | --- | ------------ | --- | ------------------------- | ------- | --- |
| 2527 | Daniel Suarez   | 99  | Chv          | 100 | 0 days 00:00:00.000000047 | 189.861 | 13  |
| 1586 | Austin Cindric  | 2   | Frd          | 171 | 0 days 00:00:00.000000046 | 193.861 | 1   |
| 3694 | Justin Haley    | 7   | Chv          | 54  | 0 days 00:00:00.000000047 | 190.010 | 39  |
| 54   | Bubba Wallace   | 23  | Tyt          | 1   | 0 days 00:00:00.000000052 | 172.206 | 3   |
| 4389 | \* Corey LaJoie | 01  | Frd          | 143 | 0 days 00:00:00.000000047 | 188.119 | 31  |
| 2679 | Ty Dillon       | 10  | Chv          | 50  | 0 days 00:00:00.000000047 | 191.152 | 34  |

Race Laps:

```python
race_data.pit_stops
```

| Driver         | Lap | Manufacturer | pit_in_flag_status | pit_out_flag_status | pit_in_race_time | pit_out_race_time | total_duration | box_stop_race_time | box_leave_race_time | ... | pit_stop_type          | left_front_tire_changed | left_rear_tire_changed | right_front_tire_changed | right_rear_tire_changed | previous_lap_time | next_lap_time | pit_in_rank | pit_out_rank | positions_gained_lost | 0   | 1   | 2   | 3   | 4   |
| -------------- | --- | ------------ | ------------------ | ------------------- | ---------------- | ----------------- | -------------- | ------------------ | ------------------- | --- | ---------------------- | ----------------------- | ---------------------- | ------------------------ | ----------------------- | ----------------- | ------------- | ----------- | ------------ | --------------------- | --- | --- | --- | --- | --- |
| William Byron  | 10  | Chv          | 2                  | 2                   | 666.638          | 882.668           | 11614.947      | 676.235            | 12258.555           | ... | OTHER                  | False                   | False                  | False                    | False                   | 0                 | 0             | 1           | 1            | 0                     |
| Austin Cindric | 10  | Frd          | 2                  | 2                   | 668.834          | 885.746           | 11615.829      | 696.015            | 12278.615           | ... | TWO_WHEEL_CHANGE_RIGHT | False                   | False                  | True                     | True                    | 0                 | 0             | 2           | 2            | 0                     |
| Ty Dillon      | 10  | Chv          | 2                  | 2                   | 669.462          | 887.356           | 11616.811      | 688.815            | 12264.695           | ... | OTHER                  | False                   | False                  | False                    | False                   | 0                 | 0             | 3           | 3            | 0                     |
| Chase Briscoe  | 10  | Tyt          | 2                  | 2                   | 670.433          | 889.714           | 11618.198      | 703.315            | 12283.555           | ... | OTHER                  | False                   | False                  | False                    | False                   | 0                 | 0             | 4           | 4            | 0                     |
| Joey Logano    | 10  | Frd          | 2                  | 2                   | 672.424          | 903.406           | 11629.899      | 700.895            | 12294.975           | ... | FOUR_WHEEL_CHANGE      | True                    | True                   | True                     | True                    | 0                 | 0             | 6           | 5            | 1                     |

📋 Copy
Clear
Buy Me a Coffee at ko-fi.com

Race Events:

```python
race_data.events

```

|     | Lap | Flag_State | Flag    | note                                              | driver_ids                                        |
| --- | --- | ---------- | ------- | ------------------------------------------------- | ------------------------------------------------- |
| 0   | 0   | 8          | Warm Up | To the rear: #5, #6, #7, #35, #48, #54, #88, ...  | [4030, 1816, 4172, 4269, 4045, 4368, 4469, 411... |
| 1   | 1   | 1          | Green   | #19 leads the field to the green on the inside... | [4228, 4180, 4228]                                |
| 2   | 3   | 1          | Green   | #19, #23 and #2 get single file in front of th... | [4228, 4025, 4180]                                |
| 3   | 5   | 1          | Green   | #77 reports fuel pressure issues and loses the... | [4326]                                            |
