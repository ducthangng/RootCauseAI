import os
import pandas as pd
import csv

COLUMNS = [
    "CMPLID", "ODINO", "MFR_NAME", "MAKETXT", "MODELTXT", "YEARTXT",
    "CRASH", "FAILDATE", "FIRE", "INJURED", "DEATHS", "COMPDESC",
    "CITY", "STATE", "VIN", "DATEA", "LDATE", "MILES", "OCCURENCES",
    "CDESCR", "CMPL_TYPE", "POLICE_RPT_YN", "PURCH_DT", "ORIG_OWNER_YN",
    "ANTI_BRAKES_YN", "CRUISE_CONT_YN", "NUM_CYLS", "DRIVE_TRAIN",
    "FUEL_SYS", "FUEL_TYPE", "TRANS_TYPE", "VEH_SPEED", "DOT",
    "TIRE_SIZE", "LOC_OF_TIRE", "TIRE_FAIL_TYPE", "ORIG_EQUIP_YN",
    "MANUF_DT", "SEAT_TYPE", "RESTRAINT_TYPE", "DEALER_NAME",
    "DEALER_TEL", "DEALER_CITY", "DEALER_STATE", "DEALER_ZIP",
    "PROD_TYPE", "REPAIRED_YN", "MEDICAL_ATTN", "VEHICLES_TOWED_YN",
    "STATE_OF_INCIDENT", "VEHICLE_OPERATOR",
]  # 51 fields, official NHTSA CMPL layout — position matters, this is not negotiable

# !IMPORTANT Columns
# COMPDESC: SPECIFIC COMPONENT'S DESCRIPTION
# CDESCR: CHAR(2048)    DESCRIPTION OF THE COMPLAINT
# OCCURENCES        NUMBER(4)     NUMBER OF OCCURRENCES

def clean_date():
    # first rule of reading data: always read as string first, then convert each column later.
    df = pd.read_csv(
        "FLAT_CMPL.txt",
        sep="\t",
        header=None,
        names=COLUMNS,
        dtype=str,                 # read as string first, always — see below
        encoding="latin-1",        # NOT utf-8. This file will throw UnicodeDecodeError or silently mangle text otherwise
        quoting=csv.QUOTE_NONE,    # CDESCR is free text and contains stray " characters — pandas' default quoting will misparse rows around them
        na_filter=False,           # keep empty fields as "" instead of NaN; you want that distinction for a column like FAILDATE
        low_memory=False,
    )

    numeric_cols = ["INJURED", "DEATHS", "MILES", "OCCURENCES", "NUM_CYLS", "VEH_SPEED"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    
    date_cols = ["FAILDATE", "DATEA", "LDATE", "PURCH_DT", "MANUF_DT"]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], format="%Y%m%d", errors="coerce")

    for col in date_cols:
        raw_col_name = col + "_RAW_INVALID"

        # Step 1: create the new column, start empty
        df[raw_col_name] = pd.NaT

        # Step 2: go row by row and check this column's value
        for i in range(len(df)):
            value = df.loc[i, col]

            is_too_late = value > pd.Timestamp("2026-09-08")
            is_too_early = value < pd.Timestamp("1886-01-01")

            if is_too_late or is_too_early:
                # Step 3: save the wrong value into the new column
                df.loc[i, raw_col_name] = value
                # Step 4: clear the original column
                df.loc[i, col] = pd.NaT

    df.to_csv("cleaned_input.csv", index=False)


def read_file():
    df = pd.read_csv(
        "cleaned_input.csv",
        dtype=str,              # still read everything as string first — parse dates explicitly after, don't trust auto-inference
        na_filter=False,        # keep this if you still want "" instead of NaN for untouched blank fields
        low_memory=False,
    )

    date_cols = ["FAILDATE", "DATEA", "LDATE", "PURCH_DT", "MANUF_DT"]
    for col in date_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")  # "" and garbage both become NaT here

    raw_cols = [col + "_RAW_INVALID" for col in date_cols]
    for col in raw_cols:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    raw_cols = df.loc[df[raw_cols].notna().any(axis=1)]

    # newdf = df.loc[df["FAILDATE_RAW_INVALID"].notna() | df["DATEA_RAW_INVALID"].notna() | df["LDATE_RAW_INVALID"].notna() | df["PURCH_DT_RAW_INVALID"].notna() | df["MANUF_DT_RAW_INVALID"].notna()]
    raw_cols.to_csv("small-input.csv",index=False)

    

    
    

    