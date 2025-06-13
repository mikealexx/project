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
import threading

from utils import tshark
from utils import dir_utils

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Global flag to indicate a skip
skip_requested = False

def wait_for_enter():
    global skip_requested
    input("Press Enter to skip this capture...\n")
    skip_requested = True

def capture_video(website, url):
    global skip_requested
    skip_requested = False  # Reset for each run

    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    base_output_dir = os.path.join(config["pcap_output_directory"], "video", website)
    os.makedirs(base_output_dir, exist_ok=True)

    base_filename = f"{website}-[{timestamp}]"
    base_path = os.path.join(base_output_dir, base_filename)

    json_file = f"{base_path}.json"
    pcap_file = f"{base_path}.pcap"
    key_file  = f"{base_path}.key"

    with open(key_file, 'a'):
        os.utime(key_file, None)

    # Chrome options
    options = Options()
    options.add_argument("--disable-gpu")
    options.add_argument("--enable-quic")
    options.add_argument("--headless")
    options.add_argument("--mute-audio")
    options.add_argument("--disable-application-cache")
    options.add_argument("--incognito")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--log-net-log={json_file}")
    options.add_argument(f"--ssl-key-log-file={key_file}")
    options.add_argument("--autoplay-policy=no-user-gesture-required")
    options.add_extension("utils/ublock.crx")

    logger.info("Starting capture...")
    tshark_process = tshark.run_tshark(config["network_interface"], pcap_file)
    time.sleep(config["warmup_time"])

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(3)  # this is now meaningful

    try:
        driver.get(url)
    except TimeoutException:
        logger.warning(f"Page timed out (>{2}s): {url}. Skipping capture.")
        try:
            tshark_process.kill()
            os.system("pkill -9 -f tshark")
            logger.info("tshark process killed.")
        except Exception as e:
            logger.warning(f"Could not kill tshark process: {e}")
        driver.quit()
        for f in [pcap_file, json_file, key_file]:
            try:
                os.remove(f)
            except FileNotFoundError:
                pass
        return

    logger.info(f"Opened {url}, checking if page finishes loading in 5s...")

    # Start the Enter listener thread
    enter_thread = threading.Thread(target=wait_for_enter, daemon=True)
    enter_thread.start()

    start_time = time.time()
    timeout = 5
    while time.time() - start_time < timeout:
        if skip_requested:
            logger.info("Skipping due to user request during page load.")
            tshark.kill_tshark(tshark_process)
            os.system("pkill -9 -f tshark")
            driver.quit()
            return
        try:
            load_event_end = driver.execute_script("return window.performance.timing.loadEventEnd")
            navigation_start = driver.execute_script("return window.performance.timing.navigationStart")
            if load_event_end and load_event_end > navigation_start:
                logger.info("Page finished loading based on performance timing.")
                break
        except Exception:
            pass
        time.sleep(0.25)

    if not skip_requested:
        logger.info("Capturing traffic...")
        capture_end_time = time.time() + config["capture_duration"]
        while time.time() < capture_end_time:
            if skip_requested:
                logger.info("Skipping due to user request during capture.")
                break
            time.sleep(0.5)

    logger.info("Capture finished.")
    tshark.kill_tshark(tshark_process)
    os.system("pkill -9 -f tshark")
    driver.quit()
    logger.info(f"Capture complete for {url}")

def capture_videos(skip_websites=[]):
    video_urls = dir_utils.load_links_from_category("video", config["links_directory"])
    for website, urls in video_urls.items():
        if website in skip_websites:
            continue
        for url in urls:
            try:
                capture_video(website, url)
            except Exception as e:
                logger.error(f"Error capturing {url}: {e}")

if __name__ == "__main__":
    capture_videos(["youtube", "dailymotion", "vimeo"])
