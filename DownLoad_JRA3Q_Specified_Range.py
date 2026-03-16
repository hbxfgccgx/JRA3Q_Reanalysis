#!/usr/bin/env python3
"""
Download JRA-3Q reanalysis data for a user-specified time range and variable set.

Supports the following datasets:
  - anl_p125   : 1.25° isobaric analysis fields (45 pressure levels, 0.01–1000 hPa)
  - anl_surf125: 1.25° surface analysis fields
  - fcst_phy2m125: 1.25° two-dimensional average diagnostic fields

Usage examples
--------------
# List available variables for the pressure-level dataset:
  python DownLoad_JRA3Q_Specified_Range.py --dataset anl_p125 --list-vars

# Download temperature at pressure levels for January–December 2000:
  python DownLoad_JRA3Q_Specified_Range.py --dataset anl_p125 --vars tmp \
      --start-year 2000 --end-year 2000

# Download temperature and specific humidity for 2010–2020, saving to ./data/:
  python DownLoad_JRA3Q_Specified_Range.py --dataset anl_p125 --vars tmp spfh \
      --start-year 2010 --end-year 2020 --output-dir ./data

# Download surface temperature for June–August 1980:
  python DownLoad_JRA3Q_Specified_Range.py --dataset anl_surf125 --vars tmp2m \
      --start-year 1980 --start-month 6 --end-year 1980 --end-month 8

Notes
-----
- JRA-3Q covers September 1947 to the present (data archived on NCAR/RDA as
  d640000). The default year range is 1948–2023.
- JRA-3Q is an *atmospheric* reanalysis. It provides pressure-level temperature
  (tmp), specific/relative humidity, and wind fields, but does not include
  ocean-interior temperature or salinity profiles. For full-ocean-depth
  temperature and salinity, consider ocean reanalysis products such as EN4,
  GLORYS12, or SODA instead.
- Downloaded files are global (1.25° × 1.25°). To extract a specific geographic
  region after downloading, use tools such as CDO or xarray/NetCDF4 in Python:
    import xarray as xr
    ds = xr.open_dataset("jra3q.anl_p125.0_0_0.tmp-pres-an-ll125.*.nc")
    region = ds.sel(latitude=slice(90, -90), longitude=slice(100, 180))
"""

import os
import sys
import ssl
import argparse
import calendar
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------------------------------------------------------------------
# Variable catalogue
# ---------------------------------------------------------------------------

VARIABLES = {
    "anl_p125": {
        "tmp":  "0_0_0.tmp-pres-an-ll125",
        "spfh": "0_1_0.spfh-pres-an-ll125",
        "rh":   "0_1_1.rh-pres-an-ll125",
        "ugrd": "0_2_2.ugrd-pres-an-ll125",
        "vgrd": "0_2_3.vgrd-pres-an-ll125",
        "vvel": "0_2_8.vvel-pres-an-ll125",
        "hgt":  "0_3_5.hgt-pres-an-ll125",
        "depr": "0_0_7.depr-pres-an-ll125",
        "relv": "0_2_12.relv-pres-an-ll125",
        "reld": "0_2_13.reld-pres-an-ll125",
        "strm": "0_2_4.strm-pres-an-ll125",
        "vpot": "0_2_5.vpot-pres-an-ll125",
    },
    "anl_surf125": {
        "tmp2m":  "0_0_0.tmp2m-hgt-an-ll125",
        "pot":    "0_0_2.pot-sfc-an-ll125",
        "depr2m": "0_0_7.depr2m-hgt-an-ll125",
        "snleng": "0_194_6.snleng-sfc-an-ll125",
        "snlh2o": "0_194_7.snlh2o-sfc-an-ll125",
        "spfh2m": "0_1_0.spfh2m-hgt-an-ll125",
        "rh2m":   "0_1_1.rh2m-hgt-an-ll125",
        "weasd":  "0_1_13.weasd-sfc-an-ll125",
        "tciwv":  "0_1_64.tciwv-col-an-ll125",
        "pres":   "0_3_0.pres-sfc-an-ll125",
        "vgrd10m":"0_2_3.vgrd10m-hgt-an-ll125",
        "ugrd10m":"0_2_2.ugrd10m-hgt-an-ll125",
        "prmsl":  "0_3_1.prmsl-msl-an-ll125",
    },
    "fcst_phy2m125": {
        "lhtfl":   "0_0_10.lhtfl1have-sfc-fc-ll125",
        "shtfl":   "0_0_11.shtfl1have-sfc-fc-ll125",
        "fgsu":    "0_194_28.fgsu1have-sfc-fc-ll125",
        "fgsv":    "0_194_29.fgsv1have-sfc-fc-ll125",
        "fglu":    "0_194_30.fglu1have-sfc-fc-ll125",
        "fglv":    "0_194_31.fglv1have-sfc-fc-ll125",
        "tuwv":    "0_194_8.tuwv1have-col-fc-ll125",
        "tvwv":    "0_194_9.tvwv1have-col-fc-ll125",
        "cprat":   "0_1_37.cprat1have-sfc-fc-ll125",
        "tprate":  "0_1_52.tprate1have-sfc-fc-ll125",
        "tsrwe":   "0_1_53.tsrwe1have-sfc-fc-ll125",
        "lsprate": "0_1_54.lsprate1have-sfc-fc-ll125",
        "evarate": "0_1_79.evarate1have-sfc-fc-ll125",
        "uflx":    "0_2_17.uflx1have-sfc-fc-ll125",
        "vflx":    "0_2_18.vflx1have-sfc-fc-ll125",
        "pres1h":  "0_3_0.pres1have-sfc-fc-ll125",
        "dswrfcs": "0_4_52.dswrfcs1have-sfc-fc-ll125",
        "uswrfcs": "0_4_53.uswrfcs1have-sfc-fc-ll125",
        "dswrf":   "0_4_7.dswrf1have-sfc-fc-ll125",
        "uswrf":   "0_4_8.uswrf1have-sfc-fc-ll125",
        "dlwrf":   "0_5_3.dlwrf1have-sfc-fc-ll125",
        "ulwrf":   "0_5_4.ulwrf1have-sfc-fc-ll125",
        "dlwrfcs": "0_5_8.dlwrfcs1have-sfc-fc-ll125",
    },
}

BASE_URL = "https://osdf-director.osg-htc.org/ncar/gdex/d640000"

# End-hour differs between dataset families
_END_HOUR = {
    "anl_p125":    "18",
    "anl_surf125": "18",
    "fcst_phy2m125": "23",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def _build_file_name(dataset: str, var_code: str, year: int, month: int) -> str:
    end_day = _last_day(year, month)
    end_hour = _END_HOUR[dataset]
    start = f"{year}{month:02d}0100"
    end   = f"{year}{month:02d}{end_day:02d}{end_hour}"
    return f"jra3q.{dataset}.{var_code}.{start}_{end}.nc"


def _ssl_opener() -> urllib.request.OpenerDirector:
    """Return a urllib opener that skips TLS certificate verification."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return urllib.request.build_opener(urllib.request.HTTPSHandler(context=ctx))


def _download_file(url: str, output_dir: str, no_check_cert: bool = True) -> bool:
    """Download *url* into *output_dir*.  Returns True on success."""
    file_name = os.path.basename(url)
    output_path = os.path.join(output_dir, file_name)

    if os.path.isfile(output_path) and os.path.getsize(output_path) > 0:
        print(f"[skip]  {file_name}  (already exists)")
        return True

    print(f"[dl]    {file_name}")
    opener = _ssl_opener() if no_check_cert else urllib.request.build_opener()
    try:
        with opener.open(url) as resp, open(output_path, "wb") as out:
            out.write(resp.read())
        print(f"[done]  {file_name}")
        return True
    except Exception as exc:
        print(f"[fail]  {file_name}: {exc}")
        if os.path.isfile(output_path):
            os.remove(output_path)
        return False


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download JRA-3Q reanalysis data for a specified time range and "
            "variable set."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dataset",
        choices=list(VARIABLES.keys()),
        default="anl_p125",
        help="Dataset type to download (default: anl_p125).",
    )
    parser.add_argument(
        "--vars",
        nargs="+",
        metavar="VAR",
        help=(
            "Short variable name(s) to download. "
            "Use --list-vars to see available options for the selected dataset."
        ),
    )
    parser.add_argument(
        "--start-year", type=int, default=1948,
        help="Start year, inclusive (default: 1948).",
    )
    parser.add_argument(
        "--end-year", type=int, default=2023,
        help="End year, inclusive (default: 2023).",
    )
    parser.add_argument(
        "--start-month", type=int, default=1,
        choices=range(1, 13), metavar="MONTH",
        help="Start month 1–12, inclusive (default: 1).",
    )
    parser.add_argument(
        "--end-month", type=int, default=12,
        choices=range(1, 13), metavar="MONTH",
        help="End month 1–12, inclusive (default: 12).",
    )
    parser.add_argument(
        "--output-dir", default=".",
        help="Directory to save downloaded files (default: current directory).",
    )
    parser.add_argument(
        "--workers", type=int, default=4,
        help="Number of parallel download workers (default: 4).",
    )
    parser.add_argument(
        "--list-vars", action="store_true",
        help="List available variable short names for the selected dataset and exit.",
    )
    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    avail = VARIABLES[args.dataset]

    # --list-vars early exit
    if args.list_vars:
        print(f"Variables available for dataset '{args.dataset}':\n")
        print(f"  {'Short name':<12}  Variable code")
        print(f"  {'-'*12}  {'-'*40}")
        for short, code in avail.items():
            print(f"  {short:<12}  {code}")
        return

    if not args.vars:
        parser.error("--vars is required (or use --list-vars to see available variables).")

    # Validate variable names
    unknown = [v for v in args.vars if v not in avail]
    if unknown:
        print(f"Error: unknown variable(s): {', '.join(unknown)}")
        print(f"Run with --list-vars to see valid options for dataset '{args.dataset}'.")
        sys.exit(1)

    # Validate year/month range
    if args.start_year > args.end_year:
        print("Error: --start-year must be <= --end-year.")
        sys.exit(1)
    if args.start_year == args.end_year and args.start_month > args.end_month:
        print("Error: --start-month must be <= --end-month when start and end year are equal.")
        sys.exit(1)
    if args.start_year < 1947 or args.end_year > 2025:
        print(
            "Warning: JRA-3Q covers Sep 1947 to the present. "
            "Files outside this range may not exist on the server."
        )

    os.makedirs(args.output_dir, exist_ok=True)

    # Build download task list
    tasks: list[tuple[str, str]] = []
    for year in range(args.start_year, args.end_year + 1):
        month_start = args.start_month if year == args.start_year else 1
        month_end   = args.end_month   if year == args.end_year   else 12
        for month in range(month_start, month_end + 1):
            month_year = f"{year}{month:02d}"
            base_url   = f"{BASE_URL}/{args.dataset}/{month_year}"
            for var_name in args.vars:
                var_code  = avail[var_name]
                file_name = _build_file_name(args.dataset, var_code, year, month)
                tasks.append((f"{base_url}/{file_name}", args.output_dir))

    print(f"Dataset   : {args.dataset}")
    print(f"Variables : {', '.join(args.vars)}")
    print(f"Period    : {args.start_year}-{args.start_month:02d} to {args.end_year}-{args.end_month:02d}")
    print(f"Output dir: {os.path.abspath(args.output_dir)}")
    print(f"Files     : {len(tasks)}")
    print()

    # Parallel downloads
    success = failed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(_download_file, url, out_dir): url
            for url, out_dir in tasks
        }
        for future in as_completed(futures):
            if future.result():
                success += 1
            else:
                failed += 1

    print(f"\nFinished — success: {success}, failed: {failed}")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
