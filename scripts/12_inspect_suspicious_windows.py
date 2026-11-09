
import zipfile
import pandas as pd
from pathlib import Path

ZIP_PATH = Path("data/original/traffic.zip")

# Inspect the most extreme observations first
TARGETS = [
    ("a3_17_one.csv", "11:38:30", "UP"),
    ("a3_15_one.csv", "11:58:50", "UP"),
    ("a3_13.csv", "10:33:14", "UP"),
]

VEHICLES = ["car", "motorbike", "bus", "truck"]

with zipfile.ZipFile(ZIP_PATH, "r") as z:
    for filename, target_time, target_direction in TARGETS:

        matches = [
            n for n in z.namelist()
            if n.lower().endswith("/" + filename.lower())
            or n.lower() == filename.lower()
        ]

        if not matches:
            print("File not found:", filename)
            continue

        df = pd.read_csv(z.open(matches[0]))

        # Reduce 25 repeated rows to one maximum counter snapshot
        grouped = (
            df.groupby(["Time", "Direction"])[VEHICLES]
              .max()
              .reset_index()
        )

        grouped["Time_dt"] = pd.to_datetime(
            grouped["Time"], format="%H:%M:%S"
        )

        grouped = grouped.sort_values(
            ["Direction", "Time_dt"]
        )

        # Calculate increments separately for each direction
        grouped[VEHICLES] = (
            grouped.groupby("Direction")[VEHICLES].diff()
        )

        target = pd.to_datetime(
            target_time, format="%H:%M:%S"
        )

        window = grouped[
            (grouped["Direction"] == target_direction)
            & (
                (grouped["Time_dt"] >= target - pd.Timedelta(seconds=5))
                & (grouped["Time_dt"] <= target + pd.Timedelta(seconds=5))
            )
        ].copy()

        window["Total"] = window[VEHICLES].sum(axis=1)

        print("\n" + "=" * 65)
        print(filename, target_time, target_direction)
        print(
            window[
                ["Time", "car", "motorbike", "bus", "truck", "Total"]
            ].to_string(index=False)
        )
