import yaml
import os

def load_config(path="config.yaml"):
    with open(path, "r") as file:
        return yaml.safe_load(file)

def create_folders(config_path="config.yaml"):
    config = load_config(config_path)

    # Directories to create (from config)
    dirs_to_create = [
        config["temp_directory"],
        config["pcap_output_directory"],
        config["csv_output_directory"],
        config["png_output_directory"],
        config["label_output_directory"],
    ]

    # Also add root folders manually
    dirs_to_create += [
        os.path.dirname(config["pcap_output_directory"]),
        os.path.dirname(config["png_output_directory"]),
    ]

    for directory in set(dirs_to_create):  # remove duplicates
        os.makedirs(directory, exist_ok=True)
        print(f"[INFO] Created or confirmed existence of: {directory}")

if __name__ == "__main__":
    create_folders('config.yaml')