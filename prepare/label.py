import os
import csv
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

PNG_OUTPUT_DIR = config['png_output_directory']
LABEL_OUTPUT_DIR = config['label_output_directory']

LABELS_CSV_PATH = os.path.join(LABEL_OUTPUT_DIR, 'labels.csv')


def collect_labels(png_dir):
    """
    Walk through the PNG directory and collect file paths, category, and application labels.
    """
    rows = []

    for root, dirs, files in os.walk(png_dir):
        for file in files:
            if file.endswith('.png'):
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, png_dir)
                parts = relative_path.split(os.sep)

                if len(parts) >= 3:
                    category = parts[0]
                    application = parts[1]
                    png_relative_path = os.path.join(*parts)

                    rows.append([png_relative_path, category, application])

    return rows


def save_labels_to_csv(rows, save_path):
    os.makedirs(os.path.dirname(save_path), exist_ok=True)

    with open(save_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['filepath', 'category', 'application'])  # Header
        for row in rows:
            writer.writerow(row)

    print(f"[INFO] Saved labels to {save_path}.")


def main():
    rows = collect_labels(PNG_OUTPUT_DIR)
    save_labels_to_csv(rows, LABELS_CSV_PATH)


if __name__ == "__main__":
    main()