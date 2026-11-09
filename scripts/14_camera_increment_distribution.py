
import pandas as pd
from pathlib import Path

INPUT = Path("data/processed/corrected_vehicle_arrivals.csv")

df = pd.read_csv(INPUT)

vehicles = ["car", "motorbike", "bus", "truck"]

df["Total_Vehicles"] = df[vehicles].sum(axis=1)

summary = (
    df.groupby(["Camera", "Direction"])["Total_Vehicles"]
      .agg(
          observations="count",
          mean="mean",
          median="median",
          p95=lambda x: x.quantile(0.95),
          p99=lambda x: x.quantile(0.99),
          maximum="max",
          total="sum"
      )
      .reset_index()
)

summary = summary.sort_values(
    ["maximum", "p99"], ascending=False
)

print("\nCAMERA-DIRECTION INCREMENT DISTRIBUTION")
print(summary.round(2).to_string(index=False))

summary.to_csv(
    "outputs/camera_increment_distribution.csv",
    index=False
)

# Specifically compare a3 UP against the other movements
print("\nA3 UP COMPARISON")
print(
    summary[
        (summary["Camera"] == "a3")
        & (summary["Direction"] == "UP")
    ].round(2).to_string(index=False)
)

print("\nSaved outputs/camera_increment_distribution.csv")
