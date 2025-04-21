from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime
import time
import os
import subprocess
import signal
import yaml
import sys
import logging

from utils import tshark
from utils import dir_utils

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

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

def capture_video(website, url):
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    base_output_dir = os.path.join(config["pcap_output_directory"], "video", website)
    os.makedirs(base_output_dir, exist_ok=True)

    base_filename = f"{website}-[{timestamp}]"
    base_path = os.path.join(base_output_dir, base_filename)

    json_file = f"{base_path}.json"
    pcap_file = f"{base_path}.pcap"
    key_file  = f"{base_path}.key"

    # Set Chrome options
    options = Options()
    # Comment out headless during debugging
    # options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--enable-quic")
    options.add_argument("--disable-application-cache")
    options.add_argument("--incognito")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--log-net-log={json_file}")
    options.add_argument(f"--ssl-key-log-file={key_file}")
    options.add_argument("--autoplay-policy=no-user-gesture-required")

    subprocess.run(f"touch {key_file} && chmod 777 {key_file}", shell=True)
    tshark_process = tshark.run_tshark(config["network_interface"], pcap_file)
    time.sleep(config["warmup_time"])

    driver = webdriver.Chrome(options=options)
    driver.get(url)

    try:
        # Dismiss YouTube cookie consent popup if it appears
        try:
            consent_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[aria-label="Accept all"]'))
            )
            consent_btn.click()
            logger.info("Accepted YouTube cookies.")
        except Exception:
            logger.info("No cookie popup appeared.")

        # Wait for and click YouTube play button
        logger.info("Waiting for play button...")
        WebDriverWait(driver, config.get("wait_timeout", 10)).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".ytp-large-play-button"))
        )
        play_button = driver.find_element(By.CSS_SELECTOR, ".ytp-large-play-button")
        play_button.click()
        logger.info("Play button clicked. Video should be playing.")

    except TimeoutException:
        logger.error("Play button not found or not clickable.")
        driver.quit()
        tshark.kill_tshark(tshark_process)
        return
    except Exception as e:
        logger.error(f"Failed to play video: {e}")
        driver.quit()
        tshark.kill_tshark(tshark_process)
        return

    # Let the video play while capturing
    time.sleep(config["capture_duration"])
    driver.quit()
    tshark.kill_tshark(tshark_process)
    logger.info(f"Capture complete for {url}")



def capture_videos():
    video_urls = dir_utils.load_links_from_category("video", config["links_directory"])
    for website, urls in video_urls.items():
        for url in urls:
            try:
                capture_video(website, url)
            except Exception as e:
                logger.error(f"Error capturing {url}: {e}")


if __name__ == "__main__":
    capture_videos()