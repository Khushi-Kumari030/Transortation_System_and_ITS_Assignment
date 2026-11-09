
import pandas as pd
from pathlib import Path

INPUT = Path("outputs/pcu_15min_intervals.csv")
OUTPUT = Path("outputs")

df = pd.read_csv(INPUT)

# Calculate observed hours from eligible intervals
df["Observed_Hours"] = df["Observed_Seconds"] / 3600

# Aggregate by camera and direction
summary = (
    df.groupby(
        ["Scenario", "Factor_Set", "Camera", "Direction"]
    )
    .agg(
        Total_PCU=("PCU", "sum"),
        Total_Vehicles=("Vehicle_Count", "sum"),
        Observed_Seconds=("Observed_Seconds", "sum"),
        Eligible_Intervals=("Interval", "count")
    )
    .reset_index()
)

summary["Observed_Hours"] = (
    summary["Observed_Seconds"] / 3600
)

summary["PCU_per_Hour"] = (
    summary["Total_PCU"] / summary["Observed_Hours"]
)

summary["Vehicles_per_Hour"] = (
    summary["Total_Vehicles"] / summary["Observed_Hours"]
)

# Rank within each scenario and factor set
summary["PCU_Rank"] = (
    summary.groupby(
        ["Scenario", "Factor_Set"]
    )["PCU_per_Hour"]
    .rank(method="min", ascending=False)
)

# Display results
for (scenario, factor), group in summary.groupby(
    ["Scenario", "Factor_Set"]
):

    print("\n======================================")
    print(scenario, "|", factor)
    print("======================================")

    result = group.sort_values(
        "PCU_per_Hour", ascending=False
    ).head(10)

    print(
        result[
            [
                "Camera",
                "Direction",
                "Total_Vehicles",
                "Total_PCU",
                "Observed_Hours",
                "PCU_per_Hour",
                "Vehicles_per_Hour",
                "PCU_Rank"
            ]
        ].round(2).to_string(index=False)
    )

# Save output
summary.to_csv(
    OUTPUT / "pcu_exposure_normalised_rates.csv",
    index=False
)

print("\nSaved: outputs/pcu_exposure_normalised_rates.csv")
