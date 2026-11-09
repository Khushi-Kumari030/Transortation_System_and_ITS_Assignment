
import pandas as pd
from pathlib import Path

ROOT = Path(".")
DATA = ROOT / "data/processed/corrected_vehicle_arrivals.csv"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

df = pd.read_csv(DATA)

classes = ["car", "motorbike", "bus", "truck"]

df["Total_Vehicles"] = df[classes].sum(axis=1, min_count=1)

# A. Flag unusually large one-second counts.
# These are screening thresholds, not claims about road capacity.
thresholds = {
    "car": 10,
    "motorbike": 10,
    "bus": 5,
    "truck": 5
}

flags = pd.Series(False, index=df.index)

for vehicle, threshold in thresholds.items():
    flags |= df[vehicle] > threshold

spikes = df.loc[
    flags,
    ["Day", "Camera", "Direction", "Time",
     "Segment", "Source_File"] + classes + ["Total_Vehicles"]
].copy()

spikes = spikes.sort_values(
    "Total_Vehicles", ascending=False
)

spikes.to_csv(OUT / "suspicious_second_counts.csv", index=False)

print("\nTOP 20 SUSPICIOUS SECONDS")
print(spikes.head(20).to_string(index=False))
print("\nTotal flagged rows:", len(spikes))
print("Flagged share (%):", round(100 * len(spikes) / len(df), 3))

# B. Summarize recording coverage for each camera/day.
# A second counts as observed when any direction has a record.
coverage = (
    df.groupby(["Camera", "Day"])
      .agg(
          Start=("Time", "min"),
          End=("Time", "max"),
          Observed_Seconds=("Time", "nunique")
      )
      .reset_index()
)

coverage["Expected_Seconds"] = (
    pd.to_timedelta(coverage["End"]).dt.total_seconds()
    - pd.to_timedelta(coverage["Start"]).dt.total_seconds()
    + 1
)

coverage["Coverage_Percent"] = (
    100 * coverage["Observed_Seconds"]
    / coverage["Expected_Seconds"]
).round(2)

coverage.to_csv(OUT / "camera_day_coverage.csv", index=False)

print("\nCAMERA-DAY COVERAGE")
print(coverage.to_string(index=False))

# C. Vehicle counts by camera
camera_summary = df.groupby("Camera")[classes].sum()
camera_summary["Total"] = camera_summary[classes].sum(axis=1)

camera_summary.to_csv(OUT / "validated_camera_totals.csv")

print("\nCAMERA TOTALS")
print(camera_summary.to_string())

print("\nSaved three audit files in outputs/")
