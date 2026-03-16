"""
Subset_Region.py
================
Subset downloaded JRA-3Q NetCDF files to a user-defined
geographic bounding box (latitude / longitude range).

After running one of the DownLoad_JRA3Q_*.sh scripts, use this
script to extract only the region of interest from the global
1.25° × 1.25° files.

Requirements
------------
    pip install xarray netCDF4

Usage
-----
1. Edit the CONFIGURATION section below to set your desired
   bounding box, input/output directories, and file patterns.
2. Run:
       python Subset_Region.py
"""

import os
import glob
import xarray as xr

# ============================================================
# CONFIGURATION – edit these values to suit your analysis
# ============================================================

# Geographic bounding box
# Longitude: 0 to 360 (E), or use -180 to 180
# Latitude : -90 (S) to 90 (N)
LON_MIN = 100.0   # western boundary (degrees East)
LON_MAX = 180.0   # eastern boundary (degrees East)
LAT_MIN = -60.0   # southern boundary (degrees North)
LAT_MAX =  60.0   # northern boundary (degrees North)

# Directory that contains the downloaded *.nc files
INPUT_DIR = "."

# Directory where subsetted files will be saved
OUTPUT_DIR = "subset_output"

# Glob pattern to match the files you want to subset.
# Examples:
#   "jra3q.anl_p125.0_0_0.tmp-pres-an-ll125.*.nc"  – temperature only
#   "jra3q.anl_p125.*.nc"                           – all pressure-level files
#   "jra3q.anl_surf125.*.nc"                        – all surface files
FILE_PATTERN = "jra3q.anl_p125.0_0_0.tmp-pres-an-ll125.*.nc"

# ============================================================
# END OF CONFIGURATION
# ============================================================


def subset_file(input_path: str, output_path: str,
                lon_min: float, lon_max: float,
                lat_min: float, lat_max: float) -> None:
    """
    Open *input_path*, slice to the requested bounding box, and
    write the result to *output_path*.

    JRA-3Q files use:
      - ``longitude`` coordinate ranging 0 – 358.75 °E
      - ``latitude``  coordinate ranging 90 °N – -90 °S
    """
    ds = xr.open_dataset(input_path)

    # Identify coordinate names (handle minor naming variations)
    lon_name = next((c for c in ds.coords if "lon" in c.lower()), None)
    lat_name = next((c for c in ds.coords if "lat" in c.lower()), None)

    if lon_name is None or lat_name is None:
        print(f"  WARNING: could not identify lat/lon coordinates in "
              f"{input_path}. Skipping.")
        ds.close()
        return

    # Determine latitude axis order (JRA-3Q is typically descending: 90→−90)
    lat_vals = ds[lat_name].values
    if lat_vals[0] > lat_vals[-1]:
        # Descending axis (north to south): slice from north to south
        lat_slice = slice(lat_max, lat_min)
    else:
        # Ascending axis (south to north): slice from south to north
        lat_slice = slice(lat_min, lat_max)

    # Perform the spatial subset
    ds_subset = ds.sel(
        {
            lon_name: slice(lon_min, lon_max),
            lat_name: lat_slice,
        }
    )

    if ds_subset[lon_name].size == 0 or ds_subset[lat_name].size == 0:
        print(f"  WARNING: empty subset for {input_path}. "
              f"Check bounding box values. Skipping.")
        ds.close()
        return

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    ds_subset.to_netcdf(output_path)
    ds.close()
    print(f"  Saved → {output_path}")


def main() -> None:
    print("=" * 60)
    print(" JRA-3Q Regional Subset Tool")
    print(f" Bounding box : lon [{LON_MIN}, {LON_MAX}]  "
          f"lat [{LAT_MIN}, {LAT_MAX}]")
    print(f" Input dir    : {os.path.abspath(INPUT_DIR)}")
    print(f" Output dir   : {os.path.abspath(OUTPUT_DIR)}")
    print(f" Pattern      : {FILE_PATTERN}")
    print("=" * 60)

    search_pattern = os.path.join(INPUT_DIR, FILE_PATTERN)
    files = sorted(glob.glob(search_pattern))

    if not files:
        print(f"No files matched: {search_pattern}")
        return

    print(f"Found {len(files)} file(s) to process.\n")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for input_path in files:
        file_name = os.path.basename(input_path)
        output_path = os.path.join(OUTPUT_DIR, file_name)

        if os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
            print(f"  Skipping (already exists): {file_name}")
            continue

        print(f"Processing: {file_name}")
        try:
            subset_file(input_path, output_path,
                        LON_MIN, LON_MAX, LAT_MIN, LAT_MAX)
        except Exception as exc:
            print(f"  ERROR processing {file_name}: {exc}")

    print("\nDone.")


if __name__ == "__main__":
    main()
