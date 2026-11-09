
import pandas as pd
from pathlib import Path

# =========================================================
# 0. PATHS AND SETTINGS
# =========================================================

INPUT = Path("outputs/pcu_15min_intervals.csv")
OUTPUT = Path("outputs")
OUTPUT.mkdir(parents=True, exist_ok=True)

# Primary analysis settings
SELECTED_FACTOR = "IRC_SP41"
SELECTED_SCENARIO = "B_Exclude_a3_UP"

# =========================================================
# 1. LOAD DATA
# =========================================================

if not INPUT.exists():
    raise FileNotFoundError(
        f"Input file not found: {INPUT.resolve()}\n"
        "Please run the PCU sensitivity analysis script first."
    )

df = pd.read_csv(INPUT)

print("=" * 65)
print("PUNE TRANSPORTATION SYSTEM - CAMERA PEAK PROFILE ANALYSIS")
print("=" * 65)

print("\nOriginal dataset shape:", df.shape)

required_columns = [
    "Factor_Set",
    "Scenario",
    "Camera",
    "Direction",
    "Day",
    "Interval",
    "PCU",
    "Vehicle_Count",
    "Coverage_Percent"
]

missing_columns = [
    col for col in required_columns if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns: {missing_columns}"
    )

# =========================================================
# 2. FILTER PRIMARY ANALYSIS SCENARIO
# =========================================================

df = df[
    (df["Factor_Set"] == SELECTED_FACTOR) &
    (df["Scenario"] == SELECTED_SCENARIO)
].copy()

if df.empty:
    raise ValueError(
        "No observations found for the selected factor set "
        "and scenario. Check the input CSV column values."
    )

df["Interval"] = pd.to_datetime(df["Interval"])

print("\nSelected PCU factor set:", SELECTED_FACTOR)
print("Selected scenario:", SELECTED_SCENARIO)
print("Filtered dataset shape:", df.shape)

# =========================================================
# 3. VERIFY a3-UP EXCLUSION
# =========================================================

print("\n" + "=" * 65)
print("DIRECTION EXCLUSION VERIFICATION")
print("=" * 65)

print("\nDirections retained by camera:")

directions_by_camera = (
    df.groupby("Camera")["Direction"]
      .unique()
)

for camera, directions in directions_by_camera.items():
    print(f"{camera}: {sorted(directions)}")

# Explicitly verify that a3-UP is absent
a3_up_exists = (
    (df["Camera"] == "a3") &
    (df["Direction"].astype(str).str.upper() == "UP")
).any()

if a3_up_exists:
    raise ValueError(
        "ERROR: a3-UP observations are still present!"
    )

print("\nSUCCESS: a3-UP observations are excluded.")

# Check expected number of directions
print("\nNumber of retained directions per camera:")

direction_counts = (
    df.groupby("Camera")["Direction"]
      .nunique()
)

print(direction_counts.to_string())

# =========================================================
# 4. MAP CAMERAS TO JUNCTIONS
# =========================================================

junction_map = {
    "a": "Alankar Chowk",
    "j": "Jehangir Chowk",
    "r": "RTO Chowk"
}

df["Junction"] = (
    df["Camera"].astype(str).str[0].map(junction_map)
)

if df["Junction"].isna().any():
    unknown_cameras = (
        df.loc[df["Junction"].isna(), "Camera"]
          .unique()
    )

    raise ValueError(
        f"Unknown camera identifiers: {unknown_cameras}"
    )

# =========================================================
# 5. CAMERA-LEVEL 15-MINUTE TOTALS
# =========================================================

# Sum the retained directional observations within each
# camera, day and 15-minute interval.

camera_intervals = (
    df.groupby(
        ["Day", "Junction", "Camera", "Interval"],
        as_index=False
    )
    .agg(
        Total_PCU=("PCU", "sum"),
        Total_Vehicles=("Vehicle_Count", "sum"),
        Minimum_Direction_Coverage=(
            "Coverage_Percent", "min"
        ),
        Direction_Count=("Direction", "nunique")
    )
)

camera_intervals["Time"] = (
    camera_intervals["Interval"].dt.strftime("%H:%M")
)

camera_intervals = camera_intervals.sort_values(
    ["Junction", "Camera", "Interval"]
)

# =========================================================
# 6. TOP 5 PEAK INTERVALS BY CAMERA
# =========================================================

camera_peaks = (
    camera_intervals
    .sort_values(
        ["Camera", "Total_PCU"],
        ascending=[True, False]
    )
    .groupby("Camera")
    .head(5)
    .sort_values(
        ["Camera", "Total_PCU"],
        ascending=[True, False]
    )
    .reset_index(drop=True)
)

print("\n" + "=" * 65)
print("TOP 5 CAMERA-LEVEL 15-MINUTE INTERVALS")
print("=" * 65)

print(
    camera_peaks[
        [
            "Junction",
            "Camera",
            "Day",
            "Interval",
            "Total_PCU",
            "Total_Vehicles",
            "Minimum_Direction_Coverage",
            "Direction_Count"
        ]
    ].round(2).to_string(index=False)
)

# =========================================================
# 7. AVERAGE CAMERA-LEVEL PCU BY TIME OF DAY
# =========================================================

# Each observation represents one camera on one day
# during one 15-minute interval.
#
# Average_PCU is the mean across available days for
# the same camera and clock-time interval.

time_profile = (
    camera_intervals
    .groupby(
        ["Junction", "Camera", "Time"],
        as_index=False
    )
    .agg(
        Average_PCU=("Total_PCU", "mean"),
        Average_Vehicles=("Total_Vehicles", "mean"),
        Number_of_Days=("Day", "nunique")
    )
)

time_profile["Peak_Rank"] = (
    time_profile
    .groupby("Camera")["Average_PCU"]
    .rank(method="min", ascending=False)
)

time_profile = time_profile.sort_values(
    ["Camera", "Peak_Rank"]
)

print("\n" + "=" * 65)
print("TOP 5 PEAK TIMES OF DAY BY CAMERA")
print("=" * 65)

top_times = (
    time_profile
    .sort_values(
        ["Camera", "Average_PCU"],
        ascending=[True, False]
    )
    .groupby("Camera")
    .head(5)
)

print(
    top_times.round(2).to_string(index=False)
)

# =========================================================
# 8. JUNCTION-LEVEL CAMERA COMPARISON
# =========================================================

# This table compares individual cameras within each
# junction. It does NOT sum different cameras together.

camera_summary = (
    camera_intervals
    .groupby(
        ["Junction", "Camera"],
        as_index=False
    )
    .agg(
        Average_15min_PCU=("Total_PCU", "mean"),
        Maximum_15min_PCU=("Total_PCU", "max"),
        Average_15min_Vehicles=("Total_Vehicles", "mean"),
        Maximum_15min_Vehicles=("Total_Vehicles", "max"),
        Number_of_Intervals=("Interval", "count"),
        Average_Direction_Count=("Direction_Count", "mean"),
        Minimum_Coverage=("Minimum_Direction_Coverage", "min")
    )
)

camera_summary = camera_summary.sort_values(
    ["Junction", "Average_15min_PCU"],
    ascending=[True, False]
)

print("\n" + "=" * 65)
print("CAMERA-LEVEL SUMMARY BY JUNCTION")
print("=" * 65)

print(camera_summary.round(2).to_string(index=False))

# =========================================================
# 9. EXPORT RESULTS
# =========================================================

files_to_save = {
    "camera_15min_combined_directions.csv": camera_intervals,
    "camera_peak_intervals_corrected.csv": camera_peaks,
    "camera_time_of_day_profile_corrected.csv": time_profile,
    "camera_summary_by_junction.csv": camera_summary
}

for filename, data in files_to_save.items():
    output_path = OUTPUT / filename
    data.to_csv(output_path, index=False)
    print(f"Saved: {output_path}")

# =========================================================
# 10. FINAL CHECKS
# =========================================================

print("\n" + "=" * 65)
print("FINAL DATA CHECKS")
print("=" * 65)

print("Selected factor set:", SELECTED_FACTOR)
print("Selected scenario:", SELECTED_SCENARIO)
print("a3-UP excluded:", not a3_up_exists)
print("Number of cameras:", camera_intervals["Camera"].nunique())
print("Number of camera-level intervals:", len(camera_intervals))
print(
    "Junctions:",
    sorted(camera_intervals["Junction"].unique())
)

print("\nAnalysis completed successfully.")
