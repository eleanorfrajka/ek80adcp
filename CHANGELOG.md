# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!-- towncrier release notes start -->

## [Unreleased]

### Features
- Add `ek80adcp extract` CLI command to condense EK80 velocity files with
  optional depth subsetting (`--depth-max`) and time averaging (`--time-bin`).
  Processing parameters are recorded in the `history` attribute of each
  output NetCDF. Hovmöller PNGs can be saved alongside with `--plot`.
- Add `ek80adcp concat` CLI command to concatenate extracted files along
  time, with `--by-day` grouping to produce one NetCDF per calendar day.

## [0.0.1] - 2026-07-09

### Features
- Read EK80 ADCP NetCDF files (VLEN velocity profiles, nanosecond timestamps)
  into compact xarray Datasets with `(time, depth)` dimensions
- Hovmöller and quiver plot functions using `cmocean` colourmaps
- Unit conversion utilities and NetCDF4 writer with attribute coercion