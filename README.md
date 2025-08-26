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

Columns for each dataframe are below

- Schedule
  - schedule = Schedule(year, series_id)
  - schedule.data
- Race
  - race = Race(year, series_id, race_id, reload=False)
  - race.telemetry.lap_times
  - race.telemetry.pit_stops
  - race.events
  - race.results  # e.g., stage_1, etc. (when present)
- Drivers
  - dd = DriversData.build(year, series_id, use_cache_only=False)
  - dd.to_dataframe()
  - dd.race_dataframe(race_id)
  - dd.driver_races(driver_id)

## Documentation


Series IDs:
1 - Cup
2 - Xfinity
3 - Trucks

# Data output examples

schedule


race_id	series_id	race_season	race_name	race_type_id	restrictor_plate	track_id	track_name	date_scheduled	race_date	...	inspection_complete	playoff_round	is_qualifying_race	qualifying_race_no	qualifying_race_id	has_qualifying	winner_driver_id	pole_winner_laptime	scheduled_at	track_type
3	5546	1	2025	DAYTONA 500	1	True	105	Daytona International Speedway	2025-02-16T14:30:00	2025-02-16T14:30:00	...	True	0	False	0	-1	False	4184.0	None	2025-02-16 14:30:00+00:00	superspeedway
4	5547	1	2025	Ambetter Health 400	1	True	111	Atlanta Motor Speedway	2025-02-23T15:00:00	2025-02-23T15:00:00	...	True	0	False	0	-1	False	4153.0	None	2025-02-23 15:00:00+00:00	intermediate
5	5551	1	2025	EchoPark Automotive Grand Prix	1	False	214	Circuit of The Americas	2025-03-02T15:30:00	2025-03-02T15:30:00	...	True	0	False	0	-1	False	4153.0	None	2025-03-02 15:30:00+00:00	road course
6	5549	1	2025	Shriners Children's 500	1	False	84	Phoenix Raceway	2025-03-09T15:30:00	2025-03-09T15:30:00	...	True	0	False	0	-1	False	4153.0	None	2025-03-09 15:30:00+00:00	short track
4 rows × 48 columns

track_type
intermediate     14
short track       9
superspeedway     7
road course       6
Name: count, dtype: int64
cache_dir: .cache format: parquet
Reading from Cache for 2025-1-5572
Fetching Data for 2025-1-5572
Reading from Cache for 2025-1-5577
Fetching Data for 2025-1-5577
Reading from Cache for 2025-1-5566
Fetching Data for 2025-1-5566
Reading from Cache for 2025-1-5571
Fetching Data for 2025-1-5571
Reading from Cache for 2025-1-5556
Fetching Data for 2025-1-5556
Reading from Cache for 2025-1-5565
Fetching Data for 2025-1-5565
Reading from Cache for 2025-1-5569
Fetching Data for 2025-1-5569
Reading from Cache for 2025-1-5576
Fetching Data for 2025-1-5576
Reading from Cache for 2025-1-5570
Fetching Data for 2025-1-5570
Reading from Cache for 2025-1-5552
Fetching Data for 2025-1-5552
Reading from Cache for 2025-1-5573
Fetching Data for 2025-1-5573
Reading from Cache for 2025-1-5568
Fetching Data for 2025-1-5568
Reading from Cache for 2025-1-5563
...
Reading from Cache for 2025-1-5544
Fetching Data for 2025-1-5544
Reading from Cache for 2025-1-5543
Fetching Data for 2025-1-5543
Output is truncated. View as a scrollable element or open in a text editor. Adjust cell output settings...
driver_id	driver_name	team	car_number	manufacturer	race_id	finishing_position	starting_position	laps_completed	points	...	avg_lap_speed	fastest_lap	total_laps	leader_laps	avg_speed_rank	total_pit_stops	avg_pit_time	norm_speed	stage3_position	stage3_points
1045	3873	Austin Dillon	Richard Childress Racing	3	Chevrolet	5543	0	24	0	0	...	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN
1046	4045	Alex Bowman	Hendrick Motorsports	48	Chevrolet	5543	19	19	199	0	...	57.632648	62.215	199.0	2.0	15.427136	NaN	NaN	0.241716	NaN	NaN
1047	4023	Ryan Blaney	Team Penske	12	Ford	5543	2	23	200	0	...	58.296585	62.150	200.0	34.0	7.995000	NaN	NaN	0.696177	NaN	NaN
1048	3859	Joey Logano	Team Penske	22	Ford	5543	4	7	200	0	...	58.319195	62.487	200.0	7.0	8.645000	NaN	NaN	0.711653	NaN	NaN
1049	4180	Austin Cindric	Team Penske	2	Ford	5543	7	16	200	0	...	58.061760	62.297	200.0	2.0	11.070000	NaN	NaN	0.535441	NaN	NaN
1050	4030	Kyle Larson	Hendrick Motorsports	5	Chevrolet	5543	17	21	199	0	...	57.784206	61.992	199.0	2.0	13.628141	NaN	NaN	0.345456	NaN	NaN
1051	4113	Daniel Suarez	Trackhouse Racing	99	Chevrolet	5543	22	18	198	0	...	57.531040	62.232	198.0	0.0	16.469697	NaN	NaN	0.172166	NaN	NaN
1052	4123	Josh Berry	Wood Brothers Racing	21	Ford	5543	13	22	199	0	...	57.668749	61.830	199.0	2.0	14.658291	NaN	NaN	0.266427	NaN	NaN
1053	1816	Brad Keselowski	RFK Racing	6	Ford	5543	21	5	199	0	...	58.020462	63.012	199.0	5.0	12.120603	NaN	NaN	0.507172	NaN	NaN
1054	1361	Denny Hamlin	Joe Gibbs Racing	11	Toyota	5543	3	3	200	0	...	58.602875	63.273	200.0	34.0	6.695000	NaN	NaN	0.905831	NaN	NaN
1055	4272	Zane Smith	Front Row Motorsports	38	Ford	5543	0	27	0	0	...	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN
1056	4184	William Byron	Hendrick Motorsports	24	Chevrolet	5543	18	11	199	0	...	57.404075	62.387	199.0	1.0	15.874372	NaN	NaN	0.085259	NaN	NaN
1057	4228	Chase Briscoe	Joe Gibbs Racing	19	Toyota	5543	23	6	120	0	...	57.545717	62.941	120.0	7.0	9.725000	NaN	NaN	0.182212	NaN	NaN
1058	4469	Shane Van Gisbergen	Trackhouse Racing	88	Chevrolet	5543	9	10	200	0	...	58.113740	62.465	200.0	3.0	10.880000	NaN	NaN	0.571021	NaN	NaN
1059	4326	Carson Hocevar	Spire Motorsports	77	Chevrolet	5543	16	15	199	0	...	58.049437	62.344	199.0	6.0	11.100503	NaN	NaN	0.527006	NaN	NaN
1060	454	Kyle Busch	Richard Childress Racing	8	Chevrolet	5543	15	13	199	0	...	57.279518	62.073	199.0	8.0	14.462312	NaN	NaN	0.000000	NaN	NaN
1061	3832	Michael McDowell	Spire Motorsports	71	Chevrolet	5543	0	26	0	0	...	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN
1062	4368	Ty Gibbs	Joe Gibbs Racing	54	Toyota	5543	0	35	0	0	...	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN
1063	4001	Ross Chastain	Trackhouse Racing	1	Chevrolet	5543	6	17	200	0	...	57.910635	61.898	200.0	5.0	12.080000	NaN	NaN	0.431996	NaN	NaN
1064	4013	Ty Dillon	Kaulig Racing	10	Chevrolet	5543	0	30	0	0	...	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN
1065	4153	Christopher Bell	Joe Gibbs Racing	20	Toyota	5543	12	8	199	0	...	58.193296	62.797	199.0	5.0	10.703518	NaN	NaN	0.625477	NaN	NaN
1066	3774	AJ Allmendinger	Kaulig Racing	16	Chevrolet	5543	0	36	0	0	...	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN
1067	3888	Ricky Stenhouse Jr.	HYAK Motorsports	47	Chevrolet	5543	0	28	0	0	...	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN
1068	4104	Cole Custer	Haas Factory Team	41	Ford	5543	0	33	0	0	...	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN
1069	4231	Todd Gilliland	Front Row Motorsports	34	Ford	5543	14	20	199	0	...	57.659045	62.099	199.0	2.0	14.492462	NaN	NaN	0.259785	NaN	NaN
1070	4059	Erik Jones	Legacy Motor Club	43	Toyota	5543	0	37	0	0	...	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN
1071	4224	Noah Gragson	Front Row Motorsports	4	Ford	5543	20	9	199	0	...	57.329980	62.596	199.0	0.0	16.567839	NaN	NaN	0.034541	NaN	NaN
1072	4025	Bubba Wallace	23XI Racing	23	Toyota	5543	5	14	200	0	...	58.264225	62.496	200.0	3.0	9.015000	NaN	NaN	0.674027	NaN	NaN
1073	3989	Chris Buescher	RFK Racing	17	Ford	5543	10	2	200	0	...	58.367015	63.247	200.0	9.0	9.770000	NaN	NaN	0.744386	NaN	NaN
1074	4269	Riley Herbst	23XI Racing	35	Toyota	5543	0	38	0	0	...	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN
1075	4125	Cody Ware	Rick Ware Racing	51	Ford	5543	0	32	0	0	...	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN
1076	4065	Tyler Reddick	23XI Racing	45	Toyota	5543	8	4	200	0	...	58.385490	63.038	200.0	15.0	8.960000	NaN	NaN	0.757032	NaN	NaN
1077	4070	Ryan Preece	RFK Racing	60	Ford	5543	11	12	200	0	...	57.837185	62.232	200.0	0.0	14.280000	NaN	NaN	0.381720	NaN	NaN
1078	4092	John Hunter Nemechek	Legacy Motor Club	42	Toyota	5543	0	25	0	0	...	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN
1079	4172	Justin Haley	Spire Motorsports	7	Chevrolet	5543	0	29	0	0	...	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN	NaN
1080	4062	Chase Elliott	Hendrick Motorsports	9	Chevrolet	5543	1	1	200	0	...	58.740450	63.555	200.0	50.0	4.995000	NaN	NaN	1.000000	NaN	NaN
36 rows × 54 columns

/tmp/ipykernel_9923/656548108.py:27: UserWarning: set_ticklabels() should only be used with a fixed number of ticks, i.e. after set_ticks() or using a FixedLocator.
  fig2.set_xticklabels(summary2025_S1['driver_name'], rotation=90,fontsize=16)
<Figure size 1600x1000 with 0 Axes>
+----+-----------+-------------+---------------+--------------------------------+----------------+--------------------+------------+--------------------------------+---------------------+---------------------+---------------------+---------------------+----------------------+-------------------+------------------+---------------+----------------+----------------+----------------+---------------------------+-------------------------+---------------------+--------------------------+---------------------+----------------------+--------------------------+-----------------+-------------------+---------------------+--------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------+---------------+---------------------+--------------------------+-------------------------------+------------------+-----------------------+-----------------+----------------------+----------------------+----------------------+------------------+--------------------+-----------------------+---------------------------+---------------+
|    |   race_id |   series_id |   race_season | race_name                      |   race_type_id | restrictor_plate   |   track_id | track_name                     | date_scheduled      | race_date           | qualifying_date     | tunein_date         |   scheduled_distance |   actual_distance |   scheduled_laps |   actual_laps |   stage_1_laps |   stage_2_laps |   stage_3_laps |   number_of_cars_in_field |   pole_winner_driver_id |   pole_winner_speed |   number_of_lead_changes |   number_of_leaders |   number_of_cautions |   number_of_caution_laps |   average_speed | total_race_time   | margin_of_victory   |   race_purse | race_comments                                                                                                                                                                                                                                                                                                                                                              |   attendance | infractions   | radio_broadcaster   | television_broadcaster   | satellite_radio_broadcaster   |   master_race_id | inspection_complete   |   playoff_round | is_qualifying_race   |   qualifying_race_no |   qualifying_race_id | has_qualifying   |   winner_driver_id | pole_winner_laptime   | scheduled_at              | track_type    |
+====+===========+=============+===============+================================+================+====================+============+================================+=====================+=====================+=====================+=====================+======================+===================+==================+===============+================+================+================+===========================+=========================+=====================+==========================+=====================+======================+==========================+=================+===================+=====================+==============+============================================================================================================================================================================================================================================================================================================================================================================+==============+===============+=====================+==========================+===============================+==================+=======================+=================+======================+======================+======================+==================+====================+=======================+===========================+===============+
|  3 |      5546 |           1 |          2025 | DAYTONA 500                    |              1 | True               |        105 | Daytona International Speedway | 2025-02-16T14:30:00 | 2025-02-16T14:30:00 | 2025-02-16T13:30:00 | 2025-02-16T13:30:00 |                500   |            502.5  |              200 |           201 |             65 |             65 |             71 |                        41 |                    4228 |             182.745 |                       56 |                  15 |                    8 |                       47 |         129.159 | 3:53:26           | .113                |            0 | William Byron has won the DAYTONA 500 at Daytona International Speedway, his 14th victory in the NASCAR Xfinity Series. Prior to the start of the race, the following vehicle(s) dropped to the rear of the field under penalty for the reason(s) indicated: No. 91 (engine change), Nos. 5, 6, 7, 35, 48, 54, 88, 99 (backup car), No. 47 (multiple inspection failures). |            0 | []            | MRN                 | FOX                      | SIRIUSXM                      |              385 | True                  |               0 | False                |                    0 |                   -1 | False            |               4184 |                       | 2025-02-16 14:30:00+00:00 | superspeedway |
+----+-----------+-------------+---------------+--------------------------------+----------------+--------------------+------------+--------------------------------+---------------------+---------------------+---------------------+---------------------+----------------------+-------------------+------------------+---------------+----------------+----------------+----------------+---------------------------+-------------------------+---------------------+--------------------------+---------------------+----------------------+--------------------------+-----------------+-------------------+---------------------+--------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------+---------------+---------------------+--------------------------+-------------------------------+------------------+-----------------------+-----------------+----------------------+----------------------+----------------------+------------------+--------------------+-----------------------+---------------------------+---------------+
|  4 |      5547 |           1 |          2025 | Ambetter Health 400            |              1 | True               |        111 | Atlanta Motor Speedway         | 2025-02-23T15:00:00 | 2025-02-23T15:00:00 | 2025-02-23T15:00:00 | 2025-02-23T15:00:00 |                400.4 |            409.64 |              260 |           266 |             60 |            100 |            106 |                        39 |                    4023 |             179.371 |                       50 |                  15 |                   11 |                       63 |         118.384 | 3:27:37           | Under Caution       |            0 | Christopher Bell has won the Ambetter Health 400 at Atlanta Motor Speedway, his 10th victory in the NASCAR Cup Series. Prior to the start of the race, no vehicle(s) dropped to the rear of the field under penalty.                                                                                                                                                       |            0 | []            | PRN                 | FOX                      | SIRIUSXM                      |             3335 | True                  |               0 | False                |                    0 |                   -1 | False            |               4153 |                       | 2025-02-23 15:00:00+00:00 | intermediate  |
+----+-----------+-------------+---------------+--------------------------------+----------------+--------------------+------------+--------------------------------+---------------------+---------------------+---------------------+---------------------+----------------------+-------------------+------------------+---------------+----------------+----------------+----------------+---------------------------+-------------------------+---------------------+--------------------------+---------------------+----------------------+--------------------------+-----------------+-------------------+---------------------+--------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------+---------------+---------------------+--------------------------+-------------------------------+------------------+-----------------------+-----------------+----------------------+----------------------+----------------------+------------------+--------------------+-----------------------+---------------------------+---------------+
|  5 |      5551 |           1 |          2025 | EchoPark Automotive Grand Prix |              1 | False              |        214 | Circuit of The Americas        | 2025-03-02T15:30:00 | 2025-03-02T15:30:00 | 2025-03-02T14:30:00 | 2025-03-02T15:30:00 |                228   |            228    |               95 |            95 |             20 |             25 |             50 |                        37 |                    4065 |              88.095 |                       20 |                   9 |                    4 |                       15 |          73.025 | 3:07:20           | 0.433               |            0 | Christopher Bell won the EchoPark Automotive Grand Prix at Circuit of the Americas, his 11th NASCAR Cup Series victory. Prior to the green flag to start the race, the following car dropped to the rear for the reason indicated: No. 38 (unapproved adjustments).                                                                                                        |            0 | []            | PRN                 | FOX                      | SIRIUSXM                      |             5033 | True                  |               0 | False                |                    0 |                   -1 | False            |               4153 |                       | 2025-03-02 15:30:00+00:00 | road course   |
+----+-----------+-------------+---------------+--------------------------------+----------------+--------------------+------------+--------------------------------+---------------------+---------------------+---------------------+---------------------+----------------------+-------------------+------------------+---------------+----------------+----------------+----------------+---------------------------+-------------------------+---------------------+--------------------------+---------------------+----------------------+--------------------------+-----------------+-------------------+---------------------+--------------+----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+--------------+---------------+---------------------+--------------------------+-------------------------------+------------------+-----------------------+-----------------+----------------------+----------------------+----------------------+------------------+--------------------+-----------------------+---------------------------+---------------+

Race Laps:

```python
race.telemetry.lap_times
```

+------+----------------+--------------+----------------+-------+---------------------------+-------------+------------+-------------+
|      | driver_name    |   car_number | manufacturer   |   Lap | lap_time                  |   lap_speed |   position |   driver_id |
+======+================+==============+================+=======+===========================+=============+============+=============+
| 1964 | Kyle Busch     |            8 | Chv            |    53 | 0 days 00:00:00.000000076 |     115.953 |         25 |         454 |
+------+----------------+--------------+----------------+-------+---------------------------+-------------+------------+-------------+
| 1472 | Zane Smith     |           38 | Frd            |    16 | 0 days 00:00:00.000000076 |     115.949 |         24 |        4272 |
+------+----------------+--------------+----------------+-------+---------------------------+-------------+------------+-------------+
| 1382 | Austin Cindric |            2 | Frd            |    17 | 0 days 00:00:00.000000098 |      89.466 |         29 |        4180 |
+------+----------------+--------------+----------------+-------+---------------------------+-------------+------------+-------------+

Pit Stops:

```python
race.telemetry.pit_stops
```
+----+---------------------+-------+----------------+----------------------+-----------------------+--------------------+---------------------+------------------+----------------------+-----------------------+---------------------+----------------------+-----------------------+-----------------+---------------------------+--------------------------+----------------------------+---------------------------+---------------------+-----------------+---------------+----------------+-------------------------+-------------+--------------+
|    | driver_name         |   lap | manufacturer   |   pit_in_flag_status |   pit_out_flag_status |   pit_in_race_time |   pit_out_race_time |   total_duration |   box_stop_race_time |   box_leave_race_time |   pit_stop_duration |   in_travel_duration |   out_travel_duration | pit_stop_type   | left_front_tire_changed   | left_rear_tire_changed   | right_front_tire_changed   | right_rear_tire_changed   |   previous_lap_time |   next_lap_time |   pit_in_rank |   pit_out_rank |   positions_gained_lost |   driver_id |   car_number |
+====+=====================+=======+================+======================+=======================+====================+=====================+==================+======================+=======================+=====================+======================+=======================+=================+===========================+==========================+============================+===========================+=====================+=================+===============+================+=========================+=============+==============+
|  0 | Ryan Blaney         |     0 | Frd            |                    8 |                     8 |                  0 |                   0 |           25.04  |                   -1 |                    -1 |                  -1 |                   -1 |                    -1 | OTHER           | False                     | False                    | False                      | False                     |                   0 |               0 |             0 |              0 |                       0 |        4023 |           12 |
+----+---------------------+-------+----------------+----------------------+-----------------------+--------------------+---------------------+------------------+----------------------+-----------------------+---------------------+----------------------+-----------------------+-----------------+---------------------------+--------------------------+----------------------------+---------------------------+---------------------+-----------------+---------------+----------------+-------------------------+-------------+--------------+
|  1 | Shane Van Gisbergen |     0 | Chv            |                    8 |                     8 |                  0 |                   0 |           24.852 |                   -1 |                    -1 |                  -1 |                   -1 |                    -1 | OTHER           | False                     | False                    | False                      | False                     |                   0 |               0 |             0 |              0 |                       0 |        4469 |           88 |
+----+---------------------+-------+----------------+----------------------+-----------------------+--------------------+---------------------+------------------+----------------------+-----------------------+---------------------+----------------------+-----------------------+-----------------+---------------------------+--------------------------+----------------------------+---------------------------+---------------------+-----------------+---------------+----------------+-------------------------+-------------+--------------+
|  2 | Chase Briscoe       |     0 | Tyt            |                    8 |                     8 |                  0 |                   0 |           25.101 |                   -1 |                    -1 |                  -1 |                   -1 |                    -1 | OTHER           | False                     | False                    | False                      | False                     |                   0 |               0 |             0 |              0 |                       0 |        4228 |           19 |
+----+---------------------+-------+----------------+----------------------+-----------------------+--------------------+---------------------+------------------+----------------------+-----------------------+---------------------+----------------------+-----------------------+-----------------+---------------------------+--------------------------+----------------------------+---------------------------+---------------------+-----------------+---------------+----------------+-------------------------+-------------+--------------+

Race Events:

```python
race.telemetry.events

```

|     | Lap | Flag_State | Flag    | note                                              | driver_ids                                        |
| --- | --- | ---------- | ------- | ------------------------------------------------- | ------------------------------------------------- |
| 0   | 0   | 8          | Warm Up | To the rear: #5, #6, #7, #35, #48, #54, #88, ...  | [4030, 1816, 4172, 4269, 4045, 4368, 4469, 411... |
| 1   | 1   | 1          | Green   | #19 leads the field to the green on the inside... | [4228, 4180, 4228]                                |
| 2   | 3   | 1          | Green   | #19, #23 and #2 get single file in front of th... | [4228, 4025, 4180]                                |
| 3   | 5   | 1          | Green   | #77 reports fuel pressure issues and loses the... | [4326]                                            |

Race Driver Data

```python
race.telemetry.events

```

+----+-------------+---------------------+------------------+----------------+------------+--------------------+---------------------+-----------------+------------------+----------------+---------------------+----------------+---------------------+------------------+-------------+--------------+-------------+--------+----------+
|    |   driver_id | driver_name         |   start_position |   mid_position |   position |   closing_position |   closing_laps_diff |   best_position |   worst_position |   avg_position |   passes_green_flag |   passing_diff |   passed_green_flag |   quality_passes |   fast_laps |   top15_laps |   lead_laps |   laps |   rating |
+====+=============+=====================+==================+================+============+====================+=====================+=================+==================+================+=====================+================+=====================+==================+=============+==============+=============+========+==========+
|  0 |        4469 | Shane Van Gisbergen |                2 |              8 |          1 |                  1 |                   0 |               1 |               23 |           4.04 |                  60 |            -14 |                  74 |               29 |          18 |           84 |          38 |     90 |   143.72 |
+----+-------------+---------------------+------------------+----------------+------------+--------------------+---------------------+-----------------+------------------+----------------+---------------------+----------------+---------------------+------------------+-------------+--------------+-------------+--------+----------+
|  1 |        4153 | Christopher Bell    |                9 |              4 |          2 |                  4 |                   2 |               2 |               32 |           8.87 |                  81 |              5 |                  76 |               28 |           7 |           80 |           0 |     90 |   113.22 |
+----+-------------+---------------------+------------------+----------------+------------+--------------------+---------------------+-----------------+------------------+----------------+---------------------+----------------+---------------------+------------------+-------------+--------------+-------------+--------+----------+
|  2 |        3989 | Chris Buescher      |               12 |             10 |          3 |                  2 |                  -1 |               1 |               36 |          11.06 |                  75 |             18 |                  57 |               25 |           4 |           68 |           5 |     90 |   105.11 |
+----+-------------+---------------------+------------------+----------------+------------+--------------------+---------------------+-----------------+------------------+----------------+---------------------+----------------+---------------------+------------------+-------------+--------------+-------------+--------+----------+

## TODO

| #   | Item                              | Progress                    | Notes                                                                   |
| --- | --------------------------------- | --------------------------- | ----------------------------------------------------------------------- |
| 1   | Add Caching                       | ![90%](https://progress-bar.xyz/90) | Works. Needs to prevent writing when no data                            |
| 2   | Add Driver Stats                  | ![100%](https://progress-bar.xyz/100) | Collected for stats. Works but is inefficient. Names need to be in sync |
| 3   | Add Lap Stats                     | ![80%](https://progress-bar.xyz/80) | Laps exist within Race. Will add functions to analyze                   |
| 3   | Add Pit Stats                     | ![70%](https://progress-bar.xyz/70) | Pits exist within Race and Driver. Will add functions to analyze        |
| 4   | Add tests                         | ![0%](https://progress-bar.xyz/0) | No work done                                                            |
| 5   | Add Laps from Practice/Qualifying | ![0%](https://progress-bar.xyz/0)  | This end point may not exist                                            |
