import codecs
from datetime import datetime
import json
import logging
import subprocess
import os
import sys
import signal
import time
import yaml
import logging

from utils import tshark
from utils import dir_utils

logging.basicConfig(stream=sys.stdout, level=0)
logger = logging.getLogger(__name__)

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

def issure_request(website, url):
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    base_output_dir = os.path.join(config["pcap_output_directory"], "browsing", website)
    os.makedirs(base_output_dir, exist_ok=True)

    base_filename = f"{website}-[{timestamp}]"
    base_path = os.path.join(base_output_dir, base_filename)

    json_file = f"{base_path}.json"
    html_file = f"{base_path}.html"
    log_file  = f"{base_path}.log"
    pcap_file = f"{base_path}.pcap"
    key_file  = f"{base_path}.key"

    request = f"SSLKEYLOGFILE={key_file} google-chrome --no-sandbox " \
              "--headless " \
              "--autoplay-policy=no-user-gesture-required " \
              "--dump-dom " \
              "--disable-gpu " \
              "--enable-logging " \
              "--enable-quic " \
              "--disable-application-cache " \
              "--incognito " \
              "--new-window " \
              "--v=3 " \
              f"--log-net-log={json_file} " \
              f"{url} " \
              f"> /dev/null " \
              f"2> /dev/null"
    
    subprocess.run(f'touch {key_file} && chmod 777 {key_file}', shell=True, executable='/bin/bash', )

    tshark_process = tshark.run_tshark(config["network_interface"], pcap_file)

    time.sleep(config["warmup_time"])

    chrome_process = subprocess.Popen(request, shell=True, executable='/bin/bash')

    time.sleep(config["capture_duration"])

    tshark.kill_tshark(tshark_process)

    if chrome_process.poll() is None:
        os.kill(chrome_process.pid, signal.SIGTERM)
        chrome_process.wait()


def capture_browsing():
    browsing_urls = dir_utils.load_links_from_category("browsing", config["links_directory"])
    for website, urls in browsing_urls.items():
        for url in urls:
            try:
                issure_request(website, url)
            except Exception as e:
                logger.error(f"Error capturing {url}: {e}")
                continue

if __name__ == "__main__":
    capture_browsing()