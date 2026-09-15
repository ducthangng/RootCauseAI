from pathlib import Path

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

def build_input_path(filename: str):
    return Path(__file__).resolve().parents[2] / "data/incoming" / f"{filename}"

def build_output_path(filename: str):
    return Path(__file__).resolve().parents[2] / "data/processed" / f"{filename}"

def build_bad_row_path(filename: str):
    return Path(__file__).resolve().parents[2] / "data/incoming" / f"{filename}"

# INPUT_PATH = Path(__file__).resolve().parents[3] / "data/incoming" / f"{}csv"

