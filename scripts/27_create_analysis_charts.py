
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


# ---------------------------------------------------------
# PATHS AND SETTINGS
# ---------------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "outputs"
FIGURE_DIR = OUTPUT_DIR / "figures"
FIGURE_DIR.mkdir(parents=True, exist_ok=True)

composition_file = OUTPUT_DIR / "vehicle_composition_by_camera.csv"
peak_summary_file = OUTPUT_DIR / "peak_hour_summary_by_camera.csv"
time_profile_file = OUTPUT_DIR / "peak_hour_time_profile.csv"
daily_peak_file = OUTPUT_DIR / "daily_peak_hour_by_camera.csv"

# Consistent camera ordering
camera_order = ["a2", "a3", "j1", "j2", "j3", "r1", "r2", "r3"]

junction_order = [
    "Alankar Chowk",
    "Jehangir Chowk",
    "RTO Chowk"
]


# ---------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------

composition = pd.read_csv(composition_file)
peak_summary = pd.read_csv(peak_summary_file)
time_profile = pd.read_csv(time_profile_file)
daily_peak = pd.read_csv(daily_peak_file)

# Ensure camera order is consistent
for df in [composition, peak_summary, time_profile, daily_peak]:
    df["Camera"] = pd.Categorical(
        df["Camera"],
        categories=camera_order,
        ordered=True
    )

composition = composition.sort_values("Camera")
peak_summary = peak_summary.sort_values("Camera")
time_profile = time_profile.sort_values(
    ["Camera", "Hour_Start_Time"]
)
daily_peak = daily_peak.sort_values(
    ["Camera", "Day"]
)

print("All four input files loaded successfully.")
print("Creating report figures...")


# ---------------------------------------------------------
# FIGURE 1: VEHICLE COMPOSITION BY CAMERA
# ---------------------------------------------------------

vehicle_classes = ["car", "motorbike", "bus", "truck"]

composition_plot = composition.set_index("Camera")[
    vehicle_classes
]

ax = composition_plot.plot(
    kind="bar",
    stacked=True,
    figsize=(11, 6),
    width=0.75
)

ax.set_title(
    "Vehicle Composition by Camera",
    fontsize=15,
    pad=15
)
ax.set_xlabel("Camera")
ax.set_ylabel("Observed Vehicle Arrivals")
ax.legend(
    title="Vehicle Class",
    bbox_to_anchor=(1.02, 1),
    loc="upper left"
)

ax.tick_params(axis="x", rotation=0)
ax.grid(axis="y", alpha=0.25)

plt.figtext(
    0.5, 0.01,
    "Scenario B: a3-UP excluded. Camera-level observations; "
    "counts across cameras are not unique junction totals.",
    ha="center",
    fontsize=8
)

plt.tight_layout(rect=[0, 0.04, 0.85, 1])

plt.savefig(
    FIGURE_DIR / "01_vehicle_composition_by_camera.png",
    dpi=300,
    bbox_inches="tight"
)
plt.close()


# ---------------------------------------------------------
# FIGURE 2: AVERAGE DAILY PEAK-HOUR PCU BY CAMERA
# ---------------------------------------------------------

peak_plot = peak_summary.sort_values(
    "Average_Peak_Hour_PCU",
    ascending=True
)

fig, ax = plt.subplots(figsize=(10, 6))

bars = ax.barh(
    peak_plot["Camera"].astype(str),
    peak_plot["Average_Peak_Hour_PCU"]
)

ax.set_title(
    "Average Daily Peak-Hour Traffic by Camera",
    fontsize=15,
    pad=15
)
ax.set_xlabel("Peak-Hour Traffic (PCU/hour)")
ax.set_ylabel("Camera")
ax.grid(axis="x", alpha=0.25)

# Add values at the end of bars
for bar in bars:
    width = bar.get_width()
    ax.text(
        width + 30,
        bar.get_y() + bar.get_height() / 2,
        f"{width:,.0f}",
        va="center",
        fontsize=9
    )

plt.figtext(
    0.5, 0.01,
    "Average of daily maximum rolling one-hour PCU values. "
    "Scenario B; IRC:SP:41 factors.",
    ha="center",
    fontsize=8
)

plt.tight_layout(rect=[0, 0.04, 1, 1])

plt.savefig(
    FIGURE_DIR / "02_average_peak_hour_pcu_by_camera.png",
    dpi=300,
    bbox_inches="tight"
)
plt.close()


# ---------------------------------------------------------
# FIGURE 3: AVERAGE ROLLING-HOUR PROFILE
# Three panels, one for each junction
# ---------------------------------------------------------

fig, axes = plt.subplots(
    nrows=3,
    ncols=1,
    figsize=(12, 13),
    sharex=True
)

for ax, junction in zip(axes, junction_order):

    junction_data = time_profile[
        time_profile["Junction"] == junction
    ].copy()

    for camera in camera_order:

        camera_data = junction_data[
            junction_data["Camera"] == camera
        ].copy()

        if camera_data.empty:
            continue

        camera_data = camera_data.sort_values(
            "Hour_Start_Time"
        )

        ax.plot(
            camera_data["Hour_Start_Time"],
            camera_data["Average_Rolling_Hour_PCU"],
            marker="o",
            markersize=3,
            linewidth=1.5,
            label=camera
        )

    ax.set_title(junction, fontsize=12)
    ax.set_ylabel("Average PCU/hour")
    ax.grid(alpha=0.25)
    ax.legend(title="Camera", ncol=4)

axes[-1].set_xlabel("Rolling-hour start time")

fig.suptitle(
    "Average Rolling-Hour Traffic Profile by Junction",
    fontsize=15,
    y=0.995
)

plt.figtext(
    0.5, 0.005,
    "Each point averages valid rolling one-hour windows "
    "starting at the indicated time.",
    ha="center",
    fontsize=8
)

plt.tight_layout(rect=[0, 0.025, 1, 0.98])

plt.savefig(
    FIGURE_DIR / "03_rolling_hour_profile.png",
    dpi=300,
    bbox_inches="tight"
)
plt.close()


# ---------------------------------------------------------
# FIGURE 4: DAILY PEAK-HOUR PCU
# Three panels, one for each junction
# ---------------------------------------------------------

daily_peak["Date"] = pd.to_datetime(
    daily_peak["Day"].astype(str).apply(
        lambda day: "2023-01-" + day.zfill(2)
    )
)

fig, axes = plt.subplots(
    nrows=3,
    ncols=1,
    figsize=(12, 13),
    sharex=True
)

for ax, junction in zip(axes, junction_order):

    junction_data = daily_peak[
        daily_peak["Junction"] == junction
    ].copy()

    for camera in camera_order:

        camera_data = junction_data[
            junction_data["Camera"] == camera
        ].sort_values("Date")

        if camera_data.empty:
            continue

        ax.plot(
            camera_data["Date"],
            camera_data["Peak_Hour_PCU"],
            marker="o",
            linewidth=1.5,
            label=camera
        )

    ax.set_title(junction, fontsize=12)
    ax.set_ylabel("Peak-Hour PCU")
    ax.grid(alpha=0.25)
    ax.legend(title="Camera", ncol=4)

axes[-1].set_xlabel("Date")
axes[-1].xaxis.set_major_formatter(
    mdates.DateFormatter("%d %b")
)

fig.suptitle(
    "Daily Peak-Hour Traffic Variation",
    fontsize=15,
    y=0.995
)

plt.figtext(
    0.5, 0.005,
    "Daily maximum rolling one-hour PCU. "
    "Scenario B; IRC:SP:41 factors.",
    ha="center",
    fontsize=8
)

plt.tight_layout(rect=[0, 0.025, 1, 0.98])

plt.savefig(
    FIGURE_DIR / "04_daily_peak_hour_variation.png",
    dpi=300,
    bbox_inches="tight"
)
plt.close()


# ---------------------------------------------------------
# FINAL OUTPUT
# ---------------------------------------------------------

print("\nAll figures generated successfully.")

for file in sorted(FIGURE_DIR.glob("*.png")):
    print(f"Saved: {file}")

print("\nFigure folder:", FIGURE_DIR)
