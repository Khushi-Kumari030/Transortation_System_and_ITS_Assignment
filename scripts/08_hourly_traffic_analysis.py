
import pandas as pd
import numpy as np
from pathlib import Path

# -------------------------------------------------
# PATHS AND SETTINGS
# -------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_DIR / "data" / "processed"
    / "corrected_vehicle_arrivals.csv"
)

OUTPUT_DIR = PROJECT_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VEHICLES = ["car", "motorbike", "bus", "truck"]
GROUPS = ["Day", "Camera", "Direction", "Hour_Start"]

MIN_COVERAGE = 95.0

# -------------------------------------------------
# LOAD DATA
# -------------------------------------------------

df = pd.read_csv(INPUT_FILE)

df["Timestamp"] = pd.to_datetime(
    df["Timestamp"], errors="coerce"
)

df = df.dropna(subset=["Timestamp"])

for col in VEHICLES:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# -------------------------------------------------
# CREATE HOURLY INTERVALS
# -------------------------------------------------

df["Hour_Start"] = df["Timestamp"].dt.floor("h")

df["Valid_Observation"] = df[VEHICLES].notna().all(axis=1)

hourly = (
    df.groupby(GROUPS)
    .agg(
        Observed_Seconds=("Timestamp", "nunique"),
        Valid_Seconds=("Valid_Observation", "sum"),
        car=("car", "sum"),
        motorbike=("motorbike", "sum"),
        bus=("bus", "sum"),
        truck=("truck", "sum")
    )
    .reset_index()
)

hourly["Total_Vehicles"] = hourly[VEHICLES].sum(axis=1)

hourly["Coverage_Percent"] = (
    hourly["Valid_Seconds"] / 3600 * 100
).clip(upper=100)

hourly["Hour"] = hourly["Hour_Start"].dt.strftime("%H:%M")

hourly["Eligible_For_Peak"] = (
    hourly["Coverage_Percent"] >= MIN_COVERAGE
)

# -------------------------------------------------
# VEHICLE COMPOSITION
# -------------------------------------------------

for vehicle in VEHICLES:
    hourly[f"{vehicle}_Share_Percent"] = np.where(
        hourly["Total_Vehicles"] > 0,
        hourly[vehicle] / hourly["Total_Vehicles"] * 100,
        np.nan
    )

# -------------------------------------------------
# SAVE ALL HOURLY OBSERVATIONS
# -------------------------------------------------

hourly_file = OUTPUT_DIR / "hourly_traffic_volume.csv"
hourly.to_csv(hourly_file, index=False)

# -------------------------------------------------
# PEAK HOUR FOR EACH DAY, CAMERA AND DIRECTION
# -------------------------------------------------

eligible = hourly[
    hourly["Eligible_For_Peak"]
].copy()

peak_idx = (
    eligible.groupby(["Day", "Camera", "Direction"])
    ["Total_Vehicles"].idxmax()
)

peak = eligible.loc[peak_idx].copy()

peak = peak.sort_values(
    "Total_Vehicles", ascending=False
)

peak_file = OUTPUT_DIR / "peak_hour_periods.csv"
peak.to_csv(peak_file, index=False)

# -------------------------------------------------
# OVERALL PEAK HOUR BY CAMERA AND DIRECTION
# Across all observed days, using eligible hours only
# -------------------------------------------------

camera_direction = (
    eligible.groupby(["Camera", "Direction"])
    .agg(
        Total_Observed_Vehicles=("Total_Vehicles", "sum"),
        Eligible_Hours=("Total_Vehicles", "count"),
        Average_Hourly_Volume=("Total_Vehicles", "mean"),
        Maximum_Hourly_Volume=("Total_Vehicles", "max")
    )
    .reset_index()
)

camera_direction_file = (
    OUTPUT_DIR / "camera_direction_hourly_summary.csv"
)

camera_direction.to_csv(
    camera_direction_file, index=False
)

# -------------------------------------------------
# SUMMARY
# -------------------------------------------------

print("\n" + "=" * 65)
print("HOURLY TRAFFIC VOLUME ANALYSIS")
print("=" * 65)

print("\nTotal hourly records:", len(hourly))

print("\nHourly vehicle totals:")
print(hourly[VEHICLES].sum())

print("\nHours below 95% valid coverage:")
print((~hourly["Eligible_For_Peak"]).sum())

print("\nEligible complete hours:", len(eligible))

print("\nTop 15 peak hourly periods:")
print(
    peak[
        [
            "Day", "Camera", "Direction",
            "Hour", "Total_Vehicles",
            "Coverage_Percent"
        ]
    ].head(15).to_string(index=False)
)

print("\nSaved:")
print(hourly_file)
print(peak_file)
print(camera_direction_file)
