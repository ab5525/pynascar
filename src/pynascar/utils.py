import re
import os
import warnings

# src/utils.py
# Utility functions for NASCAR data processing
# Can add regex patterns for validation or other utility functions as needed
def get_series_id(name):
    match name:
        case 'Cup Series':
            return 1
        case 'Xfinity':
            return 2
        case 'Truck Series':
            return 3
        case _:
            warnings.warn(f"Unknown series name: {name}, returning Cup Series ID")
            print(f'Options are: Cup Series, Xfinity, Truck Series')
            return 1
        
def get_series_name(series_id):
    match series_id:
        case 1:
            return 'Cup Series'
        case 2:
            return 'Xfinity'
        case 3:
            return 'Truck Series'
        case _:
            warnings.warn(f"Unknown series ID: {series_id}, returning Cup Series name")
            return 'Cup Series'


