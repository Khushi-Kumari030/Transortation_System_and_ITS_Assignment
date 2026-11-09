
import pandas as pd
import numpy as np
from pathlib import Path

# =========================================================
# 0. PATHS AND SETTINGS
# =========================================================

DATA = Path("data/processed/corrected_vehicle_arrivals.csv")
PCU_DATA = Path("outputs/pcu_15min_intervals.csv")
OUTPUT = Path("outputs")

OUTPUT.mkdir(parents=True, exist_ok=True)

SELECTED_FACTOR = "IRC_SP41"
SELECTED_SCENARIO = "B_Exclude_a3_UP"

VEHICLE_CLASSES = ["car", "motorbike", "bus", "truck"]

MIN_COVERAGE = 95.0
WINDOW_INTERVALS = 4

JUNCTION_MAP = {
    "a": "Alankar Chowk",
    "j": "Jehangir Chowk",
    "r": "RTO Chowk"
}

# =========================================================
# 1. LOAD AND VALIDATE RAW ARRIVAL DATA
# =========================================================

if not DATA.exists():
    raise FileNotFoundError(f"File not found: {DATA.resolve()}")

arrivals = pd.read_csv(DATA)

required_arrival_columns = [
    "Day", "Camera", "Direction", "Time",
    "car", "motorbike", "bus", "truck"
]

missing = [
    col for col in required_arrival_columns
    if col not in arrivals.columns
]

if missing:
    raise ValueError(f"Missing columns in arrival data: {missing}")

print("=" * 65)
print("VEHICLE COMPOSITION AND PEAK-HOUR ANALYSIS")
print("=" * 65)

print("\nOriginal arrival data shape:", arrivals.shape)

# Exclude the anomalous a3-UP movement
arrivals = arrivals[
    ~(
        (arrivals["Camera"] == "a3") &
        (arrivals["Direction"].astype(str).str.upper() == "UP")
    )
].copy()

# Keep valid numeric arrival increments
for col in VEHICLE_CLASSES:
    arrivals[col] = pd.to_numeric(
        arrivals[col], errors="coerce"
    )

# First observation in each file may be NaN because
# no previous counter value exists.
arrivals[VEHICLE_CLASSES] = (
    arrivals[VEHICLE_CLASSES].fillna(0)
)

# Avoid treating negative increments as valid arrivals
if (arrivals[VEHICLE_CLASSES] < 0).any().any():
    raise ValueError(
        "Negative vehicle increments found. "
        "Inspect the corrected arrival dataset."
    )

arrivals["Junction"] = (
    arrivals["Camera"].astype(str).str[0].map(JUNCTION_MAP)
)

if arrivals["Junction"].isna().any():
    raise ValueError("Unknown camera identifier found.")

print("Scenario used: B_Exclude_a3_UP")
print("a3-UP excluded from arrival data.")

# =========================================================
# 2. VEHICLE COMPOSITION BY CAMERA
# =========================================================

# Sum vehicle-class arrivals across all available days
# and retained directions for each camera.

composition = (
    arrivals.groupby(
        ["Junction", "Camera"],
        as_index=False
    )[VEHICLE_CLASSES]
    .sum()
)

composition["Total_Vehicles"] = (
    composition[VEHICLE_CLASSES].sum(axis=1)
)

for vehicle in VEHICLE_CLASSES:
    composition[f"{vehicle}_Share_Percent"] = np.where(
        composition["Total_Vehicles"] > 0,
        composition[vehicle] /
        composition["Total_Vehicles"] * 100,
        0
    )

composition = composition.sort_values(
    ["Junction", "Camera"]
)

print("\n" + "=" * 65)
print("VEHICLE COMPOSITION BY CAMERA")
print("=" * 65)

print(composition.round(2).to_string(index=False))

# =========================================================
# 3. VEHICLE COMPOSITION BY JUNCTION
# =========================================================

# This is a descriptive aggregation of camera observations.
# It must NOT be interpreted as unique junction traffic
# unless camera fields of view are confirmed to be distinct.

junction_composition = (
    composition.groupby("Junction", as_index=False)[
        VEHICLE_CLASSES + ["Total_Vehicles"]
    ].sum()
)

for vehicle in VEHICLE_CLASSES:
    junction_composition[f"{vehicle}_Share_Percent"] = np.where(
        junction_composition["Total_Vehicles"] > 0,
        junction_composition[vehicle] /
        junction_composition["Total_Vehicles"] * 100,
        0
    )

print("\n" + "=" * 65)
print("AGGREGATED CAMERA OBSERVATIONS BY JUNCTION")
print("=" * 65)

print(junction_composition.round(2).to_string(index=False))

# =========================================================
# 4. LOAD 15-MINUTE PCU DATA
# =========================================================

if not PCU_DATA.exists():
    raise FileNotFoundError(
        f"File not found: {PCU_DATA.resolve()}"
    )

pcu = pd.read_csv(PCU_DATA)

required_pcu_columns = [
    "Day", "Camera", "Direction", "Interval",
    "PCU", "Vehicle_Count", "Coverage_Percent",
    "Scenario", "Factor_Set"
]

missing = [
    col for col in required_pcu_columns
    if col not in pcu.columns
]

if missing:
    raise ValueError(f"Missing columns in PCU data: {missing}")

# Apply primary scenario and PCU factor set
pcu = pcu[
    (pcu["Factor_Set"] == SELECTED_FACTOR) &
    (pcu["Scenario"] == SELECTED_SCENARIO)
].copy()

if pcu.empty:
    raise ValueError("No PCU observations found for selected scenario.")

pcu["Interval"] = pd.to_datetime(pcu["Interval"])

pcu["PCU"] = pd.to_numeric(pcu["PCU"], errors="coerce")
pcu["Vehicle_Count"] = pd.to_numeric(
    pcu["Vehicle_Count"], errors="coerce"
)
pcu["Coverage_Percent"] = pd.to_numeric(
    pcu["Coverage_Percent"], errors="coerce"
)

pcu["Junction"] = (
    pcu["Camera"].astype(str).str[0].map(JUNCTION_MAP)
)

# Explicit exclusion verification
if (
    (pcu["Camera"] == "a3") &
    (pcu["Direction"].astype(str).str.upper() == "UP")
).any():
    raise ValueError("a3-UP still present in PCU dataset.")

print("\nPCU dataset shape after filtering:", pcu.shape)
print("PCU factor set:", SELECTED_FACTOR)
print("Scenario:", SELECTED_SCENARIO)

# =========================================================
# 5. COMBINE DIRECTIONS AT CAMERA LEVEL
# =========================================================

# Sum PCU and vehicle counts across retained directions
# for each camera, day and 15-minute interval.

camera_15min = (
    pcu.groupby(
        ["Day", "Junction", "Camera", "Interval"],
        as_index=False
    )
    .agg(
        Total_PCU=("PCU", "sum"),
        Total_Vehicles=("Vehicle_Count", "sum"),
        Minimum_Coverage=("Coverage_Percent", "min"),
        Direction_Count=("Direction", "nunique")
    )
)

camera_15min = camera_15min.sort_values(
    ["Camera", "Day", "Interval"]
)

# =========================================================
# 6. RETAIN INTERVALS WITH AT LEAST 95% COVERAGE
# =========================================================

camera_15min["Eligible"] = (
    camera_15min["Minimum_Coverage"] >= MIN_COVERAGE
)

eligible = camera_15min[
    camera_15min["Eligible"]
].copy()

print("\n" + "=" * 65)
print("15-MINUTE COVERAGE CHECK")
print("=" * 65)

coverage_summary = (
    camera_15min.groupby(
        ["Junction", "Camera"],
        as_index=False
    )
    .agg(
        Total_Intervals=("Interval", "count"),
        Eligible_Intervals=("Eligible", "sum"),
        Minimum_Coverage=("Minimum_Coverage", "min")
    )
)

coverage_summary["Eligible_Percent"] = (
    coverage_summary["Eligible_Intervals"] /
    coverage_summary["Total_Intervals"] * 100
)

print(coverage_summary.round(2).to_string(index=False))

# =========================================================
# 7. CALCULATE ROLLING PEAK-HOUR PCU
# =========================================================

# One hour = four consecutive 15-minute intervals.
#
# A valid window must:
# 1. Contain four observations.
# 2. Have exactly 15-minute gaps between intervals.
# 3. Have at least 95% coverage in every interval.
#
# Directions have already been combined at camera level.

peak_hour_records = []

for (day, camera), group in camera_15min.groupby(
    ["Day", "Camera"]
):

    group = group.sort_values("Interval").reset_index(drop=True)

    for start in range(
        len(group) - WINDOW_INTERVALS + 1
    ):

        window = group.iloc[
            start:start + WINDOW_INTERVALS
        ].copy()

        # Check that all four intervals are eligible
        if not window["Eligible"].all():
            continue

        # Check exact 15-minute continuity
        time_differences = (
            window["Interval"].diff().dropna()
        )

        if not (time_differences == pd.Timedelta(minutes=15)).all():
            continue

        start_time = window.iloc[0]["Interval"]
        end_time = (
            window.iloc[-1]["Interval"] +
            pd.Timedelta(minutes=15)
        )

        peak_hour_records.append({
            "Day": day,
            "Junction": window.iloc[0]["Junction"],
            "Camera": camera,
            "Hour_Start": start_time,
            "Hour_End": end_time,
            "Hour_Start_Time": start_time.strftime("%H:%M"),
            "Peak_Hour_PCU": window["Total_PCU"].sum(),
            "Peak_Hour_Vehicles": window["Total_Vehicles"].sum(),
            "Minimum_Coverage": window["Minimum_Coverage"].min(),
            "Number_of_Intervals": len(window)
        })

peak_hours = pd.DataFrame(peak_hour_records)

if peak_hours.empty:
    raise ValueError(
        "No valid four-interval peak-hour windows found."
    )

# =========================================================
# 8. MAXIMUM PEAK HOUR FOR EACH CAMERA AND DAY
# =========================================================

daily_peak_hour = (
    peak_hours.sort_values(
        ["Camera", "Day", "Peak_Hour_PCU"],
        ascending=[True, True, False]
    )
    .groupby(["Camera", "Day"])
    .head(1)
    .sort_values(["Camera", "Day"])
    .reset_index(drop=True)
)

print("\n" + "=" * 65)
print("DAILY PEAK-HOUR PCU BY CAMERA")
print("=" * 65)

print(
    daily_peak_hour[
        [
            "Junction", "Camera", "Day",
            "Hour_Start_Time",
            "Peak_Hour_PCU",
            "Peak_Hour_Vehicles",
            "Minimum_Coverage"
        ]
    ].round(2).to_string(index=False)
)

# =========================================================
# 9. AVERAGE AND MAXIMUM PEAK-HOUR SUMMARY
# =========================================================

peak_hour_summary = (
    daily_peak_hour.groupby(
        ["Junction", "Camera"],
        as_index=False
    )
    .agg(
        Average_Peak_Hour_PCU=("Peak_Hour_PCU", "mean"),
        Maximum_Peak_Hour_PCU=("Peak_Hour_PCU", "max"),
        Average_Peak_Hour_Vehicles=(
            "Peak_Hour_Vehicles", "mean"
        ),
        Number_of_Days=("Day", "nunique")
    )
)

peak_hour_summary = peak_hour_summary.sort_values(
    "Average_Peak_Hour_PCU",
    ascending=False
)

print("\n" + "=" * 65)
print("PEAK-HOUR SUMMARY BY CAMERA")
print("=" * 65)

print(peak_hour_summary.round(2).to_string(index=False))

# =========================================================
# 10. PEAK-HOUR START-TIME PROFILE
# =========================================================

# This identifies the most frequent and highest-demand
# starting times of rolling one-hour windows.

peak_time_profile = (
    peak_hours.groupby(
        ["Junction", "Camera", "Hour_Start_Time"],
        as_index=False
    )
    .agg(
        Average_Rolling_Hour_PCU=("Peak_Hour_PCU", "mean"),
        Number_of_Windows=("Peak_Hour_PCU", "count")
    )
)

peak_time_profile = peak_time_profile.sort_values(
    ["Camera", "Average_Rolling_Hour_PCU"],
    ascending=[True, False]
)

print("\n" + "=" * 65)
print("TOP 5 ROLLING PEAK-HOUR START TIMES")
print("=" * 65)

top_peak_times = (
    peak_time_profile.groupby("Camera")
    .head(5)
)

print(top_peak_times.round(2).to_string(index=False))

# =========================================================
# 11. EXPORT ALL RESULTS
# =========================================================

outputs = {
    "vehicle_composition_by_camera.csv": composition,
    "vehicle_composition_by_junction.csv": junction_composition,
    "camera_15min_coverage_check.csv": coverage_summary,
    "all_rolling_peak_hour_windows.csv": peak_hours,
    "daily_peak_hour_by_camera.csv": daily_peak_hour,
    "peak_hour_summary_by_camera.csv": peak_hour_summary,
    "peak_hour_time_profile.csv": peak_time_profile
}

print("\n" + "=" * 65)
print("SAVING OUTPUT FILES")
print("=" * 65)

for filename, data in outputs.items():
    path = OUTPUT / filename
    data.to_csv(path, index=False)
    print("Saved:", path)

# =========================================================
# 12. FINAL VALIDATION
# =========================================================

print("\n" + "=" * 65)
print("FINAL VALIDATION")
print("=" * 65)

print("PCU factor set:", SELECTED_FACTOR)
print("Scenario:", SELECTED_SCENARIO)
print("a3-UP excluded: True")
print("Cameras analysed:", camera_15min["Camera"].nunique())
print("Eligible 15-minute intervals:", len(eligible))
print("Valid rolling one-hour windows:", len(peak_hours))
print("Daily peak-hour records:", len(daily_peak_hour))

print("\nAnalysis completed successfully.")
