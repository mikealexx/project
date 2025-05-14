import time
import sys
import random
import glob
import os
import argparse
import yaml
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from utils import tshark

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

def join_meet_with_capture(meet_url, user_profile_dir, wav_file):
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    base_output_dir = os.path.join(config["pcap_output_directory"], "voip", "google_meet")
    os.makedirs(base_output_dir, exist_ok=True)

    base_filename = f"google_meet-[{timestamp}]"
    base_path = os.path.join(base_output_dir, base_filename)

    json_file = f"{base_path}.json"
    key_file = f"{base_path}.key"
    pcap_file = f"{base_path}.pcap"

    with open(key_file, 'a'):
        os.utime(key_file, None)

    options = Options()
    options.add_argument("--use-fake-ui-for-media-stream")
    options.add_argument("--headless")
    options.add_argument("--use-fake-device-for-media-stream")
    options.add_argument(f"--use-file-for-fake-audio-capture={wav_file}")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1280,720")
    options.add_argument(f"--user-data-dir={user_profile_dir}")
    options.add_argument(f"--log-net-log={json_file}")
    options.add_argument(f"--ssl-key-log-file={key_file}")

    logger.info("[INFO] Starting continuous tshark capture...")
    tshark_process = tshark.run_tshark(config["network_interface"], pcap_file)
    logger.info(f"[INFO] Waiting {config['warmup_time']}s for warmup...")
    time.sleep(config["warmup_time"])

    logger.info(f"[INFO] Using audio file: {wav_file}")
    logger.info("[INFO] Launching Chrome...")
    driver = webdriver.Chrome(options=options)

    logger.info(f"[INFO] Navigating to: {meet_url}")
    driver.get(meet_url)

    try:
        logger.info("[INFO] Waiting for Join button (any language)...")
        join_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//button[.//span[contains(text(),'Join now')] or .//span[contains(text(),'הצטרפות')]]"
            ))
        )
        join_button.click()
        logger.info("[INFO] Joined the call.")

    except Exception as e:
        logger.warning(f"[WARN] Could not auto-click join button: {e}")

    try:
        print("\nPress ENTER to stop meeting and capture...")
        input()

        tshark.kill_tshark(tshark_process)
        logger.info(f"[INFO] Capture finished: {pcap_file}")

    except KeyboardInterrupt:
        logger.info("[INFO] Capture interrupted by user.")
        tshark.kill_tshark(tshark_process)

    try:
        logger.info("[INFO] Leaving the meeting...")
        hangup_button = driver.find_element(By.XPATH, "//button[@aria-label='עזיבת השיחה' or @aria-label='Leave call']")
        hangup_button.click()
    except Exception as e:
        logger.warning(f"[WARN] Could not hang up automatically: {e}")

    time.sleep(2)
    driver.quit()
    logger.info("[INFO] Browser closed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--meet_url", type=str, default="https://meet.google.com/zbv-cuwd-cpc")
    parser.add_argument("--user_profile", type=str, default="google_meet_voip/meet_profiles/user2")
    args = parser.parse_args()

    sound_files = glob.glob("google_meet_voip/sounds/*.wav")
    if not sound_files:
        print("[ERROR] No .wav files found in google_meet_voip/sounds/")
        sys.exit(1)

    wav_file = random.choice(sound_files)
    join_meet_with_capture(args.meet_url, args.user_profile, wav_file)
