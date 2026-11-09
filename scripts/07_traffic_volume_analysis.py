
import pandas as pd
import numpy as np
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_DIR / "data" / "processed"
    / "corrected_vehicle_arrivals.csv"
)

OUTPUT_DIR = PROJECT_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VEHICLES = ["car", "motorbike", "bus", "truck"]
GROUPS = ["Day", "Camera", "Direction", "Interval_Start"]

# Minimum coverage for comparable peak-period analysis
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
# CREATE 15-MINUTE INTERVALS
# -------------------------------------------------

df["Interval_Start"] = df["Timestamp"].dt.floor("15min")

df["Valid_Observation"] = df[VEHICLES].notna().all(axis=1)

volume = (
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

volume["Total_Vehicles"] = volume[VEHICLES].sum(axis=1)

# Correct coverage calculation
volume["Coverage_Percent"] = (
    volume["Valid_Seconds"] / 900 * 100
).clip(upper=100)

# Display time without the artificial 1900 date
volume["Interval"] = (
    volume["Interval_Start"].dt.strftime("%H:%M")
)

# -------------------------------------------------
# VEHICLE COMPOSITION
# -------------------------------------------------

for vehicle in VEHICLES:
    volume[f"{vehicle}_Share_Percent"] = np.where(
        volume["Total_Vehicles"] > 0,
        volume[vehicle] / volume["Total_Vehicles"] * 100,
        np.nan
    )

volume["Eligible_For_Peak"] = (
    volume["Coverage_Percent"] >= MIN_COVERAGE
)

# -------------------------------------------------
# SAVE ALL 15-MINUTE INTERVALS
# -------------------------------------------------

volume_file = OUTPUT_DIR / "15_minute_traffic_volume.csv"
volume.to_csv(volume_file, index=False)

# -------------------------------------------------
# PEAK 15-MINUTE PERIODS
# Only intervals with >=95% valid coverage
# -------------------------------------------------

eligible = volume[
    volume["Eligible_For_Peak"]
].copy()

peak_idx = (
    eligible.groupby(["Day", "Camera", "Direction"])
    ["Total_Vehicles"].idxmax()
)

peak = eligible.loc[peak_idx].copy()

peak = peak.sort_values(
    "Total_Vehicles", ascending=False
)

peak_file = OUTPUT_DIR / "peak_15_minute_periods.csv"
peak.to_csv(peak_file, index=False)

# -------------------------------------------------
# DAILY OBSERVED TOTALS
# These are observed-period totals, not full-day totals
# -------------------------------------------------

daily = (
    volume.groupby(["Day", "Camera", "Direction"])
    .agg(
        car=("car", "sum"),
        motorbike=("motorbike", "sum"),
        bus=("bus", "sum"),
        truck=("truck", "sum"),
        Total_Vehicles=("Total_Vehicles", "sum"),
        Number_of_Intervals=("Interval", "count"),
        Intervals_Above_95pct_Coverage=(
            "Eligible_For_Peak", "sum"
        )
    )
    .reset_index()
)

daily["Observed_Coverage_Ratio"] = (
    daily["Intervals_Above_95pct_Coverage"]
    / daily["Number_of_Intervals"] * 100
)

daily_file = OUTPUT_DIR / "daily_traffic_volume.csv"
daily.to_csv(daily_file, index=False)

# -------------------------------------------------
# CAMERA-LEVEL COMPOSITION
# -------------------------------------------------

camera = (
    daily.groupby("Camera")[VEHICLES]
    .sum()
    .reset_index()
)

camera["Total_Vehicles"] = camera[VEHICLES].sum(axis=1)

for vehicle in VEHICLES:
    camera[f"{vehicle}_Share_Percent"] = (
        camera[vehicle] / camera["Total_Vehicles"] * 100
    )

camera_file = OUTPUT_DIR / "camera_vehicle_composition.csv"
camera.to_csv(camera_file, index=False)

# -------------------------------------------------
# SUMMARY
# -------------------------------------------------

print("\n" + "=" * 60)
print("CORRECTED 15-MINUTE TRAFFIC ANALYSIS")
print("=" * 60)

print("\nAll observed vehicle counts:")
print(volume[VEHICLES].sum())

print("\nOverall composition (%):")
total = volume[VEHICLES].sum()
print((total / total.sum() * 100).round(2))

print("\nIntervals below 95% valid coverage:")
print((~volume["Eligible_For_Peak"]).sum())

print("\nEligible peak intervals:", len(eligible))

print("\nTop 10 peak 15-minute periods:")
print(
    peak[
        [
            "Day", "Camera", "Direction",
            "Interval", "Total_Vehicles",
            "Coverage_Percent"
        ]
    ].head(10).to_string(index=False)
)

print("\nCamera-level vehicle composition:")
print(camera.round(2).to_string(index=False))

print("\nSaved:")
print(volume_file)
print(peak_file)
print(daily_file)
print(camera_file)
