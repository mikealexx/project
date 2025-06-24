import os
import csv
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

PNG_OUTPUT_DIR = config['png_output_directory']
LABEL_OUTPUT_DIR = config['label_output_directory']

def collect_labels(png_dir):
    """
    Walk through the PNG directory and collect file paths, category, and application labels.
    """
    rows = []

    for root, dirs, files in os.walk(png_dir):
        for file in files:
            if file.endswith('.png'):
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, PNG_OUTPUT_DIR)
                parts = relative_path.split(os.sep)

                if len(parts) >= 4:
                    overlap_mode = parts[0]
                    category = parts[1]
                    application = parts[2]
                    png_relative_path = os.path.join(*parts)
                    rows.append([png_relative_path, category, application])

    return rows

def save_labels_to_csv(rows, save_path):
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    with open(save_path, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['filepath', 'category', 'application'])  # Header
        writer.writerows(rows)
    print(f"[INFO] Saved labels to {save_path}.")

def main():
    overlapped_dir = os.path.join(PNG_OUTPUT_DIR, 'overlapped')
    not_overlapped_dir = os.path.join(PNG_OUTPUT_DIR, 'not_overlapped')

    overlapped_rows = collect_labels(overlapped_dir)
    not_overlapped_rows = collect_labels(not_overlapped_dir)

    save_labels_to_csv(overlapped_rows, os.path.join(LABEL_OUTPUT_DIR, 'labels_overlapped.csv'))
    save_labels_to_csv(not_overlapped_rows, os.path.join(LABEL_OUTPUT_DIR, 'labels_not_overlapped.csv'))

if __name__ == "__main__":
    main()
