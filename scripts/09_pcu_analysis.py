
import pandas as pd
from pathlib import Path

# -------------------------------------------------
# PATHS
# -------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_DIR / "outputs"
    / "hourly_traffic_volume.csv"
)

OUTPUT_DIR = PROJECT_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VEHICLES = ["car", "motorbike", "bus", "truck"]

# Scenario 1: IRC:SP:41 intersection-oriented factors
SP41 = {
    "car": 1.0,
    "motorbike": 0.5,
    "bus": 3.0,
    "truck": 3.0
}

# Scenario 2: IRC:106-1990 urban-road factors
IRC106 = {
    "car": 1.0,
    "motorbike": 0.75,
    "bus": 3.7,
    "truck": 3.7
}

# -------------------------------------------------
# LOAD HOURLY DATA
# -------------------------------------------------

df = pd.read_csv(INPUT_FILE)

for col in VEHICLES:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df["Coverage_Percent"] = pd.to_numeric(
    df["Coverage_Percent"], errors="coerce"
)

# -------------------------------------------------
# CALCULATE PCU UNDER BOTH SCENARIOS
# -------------------------------------------------

df["PCU_SP41"] = sum(
    df[vehicle] * SP41[vehicle]
    for vehicle in VEHICLES
)

df["PCU_IRC106"] = sum(
    df[vehicle] * IRC106[vehicle]
    for vehicle in VEHICLES
)

df["PCU_SP41_per_hour"] = df["PCU_SP41"]
df["PCU_IRC106_per_hour"] = df["PCU_IRC106"]

# -------------------------------------------------
# SAVE HOURLY PCU DATA
# -------------------------------------------------

hourly_file = OUTPUT_DIR / "hourly_pcu_analysis.csv"
df.to_csv(hourly_file, index=False)

# -------------------------------------------------
# PEAK PCU PERIODS
# Only use hours with at least 95% coverage
# -------------------------------------------------

eligible = df[
    (df["Coverage_Percent"] >= 95)
    & (df["Eligible_For_Peak"] == True)
].copy()

groups = ["Day", "Camera", "Direction"]

sp41_idx = eligible.groupby(groups)["PCU_SP41"].idxmax()
irc106_idx = eligible.groupby(groups)["PCU_IRC106"].idxmax()

peak_sp41 = eligible.loc[sp41_idx].copy()
peak_irc106 = eligible.loc[irc106_idx].copy()

peak_sp41 = peak_sp41.sort_values(
    "PCU_SP41", ascending=False
)

peak_irc106 = peak_irc106.sort_values(
    "PCU_IRC106", ascending=False
)

peak_file = OUTPUT_DIR / "peak_hour_pcu.csv"

peak_sp41[
    [
        "Day", "Camera", "Direction", "Hour",
        "Total_Vehicles", "PCU_SP41",
        "Coverage_Percent"
    ]
].to_csv(
    OUTPUT_DIR / "peak_hour_pcu_sp41.csv",
    index=False
)

peak_irc106[
    [
        "Day", "Camera", "Direction", "Hour",
        "Total_Vehicles", "PCU_IRC106",
        "Coverage_Percent"
    ]
].to_csv(
    OUTPUT_DIR / "peak_hour_pcu_irc106.csv",
    index=False
)

# -------------------------------------------------
# CAMERA-DIRECTION SUMMARY
# Use eligible hours only
# -------------------------------------------------

summary = (
    eligible.groupby(["Camera", "Direction"])
    .agg(
        Eligible_Hours=("PCU_SP41", "count"),
        Average_PCU_SP41=("PCU_SP41", "mean"),
        Maximum_PCU_SP41=("PCU_SP41", "max"),
        Average_PCU_IRC106=("PCU_IRC106", "mean"),
        Maximum_PCU_IRC106=("PCU_IRC106", "max")
    )
    .reset_index()
)

summary = summary.sort_values(
    "Average_PCU_SP41", ascending=False
)

summary_file = OUTPUT_DIR / "camera_direction_pcu_summary.csv"
summary.to_csv(summary_file, index=False)

# -------------------------------------------------
# OVERALL SUMMARY
# -------------------------------------------------

print("\n" + "=" * 65)
print("PASSENGER CAR UNIT (PCU) ANALYSIS")
print("=" * 65)

print("\nEligible hourly observations:", len(eligible))

print("\nTotal observed PCU:")
print("IRC:SP:41:", round(eligible["PCU_SP41"].sum(), 2))
print("IRC:106:", round(eligible["PCU_IRC106"].sum(), 2))

print("\nTop 10 peak PCU hours (IRC:SP:41):")
print(
    peak_sp41[
        [
            "Day", "Camera", "Direction",
            "Hour", "PCU_SP41"
        ]
    ].head(10).to_string(index=False)
)

print("\nTop 10 peak PCU hours (IRC:106):")
print(
    peak_irc106[
        [
            "Day", "Camera", "Direction",
            "Hour", "PCU_IRC106"
        ]
    ].head(10).to_string(index=False)
)

print("\nCamera-direction PCU summary:")
print(summary.head(15).round(2).to_string(index=False))

print("\nSaved:")
print(hourly_file)
print(OUTPUT_DIR / "peak_hour_pcu_sp41.csv")
print(OUTPUT_DIR / "peak_hour_pcu_irc106.csv")
print(summary_file)
