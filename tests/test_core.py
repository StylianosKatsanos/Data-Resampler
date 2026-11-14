import numpy as np
import pandas as pd
import pytest

from data_resampler import DEFAULT_AGGREGATION, resample_csv


@pytest.fixture
def sample_csv(tmp_path):
    """Two hours of 1-minute data in the default timestamp format."""
    idx = pd.date_range("2026-10-01 00:01", periods=120, freq="1min")
    df = pd.DataFrame({
        "Timestamp": idx.strftime("%d-%m-%y %H:%M:%S"),
        "Active Power": np.arange(1.0, 121.0),
        "Energy": 1.0,
        "Energy Meter": np.arange(1.0, 121.0),
        "Other": 2.0,
    })
    path = tmp_path / "sample.csv"
    df.to_csv(path, index=False)
    return path


def test_single_method_applies_to_all_columns(sample_csv):
    out = resample_csv(sample_csv, interval="30min", aggregation="mean")
    assert len(out) == 4
    assert out["Active Power"].iloc[0] == pytest.approx(15.5)  # mean of 1..30
    assert out["Energy"].iloc[0] == 1.0


def test_per_column_mapping(sample_csv):
    out = resample_csv(sample_csv, interval="30min", aggregation=DEFAULT_AGGREGATION)
    first = out.iloc[0]
    assert first["Energy"] == 30.0          # sum
    assert first["Energy Meter"] == 30.0    # last
    assert first["Active Power"] == pytest.approx(15.5)  # mean
    assert first["Other"] == 2.0            # not in mapping -> fallback mean


def test_writes_output_file(sample_csv, tmp_path):
    output = tmp_path / "out.csv"
    resample_csv(sample_csv, output, interval="1h")
    assert len(pd.read_csv(output)) == 2


def test_missing_timestamp_column(sample_csv):
    with pytest.raises(ValueError, match="not found"):
        resample_csv(sample_csv, timestamp_column="Time")


def test_bad_date_format(sample_csv):
    with pytest.raises(ValueError, match="could not be parsed"):
        resample_csv(sample_csv, date_format="%Y/%m/%d")


def test_missing_input_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        resample_csv(tmp_path / "nope.csv")
