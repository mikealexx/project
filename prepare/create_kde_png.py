import os
import pandas as pd
import numpy as np
from PIL import Image
import yaml
from scipy.stats import gaussian_kde
from sklearn.preprocessing import MinMaxScaler

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Constants
IMAGE_SIZE = config['image_size']
PNG_OUTPUT_DIR = config['png_output_directory']
MAX_PACKET_LENGTH = 1500 
SESSION_DURATION = config["capture_duration"] + config["warmup_time"]
USE_GAMMA_BOOST = config.get('use_gamma_boost', True)


def create_kde_density_image(df, image_size=IMAGE_SIZE, duration=SESSION_DURATION):
    """
    Generate an image using KDE for client-server and server-client packets.
    """
    image = np.zeros((image_size, image_size, 3), dtype=np.float32)

    def normalize_packets(subset_df):
        t = subset_df['Time'].values.reshape(-1, 1)
        l = subset_df['Length'].values.reshape(-1, 1)
        t_scaled = MinMaxScaler(feature_range=(0, image_size - 1)).fit_transform(t)
        l_scaled = MinMaxScaler(feature_range=(0, image_size - 1)).fit_transform(l)
        return np.vstack([t_scaled.ravel(), l_scaled.ravel()])

    for direction, channel in [(0, 2), (1, 0)]:  # Blue for client->server, Red for server->client
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
    """
    Normalize each channel to 0-255 and apply gamma correction if enabled.
    """
    for c in [0, 2]:  # Red and Blue channels
        channel = hist[:, :, c]
        min_val, max_val = channel.min(), channel.max()
        if max_val > min_val:
            hist[:, :, c] = (channel - min_val) * 255 / (max_val - min_val)

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

    # KDE-based image
    img_data = create_kde_density_image(df)

    # Normalize and convert to image
    img_data = normalize_histogram(img_data)
    img = Image.fromarray(np.uint8(img_data), mode="RGB").transpose(Image.FLIP_TOP_BOTTOM)

    # Build save path
    relative_path = os.path.relpath(cleaned_csv_path, 'captures/csv')
    category, application, filename = relative_path.split(os.sep)
    filename = filename.replace('cleaned_', '').replace('.csv', '.png')

    save_dir = os.path.join(PNG_OUTPUT_DIR, category, application)
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, filename)

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
