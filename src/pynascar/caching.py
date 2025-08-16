# This file is all boilerplate for functionality. NOT written by me. Can/will update later if needed 
# We are going with sqlite by default so we can use the same existing functions and just pass through the data
# This should work for now

from __future__ import annotations
from pathlib import Path
import re
import pandas as pd
from .config import get_settings

# Sanitize path segments and filenames
def _sanitize(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s).strip("_")

def _seg(v) -> str:
    if v is None:
        raise ValueError("year, series_id, and race_id must be provided")
    return _sanitize(str(v))

def race_cache_dir(year, series_id, race_id) -> Path:
    """
    <cache_dir>/<year>/<series_id>/<race_id>
    """
    s = get_settings()
    d = Path(s.cache_dir) / _seg(year) / _seg(series_id) / _seg(race_id)
    d.mkdir(parents=True, exist_ok=True)
    return d

def _cache_path(key: str, year, series_id, race_id, fmt: str | None = None) -> Path:
    s = get_settings()
    fmt = (fmt or s.df_format).lower()
    ext = ".parquet" if fmt == "parquet" else ".csv"
    return race_cache_dir(year, series_id, race_id) / f"{_sanitize(key)}{ext}"

def save_df(key: str, df: pd.DataFrame, *, year, series_id, race_id, fmt: str | None = None) -> Path:
    """
    Save: <cache_dir>/<year>/<series_id>/<race_id>/<key>.(csv|parquet)
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"save_df expects a pandas DataFrame; got {type(df).__name__}")
    s = get_settings()
    path = _cache_path(key, year, series_id, race_id, fmt)
    if not (s.cache_enabled and s.df_cache_enabled):
        return path  # no-op but return target path

    fmt = (fmt or s.df_format).lower()
    if fmt == "parquet":
        try:
            df.to_parquet(path, index=False)
        except Exception as e:
            raise RuntimeError(
                "Failed to write parquet. Install 'pyarrow' or set df_format='csv' via set_options()."
            ) from e
    elif fmt == "csv":
        df.to_csv(path, index=False)
    else:
        raise ValueError("Unsupported format. Use 'csv' or 'parquet'.")
    return path

def load_df(key: str, *, year, series_id, race_id, fmt: str | None = None) -> pd.DataFrame | None:
    """
    Load: <cache_dir>/<year>/<series_id>/<race_id>/<key>.(csv|parquet)
    """
    s = get_settings()
    if not (s.cache_enabled and s.df_cache_enabled):
        return None

    path = _cache_path(key, year, series_id, race_id, fmt)
    if not path.exists():
        return None

    fmt = (fmt or s.df_format).lower()
    if fmt == "parquet":
        try:
            return pd.read_parquet(path)
        except Exception as e:
            raise RuntimeError("Failed to read parquet. Install 'pyarrow' or use 'csv'.") from e
    elif fmt == "csv":
        return pd.read_csv(path)
    else:
        raise ValueError("Unsupported format. Use 'csv' or 'parquet'.")

def has_df(key: str, *, year, series_id, race_id, fmt: str | None = None) -> bool:
    return _cache_path(key, year, series_id, race_id, fmt).exists()

def clear_df(key: str, *, year, series_id, race_id, fmt: str | None = None) -> bool:
    p = _cache_path(key, year, series_id, race_id, fmt)
    if p.exists():
        p.unlink(missing_ok=True)
        return True
    return False

def clear_race(year, series_id, race_id) -> bool:
    """
    Delete <cache_dir>/<year>/<series_id>/<race_id> and prune empty parents.
    """
    d = race_cache_dir(year, series_id, race_id)
    removed = False
    if d.exists():
        for p in d.glob("*"):
            if p.is_file():
                p.unlink(missing_ok=True)
                removed = True
        try:
            d.rmdir()
        except OSError:
            pass
        # prune series and year if empty
        parent = d.parent
        for _ in range(2):
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent
    return removed