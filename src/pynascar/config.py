from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import os

@dataclass
class Settings:
    # Only DataFrame caching now
    cache_enabled: bool = bool(os.getenv("PYNASCAR_CACHE_ENABLED", "1") not in ("0", "false", "False"))
    df_cache_enabled: bool = bool(os.getenv("PYNASCAR_DF_CACHE", "1") not in ("0", "false", "False"))
    cache_dir: Path = Path(os.getenv("PYNASCAR_CACHE_DIR", Path.home() / ".cache" / "pynascar")).expanduser()
    df_format: str = os.getenv("PYNASCAR_DF_FORMAT", "parquet")  # parquet|csv

_settings = Settings()

def get_settings() -> Settings:
    return _settings

def set_options(
        cache_enabled: bool | None = None,
        df_cache_enabled: bool | None = None,
        cache_dir: Path | str | None = None,
        df_format: str | None = None,
    ) -> Settings:
    """
    Configure DataFrame caching only. Supported formats: csv, parquet. No HTTP or SQL rn 
    """
    global _settings
    s = _settings

    if isinstance(cache_dir, str):
        cache_dir = Path(cache_dir)

    fmt = s.df_format if df_format is None else str(df_format).lower()
    if fmt not in ("csv", "parquet"):
        fmt = "parquet"
        raise UserWarning("Format must be csv or parquet. This will default to 'parquet'.")

    _settings = Settings(
        cache_enabled = s.cache_enabled if cache_enabled is None else cache_enabled,
        df_cache_enabled = s.df_cache_enabled if df_cache_enabled is None else df_cache_enabled,
        cache_dir = s.cache_dir if cache_dir is None else Path(cache_dir).expanduser(),
        df_format = fmt,
    )
    return _settings