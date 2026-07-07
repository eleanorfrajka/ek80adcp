"""Data loading functions for EK80 ADCP datasets."""

from pathlib import Path

import xarray as xr

from ek80adcp import logger
from ek80adcp.logger import log_info
from ek80adcp.read_ek80 import read_ek80

log = logger.log

# EK80 file names follow the pattern T{YYYYMM}-D{YYYYMMDD}-T{HHMMSS}.nc
_EK80_GLOB = "T*-D*-T*.nc"


def find_ek80_files(
    data_dir: str | Path | None = None,
    candidate_dirs: list[str | Path] | None = None,
) -> list[Path]:
    """Find EK80 ADCP NetCDF files matching the EK80 naming convention.

    Files are matched with the glob pattern ``T*-D*-T*.nc``.

    Parameters
    ----------
    data_dir : str or Path, optional
        Primary directory to search. Defaults to the project ``data/`` folder.
    candidate_dirs : list of str or Path, optional
        Additional directories to search. Appended after ``data_dir``.

    Returns
    -------
    list of Path
        Sorted, deduplicated list of matching file paths.

    """
    from ek80adcp.utilities import get_default_data_dir

    search_dirs: list[Path] = [Path(data_dir) if data_dir else get_default_data_dir()]
    if candidate_dirs:
        search_dirs.extend(Path(d) for d in candidate_dirs)

    seen: set[Path] = set()
    files: list[Path] = []
    for d in search_dirs:
        if d.exists():
            for f in sorted(d.glob(_EK80_GLOB)):
                if f not in seen:
                    seen.add(f)
                    files.append(f)

    log_info(
        "Found %d EK80 file(s) in %d director%s",
        len(files),
        len(search_dirs),
        "y" if len(search_dirs) == 1 else "ies",
    )
    return files


def load_ek80(
    data_dir: str | Path | None = None,
    file_list: list[str | Path] | None = None,
) -> xr.Dataset:
    """Load EK80 ADCP data from a directory or an explicit file list.

    Parameters
    ----------
    data_dir : str or Path, optional
        Directory containing EK80 NetCDF files. Ignored when ``file_list``
        is provided. Defaults to the project ``data/`` folder.
    file_list : list of str or Path, optional
        Explicit list of file paths to load. When provided, ``data_dir``
        is ignored.

    Returns
    -------
    xr.Dataset
        Combined dataset with dimensions ``(time, depth)``.

    Raises
    ------
    FileNotFoundError
        If no EK80 files are found.

    """
    if logger.LOGGING_ENABLED:
        logger.setup_logger(array_name="ek80")

    if file_list is not None:
        files = [Path(f) for f in file_list]
    else:
        files = find_ek80_files(data_dir=data_dir)

    if not files:
        searched = str(data_dir) if data_dir else "default data directory"
        raise FileNotFoundError(f"No EK80 NetCDF files found in {searched}.")

    log_info("Loading %d EK80 file(s)", len(files))
    return read_ek80(files)
