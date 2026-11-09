
import zipfile
import pandas as pd
import os
import re

ZIP_PATH = "data/original/traffic.zip"

VEHICLES = ["car", "motorbike", "bus", "truck"]

def read_counter_file(z, path):

    df = pd.read_csv(z.open(path))

    df = df.dropna(subset=["Time", "Direction"]).copy()

    for col in VEHICLES:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Collapse repeated frame records
    df = (
        df.groupby(["Time", "Direction"], as_index=False)[VEHICLES]
        .max()
    )

    df["_time"] = pd.to_timedelta(df["Time"])

    return df.sort_values(["_time", "Direction"])


pairs = {}

with zipfile.ZipFile(ZIP_PATH, "r") as z:

    for path in z.namelist():

        if not path.endswith(".csv"):
            continue

        name = os.path.basename(path)

        match = re.match(
            r"(.+?)_(\d{2})(_one)?\.csv$", name
        )

        if not match:
            continue

        camera, day, continuation = match.groups()

        key = (os.path.dirname(path), camera, day)

        segment = "continuation" if continuation else "primary"

        pairs.setdefault(key, {})[segment] = path

    results = []

    for key, files in pairs.items():

        if len(files) != 2:
            continue

        p = read_counter_file(z, files["primary"])
        c = read_counter_file(z, files["continuation"])

        shared = p.merge(
            c,
            on=["Time", "Direction"],
            suffixes=("_primary", "_continuation")
        )

        if len(shared):

            equal_rows = (
                shared[
                    [f"{v}_primary" for v in VEHICLES]
                ].to_numpy()
                ==
                shared[
                    [f"{v}_continuation" for v in VEHICLES]
                ].to_numpy()
            ).all(axis=1)

            matching = int(equal_rows.sum())
            mismatching = len(shared) - matching

        else:
            matching = 0
            mismatching = 0

        # Compare boundary counters direction-wise
        p_last = (
            p.sort_values("_time")
            .groupby("Direction")
            .tail(1)
        )

        c_first = (
            c.sort_values("_time")
            .groupby("Direction")
            .head(1)
        )

        boundary = p_last.merge(
            c_first,
            on="Direction",
            suffixes=("_primary", "_continuation")
        )

        # Test whether continuation counters reset
        reset_directions = []

        for _, row in boundary.iterrows():

            if any(
                row[f"{v}_continuation"] <
                row[f"{v}_primary"]
                for v in VEHICLES
            ):
                reset_directions.append(row["Direction"])

        results.append({
            "Camera": key[1],
            "Day": key[2],
            "Shared_Records": len(shared),
            "Matching_Records": matching,
            "Mismatching_Records": mismatching,
            "Reset_Suspected_Directions": ",".join(reset_directions),
        })

result = pd.DataFrame(results)

print("\nCOUNTER CONTINUITY VALIDATION")
print(result.to_string(index=False))

result.to_csv(
    "data/processed/counter_continuity.csv",
    index=False
)

print("\nSaved counter_continuity.csv")
