"""Tests for ek80adcp plotters."""

import matplotlib
import numpy as np
import xarray as xr
from pandas import DataFrame
from pandas.io.formats.style import Styler

from ek80adcp import plotters

matplotlib.use("Agg")

# Minimal synthetic EK80 dataset for plot tests
_N_TIME = 60
_N_DEPTH = 20
_TIME = np.arange("2025-08-31T00:00", "2025-08-31T01:00", dtype="datetime64[m]")[
    :_N_TIME
]
_DEPTHS = np.linspace(14.0, 18.0, _N_DEPTH)
_RNG = np.random.default_rng(0)


def _make_ds() -> xr.Dataset:
    """Return a minimal synthetic EK80-style Dataset."""
    shape = (_N_TIME, _N_DEPTH)
    return xr.Dataset(
        {
            "vx": (
                ["time", "depth"],
                _RNG.standard_normal(shape).astype(np.float32) * 0.1,
                {"units": "m s-1", "long_name": "Eastward velocity"},
            ),
            "vy": (
                ["time", "depth"],
                _RNG.standard_normal(shape).astype(np.float32) * 0.1,
                {"units": "m s-1", "long_name": "Northward velocity"},
            ),
            "vz": (
                ["time", "depth"],
                _RNG.standard_normal(shape).astype(np.float32) * 0.02,
                {"units": "m s-1", "long_name": "Downward velocity"},
            ),
            "lon": (
                ["time"],
                np.linspace(-20.6, -20.5, _N_TIME),
                {"units": "degrees_east"},
            ),
            "lat": (
                ["time"],
                np.linspace(68.6, 68.7, _N_TIME),
                {"units": "degrees_north"},
            ),
        },
        coords={
            "time": ("time", _TIME),
            "depth": ("depth", _DEPTHS, {"units": "m", "positive": "down"}),
        },
    )


def test_plot_velocity_at_depth_returns_figure():
    ds = _make_ds()
    fig, ax = plotters.plot_velocity_at_depth(ds, depth_idx=2)
    assert fig is not None
    assert ax is not None
    assert "EK80 ADCP" in ax.get_title()
    assert ax.get_ylabel() != ""


def test_plot_hovmoller_returns_three_axes():
    ds = _make_ds()
    fig, axes = plotters.plot_hovmoller(ds)
    assert fig is not None
    n_components = len(("vx", "vy", "vz"))
    assert len(axes) == n_components


def test_plot_track_quiver_returns_figure():
    ds = _make_ds()
    fig, ax = plotters.plot_track_quiver(ds, depth_idx=0)
    assert fig is not None
    assert ax is not None
    assert "EK80 ADCP" in ax.get_title()


def test_show_variables_returns_styler():
    ds = xr.Dataset(
        {
            "vx": (
                ["time", "depth"],
                [[1.0, 2.0], [3.0, 4.0]],
                {"units": "m s-1", "comment": "Eastward velocity"},
            )
        },
        coords={"time": [0, 1], "depth": [14.0, 15.0]},
    )
    styled = plotters.show_variables(ds)
    assert isinstance(styled, Styler)


def test_show_attributes_returns_dataframe():
    ds = xr.Dataset()
    ds.attrs["title"] = "Test"
    ds.attrs["institution"] = "UHH"
    df = plotters.show_attributes(ds)
    assert isinstance(df, DataFrame)
