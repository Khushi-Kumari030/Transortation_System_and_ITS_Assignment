import zipfile
import pandas as pd
from pathlib import Path

ZIP_PATH = Path("data/original/traffic.zip")

# Inspect two files: one camera/day and another camera/day
TARGETS = ["a2_11.csv", "a3_13.csv"]

VEHICLES = ["car", "motorbike", "bus", "truck"]

with zipfile.ZipFile(ZIP_PATH, "r") as z:
    for target in TARGETS:
        matches = [
            name for name in z.namelist()
            if name.lower().endswith("/" + target.lower())
            or name.lower() == target.lower()
        ]

        if not matches:
            print(f"\nCould not find {target}")
            continue

        filename = matches[0]
        df = pd.read_csv(z.open(filename))

        # Match column names without depending on capitalization
        column_map = {c.lower().strip(): c for c in df.columns}

        time_col = column_map.get("time")
        direction_col = column_map.get("direction")
        vehicle_cols = {
            v: column_map.get(v) for v in VEHICLES
        }

        print("\n" + "=" * 70)
        print("FILE:", filename)
        print("COLUMNS:", df.columns.tolist())
        print("RAW ROW COUNT:", len(df))

        if not time_col or not direction_col:
            print("Time or Direction column not found.")
            continue

        if any(v is None for v in vehicle_cols.values()):
            print("One or more vehicle columns not found.")
            continue

        print("\nFIRST 15 RAW ROWS:")
        print(df.head(15).to_string(index=False))

        df[time_col] = pd.to_datetime(
            df[time_col], format="%H:%M:%S", errors="coerce"
        )
        df = df.dropna(subset=[time_col, direction_col])

        # Count unique timestamps and time gaps
        times = pd.Series(df[time_col].drop_duplicates().sort_values())
        gaps = times.diff().dt.total_seconds().dropna()

        print("\nUNIQUE TIMESTAMPS:", len(times))
        print("TIME GAP FREQUENCY (seconds):")
        print(gaps.value_counts().head(10).to_string())

        # Inspect repeated rows at the same timestamp/direction
        grouped = (
            df.groupby([time_col, direction_col])[list(vehicle_cols.values())]
              .agg(["min", "max", "count"])
        )

        print("\nEXAMPLE GROUPED VALUES (first 15 groups):")
        print(grouped.head(15).to_string())

        # Inspect whether grouped values increase over time
        for direction in sorted(df[direction_col].unique()):
            part = df[df[direction_col] == direction].copy()

            part = (
                part.groupby(time_col)[list(vehicle_cols.values())]
                    .max()
                    .sort_index()
            )

            print(f"\nDIRECTION: {direction}")
            print("FIRST 15 TIMESTAMP-LEVEL VALUES:")
            print(part.head(15).to_string())

            print("\nDIFFERENCES BETWEEN SUCCESSIVE VALUES:")
            print(part.diff().head(15).to_string())