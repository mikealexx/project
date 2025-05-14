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


def clean_pcap_csv(csv_path, json_path, save=False, save_path=None):
    import warnings
    warnings.filterwarnings("ignore", category=UserWarning)

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"[ERROR] Failed to load CSV {csv_path}: {e}")
        return None

    if '_ws.col.info' in df.columns:
        df.rename(columns={'_ws.col.info': '_ws.col.Info'}, inplace=True)

    if df.empty:
        print("[WARN] CSV is empty.")
        return None

    quic_ids = get_quic_connection_ids(json_path)
    if not quic_ids:
        print("[WARN] No QUIC connection IDs found.")
        return None

    ip_column = "ipv6" if df["ip.src"].isnull().all() else "ip"

    print(f"[INFO] QUIC connection IDs: {quic_ids}")

    # === Infer client IP from all DCIDs ===
    client_ip_counts = df[df["_ws.col.Info"].str.contains("|".join([f"DCID={qid}" for qid in quic_ids]))][f"{ip_column}.src"].value_counts()
    if client_ip_counts.empty:
        print("[WARN] Could not find any client IP from DCID matches.")
        return None

    client_ip = client_ip_counts.idxmax()
    print(f"[INFO] Inferred client IP: {client_ip}")

    # === Collect all server IPs from DCID matches that aren't the client ===
    server_ips_quic = []
    for cid in quic_ids:
        dst_ips = df[df["_ws.col.Info"].str.contains(f"DCID={cid}")][f"{ip_column}.dst"].unique().tolist()
        server_ips_quic.extend([ip for ip in dst_ips if ip != client_ip])
    server_ips_quic = list(set(server_ips_quic))

    if not server_ips_quic:
        print("[WARN] No candidate server IPs found.")
        return None

    print(f"[INFO] Candidate server IPs: {server_ips_quic}")

    # === Prefer server IP with most HEADERS packets ===
    server_packets = df[df[f'{ip_column}.src'].isin(server_ips_quic)]
    server_header_packets = server_packets[server_packets["_ws.col.Info"].str.contains("HEADERS", na=False)]

    if not server_header_packets.empty:
        server_ip = server_header_packets[f"{ip_column}.src"].value_counts().idxmax()
        print(f"[INFO] Selected server IP based on HEADERS: {server_ip}")
    else:
        # Fallback: most common server IP
        server_ip = server_packets[f"{ip_column}.src"].value_counts().idxmax()
        print(f"[WARN] No HEADERS found. Fallback to most common server IP: {server_ip}")

    # === Filter valid packets between client and server ===
    valid_client = (df[f'{ip_column}.src'] == client_ip) & (df[f'{ip_column}.dst'] == server_ip)
    valid_server = (df[f'{ip_column}.dst'] == client_ip) & (df[f'{ip_column}.src'] == server_ip)
    valid_data = df[valid_client | valid_server].copy()

    if valid_data.empty:
        print("[WARN] No valid packets found after filtering client-server directions.")
        return None

    print(f"[INFO] Total packets after filtering: {len(valid_data)}")

    # === Assign direction (0 = client → server, 1 = server → client) ===
    valid_data['Direction'] = valid_data.apply(lambda row: 0 if row[f'{ip_column}.src'] == client_ip else 1, axis=1)

    # === Select and rename relevant columns ===
    clean_data = valid_data.rename(columns={
        'frame.time_relative': 'Time',
        'frame.len': 'Length',
        f'{ip_column}.src': 'Source',
        f'{ip_column}.dst': 'Destination'
    })[['Time', 'Length', 'Source', 'Destination', 'Direction']]

    if save and save_path:
        clean_data.to_csv(save_path, index=False)
        print(f"[INFO] Saved cleaned CSV to: {save_path}")

    return clean_data


def clean_all_pcap_csvs(base_csv_dir, base_json_dir):
    """
    Recursively clean all CSVs under base_csv_dir and save them with 'cleaned_' prefix.
    """
    for root, dirs, files in os.walk(base_csv_dir):
        for file in files:
            if file.endswith(".csv") and not file.startswith("cleaned_"):
                csv_path = os.path.join(root, file)

                if "big_file" in csv_path:
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
                cleaned_df = clean_pcap_csv(csv_path, json_path)

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