
import pandas as pd
from pathlib import Path

# --------------------------------------------------
# 1. LOAD CORRECTED DATA
# --------------------------------------------------

INPUT = Path("data/processed/corrected_vehicle_arrivals.csv")
OUTPUT = Path("outputs")
OUTPUT.mkdir(exist_ok=True)

df = pd.read_csv(INPUT)

vehicles = ["car", "motorbike", "bus", "truck"]

# Exclude first observations with undefined increments
df = df.dropna(subset=vehicles, how="all").copy()
df[vehicles] = df[vehicles].fillna(0)

df["Total_Vehicles"] = df[vehicles].sum(axis=1)

# Construct actual January 2023 timestamps
# Day is the day of January; Time is HH:MM:SS
df["Timestamp"] = (
    pd.to_datetime(
        "2023-01-" + df["Day"].astype(int).astype(str).str.zfill(2)
    )
    + pd.to_timedelta(df["Time"])
)

# --------------------------------------------------
# 2. DEFINE TWO SCENARIOS
# --------------------------------------------------

scenario_a = df.copy()

scenario_b = df[
    ~(
        (df["Camera"] == "a3") &
        (df["Direction"] == "UP")
    )
].copy()

scenarios = {
    "A_All_Cameras": scenario_a,
    "B_Exclude_a3_UP": scenario_b
}

# --------------------------------------------------
# 3. TOTAL TRAFFIC AND VEHICLE COMPOSITION
# --------------------------------------------------

total_results = []
composition_results = []

for name, data in scenarios.items():

    total = data["Total_Vehicles"].sum()

    total_results.append({
        "Scenario": name,
        "Total_Vehicle_Increments": total,
        "Car": data["car"].sum(),
        "Motorbike": data["motorbike"].sum(),
        "Bus": data["bus"].sum(),
        "Truck": data["truck"].sum()
    })

    for vehicle in vehicles:
        count = data[vehicle].sum()

        composition_results.append({
            "Scenario": name,
            "Vehicle_Class": vehicle,
            "Count": count,
            "Share_Percent": (
                count / total * 100 if total > 0 else 0
            )
        })

total_summary = pd.DataFrame(total_results)
composition_summary = pd.DataFrame(composition_results)

# --------------------------------------------------
# 4. 15-MINUTE VOLUME AND COVERAGE
# --------------------------------------------------

interval_results = []

for name, data in scenarios.items():

    temp = data.copy()

    temp["Interval"] = temp["Timestamp"].dt.floor("15min")

    grouped = (
        temp.groupby(
            ["Day", "Camera", "Direction", "Interval"]
        )
        .agg(
            Total_Vehicles=("Total_Vehicles", "sum"),
            Observed_Seconds=("Timestamp", "nunique")
        )
        .reset_index()
    )

    grouped["Coverage_Percent"] = (
        grouped["Observed_Seconds"] / 900 * 100
    )

    # Keep intervals with at least 95% coverage
    eligible = grouped[
        grouped["Coverage_Percent"] >= 95
    ].copy()

    eligible["Scenario"] = name

    interval_results.append(eligible)

interval_summary = pd.concat(
    interval_results,
    ignore_index=True
)

# --------------------------------------------------
# 5. PEAK 15-MINUTE PERIODS
# --------------------------------------------------

peak_summary = (
    interval_summary.sort_values(
        "Total_Vehicles",
        ascending=False
    )
    .groupby("Scenario")
    .head(10)
    .copy()
)

# --------------------------------------------------
# 6. PRINT RESULTS
# --------------------------------------------------

print("\n========== TOTAL TRAFFIC COMPARISON ==========")
print(total_summary.round(2).to_string(index=False))

print("\n========== VEHICLE COMPOSITION ==========")
print(composition_summary.round(2).to_string(index=False))

print("\n========== ELIGIBLE 15-MINUTE INTERVALS ==========")

coverage_summary = (
    interval_summary.groupby("Scenario")
    .agg(
        Eligible_Intervals=("Total_Vehicles", "count"),
        Mean_Coverage=("Coverage_Percent", "mean")
    )
    .reset_index()
)

print(coverage_summary.round(2).to_string(index=False))

print("\n========== TOP 10 PEAK PERIODS ==========")

print(
    peak_summary[
        [
            "Scenario",
            "Day",
            "Camera",
            "Direction",
            "Interval",
            "Total_Vehicles",
            "Coverage_Percent"
        ]
    ].round(2).to_string(index=False)
)

# --------------------------------------------------
# 7. SAVE OUTPUTS
# --------------------------------------------------

total_summary.to_csv(
    OUTPUT / "sensitivity_total_comparison.csv",
    index=False
)

composition_summary.to_csv(
    OUTPUT / "sensitivity_vehicle_composition.csv",
    index=False
)

interval_summary.to_csv(
    OUTPUT / "sensitivity_15min_intervals.csv",
    index=False
)

peak_summary.to_csv(
    OUTPUT / "sensitivity_peak_periods.csv",
    index=False
)

coverage_summary.to_csv(
    OUTPUT / "sensitivity_coverage_summary.csv",
    index=False
)

print("\nAll sensitivity-analysis outputs saved.")
