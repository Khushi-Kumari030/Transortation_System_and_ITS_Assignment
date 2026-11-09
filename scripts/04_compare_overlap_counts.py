
import zipfile
import pandas as pd
import os
import re

ZIP_PATH = "data/original/traffic.zip"

VEHICLES = ["car", "motorbike", "bus", "truck"]

def process_file(z, path):

    df = pd.read_csv(z.open(path))

    df = df.dropna(
        subset=["Time", "Direction"]
    ).copy()

    for v in VEHICLES:
        df[v] = pd.to_numeric(df[v], errors="coerce")

    # Collapse repeated observations
    df = (
        df.groupby(["Time", "Direction"], as_index=False)[VEHICLES]
        .max()
    )

    df["_time"] = pd.to_timedelta(df["Time"])

    df = df.sort_values(["Direction", "_time"])

    # Convert cumulative counters into arrivals
    arrivals = df.groupby("Direction")[VEHICLES].diff()

    first = df.groupby("Direction").head(1).index

    arrivals.loc[first] = df.loc[first, VEHICLES]

    df[VEHICLES] = arrivals

    return df


pairs = {}

with zipfile.ZipFile(ZIP_PATH) as z:

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

        p = process_file(z, files["primary"])
        c = process_file(z, files["continuation"])

        common = p.merge(
            c,
            on=["Time", "Direction"],
            suffixes=("_p", "_c")
        )

        if common.empty:
            continue

        for v in VEHICLES:
            common[f"{v}_equal"] = (
                common[f"{v}_p"] == common[f"{v}_c"]
            )

        common["All_Equal"] = common[
            [f"{v}_equal" for v in VEHICLES]
        ].all(axis=1)

        results.append({
            "Camera": key[1],
            "Day": key[2],
            "Common_Seconds": len(common),
            "Matching_Seconds": int(common["All_Equal"].sum()),
            "Different_Seconds": int((~common["All_Equal"]).sum()),
            "Primary_Total": common[
                [f"{v}_p" for v in VEHICLES]
            ].sum().sum(),
            "Continuation_Total": common[
                [f"{v}_c" for v in VEHICLES]
            ].sum().sum()
        })

result = pd.DataFrame(results)

print("\nOVERLAP ARRIVAL COMPARISON")
print(result.to_string(index=False))

result.to_csv(
    "data/processed/overlap_arrival_comparison.csv",
    index=False
)

print("\nSaved overlap_arrival_comparison.csv")
