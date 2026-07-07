"""Reader for EK80 ADCP NetCDF files."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import netCDF4 as nc
import numpy as np
import pandas as pd
import xarray as xr

from ek80adcp import logger, utilities
from ek80adcp.logger import log_error, log_info, log_warning

log = logger.log

# NetCDF group paths inside EK80 files
_ADCP_BASE = "/Sonar/Beam_group1/ADCP"
_CURRENT_BASE = f"{_ADCP_BASE}/Mean_current"


def _convert_time_values(raw_values: np.ndarray, units: str | None) -> np.ndarray:
    """Convert an EK80 time variable to a numpy datetime64[us] array.

    Parameters
    ----------
    raw_values : np.ndarray
        Raw integer time values read from the NetCDF file.
    units : str or None
        The ``units`` attribute of the time variable.

    Returns
    -------
    np.ndarray
        Array of ``datetime64[us]`` values.

    Raises
    ------
    ValueError
        If ``units`` is None.

    """
    if units is None:
        raise ValueError("Time variable has no 'units' attribute.")
    if "nanoseconds" in units:
        # EK80 native encoding: nanoseconds since Windows FILETIME epoch (1601-01-01)
        base = datetime(1601, 1, 1, tzinfo=UTC)
        datetimes = [base + timedelta(microseconds=int(v) // 1000) for v in raw_values]
        return np.array(datetimes, dtype="datetime64[us]")
    cftime_dates = nc.num2date(raw_values, units=units, calendar="gregorian")
    return pd.to_datetime([str(d) for d in cftime_dates]).values


def _read_single_file(nc_path: Path) -> dict:
    """Read one EK80 NetCDF file and return raw arrays in a dict.

    Parameters
    ----------
    nc_path : Path
        Path to the EK80 NetCDF file.

    Returns
    -------
    dict
        Keys: ``vx``, ``vy``, ``vz`` (2-D float arrays, shape ``(time, depth)``),
        ``lon``, ``lat``, ``time`` (1-D arrays), ``depth_first`` (float),
        ``depth_interval`` (float), ``source`` (str).

    """
    with nc.Dataset(str(nc_path)) as ds:
        mc = ds[_CURRENT_BASE]
        adcp = ds[_ADCP_BASE]

        # Velocity: VLEN type stored as (n_pings,) of variable-length arrays;
        # vstack converts to (n_pings, n_depth_bins).
        vx = np.vstack(mc["current_velocity_geographical_east"][:]).astype(np.float32)
        vy = np.vstack(mc["current_velocity_geographical_north"][:]).astype(np.float32)
        vz = np.vstack(mc["current_velocity_geographical_down"][:]).astype(np.float32)

        lon = np.array(mc["mean_platform_longitude"][:], dtype=np.float64)
        lat = np.array(mc["mean_platform_latitude"][:], dtype=np.float64)

        time_var = mc["mean_time"]
        time_vals = _convert_time_values(time_var[:], getattr(time_var, "units", None))

        depth_first = float(np.nanmedian(adcp["depth_first_sample_center"][:]))
        depth_interval = float(np.nanmedian(adcp["vertical_sample_interval"][:]))

    return {
        "vx": vx,
        "vy": vy,
        "vz": vz,
        "lon": lon,
        "lat": lat,
        "time": time_vals,
        "depth_first": depth_first,
        "depth_interval": depth_interval,
        "source": str(nc_path),
    }


def read_ek80(file_list: list[Path | str]) -> xr.Dataset:
    """Read one or more EK80 ADCP NetCDF files into a combined xarray Dataset.

    Velocity components are stored as VLEN arrays inside the EK80 file.
    This function stacks them into ``(time, depth)`` arrays, padding shorter
    profiles with NaN so that all files share a common depth axis.

    Parameters
    ----------
    file_list : list of Path or str
        Paths to EK80-format NetCDF files. Non-``.nc`` files are skipped.

    Returns
    -------
    xr.Dataset
        Dataset with dimensions ``(time, depth)`` containing:

        - ``vx`` — eastward velocity (m/s)
        - ``vy`` — northward velocity (m/s)
        - ``vz`` — downward velocity (m/s)
        - ``lon`` — platform longitude (degrees_east)
        - ``lat`` — platform latitude (degrees_north)

        The ``depth`` coordinate is built from the median
        ``depth_first_sample_center`` and ``vertical_sample_interval`` across
        all files.

    Raises
    ------
    FileNotFoundError
        If ``file_list`` is empty.
    ValueError
        If no valid EK80 NetCDF files could be read.

    """
    file_list = [Path(f) for f in file_list]
    if not file_list:
        raise FileNotFoundError("No files provided to read_ek80.")

    records = []
    for path in file_list:
        if path.suffix.lower() != ".nc":
            log_warning("Skipping non-NetCDF file: %s", path)
            continue
        try:
            log_info("Reading EK80 file: %s", path)
            records.append(_read_single_file(path))
        except Exception as exc:
            log_error("Failed to read %s: %s", path, exc)
            raise

    if not records:
        raise ValueError(
            "No valid EK80 NetCDF files could be read from the provided list."
        )

    # Pad velocity profiles to a common depth dimension across all files
    max_bins = max(r["vx"].shape[1] for r in records)
    vx = np.concatenate(
        [utilities.pad_to_max_columns(r["vx"], max_bins) for r in records], axis=0
    )
    vy = np.concatenate(
        [utilities.pad_to_max_columns(r["vy"], max_bins) for r in records], axis=0
    )
    vz = np.concatenate(
        [utilities.pad_to_max_columns(r["vz"], max_bins) for r in records], axis=0
    )
    lon = np.concatenate([r["lon"] for r in records])
    lat = np.concatenate([r["lat"] for r in records])
    time = np.concatenate([r["time"] for r in records])

    # Common depth axis from median bin spacing and first-bin depth
    depth_first = float(np.median([r["depth_first"] for r in records]))
    depth_interval = float(np.median([r["depth_interval"] for r in records]))
    depths = np.arange(max_bins, dtype=np.float64) * depth_interval + depth_first

    ds = xr.Dataset(
        {
            "vx": (
                ["time", "depth"],
                vx,
                {"units": "m s-1", "long_name": "Eastward velocity"},
            ),
            "vy": (
                ["time", "depth"],
                vy,
                {"units": "m s-1", "long_name": "Northward velocity"},
            ),
            "vz": (
                ["time", "depth"],
                vz,
                {"units": "m s-1", "long_name": "Downward velocity"},
            ),
            "lon": (
                ["time"],
                lon,
                {"units": "degrees_east", "long_name": "Platform longitude"},
            ),
            "lat": (
                ["time"],
                lat,
                {"units": "degrees_north", "long_name": "Platform latitude"},
            ),
        },
        coords={
            "time": ("time", time),
            "depth": (
                "depth",
                depths,
                {"units": "m", "long_name": "Depth", "positive": "down"},
            ),
        },
        attrs={
            "source_files": ", ".join(r["source"] for r in records),
            "n_files": len(records),
            "Conventions": "CF-1.8",
        },
    )
    log_info(
        "Loaded %d EK80 file(s); combined shape: time=%d, depth=%d",
        len(records),
        len(time),
        max_bins,
    )
    return ds
