
import pandas as pd
from pathlib import Path

df = pd.read_csv("data/processed/corrected_vehicle_arrivals.csv")

vehicles = ["car", "motorbike", "bus", "truck"]

# Remove rows where all increments are undefined
df = df.dropna(subset=vehicles, how="all").copy()
df[vehicles] = df[vehicles].fillna(0)

df["Total_Vehicles"] = df[vehicles].sum(axis=1)

thresholds = [3, 5, 10, 15, 20]

results = []

for (camera, direction), group in df.groupby(["Camera", "Direction"]):
    values = group["Total_Vehicles"]
    
    row = {
        "Camera": camera,
        "Direction": direction,
        "Observations": len(values),
        "Mean": values.mean(),
        "P99": values.quantile(0.99),
        "Maximum": values.max()
    }

    for threshold in thresholds:
        row[f"Above_{threshold}"] = (
            (values > threshold).mean() * 100
        )

    results.append(row)

summary = pd.DataFrame(results)

summary = summary.sort_values(
    "Above_10", ascending=False
)

print(summary.round(4).to_string(index=False))

Path("outputs").mkdir(exist_ok=True)

summary.to_csv(
    "outputs/high_increment_frequency.csv",
    index=False
)
