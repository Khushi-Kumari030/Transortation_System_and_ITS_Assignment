
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

df = pd.read_csv("data/processed/corrected_vehicle_arrivals.csv")

vehicles = ["car", "motorbike", "bus", "truck"]

df = df.dropna(subset=vehicles, how="all").copy()
df[vehicles] = df[vehicles].fillna(0)
df["Total_Vehicles"] = df[vehicles].sum(axis=1)

groups = ["a3_UP", "a3_DOWN", "j1_DOWN", "j3_LEFT", "r2_LEFT"]
df["Camera_Direction"] = df["Camera"] + "_" + df["Direction"]

plt.figure(figsize=(12, 6))

for group in groups:
    values = df.loc[
        df["Camera_Direction"] == group, "Total_Vehicles"
    ]
    plt.hist(
        values[values <= 10],
        bins=[i - 0.5 for i in range(12)],
        alpha=0.4,
        label=group,
        density=True
    )

plt.xlabel("Vehicles recorded per second (0–10)")
plt.ylabel("Proportion of observations")
plt.title("Zoomed per-second vehicle increment distribution")
plt.xticks(range(0, 11))
plt.legend()
plt.tight_layout()

plt.savefig(
    "outputs/increment_distribution_zoomed.png",
    dpi=300
)
plt.show()
