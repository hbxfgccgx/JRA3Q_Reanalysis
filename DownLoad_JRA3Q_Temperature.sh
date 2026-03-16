#!/bin/bash
# ============================================================
# DownLoad_JRA3Q_Temperature.sh
#
# Downloads JRA-3Q 1.25° isobaric analysis temperature data
# (anl_p125) for a user-defined time span.
#
# JRA-3Q provides atmospheric temperature at 45 pressure levels
# (0.01–1000 hPa), which enables vertical profile analysis
# across the entire atmospheric column.
#
# After downloading, run Subset_Region.py to extract a specific
# geographic bounding box from the global files.
# ============================================================

opts="-N"
cert_opt="--no-check-certificate"

# ============================================================
# Configurable time range
# Modify the four variables below to select your time span.
# Valid range: 1947-09 to present (1948-2023 for full years).
# Example: START_YEAR=1990 END_YEAR=2000 for 1990-2000 data.
# ============================================================
START_YEAR=1990
END_YEAR=2020
START_MONTH=01
END_MONTH=12

# ============================================================
# Variable to download
# 0_0_0.tmp-pres-an-ll125 : Temperature at pressure levels (K)
# To also download specific humidity uncomment the second line.
# ============================================================
VARIABLES=(
    "0_0_0.tmp-pres-an-ll125"
    # "0_1_0.spfh-pres-an-ll125"   # Specific humidity (optional)
)

echo "============================================================"
echo " JRA-3Q Pressure-Level Temperature Download"
echo " Period : ${START_YEAR}-${START_MONTH} to ${END_YEAR}-${END_MONTH}"
echo " Variables : ${VARIABLES[*]}"
echo "============================================================"

# Loop through the specified years
for year in $(seq "$START_YEAR" "$END_YEAR")
do
    # Loop through each month within the specified range
    for month in $(seq -w "$START_MONTH" "$END_MONTH")
    do
        # Construct the month_year string used in the base URL
        month_year="${year}${month}"
        base_url="https://osdf-director.osg-htc.org/ncar/gdex/d640000/anl_p125/${month_year}"

        # Determine the end day of the month to handle February and leap years
        if [ "$month" == "02" ]; then
            if ((year % 4 == 0 && (year % 100 != 0 || year % 400 == 0))); then
                end_day="29" # Leap year February
            else
                end_day="28" # Non-leap year February
            fi
        elif [[ "$month" == "04" || "$month" == "06" || "$month" == "09" || "$month" == "11" ]]; then
            end_day="30"
        else
            end_day="31"
        fi

        # Loop through each variable code
        for var in "${VARIABLES[@]}"
        do
            start_time="${year}${month}0100"
            end_time="${year}${month}${end_day}18"
            file_name="jra3q.anl_p125.${var}.${start_time}_${end_time}.nc"

            # Check if the file already exists and is not empty
            if [ -f "$file_name" ] && [ -s "$file_name" ]; then
                echo "File $file_name already exists and is not empty. Skipping download."
            else
                echo "Downloading $file_name..."
                wget $cert_opt $opts "$base_url/$file_name"
            fi
        done
    done
done

echo "============================================================"
echo " Download complete."
echo " To subset the files to a specific geographic region, run:"
echo "   python Subset_Region.py"
echo "============================================================"
