import pandas as pd
import json
import os
from urllib.parse import urlparse
from event_types_list import event_type

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
    """
    Clean QUIC packets from tshark CSV and return a labeled DataFrame.
    Filters packets for a single QUIC session between client and server IPs
    based on DCID from the JSON NetLog file.

    Returns a DataFrame with:
    [Time, Length, Source, Destination, Direction]
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

    quic_ids = get_quic_connection_ids(json_path)
    if not quic_ids:
        return None

    ip_column = "ipv6" if df["ip.src"].isnull().all() else "ip"

    # Step 1: Detect client IP based on DCID match
    try:
        client_ip = df[df["_ws.col.Info"].str.contains(f"DCID={quic_ids[0]}")][f"{ip_column}.src"].iloc[0]
    except IndexError:
        print("[WARN] Could not detect client IP from NetLog ID match")
        return None

    # Step 2: Detect server IP(s) from matching DCIDs
    server_ips_quic = []
    for cid in quic_ids:
        dst_ips = df[df["_ws.col.Info"].str.contains(f"DCID={cid}")][f"{ip_column}.dst"].unique().tolist()
        server_ips_quic.extend([ip for ip in dst_ips if ip != client_ip])
    server_ips_quic = list(set(server_ips_quic))

    if not server_ips_quic:
        return None

    # Step 3: Infer final server IP based on HEADERS packet frequency
    server_packets = df[df[f'{ip_column}.src'].isin(server_ips_quic)]
    server_header_packets = server_packets[server_packets["_ws.col.Info"].str.contains("HEADERS")]
    if server_header_packets.empty:
        return None

    server_ip = server_header_packets[f"{ip_column}.src"].value_counts().idxmax()

    # Step 4: Keep only client → server or server → client packets
    valid_client = (df[f'{ip_column}.src'] == client_ip) & (df[f'{ip_column}.dst'] == server_ip)
    valid_server = (df[f'{ip_column}.dst'] == client_ip) & (df[f'{ip_column}.src'] == server_ip)
    valid_data = df[valid_client | valid_server].copy()

    if valid_data.empty:
        return None

    # Label each packet by direction
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


if __name__ == "__main__":
    # Example usage
    csv_path = "captures/csv/video/youtube/youtube-[2025-04-21-19-26-44].csv"
    json_path = "captures/pcap/video/youtube/youtube-[2025-04-21-19-26-44].json"
    cleaned_df = clean_pcap_csv(csv_path, json_path)
    if cleaned_df is not None:
        print(cleaned_df.head())
    else:
        print("[ERROR] No valid data found.")