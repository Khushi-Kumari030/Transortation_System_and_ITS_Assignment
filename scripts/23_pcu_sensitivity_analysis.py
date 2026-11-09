
import pandas as pd
from pathlib import Path

# ==================================================
# 0. PATHS AND SETTINGS
# ==================================================

INPUT = Path("data/processed/corrected_vehicle_arrivals.csv")
OUTPUT = Path("outputs")

OUTPUT.mkdir(parents=True, exist_ok=True)

vehicles = ["car", "motorbike", "bus", "truck"]

# ==================================================
# 1. LOAD DATA
# ==================================================

print("Loading corrected vehicle-arrival dataset...")

df = pd.read_csv(INPUT)

required_columns = [
    "Day", "Time", "Camera", "Direction"
] + vehicles

missing_columns = [
    col for col in required_columns if col not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing required columns in input dataset: {missing_columns}"
    )

# Convert vehicle counts to numeric
for col in vehicles:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

# Remove rows without essential identifiers
df = df.dropna(
    subset=["Day", "Time", "Camera", "Direction"]
).copy()

# Construct timestamps
df["Timestamp"] = (
    pd.to_datetime(
        "2023-01-" +
        df["Day"].astype(int).astype(str).str.zfill(2)
    )
    + pd.to_timedelta(df["Time"].astype(str))
)

# ==================================================
# 2. DEFINE SCENARIOS
# ==================================================

scenarios = {
    "A_All_Cameras": df.copy(),

    "B_Exclude_a3_UP": df[
        ~(
            (df["Camera"] == "a3") &
            (df["Direction"] == "UP")
        )
    ].copy()
}

# ==================================================
# 3. DEFINE PCU FACTORS
# ==================================================

factor_sets = {
    "IRC_SP41": {
        "car": 1.0,
        "motorbike": 0.5,
        "bus": 3.0,
        "truck": 3.0
    },

    # Comparison case only; not the primary estimate
    "IRC106_High_Composition": {
        "car": 1.0,
        "motorbike": 0.75,
        "bus": 3.7,
        "truck": 3.7
    }
}

# ==================================================
# 4. TOTAL PCU COMPARISON
# ==================================================

print("\n========== TOTAL PCU COMPARISON ==========")

total_results = []

for scenario_name, data in scenarios.items():

    for factor_name, factors in factor_sets.items():

        temp = data.copy()

        temp["PCU"] = sum(
            temp[v] * factors[v]
            for v in vehicles
        )

        total_results.append({
            "Scenario": scenario_name,
            "Factor_Set": factor_name,
            "Total_Vehicles": temp[vehicles].sum().sum(),
            "Total_PCU": temp["PCU"].sum()
        })

total_summary = pd.DataFrame(total_results)

print(total_summary.round(2).to_string(index=False))

# ==================================================
# 5. CAMERA-DIRECTION PCU TOTALS
# ==================================================

print("\n========== TOP 10 CAMERA-DIRECTIONS ==========")

movement_results = []

for scenario_name, data in scenarios.items():

    for factor_name, factors in factor_sets.items():

        temp = data.copy()

        temp["PCU"] = sum(
            temp[v] * factors[v]
            for v in vehicles
        )

        # Calculate total vehicles directly
        temp["Vehicle_Count"] = temp[vehicles].sum(axis=1)

        grouped = (
            temp.groupby(["Camera", "Direction"])
            .agg(
                Vehicle_Count=("Vehicle_Count", "sum"),
                PCU_Total=("PCU", "sum")
            )
            .reset_index()
        )

        grouped["Scenario"] = scenario_name
        grouped["Factor_Set"] = factor_name

        movement_results.append(grouped)

movement_summary = pd.concat(
    movement_results,
    ignore_index=True
)

movement_summary["Rank"] = (
    movement_summary.groupby(
        ["Scenario", "Factor_Set"]
    )["PCU_Total"]
    .rank(method="min", ascending=False)
)

for scenario_name in scenarios:

    for factor_name in factor_sets:

        result = movement_summary[
            (movement_summary["Scenario"] == scenario_name) &
            (movement_summary["Factor_Set"] == factor_name)
        ].sort_values(
            "PCU_Total", ascending=False
        ).head(10)

        print(f"\n{scenario_name} | {factor_name}")

        print(
            result[
                [
                    "Camera",
                    "Direction",
                    "Vehicle_Count",
                    "PCU_Total",
                    "Rank"
                ]
            ].round(2).to_string(index=False)
        )

# ==================================================
# 6. 15-MINUTE PCU VOLUMES
# ==================================================

print("\n========== 15-MINUTE PCU ANALYSIS ==========")

interval_results = []

for scenario_name, data in scenarios.items():

    for factor_name, factors in factor_sets.items():

        temp = data.copy()

        temp["PCU"] = sum(
            temp[v] * factors[v]
            for v in vehicles
        )

        # Create 15-minute intervals
        temp["Interval"] = temp["Timestamp"].dt.floor("15min")

        grouped = (
            temp.groupby(
                ["Day", "Camera", "Direction", "Interval"]
            )
            .agg(
                PCU=("PCU", "sum"),
                Vehicle_Count=("Vehicle_Count", "sum")
                if "Vehicle_Count" in temp.columns
                else ("PCU", "size"),
                Observed_Seconds=("Timestamp", "nunique")
            )
            .reset_index()
        )

        # Recalculate vehicle count correctly
        vehicle_counts = (
            temp.assign(
                Vehicle_Count=temp[vehicles].sum(axis=1)
            )
            .groupby(
                ["Day", "Camera", "Direction", "Interval"]
            )["Vehicle_Count"]
            .sum()
            .reset_index()
        )

        grouped = grouped.drop(
            columns=["Vehicle_Count"]
        ).merge(
            vehicle_counts,
            on=["Day", "Camera", "Direction", "Interval"],
            how="left"
        )

        grouped["Coverage_Percent"] = (
            grouped["Observed_Seconds"] / 900 * 100
        )

        # Retain intervals with at least 95% coverage
        grouped = grouped[
            grouped["Coverage_Percent"] >= 95
        ].copy()

        grouped["Scenario"] = scenario_name
        grouped["Factor_Set"] = factor_name

        interval_results.append(grouped)

interval_summary = pd.concat(
    interval_results,
    ignore_index=True
)

# ==================================================
# 7. PEAK 15-MINUTE PCU PERIODS
# ==================================================

print("\n========== TOP 10 PEAK 15-MINUTE PCU PERIODS ==========")

peak_summary = (
    interval_summary.sort_values(
        "PCU", ascending=False
    )
    .groupby(
        ["Scenario", "Factor_Set"],
        group_keys=False
    )
    .head(10)
)

for (scenario_name, factor_name), group in peak_summary.groupby(
    ["Scenario", "Factor_Set"]
):

    print(f"\n{scenario_name} | {factor_name}")

    print(
        group[
            [
                "Day",
                "Camera",
                "Direction",
                "Interval",
                "Vehicle_Count",
                "PCU",
                "Coverage_Percent"
            ]
        ].round(2).to_string(index=False)
    )

# ==================================================
# 8. SAVE OUTPUT FILES
# ==================================================

total_summary.to_csv(
    OUTPUT / "pcu_total_comparison.csv",
    index=False
)

movement_summary.to_csv(
    OUTPUT / "pcu_camera_direction_summary.csv",
    index=False
)

interval_summary.to_csv(
    OUTPUT / "pcu_15min_intervals.csv",
    index=False
)

peak_summary.to_csv(
    OUTPUT / "pcu_peak_15min_periods.csv",
    index=False
)

print("\n==========================================")
print("PCU ANALYSIS COMPLETED SUCCESSFULLY")
print("==========================================")

print("\nFiles saved:")
print("1. outputs/pcu_total_comparison.csv")
print("2. outputs/pcu_camera_direction_summary.csv")
print("3. outputs/pcu_15min_intervals.csv")
print("4. outputs/pcu_peak_15min_periods.csv")
