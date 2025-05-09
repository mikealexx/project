import os
import pandas as pd
import numpy as np
from PIL import Image
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Constants
IMAGE_SIZE = config["image_size"]  # Default to 64 if not set
PNG_OUTPUT_DIR = config['png_output_directory']
MAX_PACKET_LENGTH = 1500  # Ethernet MTU
SESSION_DURATION = 10.5   # seconds
USE_GAMMA_BOOST = config.get('use_gamma_boost', True)


def create_histogram(df, time_bins, length_bins, window_size=SESSION_DURATION):
    """
    Create a histogram for client-server and server-client packets.
    """
    hist = np.zeros((length_bins, time_bins, 3))

    dt_step = window_size / time_bins
    dl_step = MAX_PACKET_LENGTH / length_bins

    for x, dt in enumerate(np.arange(start=0, stop=window_size, step=dt_step)):
        relevant_time = (df['Time'] >= dt) & (df['Time'] < dt + dt_step)

        # Client -> Server (Direction == 0)
        client_relevant = (df['Direction'] == 0)
        server_relevant = (df['Direction'] == 1)

        for y, dl in enumerate(np.arange(start=0, stop=MAX_PACKET_LENGTH, step=dl_step)):
            relevant_length = (df['Length'] > dl) & (df['Length'] <= dl + dl_step)

            hist[y, x, 2] = np.sum(relevant_time & relevant_length & client_relevant)  # Blue Channel
            hist[y, x, 0] = np.sum(relevant_time & relevant_length & server_relevant)  # Red Channel

    return hist


def normalize_histogram(hist):
    """
    Normalize each color channel independently to 0-255 and apply optional gamma boost.
    """
    for c in [0, 2]:  # Only Red and Blue channels used
        if hist[:, :, c].max() != hist[:, :, c].min():
            hist[:, :, c] = (hist[:, :, c] - hist[:, :, c].min()) * 255 / (hist[:, :, c].max() - hist[:, :, c].min())

    if USE_GAMMA_BOOST:
        hist = np.power(hist / 255, 0.5) * 255

    return hist


def create_png_from_csv(cleaned_csv_path):
    try:
        df = pd.read_csv(cleaned_csv_path)
    except Exception as e:
        print(f"[ERROR] Failed to load {cleaned_csv_path}: {e}")
        return

    if df.empty:
        print(f"[WARN] Empty DataFrame for {cleaned_csv_path}, skipping.")
        return

    # Build histogram
    hist = create_histogram(df, time_bins=IMAGE_SIZE, length_bins=IMAGE_SIZE)

    # Normalize
    hist = normalize_histogram(hist)

    # Build save path
    relative_path = os.path.relpath(cleaned_csv_path, 'captures/csv')
    parts = relative_path.split(os.sep)
    category, application, filename = parts[0], parts[1], parts[2]
    filename = filename.replace('cleaned_', '').replace('.csv', '.png')

    save_dir = os.path.join(PNG_OUTPUT_DIR, category, application)
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, filename)

    # Save image
    img = Image.fromarray(np.uint8(hist), mode="RGB").transpose(Image.FLIP_TOP_BOTTOM)
    img.save(save_path)
    print(f"[INFO] Saved PNG to {save_path}.")


def create_pngs_for_all_cleaned_csvs(base_cleaned_csv_dir='captures/csv'):
    for root, dirs, files in os.walk(base_cleaned_csv_dir):
        for file in files:
            if file.startswith('cleaned_') and file.endswith('.csv'):
                cleaned_csv_path = os.path.join(root, file)
                create_png_from_csv(cleaned_csv_path)


if __name__ == "__main__":
    create_pngs_for_all_cleaned_csvs()