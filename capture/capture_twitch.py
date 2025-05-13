from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime
import time
import os
import yaml
import logging
import sys
import requests
from bs4 import BeautifulSoup

from utils import tshark

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

def get_live_twitch_streams(limit=10, base_url="https://www.twitch.tv/directory/game/Music?sort=VIEWER_COUNT_DESC"):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    response = requests.get(base_url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"Failed to fetch Twitch directory page: {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")
    streams = []
    for a in soup.find_all("a", href=True):
        href = a['href']
        if href.startswith("/") and len(href.strip("/")) > 0 and not any(x in href for x in ["directory", "videos"]):
            stream_url = f"https://www.twitch.tv{href}"
            if stream_url not in streams:
                streams.append(stream_url)
        if len(streams) >= limit:
            break
    return streams

def capture_stream(website, url):
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
    logger.info(f"Opened {url}, sleeping {config['capture_duration']}s...")
    time.sleep(config["capture_duration"])

    logger.info("Capture finished.")
    tshark.kill_tshark(tshark_process)
    page_source = driver.page_source
    driver.quit()
    logger.info(f"Capture complete for {url}")

    return page_source

def capture_streams():
    visited_links = set()
    current_links = get_live_twitch_streams()
    logger.info(f"Initial live streams found: {len(current_links)}")

    if not current_links:
        current_links = ["https://www.twitch.tv/chillloop"]  # fallback default

    while current_links:
        logger.info(f"\n✨ Starting new capture round with {len(current_links)} streams")
        next_links = []
        for link in current_links:
            if link in visited_links:
                logger.info(f"Skipping already visited: {link}")
                continue
            try:
                logger.info(f"\U0001F4FA Capturing stream: {link}")
                page_source = capture_stream("twitch", link)
                visited_links.add(link)

                # Extract new stream links from current page
                soup = BeautifulSoup(page_source, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a['href']
                    if href.startswith("/") and len(href.strip("/")) > 0 and not any(x in href for x in ["directory", "videos"]):
                        stream_url = f"https://www.twitch.tv{href}"
                        if stream_url not in visited_links and stream_url not in next_links:
                            next_links.append(stream_url)
            except Exception as e:
                logger.error(f"Error capturing {link}: {e}")
        if not next_links:
            logger.info("No new links discovered. Resetting to chillloop as fallback.")
            next_links = ["https://www.twitch.tv/chillloop"]
        current_links = next_links

if __name__ == "__main__":
    capture_streams()
