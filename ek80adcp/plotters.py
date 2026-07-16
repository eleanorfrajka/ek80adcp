"""Visualization utilities for EK80 ADCP data."""

from pathlib import Path
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from pandas import DataFrame
from pandas.io.formats.style import Styler


def _use_style() -> None:
    """Apply the package matplotlib style."""
    here = Path(__file__).resolve().parent
    plt.style.use(here / "ek80adcp.mplstyle")


def plot_velocity_at_depth(
    ds: xr.Dataset,
    depth_idx: int = 3,
    figsize: tuple[float, float] = (15, 8),
) -> tuple[Any, Any]:
    """Plot eastward and northward velocity at one depth bin.

    Parameters
    ----------
    ds : xr.Dataset
        Dataset with ``vx``, ``vy`` variables and ``time``, ``depth`` coords,
        as returned by :func:`~ek80adcp.readers.load_ek80`.
    depth_idx : int, optional
        Index along the depth axis to plot. Default is 3.
    figsize : tuple of float, optional
        Figure size in inches ``(width, height)``.

    Returns
    -------
    fig, ax : matplotlib Figure and Axes

    """
    _use_style()

    depth_m = float(ds.depth.values[depth_idx])
    vx = ds["vx"].isel(depth=depth_idx).values
    vy = ds["vy"].isel(depth=depth_idx).values
    t = ds["time"].values

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(t, vy, color="blue", linewidth=0.8, label="North (vy)")
    ax.plot(t, vx, color="red", linewidth=0.8, label="East (vx)")
    ax.axhline(0, color="black", linestyle="--", linewidth=0.5)
    ax.set_title(f"EK80 ADCP velocity at depth bin {depth_idx} ({depth_m:.1f} m)")
    ax.set_xlabel("Time")
    ax.set_ylabel("Velocity (m s⁻¹)")
    ax.xaxis_date()
    ax.tick_params(axis="x", rotation=30)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend()
    plt.tight_layout()
    return fig, ax


def plot_hovmoller(
    ds: xr.Dataset,
    vmin: tuple[float, float, float] | None = None,
    vmax: tuple[float, float, float] | None = None,
    figsize: tuple[float, float] = (15, 18),
) -> tuple[Any, Any]:
    """Plot depth-time Hovmoller diagrams for vx, vy, and vz.

    Parameters
    ----------
    ds : xr.Dataset
        Dataset with ``vx``, ``vy``, ``vz`` and ``time``, ``depth`` coords.
    vmin : tuple of float or None, optional
        Colour scale minimum for each variable. Default is taken from the largest min or max value of the variable to create a symetrical colorbar.
    vmax : tuple of float or None, optional
        Colour scale maximum for each variable. Default is taken from the largest min or max value of the variable to create a symetrical colorbar.
    figsize : tuple of float, optional
        Figure size in inches.

    Returns
    -------
    fig, axes : matplotlib Figure and array of Axes

    """
    import cmocean  # noqa: PLC0415

    _use_style()

    x_time = mdates.date2num(ds["time"].values.astype("datetime64[ms]").astype(object))
    depths = ds["depth"].values

    fig, axes = plt.subplots(3, 1, figsize=figsize, sharex=True)
    components = [
        ("vx", "Eastward (vx)"),
        ("vy", "Northward (vy)"),
        ("vz", "Downward (vz)"),
    ]
    if vmin is not None and vmax is not None:
        min_max = {
            "vx": (vmin[0], vmax[0]),
            "vy": (vmin[1], vmax[1]),
            "vz": (vmin[2], vmax[2]),
        }
    else:
        min_max = {}
        for var in ["vx", "vy", "vz"]:
            max_value = ds[var].max()
            min_value = ds[var].min()
            if abs(max_value) >= abs(min_value):
                limit = max_value
            else:
                limit = min_value
            min_max[var] = (-limit, limit)

    for ax, (var, label) in zip(axes, components, strict=True):
        data = ds[var].values.T  # (depth, time)
        img = ax.pcolormesh(
            x_time,
            depths,
            np.ma.masked_invalid(data),
            cmap=cmocean.cm.balance,
            vmin=min_max[var][0],
            vmax=min_max[var][1],
            shading="auto",
        )
        ax.set_title(label)
        ax.set_ylabel("Depth (m)")
        ax.set_ylim(depths[-1], depths[0])
        cbar = fig.colorbar(img, ax=ax, pad=0.03)
        cbar.set_label("m s⁻¹")
        ax.xaxis_date()
        ax.tick_params(axis="x", rotation=30)

    axes[-1].set_xlabel("Time")
    fig.suptitle("EK80 ADCP velocity components")
    fig.tight_layout(rect=[0, 0, 1, 0.98])
    return fig, axes


def plot_track_quiver(
    ds: xr.Dataset,
    depth_idx: int | str = 0,
    step: int | None = None,
    figsize: tuple[float, float] = (10, 10),
) -> tuple[Any, Any]:
    """Plot platform track with current vector arrows.

    Parameters
    ----------
    ds : xr.Dataset
        Dataset with ``lon``, ``lat``, ``vx``, ``vy`` and ``time``, ``depth`` coords.
    depth_idx : int, optional
        Depth bin index to use for arrow magnitude. Default is 0 (shallowest).
    step : int or None, optional
        Subsample interval for arrows. ``None`` auto-selects ~150 arrows.
    figsize : tuple of float, optional
        Figure size in inches.

    Returns
    -------
    fig, ax : matplotlib Figure and Axes

    """
    _use_style()

    if depth_idx == "mean":
        u = ds["vx"].mean(dim="depth")
        v = ds["vy"].mean(dim="depth")
        title = "EK80 ADCP current vectors depth mean"
    elif isinstance(depth_idx, int):
        u = ds["vx"].isel(depth=depth_idx).values
        v = ds["vy"].isel(depth=depth_idx).values
        depth_m = float(ds.depth.values[depth_idx])
        title = f"EK80 ADCP current vectors at {depth_m:.1f} m"
    else:
        raise ValueError(
            f"{depth_idx} has no valid value, must be either int or 'mean'!"
        )

    margin = 0.05

    lon = ds["lon"].values
    lat = ds["lat"].values

    mask = np.isfinite(lon) & np.isfinite(lat) & np.isfinite(u) & np.isfinite(v)
    lon, lat, u, v = lon[mask], lat[mask], u[mask], v[mask]

    if step is None:
        step = max(1, len(lon) // 150)

    fig, ax = plt.subplots(figsize=figsize)
    ax.plot(lon, lat, color="gray", linewidth=1, alpha=0.8, label="Track")
    ax.quiver(
        lon[::step],
        lat[::step],
        u[::step],
        v[::step],
        angles="xy",
        scale_units="xy",
        scale=10,
        width=0.003,
    )
    ax.set_xlim(lon.min() - margin, lon.max() + margin)
    ax.set_ylim(lat.min() - margin, lat.max() + margin)

    ax.set_title(title)
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    ax.grid(visible=True, alpha=0.3)
    ax.legend()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    return fig, ax


def show_variables(data: str | xr.Dataset) -> Styler:
    """Extract variable information from a Dataset or netCDF file as a styled DataFrame.

    Parameters
    ----------
    data : str or xr.Dataset
        File path to a netCDF file or an xarray Dataset.

    Returns
    -------
    pandas.io.formats.style.Styler
        Styled DataFrame with columns ``dims``, ``units``, ``comment``,
        ``standard_name``, ``dtype``.

    """
    if isinstance(data, str):
        print(f"information is based on file: {data}")
        dataset = xr.open_dataset(data)
        variables = dataset.variables
    elif isinstance(data, xr.Dataset):
        print("information is based on xarray Dataset")
        variables = data.variables
    else:
        raise TypeError("Input data must be a file path (str) or an xarray Dataset")

    info = {}
    for i, key in enumerate(variables):
        var = variables[key]
        if isinstance(data, str):
            dims = var.dimensions[0] if len(var.dimensions) == 1 else "string"
            units = "" if not hasattr(var, "units") else var.units
            comment = "" if not hasattr(var, "comment") else var.comment
        else:
            dims = var.dims[0] if len(var.dims) == 1 else "string"
            units = var.attrs.get("units", "")
            comment = var.attrs.get("comment", "")

        info[i] = {
            "name": key,
            "dims": dims,
            "units": units,
            "comment": comment,
            "standard_name": var.attrs.get("standard_name", ""),
            "dtype": str(var.dtype) if isinstance(data, str) else str(var.data.dtype),
        }

    vars_df = DataFrame(info).T

    dim = vars_df.dims
    dim[dim.str.startswith("str")] = "string"
    vars_df["dims"] = dim

    return (
        vars_df.sort_values(["dims", "name"])
        .reset_index(drop=True)
        .loc[:, ["dims", "name", "units", "comment", "standard_name", "dtype"]]
        .set_index("name")
        .style
    )


def show_attributes(data: str | xr.Dataset) -> DataFrame:
    """Extract global attributes from a Dataset or netCDF file as a DataFrame.

    Parameters
    ----------
    data : str or xr.Dataset
        File path to a netCDF file or an xarray Dataset.

    Returns
    -------
    pandas.DataFrame
        DataFrame with columns ``Attribute``, ``Value``, ``DType``.

    """
    if isinstance(data, str):
        from netCDF4 import Dataset  # noqa: PLC0415

        print(f"information is based on file: {data}")
        rootgrp = Dataset(data, "r", format="NETCDF4")
        attributes = rootgrp.ncattrs()

        def get_attr(key: str) -> Any:
            return getattr(rootgrp, key)

    elif isinstance(data, xr.Dataset):
        print("information is based on xarray Dataset")
        attributes = data.attrs.keys()

        def get_attr(key: str) -> Any:
            return data.attrs[key]

    else:
        raise TypeError("Input data must be a file path (str) or an xarray Dataset")

    info = {}
    for i, key in enumerate(attributes):
        dtype = type(get_attr(key)).__name__
        info[i] = {"Attribute": key, "Value": get_attr(key), "DType": dtype}

    return DataFrame(info).T
