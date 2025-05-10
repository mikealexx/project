from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime
import time
import os
import subprocess
import signal
import yaml
import logging
import sys

from utils import tshark
from utils import dir_utils

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

def capture_big_file_tcp(website, url):
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    base_output_dir = os.path.join(config["pcap_output_directory"], "big_file", website)
    os.makedirs(base_output_dir, exist_ok=True)

    base_filename = f"{website}-[{timestamp}]"
    base_path = os.path.join(base_output_dir, base_filename)

    json_file = f"{base_path}.json"
    pcap_file = f"{base_path}.pcap"
    key_file  = f"{base_path}.key"

    # Create the key log file
    with open(key_file, 'a'):
        os.utime(key_file, None)

    # Chrome options for TCP only
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-quic")  # <== explicitly disable QUIC
    options.add_argument("--disable-application-cache")
    options.add_argument("--incognito")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--log-net-log={json_file}")
    options.add_argument(f"--ssl-key-log-file={key_file}")
    options.add_argument("--autoplay-policy=no-user-gesture-required")

    # Set download behavior
    prefs = {
        "download.default_directory": config["temp_directory"],
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)

    logger.info("Starting big file TCP capture...")
    tshark_process = tshark.run_tshark(config["network_interface"], pcap_file)
    time.sleep(config["warmup_time"])

    # Launch browser
    driver = webdriver.Chrome(options=options)

    # Force download to the specified folder using CDP
    download_dir = config.get("download_temp_dir", "/tmp/downloads")
    os.makedirs(download_dir, exist_ok=True)
    driver.execute_cdp_cmd(
        "Page.setDownloadBehavior",
        {
            "behavior": "allow",
            "downloadPath": download_dir,
        }
    )

    driver.get(url)

    logger.info(f"Started downloading {url}")

    time.sleep(config["capture_duration"])

    logger.info("Capture finished. Cleaning up...")
    tshark.kill_tshark(tshark_process)
    driver.quit()

    # Delete any downloaded files
    for filename in os.listdir(download_dir):
        if filename.endswith('.crdownload') or filename.endswith('.part') or filename.endswith('.tmp'):
            file_path = os.path.join(download_dir, filename)
            logger.info(f"Deleting partial file: {file_path}")
            os.remove(file_path)

    logger.info(f"TCP Capture complete for {url}")

def capture_big_files():
    big_file_urls = dir_utils.load_links_from_category("big_file", config["links_directory"])
    for website, urls in big_file_urls.items():
        for url in urls:
            try:
                capture_big_file_tcp(website, url)
            except Exception as e:
                logger.error(f"Error capturing {url}: {e}")

if __name__ == "__main__":
    capture_big_files()
