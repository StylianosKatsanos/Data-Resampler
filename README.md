# Data Resampler

Resample time-series CSV files from one time interval to another
(e.g. 1-minute data to 15-minute data).

## Setup (Windows)

```
py -m venv .venv
.venv\Scripts\activate.bat
pip install -r requirements.txt
pip install -e .
```

`pip install -e .` installs the package in editable mode, so changes to the
code take effect without reinstalling.

## Run the GUI

```
data-resampler
```

or

```
python -m data_resampler
```

## Use from Python

```python
from data_resampler import DEFAULT_AGGREGATION, resample_csv

# Same method for every column
df = resample_csv("input.csv", "output_15min.csv", interval="15min")

# Per-column rules (e.g. Energy is summed, Energy Meter keeps the last value)
df = resample_csv("input.csv", "output_1h.csv", interval="1h",
                  aggregation=DEFAULT_AGGREGATION)
```

## Run the tests

```
pip install pytest
pytest
```
