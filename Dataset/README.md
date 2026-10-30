# Dataset — UCI ElectricityLoadDiagrams20112014

> **In the GitHub repository:** only `electricity_hourly_2012_2014.csv` (the file the code uses) is stored. Run `python Dataset/download_dataset.py` from the project root to download the complete original UCI file and the LSTNet hourly release, and to rebuild the CSV (it reproduces the committed file exactly). The raw files are over GitHub's 100 MB limit.

Source dataset: UCI Machine Learning Repository, "ElectricityLoadDiagrams20112014" (ID 321).
Original page: https://archive.ics.uci.edu/dataset/321/electricityloaddiagrams20112014

## Files in this folder

### `electricity_hourly_2012_2014.csv`  (ready to use)
The standard research version of this dataset, as used by essentially every recent
time-series-forecasting paper in the literature review (PatchTST, DLinear, Autoformer,
FSNet, OneNet, etc.).

- 26,304 rows = hourly timesteps, `2012-01-01 00:00:00` .. `2014-12-31 23:00:00`
- 321 columns `MT_001 .. MT_321` = individual client electricity consumption (integer kWh per hour)
- plus a leading `date` column (added here for convenience; the raw benchmark has no date column)

This version has ALREADY had two of the Module 1 preprocessing steps applied to it:
  1. the native 15-minute readings aggregated to hourly (four readings summed), and
  2. the all-zero year 2011 dropped, along with clients that had no consumption history
     (370 clients in the raw file -> 321 here).

Provenance: extracted from `laiguokun/multivariate-time-series-data` (the LSTNet dataset
release), which is the canonical hourly-321 packaging of UCI 321.

### `electricity_hourly_LSTNet.txt.gz`
The same hourly matrix, exactly as published by LSTNet: gzip-compressed, comma-separated,
NO header row and NO date column — just 26,304 lines x 321 values. Kept as the untouched
source for `electricity_hourly_2012_2014.csv`.

### `LD2011_2014_raw.txt.zip`  +  `LD2011_2014.txt`  (the raw UCI file)
The original file straight from archive.ics.uci.edu, plus its extracted contents.
- `LD2011_2014.txt`: 710 MB, 140,256 data rows = 15-minute readings from
  `2011-01-01 00:15:00` to `2015-01-01 00:00:00`
- 371 columns: an unnamed timestamp column + `MT_001 .. MT_370` (370 clients)
- **semicolon-delimited**, and values use a **comma as the decimal separator**
  (e.g. `2011-01-01 00:15:00;0;0;...`). In pandas:
  `pd.read_csv("LD2011_2014.txt", sep=";", decimal=",", index_col=0, parse_dates=True)`
- consumption is in kW for each 15-min interval; multiply by 0.25 for kWh, or resample
  to hourly by summing the four intervals in each hour

Use this if you want to run the 15-min -> hourly aggregation yourself as an explicit
pipeline step, or need the 2011 period / the ~49 extra clients. Otherwise
`electricity_hourly_2012_2014.csv` already reflects that preprocessing and is the more
reproducible / literature-comparable choice.

## Client IDs
The hourly packaging keeps 321 of the 370 clients and renumbers them `MT_001 .. MT_321`, so the IDs used in this project (e.g. MT_105, MT_135) refer to that numbering, not to the raw UCI file's columns.
