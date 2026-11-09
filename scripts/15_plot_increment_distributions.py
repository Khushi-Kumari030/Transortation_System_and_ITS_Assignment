
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

INPUT = Path("data/processed/corrected_vehicle_arrivals.csv")
OUTPUT = Path("outputs")

df = pd.read_csv(INPUT)

vehicles = ["car", "motorbike", "bus", "truck"]

# Exclude first observations where increments are undefined
df = df.dropna(subset=vehicles, how="all").copy()
df[vehicles] = df[vehicles].fillna(0)

df["Total_Vehicles"] = df[vehicles].sum(axis=1)

# Compare a3 UP with other camera-directions
df["Camera_Direction"] = df["Camera"] + "_" + df["Direction"]

plt.figure(figsize=(13, 6))

for group in ["a3_UP", "a3_DOWN", "j1_DOWN", "j3_LEFT", "r2_LEFT"]:
    values = df.loc[
        df["Camera_Direction"] == group, "Total_Vehicles"
    ]
    plt.hist(
        values,
        bins=range(0, 48, 1),
        alpha=0.45,
        label=group,
        density=True
    )

plt.xlabel("Vehicles recorded per second")
plt.ylabel("Proportion of observations")
plt.title("Per-second vehicle increment distribution")
plt.legend()
plt.tight_layout()

plt.savefig(OUTPUT / "increment_distribution_comparison.png", dpi=300)
plt.show()
