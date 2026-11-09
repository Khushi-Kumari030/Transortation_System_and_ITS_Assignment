
import pandas as pd
from pathlib import Path

df = pd.read_csv(
    "data/processed/corrected_vehicle_arrivals.csv"
)

# Focus on a3 UP
df = df[
    (df["Camera"] == "a3") &
    (df["Direction"] == "UP")
].copy()

results = []

for filename, group in df.groupby("Source_File"):

    car = group["car"].dropna()

    results.append({
        "Source_File": filename,
        "Observations": len(car),
        "Car_Total": car.sum(),
        "Car_Mean": car.mean(),
        "Car_P95": car.quantile(0.95),
        "Car_P99": car.quantile(0.99),
        "Car_Maximum": car.max(),
        "Seconds_Above_5": (car > 5).sum(),
        "Seconds_Above_10": (car > 10).sum(),
        "Seconds_Above_20": (car > 20).sum()
    })

summary = pd.DataFrame(results)

summary["Above_10_Percent"] = (
    summary["Seconds_Above_10"] /
    summary["Observations"] * 100
)

summary = summary.sort_values(
    "Above_10_Percent",
    ascending=False
)

print("\nA3 UP: FILE-WISE CAR ANALYSIS")
print(summary.round(3).to_string(index=False))

Path("outputs").mkdir(exist_ok=True)

summary.to_csv(
    "outputs/a3_up_car_file_analysis.csv",
    index=False
)
