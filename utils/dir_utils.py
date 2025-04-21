import os
import yaml
from glob import glob

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

def load_links_from_category(category, links_root=config['links_directory']):
    category_path = os.path.join(links_root, category)
    links_dict = {}

    if not os.path.isdir(category_path):
        raise FileNotFoundError(f"[ERROR] Category directory not found: {category_path}")

    for filename in os.listdir(category_path):
        file_path = os.path.join(category_path, filename)
        if os.path.isfile(file_path):
            with open(file_path, "r") as f:
                links = [line.strip() for line in f if line.strip()]
                links_dict[filename] = links

    return links_dict

def find_all_pcap_files(pcap_root=config['pcap_output_directory']):
    return glob(os.path.join(pcap_root, "*", "*", "*.pcap"))