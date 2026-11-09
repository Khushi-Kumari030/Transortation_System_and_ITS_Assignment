
import pandas as pd
from pathlib import Path

df = pd.read_csv(
    "data/processed/corrected_vehicle_arrivals.csv"
)

vehicles = ["car", "motorbike", "bus", "truck"]

df = df.dropna(subset=vehicles, how="all").copy()
df[vehicles] = df[vehicles].fillna(0)

subset = df[
    (df["Camera"] == "a3") &
    (df["Direction"] == "UP")
].copy()

results = []

for vehicle in vehicles:
    x = subset[vehicle]

    results.append({
        "Vehicle_Class": vehicle,
        "Total_Count": x.sum(),
        "Mean_Per_Second": x.mean(),
        "Median": x.median(),
        "P95": x.quantile(0.95),
        "P99": x.quantile(0.99),
        "Maximum": x.max(),
        "Seconds_Above_5": (x > 5).sum(),
        "Seconds_Above_10": (x > 10).sum()
    })

summary = pd.DataFrame(results)

summary["Share_Percent"] = (
    summary["Total_Count"] /
    summary["Total_Count"].sum() * 100
)

print("\nA3 UP: VEHICLE CLASS ANALYSIS")
print(summary.round(3).to_string(index=False))

Path("outputs").mkdir(exist_ok=True)

summary.to_csv(
    "outputs/a3_up_vehicle_class_analysis.csv",
    index=False
)
