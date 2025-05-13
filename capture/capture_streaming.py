from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
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

def capture_stream(website, url):
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    base_output_dir = os.path.join(config["pcap_output_directory"], "streaming", website)
    os.makedirs(base_output_dir, exist_ok=True)

    base_filename = f"{website}-[{timestamp}]"
    base_path = os.path.join(base_output_dir, base_filename)

    json_file = f"{base_path}.json"
    pcap_file = f"{base_path}.pcap"
    key_file  = f"{base_path}.key"

    # Create the key log file
    with open(key_file, 'a'):
        os.utime(key_file, None)

    # Chrome options
    options = Options()
    # options.add_argument("--headless=new")  # Uncomment if needed
    options.add_argument("--disable-gpu")
    options.add_argument("--enable-quic")
    options.add_argument("--disable-application-cache")
    options.add_argument("--incognito")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--log-net-log={json_file}")
    options.add_argument(f"--ssl-key-log-file={key_file}")
    options.add_argument("--autoplay-policy=no-user-gesture-required")
    options.add_extension("adblock.crx")

    logger.info("Starting capture...")
    tshark_process = tshark.run_tshark(config["network_interface"], pcap_file)
    time.sleep(config["warmup_time"])

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    logger.info(f"Opened {url}, checking if page finishes loading in 5s...")

    start_time = time.time()
    timeout = 5

    while time.time() - start_time < timeout:
        try:
            load_event_end = driver.execute_script("return window.performance.timing.loadEventEnd")
            navigation_start = driver.execute_script("return window.performance.timing.navigationStart")
            if load_event_end and load_event_end > navigation_start:
                logger.info("Page finished loading based on performance timing.")
                break
        except Exception:
            pass
        time.sleep(0.25)
    else:
        logger.warning("Page did not finish loading in time. Skipping this URL.")
        tshark.kill_tshark(tshark_process)
        driver.quit()
        return


    time.sleep(config["capture_duration"])

    logger.info("Capture finished.")
    tshark.kill_tshark(tshark_process)
    driver.quit()
    logger.info(f"Capture complete for {url}")

def capture_streams():
    stream_urls = dir_utils.load_links_from_category("streaming", config["links_directory"])
    for website, urls in stream_urls.items():
        for url in urls:
            try:
                capture_stream(website, url)
            except Exception as e:
                logger.error(f"Error capturing {url}: {e}")


if __name__ == "__main__":
    capture_streams()