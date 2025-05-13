import yaml
import os
import tempfile
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import subprocess


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

    # Create temporary file paths for required Chrome flags
    json_file = tempfile.NamedTemporaryFile(delete=False).name
    key_file = tempfile.NamedTemporaryFile(delete=False).name

    # Launch Chrome, open google.com, then close it
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--enable-quic")
    options.add_argument("--disable-application-cache")
    options.add_argument("--incognito")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--log-net-log={json_file}")
    options.add_argument(f"--ssl-key-log-file={key_file}")
    options.add_argument("--autoplay-policy=no-user-gesture-required")
    options.add_extension("utils/adblock.crx")

    driver = webdriver.Chrome(options=options)
    driver.get("https://www.google.com")
    driver.quit()
    print("[INFO] Chrome launched and closed with Adblock.")

    # Run the Adblock incognito patcher
    subprocess.run(["python3", "utils/enable_incognito_adblock.py"])

if __name__ == "__main__":
    create_folders('config.yaml')
