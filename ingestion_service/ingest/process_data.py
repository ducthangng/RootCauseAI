import os
import pandas as pd
import csv
import sys
import logging
from .process_data_type import COLUMNS, build_input_path, build_output_path, build_bad_row_path, get_raw_path, AWS_BUCKET_NAME
from .guardrails import sanitize_urls
from .push import upload_to_s3
from datetime import datetime, timezone

csv.field_size_limit(sys.maxsize)
log = logging.getLogger("processer")

def clean_data(filename: str):
    log.info(f" -- processing: {filename}")
    log.info(f" -- path: {build_input_path(filename=filename)}")
    # first rule of reading data: always read as string first, then convert each column later.
    df = pd.read_csv(
        build_input_path(filename),
        sep="\t",
        header=None,
        names=COLUMNS,
        dtype=str,                 # read as string first, always — see below
        encoding="latin-1",        # NOT utf-8. This file will throw UnicodeDecodeError or silently mangle text otherwise
        quoting=csv.QUOTE_NONE,    # CDESCR is free text and contains stray " characters — pandas' default quoting will misparse rows around them
        na_filter=False,           # keep empty fields as "" instead of NaN; you want that distinction for a column like FAILDATE
        low_memory=False
        # nrows=100
    )

    # script "
    df = df.apply(lambda col: col.str.replace('"', '', regex=False))

    # defang url in input field
    for col in ["COMPDESC", "CDESCR"]:
        df[col] = df[col].apply(sanitize_urls)

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

    df = df[df["COMPDESC"].str.len() > 5]

    # remove duplicates
    df = df.drop_duplicates(subset="CMPLID")

    # make the MFR_NAME universal
    df['MFR_NAME'] = df['MFR_NAME'].str.strip().str.upper().str.replace(" ", "_")

    # merge row with the same CDESCR
    # 1. Define your primary identifier (the Report ID column)
    report_id_col = 'ODINO' 

    # 2. Dynamically build the aggregation rules for all 54 columns
    agg_dict = {}

    for col in df.columns:
        if col == report_id_col:
            # Skip the grouping column; Pandas handles it automatically
            continue 
        elif col == 'CMPLID':
            # Rule for CMPLID: Take the smaller ID
            agg_dict[col] = 'min'
        elif col == 'COMPDESC':
            # Rule for COMPDESC: Merge the unique descriptions with a separator
            agg_dict[col] = lambda x: ' | '.join(x.dropna().astype(str).unique())
        else:
            # Rule for all other 51 columns: Keep the first value found
            agg_dict[col] = 'first'

    # 3. Group by the Report ID and apply the rules
    df = df.groupby(report_id_col, as_index=False).agg(agg_dict)
    
    # !TODO: add rich texts
    df['summary'] = 'a ' + df['MAKETXT'] + " model " + df['MODELTXT'] + " produced in " + df["YEARTXT"] + " was " + df['COMPDESC'] + " with detail: " + df['CDESCR']

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT_%H%M%SZ")

    raw_filename = filename.removesuffix((".csv"))
    new_filename = f"{raw_filename}_{stamp}.csv"
    output_path = build_output_path(filename=new_filename)

    log.info(f"writing -> {output_path}")
    df.to_csv(output_path, index=False)

    log.info(f"pushing to S3 {AWS_BUCKET_NAME}...")
    upload_to_s3(output_path, AWS_BUCKET_NAME, new_filename)

    
