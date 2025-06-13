from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from datetime import datetime
import time
import os
import yaml
import logging
import sys

from utils import tshark
from utils import dir_utils

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

def capture_io_game_traffic(website, url):
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    base_output_dir = os.path.join(config["pcap_output_directory"], "game", website)
    os.makedirs(base_output_dir, exist_ok=True)

    base_filename = f"{website}-[{timestamp}]"
    base_path = os.path.join(base_output_dir, base_filename)

    pcap_file = f"{base_path}.pcap"
    key_file = f"{base_path}.key"
    json_file = f"{base_path}.json"

    # Create the key log file
    with open(key_file, 'a'):
        os.utime(key_file, None)

    # Chrome options for capturing IO game traffic
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-quic")  # Disable QUIC for TCP traffic
    options.add_argument("--disable-application-cache")
    # options.add_argument("--incognito")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--ssl-key-log-file={key_file}")
    options.add_argument(f"--log-net-log={json_file}")
    options.add_argument("--autoplay-policy=no-user-gesture-required")
    options.add_extension("utils/ublock.crx")

    logger.info("Starting IO game traffic capture...")
    tshark_process = tshark.run_tshark(config["network_interface"], pcap_file)
    time.sleep(config["warmup_time"])

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(3)  # Set timeout to 3 seconds

    logger.info(f"Opening game: {url}")

    try:
        driver.get(url)
    except TimeoutException:
        logger.warning(f"Page load timed out for {url}. Skipping capture.")
        try:
            tshark_process.kill()
            os.system("pkill -9 -f tshark")
            logger.info("tshark process killed.")
        except Exception as e:
            logger.warning(f"Failed to kill tshark: {e}")

        driver.quit()

        for f in [pcap_file, json_file, key_file]:
            try:
                os.remove(f)
            except FileNotFoundError:
                pass
        return

    # Keep the browser open for a specified duration to capture traffic
    capture_duration = config.get("capture_duration", 60)
    time.sleep(capture_duration)

    logger.info("Capture finished. Cleaning up...")
    try:
        tshark_process.kill()
        os.system("pkill -9 -f tshark")
        logger.info("tshark process killed.")
    except Exception as e:
        logger.warning(f"Failed to kill tshark: {e}")

    driver.quit()
    logger.info(f"Traffic capture complete for {url}")

def capture_io_games():
    io_game_urls = dir_utils.load_links_from_category("game", config["links_directory"])
    for website, urls in io_game_urls.items():
        for url in urls:
            try:
                capture_io_game_traffic(website, url)
            except Exception as e:
                logger.error(f"Error capturing traffic for {url}: {e}")

if __name__ == "__main__":
    capture_io_games()
