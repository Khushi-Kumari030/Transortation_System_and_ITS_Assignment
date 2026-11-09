
import zipfile
import re
from pathlib import Path

import pandas as pd
import numpy as np


# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parents[1]
ZIP_PATH = PROJECT_DIR / "data" / "original" / "traffic.zip"

OUTPUT_DIR = PROJECT_DIR / "data" / "processed"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VEHICLES = ["car", "motorbike", "bus", "truck"]
KEYS = ["Time", "Direction"]


# ---------------------------------------------------------
# HELPER: IDENTIFY CAMERA, DAY AND SEGMENT
# ---------------------------------------------------------

def parse_filename(filename):

    name = Path(filename).stem

    continuation = name.endswith("_one")
    if continuation:
        name = name[:-4]

    match = re.match(r"([a-zA-Z]+\d+)_(\d+)$", name)

    if not match:
        return None

    camera = match.group(1)
    day = int(match.group(2))

    return {
        "Camera": camera,
        "Day": day,
        "Segment": "continuation" if continuation else "primary"
    }


# ---------------------------------------------------------
# HELPER: READ AND CLEAN ONE CSV
# ---------------------------------------------------------

def read_one_file(zip_file, filename):

    with zip_file.open(filename) as f:
        df = pd.read_csv(f)

    required = ["Time", "Direction"] + VEHICLES

    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(
            f"Missing columns in {filename}: {missing}"
        )

    df = df[required].copy()

    df["Time"] = df["Time"].astype(str).str.strip()
    df["Direction"] = (
        df["Direction"].astype(str).str.strip().str.upper()
    )

    df = df[
        df["Time"].notna()
        & df["Direction"].notna()
        & (df["Time"] != "")
        & (df["Time"].str.lower() != "nan")
        & (df["Direction"] != "")
    ].copy()

    for col in VEHICLES:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=VEHICLES)

    # Repeated frame-level records are collapsed to one
    # cumulative counter per timestamp and direction.
    df = (
        df.groupby(KEYS, as_index=False)[VEHICLES]
        .max()
    )

    df["Timestamp"] = pd.to_datetime(
        df["Time"], format="%H:%M:%S", errors="coerce"
    )

    df = df.dropna(subset=["Timestamp"])
    df = df.sort_values(["Direction", "Timestamp"])

    return df


# ---------------------------------------------------------
# STEP 1: LOAD ALL FILES AND CALCULATE WITHIN-FILE ARRIVALS
# ---------------------------------------------------------

file_data = {}
file_metadata = []

with zipfile.ZipFile(ZIP_PATH, "r") as z:

    csv_files = [
        name for name in z.namelist()
        if name.lower().endswith(".csv")
    ]

    print("CSV files found:", len(csv_files))

    for filename in csv_files:

        metadata = parse_filename(filename)

        if metadata is None:
            print("Skipping unrecognised filename:", filename)
            continue

        df = read_one_file(z, filename)

        if df.empty:
            print("Skipping empty file:", filename)
            continue

        # Calculate differences separately for each direction.
        df[VEHICLES] = (
            df.groupby("Direction")[VEHICLES]
            .diff()
        )

        # First observation of each direction is unknown.
        # Negative differences are invalid and flagged.
        negative_mask = df[VEHICLES].lt(0).any(axis=1)

        negative_count = int(negative_mask.sum())

        # Do not convert negative differences to zero.
        # Keep them missing so they cannot inflate totals.
        df.loc[negative_mask, VEHICLES] = np.nan

        # Preserve the first observation as missing.
        df[VEHICLES] = df[VEHICLES].astype(float)

        df["Source_File"] = Path(filename).name
        df["Camera"] = metadata["Camera"]
        df["Day"] = metadata["Day"]
        df["Segment"] = metadata["Segment"]

        file_data[filename] = df

        file_metadata.append({
            "Source_File": Path(filename).name,
            "Camera": metadata["Camera"],
            "Day": metadata["Day"],
            "Segment": metadata["Segment"],
            "First_Time": df["Time"].min(),
            "Last_Time": df["Time"].max(),
            "Unique_Timestamps": df["Time"].nunique(),
            "Negative_Difference_Rows": negative_count
        })


# ---------------------------------------------------------
# STEP 2: IDENTIFY PRIMARY / CONTINUATION PAIRS
# ---------------------------------------------------------

primary_lookup = {}

for filename in file_data:

    meta = parse_filename(filename)

    if meta["Segment"] == "primary":
        key = (meta["Camera"], meta["Day"])
        primary_lookup[key] = filename


# ---------------------------------------------------------
# STEP 3: REMOVE OVERLAPPING CONTINUATION PERIODS
# ---------------------------------------------------------

final_parts = []
segment_audit = []

for filename, df in file_data.items():

    meta = parse_filename(filename)

    camera = meta["Camera"]
    day = meta["Day"]
    segment = meta["Segment"]

    retained = df.copy()
    cutoff = None
    action = "Retained all timestamps"

    if segment == "continuation":

        primary_filename = primary_lookup.get((camera, day))

        if primary_filename is not None:

            primary_df = file_data[primary_filename]

            primary_end = primary_df["Timestamp"].max()
            continuation_start = df["Timestamp"].min()

            cutoff = primary_end.strftime("%H:%M:%S")

            # Primary owns all timestamps up to and including
            # its final timestamp. Continuation contributes
            # only later timestamps.
            retained = df[df["Timestamp"] > primary_end].copy()

            action = "Continuation clipped at primary end"

            if continuation_start > primary_end:
                action = "Continuation retained after gap"

        else:
            action = "No matching primary file"

    segment_audit.append({
        "Source_File": Path(filename).name,
        "Camera": camera,
        "Day": day,
        "Segment": segment,
        "Cutoff_Time": cutoff,
        "Original_Rows": len(df),
        "Retained_Rows": len(retained),
        "Removed_Rows": len(df) - len(retained),
        "Action": action
    })

    if not retained.empty:
        final_parts.append(retained)


# ---------------------------------------------------------
# STEP 4: COMBINE AND SAVE
# ---------------------------------------------------------

if not final_parts:
    raise RuntimeError("No records available after processing.")

final_df = pd.concat(final_parts, ignore_index=True)

final_df = final_df[
    [
        "Day",
        "Camera",
        "Direction",
        "Time",
        "Timestamp",
        *VEHICLES,
        "Segment",
        "Source_File"
    ]
]

final_df = final_df.sort_values(
    ["Day", "Camera", "Direction", "Timestamp"]
)

# The dataset contains one row per camera, direction and
# timestamp. It does not combine different cameras.
output_file = OUTPUT_DIR / "corrected_vehicle_arrivals.csv"
final_df.to_csv(output_file, index=False)


# ---------------------------------------------------------
# STEP 5: SAVE AUDIT FILES
# ---------------------------------------------------------

file_audit = pd.DataFrame(file_metadata)
segment_audit = pd.DataFrame(segment_audit)

file_audit.to_csv(
    OUTPUT_DIR / "file_processing_audit.csv",
    index=False
)

segment_audit.to_csv(
    OUTPUT_DIR / "segment_processing_audit.csv",
    index=False
)


# ---------------------------------------------------------
# STEP 6: SUMMARY
# ---------------------------------------------------------

print("\n" + "=" * 65)
print("CORRECTED DATASET SUMMARY")
print("=" * 65)

print("Files processed:", len(file_data))
print("Final rows:", len(final_df))
print("Cameras:", sorted(final_df["Camera"].unique()))
print("Days:", sorted(final_df["Day"].unique()))

print("\nVehicle arrival totals (provisional):")

for vehicle in VEHICLES:
    print(
        vehicle,
        round(final_df[vehicle].sum(skipna=True), 2)
    )

print("\nNegative-difference rows:")
print(file_audit["Negative_Difference_Rows"].sum())

print("\nRows removed due to segment overlap:")
print(segment_audit["Removed_Rows"].sum())

print("\nSaved:")
print(output_file)
print(OUTPUT_DIR / "file_processing_audit.csv")
print(OUTPUT_DIR / "segment_processing_audit.csv")
