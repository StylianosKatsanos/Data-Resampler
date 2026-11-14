# -*- coding: utf-8 -*-
"""
Core resampling logic. Has no GUI dependencies so it can be used from
scripts, notebooks and tests.

@author: stkats
"""

from collections.abc import Mapping
from pathlib import Path

import pandas as pd

# Per-column aggregation rules for the known columns.
# Pass this as `aggregation` to resample_csv to use it.
DEFAULT_AGGREGATION: dict[str, str] = {
    "POA Irradiance": "mean",
    "Active Power": "mean",
    "Energy": "sum",
    "Setpoint": "mean",
    "Energy Meter": "last",
}


def resample_csv(
    input_file: str | Path,
    output_file: str | Path | None = None,
    interval: str = "15min",
    timestamp_column: str = "Timestamp",
    date_format: str | None = "%d-%m-%y %H:%M:%S",
    aggregation: str | Mapping[str, str] = "mean",
    fallback_aggregation: str = "mean",
) -> pd.DataFrame:
    """
    Load a time-series CSV, resample it to a specified interval,
    and optionally save the result.

    Parameters
    ----------
    input_file:
        Path to the input CSV.

    output_file:
        Path for the resampled CSV.
        If None, no file is written.

    interval:
        Pandas resampling interval, e.g. "15min", "30min", "1h".

    timestamp_column:
        Name of the timestamp column.

    date_format:
        Expected timestamp format.
        Set to None to let pandas detect it automatically.

    aggregation:
        Either one method applied to every numeric column
        ("mean", "sum", "min", "max", "median", "first", "last"),
        or a mapping of column name to method, e.g. DEFAULT_AGGREGATION.

    fallback_aggregation:
        Only used when `aggregation` is a mapping: the method for numeric
        columns that are not listed in it.

    Returns
    -------
    pd.DataFrame
        The resampled DataFrame.
    """

    input_file = Path(input_file)

    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Load data
    df = pd.read_csv(input_file)

    if timestamp_column not in df.columns:
        raise ValueError(
            f"Timestamp column '{timestamp_column}' not found.\n"
            f"Available columns: {list(df.columns)}"
        )

    # Parse timestamp
    df[timestamp_column] = pd.to_datetime(
        df[timestamp_column],
        format=date_format,
        errors="coerce",
    )

    # Check for timestamps that could not be parsed
    invalid_timestamps = df[timestamp_column].isna().sum()

    if invalid_timestamps:
        raise ValueError(
            f"{invalid_timestamps} timestamps could not be parsed."
        )

    # Set time index and make sure it is sorted
    df = df.set_index(timestamp_column).sort_index()

    # Resample numeric columns
    numeric_columns = df.select_dtypes(include="number").columns

    if isinstance(aggregation, Mapping):
        agg = {
            column: aggregation.get(column, fallback_aggregation)
            for column in numeric_columns
        }
    else:
        agg = aggregation

    resampled = (
        df[numeric_columns]
        .resample(
            interval,
            label="right",
            closed="right",
        )
        .agg(agg)
    )

    # Save if requested
    if output_file is not None:
        resampled.to_csv(Path(output_file))

    return resampled
