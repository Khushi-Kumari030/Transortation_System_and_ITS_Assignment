
import zipfile
import pandas as pd

ZIP_PATH = "data/original/traffic.zip"

TARGETS = [
    ("a3_17_one.csv", "11:38:30", "UP"),
    ("a3_15_one.csv", "11:58:50", "UP"),
    ("a3_13.csv", "10:33:14", "UP"),
]

with zipfile.ZipFile(ZIP_PATH, "r") as z:
    for filename, target_time, direction in TARGETS:

        match = [
            n for n in z.namelist()
            if n.lower().endswith("/" + filename.lower())
            or n.lower() == filename.lower()
        ]

        if not match:
            print("Not found:", filename)
            continue

        df = pd.read_csv(z.open(match[0]))

        # Keep the target second and the two adjacent seconds
        times = [
            (pd.to_datetime(target_time, format="%H:%M:%S")
             + pd.Timedelta(seconds=i)).strftime("%H:%M:%S")
            for i in [-1, 0, 1]
        ]

        subset = df[
            (df["Time"].isin(times))
            & (df["Direction"] == direction)
        ].copy()

        print("\n" + "=" * 70)
        print(filename, target_time, direction)

        for t in times:
            part = subset[subset["Time"] == t]

            print(f"\nTIME: {t} | RAW ROWS: {len(part)}")

            if part.empty:
                continue

            for col in ["car", "motorbike", "bus", "truck"]:
                print(
                    col,
                    "| min:", part[col].min(),
                    "| max:", part[col].max(),
                    "| distinct values:", sorted(part[col].unique())
                )

            print("Raw counter sequence:")
            print(part[["car", "motorbike", "bus", "truck"]]
                  .to_string(index=False))
