import os
import pandas as pd
import yaml
from glob import glob

def load_config():
    with open("config.yaml", "r") as f:
        return yaml.safe_load(f)

def compute_capture_time(csv_path):
    df = pd.read_csv(csv_path)
    if "Time" not in df.columns:
        raise ValueError(f"'Time' column missing in {csv_path}")
    return df["Time"].max() - df["Time"].min()

def main():
    config = load_config()
    base_dir = config["csv_output_directory"]

    for category in os.listdir(base_dir):
        category_path = os.path.join(base_dir, category)
        if not os.path.isdir(category_path):
            continue

        csv_files = glob(os.path.join(category_path, "**", "cleaned_*.csv"), recursive=True)
        if not csv_files:
            print(f"No CSV files found in category '{category}'")
            continue

        total_time = 0
        count = 0
        max_time = 0

        for csv_file in csv_files:
            try:
                duration = compute_capture_time(csv_file)
                total_time += duration
                max_time = max(max_time, duration)
                count += 1
            except Exception as e:
                print(f"Error processing {csv_file}: {e}")

        if count > 0:
            avg_time = total_time / count
            print(f"Category '{category}' - Average capture time: {avg_time:.2f} seconds, Max capture time: {max_time:.2f} seconds")
        else:
            print(f"Category '{category}' - No valid CSVs processed")

if __name__ == "__main__":
    main()
