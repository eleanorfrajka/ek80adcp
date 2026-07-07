"""Tests for ek80adcp readers."""

from pathlib import Path

import numpy as np
import pytest
import xarray as xr

from ek80adcp import logger
from ek80adcp.read_ek80 import read_ek80
from ek80adcp.readers import find_ek80_files, load_ek80

logger.disable_logging()

# Path to the sample EK80 file checked in to data/
_SAMPLE_FILE = (
    Path(__file__).resolve().parent.parent / "data" / "T202508-D20250831-T002541.nc"
)


# ---------------------------------------------------------------------------
# find_ek80_files
# ---------------------------------------------------------------------------


def test_find_ek80_files_returns_empty_list(tmp_path):
    result = find_ek80_files(data_dir=tmp_path)
    assert isinstance(result, list)
    assert result == []


def test_find_ek80_files_matches_naming_pattern(tmp_path):
    (tmp_path / "T202508-D20250831-T002541.nc").touch()
    (tmp_path / "other_file.nc").touch()
    result = find_ek80_files(data_dir=tmp_path)
    assert len(result) == 1
    assert result[0].name == "T202508-D20250831-T002541.nc"


def test_find_ek80_files_deduplicates_candidate_dirs(tmp_path):
    (tmp_path / "T202508-D20250831-T000000.nc").touch()
    result = find_ek80_files(data_dir=tmp_path, candidate_dirs=[tmp_path])
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


def test_load_ek80_raises_when_no_files(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_ek80(data_dir=tmp_path)


def test_read_ek80_raises_on_empty_list():
    with pytest.raises(FileNotFoundError):
        read_ek80([])


# ---------------------------------------------------------------------------
# Integration test against the sample EK80 file
# ---------------------------------------------------------------------------


@pytest.mark.file_io
@pytest.mark.skipif(not _SAMPLE_FILE.exists(), reason="Sample EK80 file not present")
def test_load_sample_ek80_file():
    """Reading the sample file produces a well-formed (time, depth) Dataset."""
    ds = load_ek80(file_list=[_SAMPLE_FILE])

    assert isinstance(ds, xr.Dataset)

    for var in ("vx", "vy", "vz", "lon", "lat"):
        assert var in ds, f"Missing variable: {var}"

    assert "time" in ds.dims
    assert "depth" in ds.dims
    assert ds.sizes["time"] > 0
    assert ds.sizes["depth"] > 0

    assert ds["vx"].dims == ("time", "depth")
    assert ds["vy"].shape == ds["vx"].shape
    assert ds["vz"].shape == ds["vx"].shape

    assert ds["lon"].shape == (ds.sizes["time"],)
    assert ds["lat"].shape == (ds.sizes["time"],)

    depths = ds["depth"].values
    assert np.all(depths >= 0), "Depths must be non-negative"
    assert np.all(np.diff(depths) > 0), (
        "Depth coordinate must be monotonically increasing"
    )

    assert ds["vx"].attrs.get("units") == "m s-1"
    assert ds["depth"].attrs.get("positive") == "down"

    assert ds.attrs["n_files"] == 1
    assert "source_files" in ds.attrs
