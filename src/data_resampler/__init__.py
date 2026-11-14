"""Resample time-series CSV files from one time interval to another."""

from .core import DEFAULT_AGGREGATION, resample_csv

__all__ = ["DEFAULT_AGGREGATION", "resample_csv"]
