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

# Ready-made timestamp formats: example of what the timestamp looks like
# -> pandas/strftime format code. The first entry is the default.
DATE_FORMATS: dict[str, str] = {
    "31-12-26 23:59:59": "%d-%m-%y %H:%M:%S",
    "31-12-26 23:59": "%d-%m-%y %H:%M",
    "31-12-2026 23:59:59": "%d-%m-%Y %H:%M:%S",
    "31-12-2026 23:59": "%d-%m-%Y %H:%M",
    "31/12/2026 23:59:59": "%d/%m/%Y %H:%M:%S",
    "31/12/2026 23:59": "%d/%m/%Y %H:%M",
    "31.12.2026 23:59:59": "%d.%m.%Y %H:%M:%S",
    "31.12.2026 23:59": "%d.%m.%Y %H:%M",
    "2026-12-31 23:59:59 (ISO)": "%Y-%m-%d %H:%M:%S",
    "2026-12-31 23:59 (ISO)": "%Y-%m-%d %H:%M",
    "12/31/2026 23:59:59 (US)": "%m/%d/%Y %H:%M:%S",
    "12/31/2026 23:59 (US)": "%m/%d/%Y %H:%M",
}

# Timestamp convention of the resampled data -> pandas `label`/`closed` side.
#   "end":   00:15 holds the data after 00:00 up to and including 00:15
#   "start": 00:00 holds the data from 00:00 up to but excluding 00:15
TIMESTAMP_CONVENTIONS: dict[str, str] = {
    "end": "right",
    "start": "left",
}

# Delimiters tried when auto-detecting.
CANDIDATE_DELIMITERS = (",", ";", "\t", "|")


def detect_delimiter(input_file: str | Path) -> str:
    """
    Guess the delimiter of a CSV file from its header line: the candidate
    that appears most often wins. Falls back to a comma.
    """
    with open(input_file, encoding="utf-8-sig", errors="replace") as f:
        header = f.readline()

    counts = {d: header.count(d) for d in CANDIDATE_DELIMITERS}
    best = max(counts, key=counts.get)
    return best if counts[best] > 0 else ","


def resample_csv(
    input_file: str | Path,
    output_file: str | Path | None = None,
    interval: str = "15min",
    timestamp_column: str = "Timestamp",
    date_format: str | None = "%d-%m-%y %H:%M:%S",
    aggregation: str | Mapping[str, str] = "mean",
    fallback_aggregation: str = "mean",
    delimiter: str | None = None,
    convention: str= "end",
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
        Expected timestamp format, e.g. one of the values in DATE_FORMATS.
        Set to None to let pandas guess it. Not recommended for
        day-first dates: pandas may silently swap day and month.

    aggregation:
        Either one method applied to every numeric column
        ("mean", "sum", "min", "max", "median", "first", "last"),
        or a mapping of column name to method, e.g. DEFAULT_AGGREGATION.

    fallback_aggregation:
        Only used when `aggregation` is a mapping: the method for numeric
        columns that are not listed in it.

    delimiter:
        Column separator of the input file, e.g. "," or ";".
        If None, it is detected from the header line.
        The output file is written with the same delimiter.
    
    convention:
        "end": each timestamp marks the end of its interval, e.g. with
        "15min" the row 00:15 covers the data after 00:00 up to 00:15.
        "start": each timestamp marks the start of its interval, e.g.
        the row 00:00 covers the data from 00:00 up to before 00:15.

    Returns
    -------
    pd.DataFrame
        The resampled DataFrame.
    """
    
    if convention not in TIMESTAMP_CONVENTIONS:
        raise ValueError(
            f"Unknown convention '{convention}'. "
            f"Choose one of: {list(TIMESTAMP_CONVENTIONS)}"
        )
    side = TIMESTAMP_CONVENTIONS[convention]

    input_file = Path(input_file)

    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Load data
    if delimiter is None:
        delimiter = detect_delimiter(input_file)

    # index_col=False: rows ending with a trailing delimiter must not turn
    # the first column into the index (which shifts all columns by one).
    df = pd.read_csv(input_file, sep=delimiter, index_col=False)

    # A trailing delimiter on the header line creates an empty
    # "Unnamed: N" column; drop such columns.
    empty_unnamed = [
        column for column in df.columns
        if str(column).startswith("Unnamed:") and df[column].isna().all()
    ]
    df = df.drop(columns=empty_unnamed)

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
            label=side,
            closed=side,
        )
        .agg(agg)
    )

    # Save if requested
    if output_file is not None:
        resampled.to_csv(Path(output_file), sep=delimiter)

    return resampled
