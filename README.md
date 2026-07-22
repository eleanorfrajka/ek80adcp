# ek80adcp

Python tools for reading, condensing, and plotting EK80 ADCP velocity data.

Raw EK80 NetCDF files are typically 1–2 GB each and contain full-resolution
backscatter, attitude, and raw acoustic data alongside the velocity profiles.
This package extracts only the velocity components (vx, vy, vz), position
(lon, lat), and time into compact files that are ~1000× smaller.

---

## Installation

```bash
git clone https://github.com/eleanorfrajka/ek80adcp.git
cd ek80adcp
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -e ".[dev]"
```

After installation the `ek80adcp` command is available in the activated
environment.

---

## File naming convention

Raw EK80 files follow the pattern:

```
{cruise}-D{YYYYMMDD}-T{HHMMSS}.nc
```

Example: `DSMIXSED2-D20260709-T161720.nc`

- `DSMIXSED2` — cruise/ship identifier (prefix)
- `D20260709` — UTC date the file starts
- `T161720`   — UTC time the file starts

Each file covers about 10 minutes at 2-second ping resolution with ~40 000
depth bins at 2.5 cm vertical spacing (roughly 14–800 m depth range).

---

## 3-step workflow

### Step 1 — Extract (one condensed file per raw file)

Reads each raw file, subsets to a maximum depth, resamples in time, and
writes a compact NetCDF. Processing parameters are recorded in the `history`
attribute. Use `-p` to filter by a filename prefix (such as the cruise name) or `--plot` to save a Hovmöller PNG alongside each file.

```bash
ek80adcp extract /path/to/raw/ \
    -o /path/to/out/ \
    -p DSMIXSEDII \
    --depth-max 800 \
    --time-bin 60s \
    --plot
```

Options:

| Flag | Description |
|---|---|
| `FILE_OR_DIR` | One or more raw `.nc` files, or a directory of them |
| `-o DIR` | Output directory (created if absent) |
| `-p PREFIX` | Prefix which is expected at the beginning of the filename |
| `--depth-max M` | Drop depth bins below M metres (e.g. `800`) |
| `--time-bin OFFSET` | Resample to this interval, e.g. `60s`, `5min` (default: native 2 s) |
| `--method mean\|median` | Averaging method when `--time-bin` is set (default: `mean`) |
| `--plot` | Save a 3-panel Hovmöller PNG for each file |
| `--skip-existing` | Skip files whose output already exists (safe to re-run) |

Output names match the input names; a `manifest.json` is written to the
output directory recording what was processed and with what settings. It also records errors and the files skipped due to that.

---

### Step 2 — Concatenate by day (one NetCDF per calendar day) or by time range

Groups the extracted files by the `D{YYYYMMDD}` token in their names and
writes one combined file per day, named `{prefix}-D{YYYYMMDD}.nc`.

```bash
ek80adcp concat /path/to/out/ \
    -o /path/to/daily/ \
    --by-day \
    --plot
```

Options:

| Flag | Description |
|---|---|
| `FILE_OR_DIR` | Extracted `.nc` files, or a directory of them |
| `-o DIR` | Output directory for daily files |
| `--by-day` | Group by date and write one file per day |
| `--plot` | Save a Hovmöller PNG for each daily file |

---

Alternatively groups the files by a given time range and concatenates them based on a range in the format `D{YYYYMMDD}-T{HHMMSS}--D{YYYYMMDD}-T{HHMMSS}` with a start and end date. The concatenated file is named with the prefix and this time range.

```bash
ek80adcp concat /path/to/out/ \
    -o /path/to/time/range/ \
    --by-time-range D20260712-T123401--D20260714-T000000 \
    --plot
```

Options:

| Flag | Description |
|---|---|
| `FILE_OR_DIR` | Extracted `.nc` files, or a directory of them |
| `-o DIR` | Output directory for daily files |
| `--by-time-range TIME-RANGE` | Group by time range and writes into one file |
| `--plot` | Save a Hovmöller PNG for each daily file |

---

### Step 3 — Concatenate all days into one file

```bash
ek80adcp concat /path/to/daily/ \
    -o /path/to/DSMIXSED2-combined.nc \
    --plot
```

Options:

| Flag | Description |
|---|---|
| `FILE_OR_DIR` | Daily `.nc` files, or a directory of them |
| `-o FILE` | Single output NetCDF |
| `--plot` | Save a Hovmöller PNG of the full dataset |

---

## Full example (MIXSED2 cruise)

```bash
RAW=/Volumes/Compartida/MIXSED2/EK80/EK80ADCP/files
OUT=/Volumes/Compartida/MIXSED2/EK80/EK80ADCP/extracted
DAILY=/Volumes/Compartida/MIXSED2/EK80/EK80ADCP/daily

# Step 1 – extract all raw files (skip any already done)
ek80adcp extract "$RAW" -o "$OUT" \
    --depth-max 800 --time-bin 60s --skip-existing

# Step 2 – one NetCDF per day
ek80adcp concat "$OUT" -o "$DAILY" --by-day --plot

# Step 3 – everything in one file
ek80adcp concat "$DAILY" -o "$DAILY/DSMIXSED2-combined.nc" --plot
```

---

## Output variables

Each extracted NetCDF contains:

| Variable | Dimensions | Units | Description |
|---|---|---|---|
| `vx` | time, depth | m s⁻¹ | Eastward velocity |
| `vy` | time, depth | m s⁻¹ | Northward velocity |
| `vz` | time, depth | m s⁻¹ | Downward velocity |
| `lon` | time | degrees_east | Platform longitude |
| `lat` | time | degrees_north | Platform latitude |

Global attributes include `history` (CF-convention processing log) and
`source_files`.

---

## Development

```bash
# Run tests
pytest

# Lint and format
ruff check --fix .
ruff format .

# Type checking
mypy ek80adcp/

# Add a changelog entry
# (fragment type: feature / bugfix / doc / removal / misc)
echo "Your change description." > changelog.d/<issue>.<type>.md
```
