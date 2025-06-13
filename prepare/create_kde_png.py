import os
import pandas as pd
import numpy as np
from PIL import Image
import yaml
from scipy.stats import gaussian_kde
from sklearn.preprocessing import MinMaxScaler
import math

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Constants
IMAGE_SIZE = config['image_size']
BASE_PNG_OUTPUT_DIR = config['png_output_directory']

OVERLAP_MODE = "not_overlapped" if config['window_overlap'] == 0.0 else "overlapped"
OVERLAP_OUTPUT_DIR = os.path.join(BASE_PNG_OUTPUT_DIR, OVERLAP_MODE)

MAX_PACKET_LENGTH = 1500
SESSION_DURATION = config["capture_duration"] + config["warmup_time"]
USE_GAMMA_BOOST = True
WINDOW_SIZE = config['window_size']
WINDOW_OVERLAP = config['window_overlap']
STEP_SIZE = WINDOW_SIZE * (1 - WINDOW_OVERLAP)

def create_kde_density_image(df, image_size=IMAGE_SIZE):
    image = np.zeros((image_size, image_size, 3), dtype=np.float32)

    def normalize_packets(subset_df):
        t = subset_df['Time'].values.reshape(-1, 1)
        l = subset_df['Length'].values.reshape(-1, 1)
        t_scaled = MinMaxScaler(feature_range=(0, image_size - 1)).fit_transform(t)
        l_scaled = MinMaxScaler(feature_range=(0, image_size - 1)).fit_transform(l)
        return np.vstack([t_scaled.ravel(), l_scaled.ravel()])

    for direction, channel in [(0, 2), (1, 0)]:
        sub_df = df[df['Direction'] == direction]
        if len(sub_df) == 0:
            continue

        values = normalize_packets(sub_df)

        try:
            kde = gaussian_kde(values, bw_method='scott')
        except np.linalg.LinAlgError:
            print(f"[WARN] KDE failed for direction {direction} due to singular matrix.")
            continue

        x_grid, y_grid = np.meshgrid(
            np.linspace(0, image_size - 1, image_size),
            np.linspace(0, image_size - 1, image_size)
        )
        coords = np.vstack([x_grid.ravel(), y_grid.ravel()])
        z = kde(coords).reshape(image_size, image_size)
        image[:, :, channel] = z

    return image

def normalize_histogram(hist):
    for c in [0, 2]:  # Red and Blue channels
        channel = hist[:, :, c]
        min_val, max_val = channel.min(), channel.max()
        if max_val > min_val:
            hist[:, :, c] = (channel - min_val) * 255 / (max_val - min_val)

    if USE_GAMMA_BOOST:
        hist = np.power(hist / 255, 0.5) * 255

    return hist

def create_pngs_from_trace(cleaned_csv_path):
    try:
        df = pd.read_csv(cleaned_csv_path)
    except Exception as e:
        print(f"[ERROR] Failed to load {cleaned_csv_path}: {e}")
        return

    if df.empty:
        print(f"[WARN] Empty DataFrame for {cleaned_csv_path}, skipping.")
        return

    min_time = float(df['Time'].min())
    max_time = float(df['Time'].max())
    total_duration = max_time - min_time

    relative_path = os.path.relpath(cleaned_csv_path, config['csv_output_directory'])
    category, application, filename = relative_path.split(os.sep)
    base_filename = filename.replace('cleaned_', '').replace('.csv', '')
    save_dir = os.path.join(OVERLAP_OUTPUT_DIR, category, application)
    os.makedirs(save_dir, exist_ok=True)

    if total_duration < WINDOW_SIZE:
        print(f"[INFO] Short trace ({total_duration:.2f}s), generating one window up to {WINDOW_SIZE}s")
        window_end = min_time + WINDOW_SIZE
        window_df = df[(df['Time'] >= min_time) & (df['Time'] <= window_end)]

        img_data = create_kde_density_image(window_df)
        img_data = normalize_histogram(img_data)
        img = Image.fromarray(np.uint8(img_data), mode="RGB").transpose(Image.FLIP_TOP_BOTTOM)

        save_path = os.path.join(save_dir, f"{base_filename}_0.png")
        img.save(save_path)
        print(f"[INFO] Saved single PNG to {save_path}.")
        return

    num_windows = math.floor((total_duration - WINDOW_SIZE) / STEP_SIZE) + 1
    for i in range(num_windows):
        window_start = min_time + i * STEP_SIZE
        window_end = window_start + WINDOW_SIZE

        if window_end > max_time:
            window_end = max_time
            window_start = window_end - WINDOW_SIZE
            if window_start < min_time:
                break

        window_df = df[(df['Time'] >= window_start) & (df['Time'] < window_end)]
        if window_df.empty:
            continue

        img_data = create_kde_density_image(window_df)
        img_data = normalize_histogram(img_data)
        img = Image.fromarray(np.uint8(img_data), mode="RGB").transpose(Image.FLIP_TOP_BOTTOM)

        save_path = os.path.join(save_dir, f"{base_filename}_{i}.png")
        img.save(save_path)
        print(f"[INFO] Saved PNG to {save_path}.")

def create_pngs_for_all_cleaned_csvs(base_cleaned_csv_dir=config['csv_output_directory'], skip_categories=[]):
    for root, dirs, files in os.walk(base_cleaned_csv_dir):
        if any(skip in root for skip in skip_categories):
            continue
        for file in files:
            if file.startswith('cleaned_') and file.endswith('.csv'):
                cleaned_csv_path = os.path.join(root, file)
                create_pngs_from_trace(cleaned_csv_path)

if __name__ == "__main__":
    create_pngs_for_all_cleaned_csvs(skip_categories=["browsing", "game", "streaming", "video"])
