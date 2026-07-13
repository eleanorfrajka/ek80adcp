"""Command-line interface for ek80adcp."""

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

import xarray as xr

from ek80adcp import logger
from ek80adcp.read_ek80 import read_ek80

_MANIFEST_NAME = "manifest.json"


def _find_nc_files(paths: list[str]) -> list[Path]:
    """Resolve input paths (files or directories) to non-empty .nc files.

    Parameters
    ----------
    paths : list of str
        File paths or directory paths to search.

    Returns
    -------
    list of Path
        Sorted, deduplicated list of non-empty .nc files.

    """
    seen: set[Path] = set()
    files: list[Path] = []
    for p in paths:
        path = Path(p)
        candidates = sorted(path.glob("*.nc")) if path.is_dir() else [path]
        for f in candidates:
            if f in seen or f.suffix.lower() != ".nc":
                continue
            try:
                size = f.stat().st_size
            except OSError as exc:
                print(f"Warning: cannot stat {f}, skipping ({exc}).", file=sys.stderr)
                continue
            if size > 0:
                seen.add(f)
                files.append(f)
    return sorted(files)


def _build_history(
    input_path: Path,
    depth_max: float | None,
    time_bin: str | None,
    method: str = "mean",
) -> str:
    """Build a CF-convention history string for the processing step.

    Parameters
    ----------
    input_path : Path
        The source file that was processed.
    depth_max : float or None
        ``--depth-max`` value used, or ``None`` if not applied.
    time_bin : str or None
        ``--time-bin`` value used, or ``None`` if not applied.
    method : str, optional
        Averaging method (``"mean"`` or ``"median"``). Default ``"mean"``.

    Returns
    -------
    str
        Single-line history entry in the form
        ``"YYYY-MM-DDTHH:MM:SSZ: ek80adcp extract [options] <filename>"``.

    """
    parts = ["ek80adcp extract"]
    if depth_max is not None:
        parts.append(f"--depth-max {depth_max}")
    if time_bin is not None:
        parts.append(f"--time-bin {time_bin}")
        parts.append(f"--method {method}")
    parts.append(input_path.name)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return f"{timestamp}: {' '.join(parts)}"


def _plot_hovmoller(ds: xr.Dataset, output_path: Path) -> None:
    """Save a 3-panel Hovmöller PNG (vx, vy, vz vs time and depth).

    Parameters
    ----------
    ds : xr.Dataset
        Dataset with ``(time, depth)`` dimensions and ``vx``, ``vy``,
        ``vz`` variables.
    output_path : Path
        NetCDF output path; PNG is saved alongside with the same stem
        and a ``.png`` suffix.

    """
    import matplotlib  # noqa: PLC0415
    import numpy as np  # noqa: PLC0415

    matplotlib.use("Agg")
    import cmocean  # noqa: F401, PLC0415  — registers cmo.* colormaps
    import matplotlib.dates as mdates  # noqa: PLC0415
    import matplotlib.pyplot as plt  # noqa: PLC0415

    plt.style.use(Path(__file__).resolve().parent / "ek80adcp.mplstyle")

    depths = ds.depth.values
    x_time = mdates.date2num(ds.time.values.astype("datetime64[ms]").astype("O"))

    fields = [("vx", ds["vx"].values), ("vy", ds["vy"].values), ("vz", ds["vz"].values)]
    fig, axes = plt.subplots(3, 1, figsize=(15, 18), sharex=True)

    for ax, (name, data) in zip(axes, fields, strict=True):
        img = ax.pcolormesh(
            x_time,
            depths,
            np.ma.masked_invalid(data.T),
            cmap="cmo.balance",
            vmin=-0.3,
            vmax=0.3,
            shading="auto",
        )
        ax.set_title(f"{name} versus time and depth")
        ax.set_ylabel("depth (m)")
        ax.set_ylim(depths[-1], 0)
        cbar = fig.colorbar(img, ax=ax, pad=0.03)
        cbar.set_label(f"{name} (m/s)")

    for ax in axes:
        ax.xaxis_date()
        ax.tick_params(axis="x", rotation=45)

    fig.autofmt_xdate()
    axes[-1].set_xlabel("time (date and hour)")
    fig.suptitle(f"Velocity components: {output_path.stem}", fontsize=22)
    fig.tight_layout(rect=[0, 0, 1, 0.98])

    png_path = output_path.with_suffix(".png")
    fig.savefig(png_path, dpi=100, bbox_inches="tight")
    plt.close(fig)


def _extract_one(
    input_path: Path,
    output_path: Path,
    depth_max: float | None,
    time_bin: str | None,
    method: str = "mean",
    plot: bool = False,
) -> dict:
    """Extract velocity data from one EK80 file and write a condensed NetCDF.

    Parameters
    ----------
    input_path : Path
        Input EK80 NetCDF file.
    output_path : Path
        Destination path for the condensed NetCDF.
    depth_max : float or None
        Keep only depth bins at or above this depth in metres. ``None``
        retains all bins.
    time_bin : str or None
        Pandas offset alias for time averaging (e.g. ``"60s"``, ``"5min"``).
        ``None`` keeps the native 2-second resolution.
    method : str, optional
        Averaging method when ``time_bin`` is set: ``"mean"`` (default) or
        ``"median"``.
    plot : bool, optional
        If ``True``, save a Hovmöller PNG alongside the NetCDF.

    Returns
    -------
    dict
        Summary with keys ``input``, ``output``, ``n_time``, ``n_depth``.

    """
    ds = read_ek80([input_path])

    if depth_max is not None:
        ds = ds.sel(depth=slice(None, depth_max))

    if time_bin is not None:
        resampled = ds.resample(time=time_bin)
        ds = (
            resampled.mean(skipna=True)
            if method == "mean"
            else resampled.median(skipna=True)
        )

    history_entry = _build_history(input_path, depth_max, time_bin, method)
    existing = ds.attrs.get("history", "")
    ds.attrs["history"] = (
        f"{existing}\n{history_entry}".strip() if existing else history_entry
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(output_path)

    if plot:
        try:
            _plot_hovmoller(ds, output_path)
        except Exception as exc:
            print(
                f"Warning: plot failed for {output_path.name}: {exc}", file=sys.stderr
            )

    return {
        "input": str(input_path),
        "output": str(output_path),
        "n_time": int(ds.sizes["time"]),
        "n_depth": int(ds.sizes["depth"]),
    }


def _load_manifest(path: Path) -> dict:
    """Load the processing manifest, or return a fresh one if absent.

    Parameters
    ----------
    path : Path
        Path to the manifest JSON file.

    Returns
    -------
    dict
        Manifest dict with a ``"files"`` list.

    """
    if path.exists():
        return json.loads(path.read_text())
    return {"files": []}


def _save_manifest(path: Path, manifest: dict) -> None:
    """Write the manifest dict to a JSON file.

    Parameters
    ----------
    path : Path
        Destination path.
    manifest : dict
        Manifest data to serialise.

    """
    path.write_text(json.dumps(manifest, indent=2))


def cmd_extract(args: argparse.Namespace) -> int:
    """Run the ``extract`` subcommand.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI arguments.

    Returns
    -------
    int
        Exit code (0 on success, 1 if any file failed).

    """
    logger.disable_logging()

    files = _find_nc_files(args.input)
    if not files:
        print("ek80adcp extract: no .nc files found.", file=sys.stderr)
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_path = output_dir / _MANIFEST_NAME
    manifest = _load_manifest(manifest_path)

    n_done = 0
    n_skip = 0
    n_err = 0

    for f in files:
        out = output_dir / f.name
        if args.skip_existing and out.exists():
            print(f"skip     {f.name}")
            n_skip += 1
            continue

        print(f"extract  {f.name} ...", end=" ", flush=True)
        try:
            result = _extract_one(
                f, out, args.depth_max, args.time_bin, args.method, args.plot
            )
            result["processed_at"] = datetime.now(UTC).isoformat()
            manifest["files"].append(result)
            _save_manifest(manifest_path, manifest)
            suffix = "  [+png]" if args.plot else ""
            print(f"time={result['n_time']}  depth={result['n_depth']}{suffix}")
            n_done += 1
        except Exception as exc:
            print(f"\nERROR: {exc}", file=sys.stderr)
            n_err += 1

    print(f"\n{n_done} extracted, {n_skip} skipped, {n_err} errors")
    return 0 if n_err == 0 else 1


_DATE_RE = re.compile(r"D(\d{8})")
_TIME_RE = re.compile(r"T(\d{8})")


def _date_key(path: Path) -> str | None:
    """Return the YYYYMMDD string embedded in a filename, or ``None``.

    Parameters
    ----------
    path : Path
        File whose stem contains ``D{YYYYMMDD}``, e.g.
        ``DSMIXSED2-D20260709-T161720.nc``.

    Returns
    -------
    str or None
        Eight-digit date string, e.g. ``"20260709"``, or ``None`` if the
        pattern is absent.

    """
    m = _DATE_RE.search(path.stem)
    return m.group(1) if m else None


def _time_key(path: Path) -> str | None:
    """Return the HHMMSS string embedded in a filename, or ``None``.

    Parameters
    ----------
    path : Path
        File whose stem contains ``T{HHMMSS}``, e.g.
        ``DSMIXSED2-D20260709-T161720.nc``.

    Returns
    -------
    str or None
        Eight-digit date string, e.g. ``"20260709"``, or ``None`` if the
        pattern is absent.

    """
    m = _TIME_RE.search(path.stem)
    return m.group(1) if m else None


def _stem_prefix(path: Path) -> str:
    """Return the part of the stem before the date token.

    Parameters
    ----------
    path : Path
        File whose stem contains ``D{YYYYMMDD}``, e.g.
        ``DSMIXSED2-D20260709-T161720.nc``.

    Returns
    -------
    str
        Everything before ``-D{YYYYMMDD}``, e.g. ``"DSMIXSED2"``.

    """
    m = re.match(r"^(.+?)-D\d{8}", path.stem)
    return m.group(1) if m else path.stem


def _concat_group(group_files: list[Path], output_path: Path, plot: bool) -> None:
    """Concatenate a list of NetCDF files and write the result.

    Parameters
    ----------
    group_files : list of Path
        Source files to concatenate (already sorted).
    output_path : Path
        Destination NetCDF file.
    plot : bool
        If ``True``, save a Hovmöller PNG alongside the NetCDF.

    """
    raw_datasets = [xr.open_dataset(f) for f in group_files]
    try:
        # The depth coordinate varies slightly between raw files (float precision
        # in depth_first_sample_center and vertical_sample_interval), so a plain
        # concat produces a union depth axis (outer join) that is 3× too large and
        # mostly NaN.  Fix: truncate all datasets to the shortest depth profile and
        # assign the first file's depth values so every dataset has an identical
        # coordinate before concatenation.
        datasets = raw_datasets
        if len(datasets) > 1:
            min_depth = min(ds.sizes["depth"] for ds in datasets)
            depth_ref = datasets[0].depth.values[:min_depth]
            datasets = [
                ds.isel(depth=slice(None, min_depth)).assign_coords(depth=depth_ref)
                for ds in datasets
            ]

        ds = xr.concat(datasets, dim="time")
        ds = ds.sortby("time")

        source_names = ", ".join(f.name for f in group_files)
        timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        history_entry = f"{timestamp}: ek80adcp concat {source_names}"
        existing = ds.attrs.get("history", "")
        ds.attrs["history"] = (
            f"{existing}\n{history_entry}".strip() if existing else history_entry
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        ds.to_netcdf(output_path)
        print(
            f"  saved {output_path.name}  "
            f"(time={ds.sizes['time']}, depth={ds.sizes['depth']})"
        )

        if plot:
            try:
                _plot_hovmoller(ds, output_path)
                print(f"  plot  {output_path.with_suffix('.png').name}")
            except Exception as exc:
                print(
                    f"Warning: plot failed for {output_path.name}: {exc}",
                    file=sys.stderr,
                )
    finally:
        for d in raw_datasets:
            d.close()


def cmd_concat(args: argparse.Namespace) -> int:
    """Run the ``concat`` subcommand.

    Parameters
    ----------
    args : argparse.Namespace
        Parsed CLI arguments.

    Returns
    -------
    int
        Exit code (0 on success, 1 on failure).

    """
    logger.disable_logging()

    files = _find_nc_files(args.input)
    output_path = Path(args.output)
    files = [f for f in files if f != output_path]

    if not files:
        print("ek80adcp concat: no .nc files found.", file=sys.stderr)
        return 1

    if args.by_day:
        groups: dict[str, list[Path]] = {}
        undated: list[Path] = []
        for f in files:
            key = _date_key(f)
            if key:
                groups.setdefault(key, []).append(f)
            else:
                undated.append(f)

        if undated:
            print(
                f"Warning: {len(undated)} file(s) lack a D{{YYYYMMDD}} token "
                "and will be skipped.",
                file=sys.stderr,
            )

        dated_files = [f for f in files if _date_key(f)]
        if not dated_files:
            print("ek80adcp concat --by-day: no dated files found.", file=sys.stderr)
            return 1
        prefix = _stem_prefix(dated_files[0])
        output_dir = output_path
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"By-day concat: {len(groups)} day(s) found.")
        for date_str, day_files in sorted(groups.items()):
            day_out = output_dir / f"{prefix}-D{date_str}.nc"
            print(
                f"  day {date_str}: {len(day_files)} file(s) ...", end=" ", flush=True
            )
            _concat_group(sorted(day_files), day_out, args.plot)

    elif args.by_time_range:
        in_time_range: list[Path] = []
        group: dict[str, list[Path]] = {}
        undated: list[Path] = []

        start_dt = args.by_time_range.split("--")[0]
        start_dt = datetime.strptime(start_dt, "D%Y%m%d-T%H%M%S")
        end_dt = args.by_time_range.split("--")[1]
        end_dt = datetime.strptime(end_dt, "D%Y%m%d-T%H%M%S")

        for f in files:
            key = _date_key(f)
            if key:
                date = "D" + str(_date_key(f))
                time = "T" + str(_time_key(f))
                dt = datetime.strptime(date + "--" + time, "D%Y%m%d-T%H%M%S")
                if start_dt <= dt <= end_dt:
                    in_time_range.append(f)
            else:
                undated.append(f)

        group[args.by_time_range] = in_time_range

        if undated:
            print(
                f"Warning: {len(undated)} file(s) lack a D{{YYYYMMDD}} token "
                "and will be skipped.",
                file=sys.stderr,
            )

        dated_files = [f for f in files if _date_key(f)]
        if not dated_files:
            print("ek80adcp concat --by-day: no dated files found.", file=sys.stderr)
            return 1
        prefix = _stem_prefix(dated_files[0])
        output_dir = output_path
        output_dir.mkdir(parents=True, exist_ok=True)

        print(
            f"By-time-range concat:{len(in_time_range)} files found in time range {args.by_time_range}."
        )
        time_range_out = output_dir / f"{prefix}-{args.by_time_range}.nc"
        print(
            f"  Time-range {args.by_time_range}: {len(in_time_range)} file(s) ...",
            end=" ",
            flush=True,
        )
        _concat_group(in_time_range, time_range_out, args.plot)

    else:
        print(f"Concatenating {len(files)} file(s) ...", end=" ", flush=True)
        _concat_group(sorted(files), output_path, args.plot)

    return 0


def main() -> None:
    """Entry point for the ``ek80adcp`` command-line tool."""
    parser = argparse.ArgumentParser(
        prog="ek80adcp",
        description="EK80 ADCP processing tools.",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    ext = sub.add_parser(
        "extract",
        help="Extract and condense EK80 velocity data.",
        description=(
            "Read EK80 NetCDF files, optionally subset by depth and/or "
            "resample in time, and write compact output files."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  ek80adcp extract /data/raw/ -o /data/out/ --depth-max 300\n"
            "  ek80adcp extract file.nc -o /data/out/ --depth-max 300 --time-bin 60s\n"
            "  ek80adcp extract /data/raw/ -o /data/out/ --skip-existing --plot\n"
        ),
    )
    ext.add_argument(
        "input",
        nargs="+",
        metavar="FILE_OR_DIR",
        help="Input .nc file(s) or director(ies) containing them.",
    )
    ext.add_argument(
        "-o",
        "--output-dir",
        required=True,
        metavar="DIR",
        help="Directory for output files (created if absent).",
    )
    ext.add_argument(
        "--depth-max",
        type=float,
        default=None,
        metavar="M",
        help="Discard depth bins below M metres (e.g. 300).",
    )
    ext.add_argument(
        "--time-bin",
        default=None,
        metavar="OFFSET",
        help=(
            "Resample to this time interval, e.g. '60s' or '5min'. "
            "Default: keep native 2-second resolution."
        ),
    )
    ext.add_argument(
        "--method",
        default="mean",
        choices=["mean", "median"],
        help="Averaging method when --time-bin is set (default: mean).",
    )
    ext.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip input files whose output already exists in DIR.",
    )
    ext.add_argument(
        "--plot",
        action="store_true",
        help="Save a 3-panel Hovmöller PNG for each extracted file.",
    )

    cat = sub.add_parser(
        "concat",
        help="Concatenate extracted NetCDF files into one dataset.",
        description=(
            "Load extracted NetCDF files, concatenate along time, and write "
            "output.  Without ``--by-day``, -o is a single output file.  "
            "With ``--by-day``, -o is a directory and one file per day is "
            "written, named ``{prefix}-D{YYYYMMDD}.nc``."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # One file per day from extracted files:\n"
            "  ek80adcp concat /data/out/ -o /data/daily/ --by-day\n"
            "  ek80adcp concat /data/out/ -o /data/daily/ --by-day --plot\n"
            "  # All days into one file:\n"
            "  ek80adcp concat /data/daily/ -o /data/combined.nc\n"
            "  ek80adcp concat /data/daily/ -o /data/combined.nc --plot\n"
        ),
    )
    cat.add_argument(
        "input",
        nargs="+",
        metavar="FILE_OR_DIR",
        help="Extracted .nc file(s) or a directory containing them.",
    )
    cat.add_argument(
        "-o",
        "--output",
        required=True,
        metavar="FILE_OR_DIR",
        help=(
            "Output file path (without --by-day) or output directory (with --by-day)."
        ),
    )
    cat.add_argument(
        "--by-day",
        action="store_true",
        help=(
            "Group input files by calendar day and write one NetCDF per day, "
            "named {prefix}-D{YYYYMMDD}.nc, into the -o directory."
        ),
    )
    cat.add_argument(
        "--by-time-range",
        type=str,
        metavar="TIME-RANGE",
        help=(
            "Group input files by time range and write as one NetCDF file."
            "Time range must be specified as a string e.g.: 'DYYYYMMDD-THHMMSS--DYYYYMMDD-THHMMSS.'"
        ),
    )
    cat.add_argument(
        "--plot",
        action="store_true",
        help="Save a Hovmöller PNG alongside each output file.",
    )

    parsed = parser.parse_args()
    if parsed.command == "extract":
        sys.exit(cmd_extract(parsed))
    elif parsed.command == "concat":
        sys.exit(cmd_concat(parsed))
    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
