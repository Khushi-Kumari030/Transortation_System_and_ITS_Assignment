
import zipfile
import pandas as pd
import re
import os

ZIP_PATH = "data/original/traffic.zip"

pairs = {}

with zipfile.ZipFile(ZIP_PATH) as z:

    for fn in z.namelist():

        if not fn.endswith(".csv"):
            continue

        name = os.path.basename(fn)

        match = re.match(
            r"(.+?)_(\d{2})(_one)?\.csv$", name
        )

        if not match:
            continue

        camera = match.group(1)
        day = match.group(2)

        segment = (
            "continuation"
            if match.group(3)
            else "primary"
        )

        key = (os.path.dirname(fn), camera, day)

        pairs.setdefault(key, {})[segment] = fn

    results = []

    for key, files in pairs.items():

        if "primary" not in files or "continuation" not in files:
            continue

        p = pd.read_csv(
            z.open(files["primary"]),
            usecols=["Time"]
        ).dropna()

        c = pd.read_csv(
            z.open(files["continuation"]),
            usecols=["Time"]
        ).dropna()

        p_start = pd.to_timedelta(p["Time"]).min()
        p_end = pd.to_timedelta(p["Time"]).max()

        c_start = pd.to_timedelta(c["Time"]).min()
        c_end = pd.to_timedelta(c["Time"]).max()

        overlap = max(
            0,
            (p_end - c_start).total_seconds()
        )

        gap = max(
            0,
            (c_start - p_end).total_seconds()
        )

        results.append({
            "Camera": key[1],
            "Day": key[2],
            "Primary_End": str(p_end),
            "Continuation_Start": str(c_start),
            "Overlap_Seconds": overlap,
            "Gap_Seconds": gap
        })

result = pd.DataFrame(results)

print("\nSEGMENT VALIDATION")
print(result.to_string(index=False))

print("\nTotal pairs:", len(result))
print("Overlapping pairs:", (result["Overlap_Seconds"] > 0).sum())
print("Gaps:", (result["Gap_Seconds"] > 0).sum())

result.to_csv(
    "data/processed/segment_validation.csv",
    index=False
)

print("\nSaved segment_validation.csv")
