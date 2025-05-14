import os
import sys
import subprocess
import yaml
from utils import dir_utils

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

def convert_pcaps(parallel_processes=5):
    pcap_files = dir_utils.find_all_pcap_files(config["pcap_output_directory"])
    csv_base = config["csv_output_directory"]

    while len(pcap_files) > 0:
        batch = pcap_files[:parallel_processes]
        processes = []

        for pcap in batch:
            category, website = pcap.split(os.path.sep)[-3:-1]

            if category != "big_file" or category != "game":
                continue

            csv_dir = os.path.join(csv_base, category, website)
            os.makedirs(csv_dir, exist_ok=True)

            key_file = pcap.replace(".pcap", ".key")  # Still useful if TLS decryption is needed
            csv_file = os.path.join(csv_dir, os.path.basename(pcap).replace(".pcap", ".csv"))

            tshark_cmd = (
                f'tshark -r "{pcap}" -Y tcp -2 -T fields '
                '-e frame.number -e frame.time_relative -e frame.len '
                '-e eth.src -e eth.dst -e ip.src -e ip.dst '
                '-e ipv6.src -e ipv6.dst -e ip.proto -e _ws.col.Info '
                '-E header=y -E separator=, -E quote=d -E occurrence=f '
                f'-o tls.keylog_file:"{key_file}" > "{csv_file}"'
            )

            print(f"[INFO] Converting {pcap} -> {csv_file}")
            processes.append(subprocess.Popen(tshark_cmd, shell=True, executable='/bin/bash'))

        for proc in processes:
            proc.wait()

        pcap_files = pcap_files[parallel_processes:]

if __name__ == "__main__":
    convert_pcaps(1)
