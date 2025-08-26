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


# Build name map from results, stripping symbols for matching
def _clean_name(name):
    if name is None:
        return None
    
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

def normalize_name(name):
    cleaned = _clean_name(name)
    if cleaned in name_mappings:
        return name_mappings[cleaned]
    return cleaned
