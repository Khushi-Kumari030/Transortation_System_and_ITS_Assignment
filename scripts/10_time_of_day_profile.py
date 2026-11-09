
import pandas as pd
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]

INPUT_FILE = (
    PROJECT_DIR / "outputs"
    / "hourly_pcu_analysis.csv"
)

OUTPUT_DIR = PROJECT_DIR / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------
# LOAD DATA
# -------------------------------------------------

df = pd.read_csv(INPUT_FILE)

df["Coverage_Percent"] = pd.to_numeric(
    df["Coverage_Percent"], errors="coerce"
)

df["PCU_SP41"] = pd.to_numeric(
    df["PCU_SP41"], errors="coerce"
)

df["PCU_IRC106"] = pd.to_numeric(
    df["PCU_IRC106"], errors="coerce"
)

# Retain only sufficiently complete hours
df = df[df["Coverage_Percent"] >= 95].copy()

# Extract hour of day
df["Hour_of_Day"] = pd.to_datetime(
    df["Hour"], format="%H:%M"
).dt.hour

# -------------------------------------------------
# AVERAGE HOURLY PCU BY TIME OF DAY
# -------------------------------------------------

groups = ["Camera", "Direction", "Hour_of_Day"]

profile = (
    df.groupby(groups)
    .agg(
        Number_of_Days=("Day", "nunique"),
        Average_PCU_SP41=("PCU_SP41", "mean"),
        Maximum_PCU_SP41=("PCU_SP41", "max"),
        Average_PCU_IRC106=("PCU_IRC106", "mean"),
        Maximum_PCU_IRC106=("PCU_IRC106", "max")
    )
    .reset_index()
)

profile["Hour_Label"] = profile["Hour_of_Day"].apply(
    lambda x: f"{x:02d}:00"
)

profile_file = OUTPUT_DIR / "time_of_day_pcu_profile.csv"
profile.to_csv(profile_file, index=False)

# -------------------------------------------------
# TYPICAL PEAK HOUR FOR EACH CAMERA-DIRECTION
# -------------------------------------------------

peak_idx = (
    profile.groupby(["Camera", "Direction"])
    ["Average_PCU_SP41"].idxmax()
)

typical_peak = profile.loc[peak_idx].copy()

typical_peak = typical_peak.sort_values(
    "Average_PCU_SP41", ascending=False
)

typical_peak_file = (
    OUTPUT_DIR / "typical_peak_hour_by_approach.csv"
)

typical_peak.to_csv(typical_peak_file, index=False)

# -------------------------------------------------
# OVERALL TIME-OF-DAY PROFILE
# -------------------------------------------------

overall = (
    df.groupby("Hour_of_Day")
    .agg(
        Camera_Direction_Observations=("PCU_SP41", "count"),
        Average_PCU_SP41=("PCU_SP41", "mean"),
        Average_PCU_IRC106=("PCU_IRC106", "mean")
    )
    .reset_index()
)

overall["Hour_Label"] = overall["Hour_of_Day"].apply(
    lambda x: f"{x:02d}:00"
)

overall_file = OUTPUT_DIR / "overall_time_of_day_profile.csv"
overall.to_csv(overall_file, index=False)

# -------------------------------------------------
# PRINT RESULTS
# -------------------------------------------------

print("\n" + "=" * 65)
print("TIME-OF-DAY PCU PROFILE")
print("=" * 65)

print("\nNumber of eligible observations:", len(df))

print("\nTypical peak hour by camera and direction:")
print(
    typical_peak[
        [
            "Camera", "Direction", "Hour_Label",
            "Number_of_Days", "Average_PCU_SP41",
            "Maximum_PCU_SP41"
        ]
    ].to_string(index=False)
)

print("\nOverall average PCU by hour:")
print(
    overall[
        [
            "Hour_Label",
            "Camera_Direction_Observations",
            "Average_PCU_SP41"
        ]
    ].to_string(index=False)
)

print("\nSaved:")
print(profile_file)
print(typical_peak_file)
print(overall_file)
