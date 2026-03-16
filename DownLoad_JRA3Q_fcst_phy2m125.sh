#!/bin/bash

opts="-N"
cert_opt="--no-check-certificate"

# ============================================================
# Configurable time range
# Modify START_YEAR, END_YEAR, START_MONTH, END_MONTH to
# download data for a specific time span.
# Valid range: 1947-09 to present (1948-2023 for full years).
# ============================================================
START_YEAR=1948
END_YEAR=2023
START_MONTH=01
END_MONTH=12

# ============================================================
# Configurable variable selection
# Comment out any variables you do not need to save time and
# disk space.
# ============================================================
ALL_VARIABLES=(
    "0_0_10.lhtfl1have-sfc-fc-ll125"
    "0_0_11.shtfl1have-sfc-fc-ll125"
    "0_194_28.fgsu1have-sfc-fc-ll125"
    "0_194_29.fgsv1have-sfc-fc-ll125"
    "0_194_30.fglu1have-sfc-fc-ll125"
    "0_194_31.fglv1have-sfc-fc-ll125"
    "0_194_8.tuwv1have-col-fc-ll125"
    "0_194_9.tvwv1have-col-fc-ll125"
    "0_1_37.cprat1have-sfc-fc-ll125"
    "0_1_52.tprate1have-sfc-fc-ll125"
    "0_1_53.tsrwe1have-sfc-fc-ll125"
    "0_1_54.lsprate1have-sfc-fc-ll125"
    "0_1_79.evarate1have-sfc-fc-ll125"
    "0_2_17.uflx1have-sfc-fc-ll125"
    "0_2_18.vflx1have-sfc-fc-ll125"
    "0_3_0.pres1have-sfc-fc-ll125"
    "0_4_52.dswrfcs1have-sfc-fc-ll125"
    "0_4_53.uswrfcs1have-sfc-fc-ll125"
    "0_4_53.uswrfcs1have-toa-fc-ll125"
    "0_4_7.dswrf1have-sfc-fc-ll125"
    "0_4_7.dswrf1have-toa-fc-ll125"
    "0_4_8.uswrf1have-sfc-fc-ll125"
    "0_4_8.uswrf1have-toa-fc-ll125"
    "0_5_3.dlwrf1have-sfc-fc-ll125"
    "0_5_4.ulwrf1have-sfc-fc-ll125"
    "0_5_4.ulwrf1have-toa-fc-ll125"
    "0_5_6.nlwrcs1have-toa-fc-ll125"
    "0_5_8.dlwrfcs1have-sfc-fc-ll125"
)

# Loop through the specified years
for year in $(seq "$START_YEAR" "$END_YEAR")
do
    # Loop through each month within the specified range
    for month in $(seq -w "$START_MONTH" "$END_MONTH")
    do
        # Construct the month_year string used in the base URL
        month_year="${year}${month}"
        base_url="https://osdf-director.osg-htc.org/ncar/gdex/d640000/fcst_phy2m125/${month_year}"

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
        for var in "${ALL_VARIABLES[@]}"
        do
            file_name="jra3q.fcst_phy2m125.${var}.${month_year}0100_${month_year}${end_day}23.nc"
            
            # Check if the file already exists and is not empty
            if [ -f "$file_name" ] && [ -s "$file_name" ]; then
                echo "File $file_name already exists and is not empty. Skipping download."
            else
                echo "Downloading $file_name from $base_url..."
                # Download the file
                wget $cert_opt $opts "${base_url}/${file_name}"
            fi
        done
    done
done
