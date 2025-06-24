import os
import sys
import time
import yaml
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

from utils import tshark

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

def get_channel_links(limit=10, base_url="https://www.twitch.tv/directory/game/Music/videos?filter=archives&sort=VIEWS_DESC"):
    """Return a list of channel URLs from the Twitch directory page using Selenium."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    driver.get(base_url)

    try:
        WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.TAG_NAME, "a")))
    except Exception as e:
        logger.warning("Timeout or error waiting for anchor tags: %s", e)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    channels = []
    for a in soup.find_all("a", href=True):
        href = a['href']
        if (href.startswith("/") and
            2 <= len(href.strip("/")) <= 25 and
            not any(x in href for x in ["directory", "videos", "collections", "clips"])
        ):
            channel_url = f"https://www.twitch.tv{href}"
            if channel_url not in channels:
                channels.append(channel_url)
        if len(channels) >= limit:
            break
    return channels

def get_vod_links(channel_url, limit=5):
    """Return a list of VOD URLs from a channel's videos page using Selenium."""
    vods = []
    videos_url = channel_url.rstrip("/") + "/videos?filter=archives&sort=views"

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_extension("utils/ublock.crx")
    driver = webdriver.Chrome(options=options)
    driver.get(videos_url)

    try:
        WebDriverWait(driver, 15).until(EC.presence_of_all_elements_located((By.TAG_NAME, "a")))
    except Exception as e:
        logger.warning("Timeout or error waiting for anchor tags on channel videos: %s", e)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    for a in soup.find_all("a", href=True):
        href = a['href']
        if href.startswith("/videos/") and href.count("/") == 2:
            vod_url = f"https://www.twitch.tv{href}"
            if vod_url not in vods:
                vods.append(vod_url)
        if len(vods) >= limit:
            break
    return vods

def capture_stream(website, url):
    """Capture PCAP and Chrome NetLog for the given URL."""
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    base_output_dir = os.path.join(config["pcap_output_directory"], "streaming", website)
    os.makedirs(base_output_dir, exist_ok=True)

    base_filename = f"{website}-[{timestamp}]"
    base_path = os.path.join(base_output_dir, base_filename)

    json_file = f"{base_path}.json"
    pcap_file = f"{base_path}.pcap"
    key_file  = f"{base_path}.key"

    with open(key_file, 'a'):
        os.utime(key_file, None)

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

    logger.info("Starting capture...")
    tshark_process = tshark.run_tshark(config["network_interface"], pcap_file)
    time.sleep(config["warmup_time"])

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    logger.info(f"Opened {url}, sleeping {config['capture_duration']}s to capture traffic...")
    time.sleep(config["capture_duration"])

    logger.info("Capture finished.")
    tshark.kill_tshark(tshark_process)
    driver.quit()
    logger.info(f"Capture complete for {url}")

def main():
    visited_vods = set()
    channels = get_channel_links(limit=10)
    logger.info(f"Found {len(channels)} channels.")

    vod_links = []
    for channel in channels:
        vods = get_vod_links(channel, limit=3)
        for vod in vods:
            if vod not in visited_vods:
                vod_links.append(vod)
                visited_vods.add(vod)
            if len(vod_links) >= 10:
                break
        if len(vod_links) >= 10:
            break

    logger.info(f"Prepared {len(vod_links)} VOD links to capture.")

    for vod in vod_links:
        try:
            logger.info(f"Capturing VOD: {vod}")
            capture_stream("twitch_vod", vod)
        except Exception as e:
            logger.error(f"Error capturing {vod}: {e}")

if __name__ == "__main__":
    main()