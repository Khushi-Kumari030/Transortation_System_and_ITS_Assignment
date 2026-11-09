
import zipfile
import pandas as pd
import os
import re

ZIP_PATH = "data/original/traffic.zip"

VEHICLES = ["car", "motorbike", "bus", "truck"]

def read_raw(z, path):

    df = pd.read_csv(z.open(path))
    df = df.dropna(subset=["Time", "Direction"]).copy()

    for v in VEHICLES:
        df[v] = pd.to_numeric(df[v], errors="coerce")

    df = (
        df.groupby(["Time", "Direction"], as_index=False)[VEHICLES]
        .max()
    )

    df["_time"] = pd.to_timedelta(df["Time"])

    return df.sort_values(["Direction", "_time"])


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

    # Focus on J1 overlaps and one ordinary boundary
    selected = [
        ("j1", "11"),
        ("j1", "14"),
        ("a2", "12")
    ]

    for camera, day in selected:

        key = next(
            k for k in pairs
            if k[1] == camera and k[2] == day
        )

        files = pairs[key]

        p = read_raw(z, files["primary"])
        c = read_raw(z, files["continuation"])

        print("\n" + "=" * 70)
        print("CAMERA:", camera, "| DAY:", day)

        common = p.merge(
            c,
            on=["Time", "Direction"],
            suffixes=("_P", "_C")
        )

        print("\nCOMMON TIMESTAMPS:", len(common))

        if len(common):
            print("\nRAW CUMULATIVE COUNTERS AT OVERLAP:")

            print(
                common[
                    ["Time", "Direction"] +
                    [f"{v}_P" for v in VEHICLES] +
                    [f"{v}_C" for v in VEHICLES]
                ].head(12).to_string(index=False)
            )

        for direction in ["UP", "DOWN", "LEFT", "RIGHT"]:

            print("\nDIRECTION:", direction)

            pp = p[p["Direction"] == direction]
            cc = c[c["Direction"] == direction]

            print("\nPRIMARY LAST 5:")
            print(
                pp[["Time"] + VEHICLES]
                .tail(5).to_string(index=False)
            )

            print("\nCONTINUATION FIRST 5:")
            print(
                cc[["Time"] + VEHICLES]
                .head(5).to_string(index=False)
            )
