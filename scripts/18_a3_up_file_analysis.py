
import pandas as pd
from pathlib import Path

df = pd.read_csv(
    "data/processed/corrected_vehicle_arrivals.csv"
)

vehicles = ["car", "motorbike", "bus", "truck"]

df = df.dropna(subset=vehicles, how="all").copy()
df[vehicles] = df[vehicles].fillna(0)

df["Total_Vehicles"] = df[vehicles].sum(axis=1)

# Focus on a3 UP
subset = df[
    (df["Camera"] == "a3") &
    (df["Direction"] == "UP")
].copy()

# Display columns to verify the source-file field
print("Available columns:")
print(df.columns.tolist())

# Identify the source-file column
possible_columns = [
    "Source_File", "source_file",
    "File", "file", "Filename", "filename"
]

file_column = next(
    (c for c in possible_columns if c in subset.columns),
    None
)

if file_column is None:
    raise ValueError(
        "Source file column not found. "
        "Check the printed column names."
    )

summary = (
    subset.groupby(file_column)["Total_Vehicles"]
    .agg(
        observations="count",
        total="sum",
        mean="mean",
        p99=lambda x: x.quantile(0.99),
        maximum="max",
        above_5=lambda x: (x > 5).sum(),
        above_10=lambda x: (x > 10).sum(),
        above_20=lambda x: (x > 20).sum()
    )
    .reset_index()
)

summary["Above_10_Percent"] = (
    summary["above_10"] /
    summary["observations"] * 100
)

summary = summary.sort_values(
    "Above_10_Percent",
    ascending=False
)

print("\nA3 UP: FILE-WISE ANALYSIS")
print(summary.round(3).to_string(index=False))

Path("outputs").mkdir(exist_ok=True)
summary.to_csv(
    "outputs/a3_up_file_analysis.csv",
    index=False
)
