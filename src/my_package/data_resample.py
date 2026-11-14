# -*- coding: utf-8 -*-
"""
Created on Sat Nov 14 12:01:14 2026

@author: stkats
"""

from pathlib import Path

import pandas as pd

aggregation = {
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
    aggregation: str = "mean",
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
        Aggregation method: "mean", "sum", "min", "max", "median".

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

    resampled = (
        df[numeric_columns]
        .resample(
            interval,
            label="right",
            closed="right",
        )
        .agg(aggregation)
    )

    # Save if requested
    if output_file is not None:
        output_file = Path(output_file)
        resampled.to_csv(output_file)

        print(f"Saved resampled data to:\n{output_file.resolve()}")

    return resampled


if __name__ == "__main__":

    base_dir = Path(__file__).parent

    input_file = base_dir / "MMB_setpoint_1m_10_26.csv"
    output_file = base_dir / "MMB_setpoint_15min_10_26.csv"

    df_15min = resample_csv(
        input_file=input_file,
        output_file=output_file,
        interval="15min",
    )

    print(df_15min.head())