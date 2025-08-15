# This file is all boilerplate for functionality. NOT written by me. Can/will update later if needed 
# We are going with sqlite by default so we can use the same existing functions and just pass through the data
# This should work for now

from __future__ import annotations
from pathlib import Path
import re
import pandas as pd
from .config import get_settings

# Ensures that any string does not contain characters that are not allowed in file names
def _sanitize_key(key: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", key).strip("_")

def _compose_key(base: str, parts: dict | None = None) -> str:
    """
    Compose a stable cache key from a base name and optional parameters.
    Example: base='lap_times', parts={'year': 2024, 'series': 'cup'}
             -> 'lap_times__series-cup__year-2024' (sorted by key)
    Hyphens and underscores are preserved by _sanitize_key.
    """
    if not parts:
        return base
    # Normalize values to short strings
    normalized = {}
    for k, v in parts.items():
        if isinstance(v, (list, tuple, set)):
            v = ",".join(map(str, v))
        elif isinstance(v, dict):
            v = ",".join(f"{kk}:{vv}" for kk, vv in sorted(v.items()))
        else:
            v = str(v)
        normalized[str(k)] = v
    tokens = [f"{k}-{normalized[k]}" for k in sorted(normalized.keys())]
    return f"{base}__{'__'.join(tokens)}"

def _cache_path(key: str, fmt: str | None = None) -> Path:
    s = get_settings()
    # Even if disabled, return the would-be path for callers that want to know it.
    fmt = (fmt or s.df_format).lower()
    ext = ".parquet" if fmt == "parquet" else ".csv"
    cache_dir = s.cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / f"{_sanitize_key(key)}{ext}"

def save_df(key: str, df: pd.DataFrame, fmt: str | None = None, **key_parts) -> Path:
    """
    Save a DataFrame to cache. Extra keyword args are folded into the key.
    Example: save_df("lap_times", df, year=2024, series="cup")
    """
    s = get_settings()
    full_key = _compose_key(key, key_parts)
    if not (s.cache_enabled and s.df_cache_enabled):
        return _cache_path(full_key, fmt)  # no-op but return target path

    fmt = (fmt or s.df_format).lower()
    path = _cache_path(full_key, fmt)

    if fmt == "parquet":
        try:
            df.to_parquet(path, index=False)
            print(f'Saved to local Cache: {path}')
        except Exception as e:
            raise RuntimeError(
                "Failed to write parquet. Install the optional dependency 'pyarrow' "
                "or set df_format='csv' via set_options()."
            ) from e
    elif fmt == "csv":
        df.to_csv(path, index=False)
        print(f'Saved to local Cache: {path}')
    else:
        raise ValueError("Unsupported format. Use 'csv' or 'parquet'.")

    return path

def load_df(key: str, fmt: str | None = None, **key_parts) -> pd.DataFrame | None:
    """
    Load a DataFrame from cache. Extra keyword args are folded into the key.
    Example: load_df("lap_times", year=2024, series="cup")
    """
    s = get_settings()
    if not (s.cache_enabled and s.df_cache_enabled):
        return None

    fmt = (fmt or s.df_format).lower()
    full_key = _compose_key(key, key_parts)
    path = _cache_path(full_key, fmt)
    if not path.exists():
        return None

    if fmt == "parquet":
        try:
            loaded_df = pd.read_parquet(path)
            print(f'Loaded from local Cache: {path}')
            return loaded_df
        except Exception as e:
            raise RuntimeError(
                "Failed to read parquet. Install 'pyarrow' or use 'csv' format."
            ) from e
    elif fmt == "csv":
        loaded_df = pd.read_csv(path)
        print(f'Loaded from local Cache: {path}')
        return loaded_df
    else:
        raise ValueError("Unsupported format. Use 'csv' or 'parquet'.")

def has_df(key: str, fmt: str | None = None, **key_parts) -> bool:
    full_key = _compose_key(key, key_parts)
    return _cache_path(full_key, fmt).exists()

def clear_df(key: str, fmt: str | None = None, **key_parts) -> bool:
    full_key = _compose_key(key, key_parts)
    p = _cache_path(full_key, fmt)
    if p.exists():
        p.unlink(missing_ok=True)
        return True
    return False