```python
from pynascar import Schedule, Race, set_options,get_settings
from pynascar.driver import DriversData

import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib import patches as mpatches
from matplotlib import patheffects as pe
import numpy as np

set_options(cache_enabled=True, cache_dir=".cache/", df_format="parquet")

s = get_settings()
print("cache_dir:", s.cache_dir, "format:", s.df_format)

```

## Get the Schedule Data 


```python
# Get the schedule and a count of track types
schedule_2025 = Schedule(2025, 1).data

# Get points races. (Skip clash, duels, allstar)
schedule_2025 = schedule_2025[schedule_2025['race_type_id'] == 1]
display(schedule_2025.head(4))
display(schedule_2025['track_type'].value_counts())

# Isolate intermediate tracks
intermediates_2025 = schedule_2025[schedule_2025['track_type'] == 'intermediate']
short_tracks_2025 = schedule_2025[schedule_2025['track_type'] == 'short track']
super_speedways_2025 = schedule_2025[schedule_2025['track_type'] == 'superspeedway']
rc_2025 = schedule_2025[schedule_2025['track_type'] == 'road course']
```

## Get the Data for 2025

```python
driver_data = DriversData.build(2025, 1, use_cache_only=False, reload_cache=False)
```

## Get data for each driver

```python
# Sorting by min participation (avoid 1 offs). We could do this naturally but im planning to add this function braodly
summary2025_S1 = driver_data.to_dataframe(min_participation=0.4)
summary2025_S1.head()

playoff_drivers = [
  "Kyle Larson",
  "William Byron",
  "Denny Hamlin",
  "Ryan Blaney",
  "Christopher Bell",
  "Shane Van Gisbergen",
  "Chase Elliott",
  "Chase Briscoe",
  "Bubba Wallace",
  "Austin Cindric",
  "Ross Chastain",
  "Joey Logano",
  "Josh Berry",
  "Tyler Reddick",
  "Austin Dillon",
  "Alex Bowman"
]

driver_data.driver_season_dataframe(3873)
race_data = driver_data.all_races_dataframe()
race_data = race_data[race_data['driver_id'].isin(summary2025_S1['driver_id'])]

summary2025_S1['is_playoff'] = summary2025_S1['driver_name'].isin(playoff_drivers)
race_data['is_playoff'] = race_data['driver_name'].isin(playoff_drivers)

# #lets look at different track types
results_intermediate = race_data[race_data['race_id'].isin(intermediates_2025['race_id'])]
results_short = race_data[race_data['race_id'].isin(short_tracks_2025['race_id'])]
results_superSpeedways = race_data[race_data['race_id'].isin(super_speedways_2025['race_id'])]
results_rc = race_data[race_data['race_id'].isin(rc_2025['race_id'])]

```

```python
def calculate_averages(results):

    averages = results.groupby('driver_id').agg({
        'qualifying_position': 'mean',
        'starting_position': 'mean',
        'closing_position': 'mean',
        'avg_speed_rank': 'mean',
        'leader_laps': 'mean',
        'avg_lap_speed': 'mean',
        'norm_speed': 'mean'
        }).reset_index()

    averages_std = results.groupby('driver_id').agg({
        'qualifying_position': 'std',
        'starting_position': 'std',
        'closing_position': 'std',
        'avg_speed_rank': 'std',
        'leader_laps': 'std',
        'avg_lap_speed': 'std',
        'norm_speed': 'std'
    }).reset_index()

    averages = averages.merge(averages_std, on='driver_id', how = 'left', suffixes=('', '_std'))
    averages = averages.merge(results[['driver_id','team','driver_name','is_playoff']].drop_duplicates(),
                              on='driver_id', how='left')
    return averages

stats_season = calculate_averages(race_data)
stats_intermediates = calculate_averages(results_intermediate)
stats_short = calculate_averages(results_short)
stats_rc = calculate_averages(results_rc)
stats_speedway = calculate_averages(results_superSpeedways)
```

## Create Graphs for each

```python
# a map for team colors. You can pick whatever you want
team_colors = {
    'Richard Childress Racing': '#FF1744',
    'Joe Gibbs Racing': '#1E90FF',
    'RFK Racing': '#FF8C00',
    'Kaulig Racing': '#2E8B57',
    'Spire Motorsports': '#FFD700',
    'Team Penske': '#651FFF', 
    'HYAK Motorsports': '#8A2BE2',
    'Trackhouse Racing': '#FF69B4',
    '23XI Racing': '#FF6D00',
    'Hendrick Motorsports': '#1DE9B6',
    'Legacy Motor Club': '#DA70D6',
    'Haas Factory Team': '#708090',
    'Wood Brothers Racing': '#A0522D',
    'Rick Ware Racing': '#7FFF00',
    'Front Row Motorsports': '#9ACD32',
    'NY Racing Team': "#00CED1",
}


def create_track_figure(results,col = 'avg_speed_rank', title='',text_color='white',background_color='#41444a'):
    
    # Sort drivers by average speed rank
    results = results.sort_values(by=col, ascending=True).reset_index(drop=True)

    # Create the barplot
    fig, ax = plt.subplots(figsize=(12, 8))
    sns.barplot(
        data=results,
        x='driver_name',
        y=col,
        hue='team',
        palette=team_colors,
        errorbar=None,
        ax=ax
    )

    fig.patch.set_linewidth(3)
    fig.patch.set_edgecolor('white') 
    fig.patch.set_facecolor(background_color)
    ax.patch.set_linewidth(3)
    ax.patch.set_edgecolor('white') 

    ax.set_facecolor(background_color)
    ax.tick_params(axis='x', colors=text_color,length=8,width=3)
    ax.tick_params(axis='y', colors=text_color,length=8,width=3)
    ax.set_xticklabels(summary2025_S1['driver_name'], rotation=90,fontsize=14,fontweight='bold',color=text_color)
    ax.set_yticklabels(ax.get_yticks(), fontsize=14,color=text_color,fontweight='bold')
    ax.set_ylabel('Average Lap Speed Rank \n (lower = better)', fontsize=16, fontweight='bold', color=text_color,labelpad=15)
    ax.set_xlabel('', fontsize=16,color=text_color,labelpad=15)
    ax.set_title(title,fontsize=20, fontweight='bold', color='white',pad=20)
    
    x_positions = range(len(results))

    patches = ax.patches
    order_names = [t.get_text() for t in ax.get_xticklabels()]
    centers = [round(p.get_x() + p.get_width()/2, 10) for p in patches]
    unique_centers = sorted(set(centers))
    center_to_idx = {c: i for i, c in enumerate(unique_centers)}
    playoff_by_name = results.set_index('driver_name')['is_playoff'].to_dict()

    tallest_by_center = {}
    for p, c in zip(patches, centers):
        if c not in tallest_by_center or p.get_height() > tallest_by_center[c].get_height():
            tallest_by_center[c] = p

    ymin, ymax = ax.get_ylim()
    yr = ymax - ymin
    margin = 0.05 * yr
    base = max(ymin, 0.0)

    for c, p in tallest_by_center.items():
        driver = order_names[center_to_idx[c]]
        if bool(playoff_by_name.get(driver, False)):
            cx = p.get_x() + p.get_width() / 2
            top = p.get_height()
            vis_mid = (base + min(top, ymax)) / 2.0
            cy = min(max(vis_mid, ymin + margin), ymax - margin)
            ax.text(
                cx, cy, 'P',
                ha='center', va='center',
                fontsize=14, fontweight='bold', color='white',
                path_effects=[pe.withStroke(linewidth=2, foreground='black')],
                zorder=6, clip_on=False
            )

    # Style
    ax.set_facecolor('#41444a')
    ax.set_xticks(x_positions)
    ax.set_xticklabels(results['driver_name'], rotation=90, fontsize=14)
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5), title='Team')
```

```python
create_track_figure(stats_intermediates, col='avg_speed_rank', title="2025 Season Average Lap Speed on Intermediates")
create_track_figure(stats_short, col='avg_speed_rank', title="2025 Season Average Lap Speed on Short Tracks")
create_track_figure(stats_rc, col='avg_speed_rank', title="2025 Season Average Lap Speed on Road Courses")
create_track_figure(stats_speedway, col='avg_speed_rank', title="2025 Season Average Lap Speed on Superspeedways")
create_track_figure(summary2025_S1, col='avg_speed_rank', title="2025 Season Average Lap Speed Overall")

```

## An example of a boxplot

```python
# Calculate median avg_speed_rank for each driver
driver_medians = race_data.groupby('driver_name')['avg_speed_rank'].median().sort_values()

# Create ordered categories based on median
race_data['driver_name'] = race_data['driver_name'].astype('category')
race_data['driver_name'] = race_data['driver_name'].cat.reorder_categories(driver_medians.index)

plt.figure(figsize=(16, 10))
sns.boxplot(
    data=race_data,
    x='driver_name',
    y='avg_speed_rank',
    hue='team',
    palette=team_colors,
)
plt.xticks(rotation=90)
plt.show()
```