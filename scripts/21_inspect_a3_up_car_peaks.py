
import pandas as pd
from pathlib import Path

df = pd.read_csv(
    "data/processed/corrected_vehicle_arrivals.csv"
)

df = df[
    (df["Camera"] == "a3") &
    (df["Direction"] == "UP")
].copy()

df["Timestamp"] = pd.to_datetime(df["Timestamp"])

# Sort within each original recording segment
df = df.sort_values(["Source_File", "Timestamp"])

# Select the 30 largest car increments
peaks = df.nlargest(30, "car").copy()

records = []

for _, peak in peaks.iterrows():
    source = peak["Source_File"]
    timestamp = peak["Timestamp"]

    nearby = df[
        (df["Source_File"] == source) &
        (df["Timestamp"] >= timestamp - pd.Timedelta(seconds=2)) &
        (df["Timestamp"] <= timestamp + pd.Timedelta(seconds=2))
    ].copy()

    nearby["Peak_Timestamp"] = timestamp
    nearby["Peak_Car_Count"] = peak["car"]

    records.append(nearby)

if records:
    result = pd.concat(records, ignore_index=True)

    result = result.sort_values(
        ["Source_File", "Peak_Timestamp", "Timestamp"]
    )

    columns = [
        "Source_File",
        "Peak_Timestamp",
        "Peak_Car_Count",
        "Timestamp",
        "car",
        "motorbike",
        "bus",
        "truck"
    ]

    print(result[columns].to_string(index=False))

    Path("outputs").mkdir(exist_ok=True)

    result[columns].to_csv(
        "outputs/a3_up_car_peak_windows.csv",
        index=False
    )
