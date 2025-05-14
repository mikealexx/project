import pandas as pd
import json
import os
from urllib.parse import urlparse
from event_types_list import event_type
import yaml

with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

MAX_PACKET_LENGTH = 1500

QUIC_SESSION_TYPE_ID = 308

def get_hosts_from_domain(json_file):
    """
    return the hosts names from the json_file name.
    """
    domain = json_file.split(os.path.sep)[-1]
    
    # replace _ with / in the domain name
    domain = domain.replace("_", "/")
    domain = urlparse(domain).netloc
    hosts = domain.split(".")
    hosts = hosts[1:-1] if len(hosts) > 2 else hosts[:-1]
    return hosts


def get_quic_connection_ids(json_file):
    """
    go over all the lines in the json file and return a list of the source.id
    that correspond to events of type QUIC_SESSION
    """
    quic_connection_ids = []
    events_ids = []  # the event_ids of quic sessions that will later be used to find the quic connection ids

    hosts = get_hosts_from_domain(json_file)
    with open(json_file, 'r') as f:
        data = json.load(f)
        for event in data['events']:
            if 'type' in event:
                if event_type[event['type']] == 'QUIC_SESSION' or event_type[event['type']] == 'QUIC_STREAM_FACTORY_JOB_STALE_HOST_NOT_USED_ON_CONNECTION':
                    if 'params' in event:
                        # if 'host' in event['params']:
                        #     for host in hosts:
                        #         if host in event['params']['host']:
                                    quic_connection_ids.append(event['params']['connection_id'])
                                    print(event['params']['connection_id'])
                                    break

                elif event_type[event['type']] == 'QUIC_SESSION_CERTIFICATE_VERIFIED':
                    if 'params' in event:
                        if 'subjects' in event['params']:
                            for host in hosts:
                                for domain in event['params']['subjects']:
                                    if host in domain:
                                        events_ids.append(event['source']['id'])
                                        break
        if len(quic_connection_ids) == 0:
            if len(events_ids):
                for event in data['events']:
                    if event_type[event['type']] == 'QUIC_SESSION':
                        if 'source' in event:
                            if event['source']['id'] in events_ids:
                                if 'params' in event:
                                    if 'connection_id' in event['params']:
                                        quic_connection_ids.append(event['params']['connection_id'])
                                        print(event['params']['connection_id'])

            
    return list(set(quic_connection_ids))


def clean_pcap_csv_tcp(csv_path, save=False, save_path=None):
    """
    Clean TCP packets from tshark CSV and return a labeled DataFrame.
    Identifies the main client-server pair and filters the communication between them.
    """
    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"[ERROR] Failed to load CSV {csv_path}: {e}")
        return None

    if '_ws.col.info' in df.columns:
        df.rename(columns={'_ws.col.info': '_ws.col.Info'}, inplace=True)

    if df.empty:
        return None

    ip_column = "ipv6" if df["ip.src"].isnull().all() else "ip"

    # Focus only on TCP packets
    df = df[df["ip.proto"] == 6]
    if df.empty:
        return None

    # Identify the top source-destination pair by total bytes
    df['pair'] = df[f'{ip_column}.src'] + "->" + df[f'{ip_column}.dst']
    top_pair = df.groupby('pair')['frame.len'].sum().idxmax()
    client_ip, server_ip = top_pair.split('->')

    # Keep only packets between client and server
    valid_client = (df[f'{ip_column}.src'] == client_ip) & (df[f'{ip_column}.dst'] == server_ip)
    valid_server = (df[f'{ip_column}.dst'] == client_ip) & (df[f'{ip_column}.src'] == server_ip)
    valid_data = df[valid_client | valid_server].copy()

    if valid_data.empty:
        return None

    # Label direction: 0 = client → server, 1 = server → client
    def label_direction(row):
        return 0 if row[f'{ip_column}.src'] == client_ip else 1

    valid_data['Direction'] = valid_data.apply(label_direction, axis=1)

    clean_data = valid_data.rename(columns={
        'frame.time_relative': 'Time',
        'frame.len': 'Length',
        f'{ip_column}.src': 'Source',
        f'{ip_column}.dst': 'Destination'
    })[['Time', 'Length', 'Source', 'Destination', 'Direction']]

    if save and save_path:
        clean_data.to_csv(save_path, index=False)

    return clean_data

def clean_all_pcap_csvs(base_csv_dir, base_json_dir):
    """
    Recursively clean all CSVs under base_csv_dir and save them with 'cleaned_' prefix.
    """
    for root, dirs, files in os.walk(base_csv_dir):
        for file in files:
            if file.endswith(".csv") and not file.startswith("cleaned_"):
                csv_path = os.path.join(root, file)

                if "big_file" not in csv_path or "game" not in csv_path:
                    continue
                
                # Build the corresponding JSON path
                relative_path = os.path.relpath(csv_path, base_csv_dir)
                json_path = os.path.join(base_json_dir, relative_path)
                json_path = os.path.splitext(json_path)[0] + ".json"  # replace .csv with .json
                
                if not os.path.exists(json_path):
                    print(f"[WARN] JSON not found for {csv_path}, skipping.")
                    continue

                print(f"[INFO] Processing {csv_path}...")

                # Clean the CSV
                cleaned_df = clean_pcap_csv_tcp(csv_path, json_path)

                if cleaned_df is not None:
                    cleaned_filename = "cleaned_" + file
                    cleaned_path = os.path.join(root, cleaned_filename)
                    cleaned_df.to_csv(cleaned_path, index=False)
                    print(f"[INFO] Saved cleaned CSV to {cleaned_path}.")
                else:
                    print(f"[WARN] No valid data in {csv_path}, skipped saving.") 

if __name__ == "__main__":
    base_csv_dir = config['csv_output_directory']
    base_json_dir = config['pcap_output_directory']
    clean_all_pcap_csvs(base_csv_dir, base_json_dir)