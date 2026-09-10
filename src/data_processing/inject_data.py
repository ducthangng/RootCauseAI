
import pandas as pd
import src.data_processing.connect_pg

def inject():
    df = pd.read_csv(
        "assets/cleaned_input.csv",
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

    raw_cols = df.loc[df["MFR_NAME"] == ""]
    print(len(raw_cols.index))

    raw_cols = df.loc[df["CMPLID"] == ""]
    print(len(raw_cols.index))

    raw_cols = df.loc[df["ODINO"] == ""]
    print(len(raw_cols.index))

    
    # print(len(df.index))
    # df.sort_values(by='DEATHS', ascending=False).head(100).to_csv("input.csv", index=False)
    # check for cols with invalid date
    # raw_cols = df.loc[df[raw_cols].notna().any(axis=1)]
    # raw_cols.s.to_csv("small-input.csv",index=False)

    # !TODO: check for cols with too short context
    # !TODO: check for cols with sensitive values

    # connect_pg.insert_dataframe(df)

