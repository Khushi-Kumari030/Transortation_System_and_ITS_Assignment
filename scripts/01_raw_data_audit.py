
import zipfile
import pandas as pd
import numpy as np
import re
from pathlib import Path

# ---------------------------------
# 1. PATHS
# ---------------------------------

ZIP_PATH = Path("data/original/traffic.zip")
OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VEHICLES = ["car", "motorbike", "bus", "truck"]

# ---------------------------------
# 2. READ ALL CSV FILES
# ---------------------------------

all_files = []

audit = []

with zipfile.ZipFile(ZIP_PATH, "r") as z:

    csv_files = [
        f for f in z.namelist()
        if f.endswith(".csv")
    ]

    print("Total CSV files:", len(csv_files))

    for file in csv_files:

        df = pd.read_csv(z.open(file))

        # Extract metadata from folder structure
        parts = file.split("/")

        junction = parts[1]
        camera = parts[2]

        filename = parts[-1]

        # Extract date from filename
        match = re.search(r"_(\d{2})(?:_one)?\.csv$", filename)

        day = int(match.group(1))

        segment = "continuation" if "_one" in filename else "primary"

        # Remove completely blank rows
        original_rows = len(df)

        df = df.dropna(
            subset=["Time", "Direction"]
        ).copy()

        df[VEHICLES] = df[VEHICLES].fillna(0)

        # ---------------------------------
        # 3. COLLAPSE REPEATED FRAME RECORDS
        # ---------------------------------

        second_data = (
            df.groupby(
                ["Time", "Direction"],
                as_index=False
            )[VEHICLES]
            .max()
        )

        # ---------------------------------
        # 4. SORT CHRONOLOGICALLY
        # ---------------------------------

        second_data["_time"] = pd.to_timedelta(
            second_data["Time"]
        )

        second_data = second_data.sort_values(
            ["Direction", "_time"]
        )

        
        # ---------------------------------
        # 5. CALCULATE NEW VEHICLES
        # ---------------------------------

        # Preserve original cumulative counters
        cumulative = second_data[VEHICLES].copy()

        # Calculate differences separately for each direction
        new_counts = cumulative.groupby(
            second_data["Direction"]
        ).diff()

        # First observation for each direction
        first_rows = second_data.groupby(
            "Direction",
            sort=False
        ).head(1).index

        # First observation represents the initial counter value
        new_counts.loc[first_rows] = cumulative.loc[first_rows]

        # Check initial counters
        initial_values = cumulative.loc[first_rows]

        if (initial_values < 0).any().any():
            raise ValueError(f"Negative initial counter: {file}")

        # Check for counter decreases
        if (new_counts < 0).any().any():
            raise ValueError(
                f"Counter reset or decrease detected: {file}"
            )

        # Replace original cumulative columns with new counts
        second_data[VEHICLES] = new_counts

        # No missing values should remain
        second_data[VEHICLES] = (
            second_data[VEHICLES].fillna(0)
        )

        # Display initial counter information
        if (initial_values > 0).any().any():
            print("Non-zero initial counter:", file)
            print(initial_values)


        # ---------------------------------
        # 6. ADD METADATA
        # ---------------------------------

        second_data["Junction"] = junction
        second_data["Camera"] = camera
        second_data["Day"] = day
        second_data["Segment"] = segment
        second_data["Source_File"] = filename

        second_data = second_data.drop(
            columns=["_time"]
        )

        all_files.append(second_data)

        # Audit summary
        audit.append({
            "File": filename,
            "Junction": junction,
            "Camera": camera,
            "Day": day,
            "Segment": segment,
            "Original_Rows": original_rows,
            "Valid_Rows": len(df),
            "Unique_Seconds": len(second_data),
            "Blank_Rows": original_rows - len(df),
            "Vehicles_Count": second_data[VEHICLES].sum().sum()
        })

# ---------------------------------
# 7. COMBINE FILES
# ---------------------------------

final_data = pd.concat(
    all_files,
    ignore_index=True
)

audit_df = pd.DataFrame(audit)

# ---------------------------------
# 8. SAVE OUTPUTS
# ---------------------------------

final_data.to_csv(
    OUTPUT_DIR / "per_second_counts_by_file.csv",
    index=False
)

audit_df.to_csv(
    OUTPUT_DIR / "raw_data_audit.csv",
    index=False
)

print("\nAUDIT COMPLETED")

print("Total files:", len(audit_df))

print("Total original rows:",
      audit_df["Original_Rows"].sum())

print("Total blank rows:",
      audit_df["Blank_Rows"].sum())

print("\nVehicle counts:")
print(final_data[VEHICLES].sum())

print("\nJunction-wise vehicle counts:")
print(
    final_data.groupby("Junction")[VEHICLES].sum()
)

print("\nOutput files saved successfully.")
