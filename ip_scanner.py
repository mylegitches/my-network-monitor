import subprocess
import re
import socket
import csv
import json
import os
import urllib.request
import urllib.parse
import urllib.error
import concurrent.futures
from datetime import datetime

CSV_FILE = "ipscan_results.csv"
OUI_CACHE_FILE = "mac_vendors_cache.json"
OUI_URL = "https://raw.githubusercontent.com/davidonzo/mac-vendors-export/master/mac-vendors-export.json"

def get_local_ip_and_subnet():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        # Defaulting to /24 subnet
        base_ip = ".".join(local_ip.split(".")[:3])
        return base_ip
    except Exception:
        return None

def load_oui_database():
    try:
        if os.path.exists(OUI_CACHE_FILE):
            with open(OUI_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_oui_database(mapping):
    try:
        with open(OUI_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=2)
    except Exception as e:
        print(f"Error saving OUI cache: {e}")

def get_manufacturer(mac, oui_mapping):
    # Try looking up in the cache first
    # API MACs are generally handled well, we'll store them exactly as we get them
    if mac in oui_mapping:
        return oui_mapping[mac]
        
    print(f"Looking up MAC {mac} via API...")
    try:
        # Rate limit is 1 req/sec for api.macvendors.com
        import time
        req = urllib.request.Request(f"https://api.macvendors.com/{urllib.parse.quote(mac)}", headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            vendor = response.read().decode('utf-8')
            oui_mapping[mac] = vendor
            save_oui_database(oui_mapping)
            time.sleep(1) # Be nice to the API
            return vendor
    except urllib.error.HTTPError as e:
        if e.code == 404:
            oui_mapping[mac] = "Unknown/Not Found"
            save_oui_database(oui_mapping)
            time.sleep(1)
            return "Unknown/Not Found"
        if e.code == 429:
            print("Rate limited by MAC vendors API.")
            time.sleep(2)
        print(f"HTTP Error checking MAC vendor: {e.code}")
    except Exception as e:
        print(f"Error checking MAC vendor: {e}")
        
    return "Unknown"

def ping_host(ip):
    # -n 1 = 1 ping, -w 200 = 200ms timeout
    subprocess.run(["ping", "-n", "1", "-w", "200", ip], capture_output=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000))
    return ip

def get_active_arp_entries():
    # Run arp -a to get IP to MAC mappings
    result = subprocess.run(["arp", "-a"], capture_output=True, text=True, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000))
    entries = []
    # arp -a format Windows:
    # Interface: 192.168.1.100 --- 0x4
    #   Internet Address      Physical Address      Type
    #   192.168.1.1           00-11-22-33-44-55     dynamic
    for line in result.stdout.split('\n'):
        line = line.strip()
        if not line or "Interface" in line or "Internet Address" in line:
            continue
        parts = line.split()
        if len(parts) >= 3 and parts[2] == "dynamic":
            ip = parts[0]
            mac = parts[1]
            # Ignore multicast/broadcast IPs
            if not ip.startswith("224.") and not ip.startswith("239.") and not ip.endswith(".255"):
                entries.append((ip, mac))
    return entries

def resolve_hostname(ip):
    try:
        # set timeout so it doesn't hang
        socket.setdefaulttimeout(0.5)
        hostname, _, _ = socket.gethostbyaddr(ip)
        return ip, hostname
    except Exception:
        return ip, "Unknown"

def perform_scan():
    base_ip = get_local_ip_and_subnet()
    if not base_ip:
        print("Could not determine local subnet.")
        return
        
    print(f"Scanning subnet: {base_ip}.0/24")
    
    # 1. Sweep ping to populate ARP cache
    ips_to_ping = [f"{base_ip}.{i}" for i in range(1, 255)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        list(executor.map(ping_host, ips_to_ping))
        
    # 2. Extract active IPs and MACs from ARP table
    active_devices = get_active_arp_entries()
    print(f"Found {len(active_devices)} active devices.")
    
    # 3. Resolve hostnames concurrently
    hostnames = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(resolve_hostname, ip) for ip, _ in active_devices]
        for future in concurrent.futures.as_completed(futures):
            ip, hname = future.result()
            hostnames[ip] = hname
            
    # 4. Load OUI mapping
    oui_mapping = load_oui_database()
    
    # 5. Prepare results
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    results = []
    for ip, mac in active_devices:
        hostname = hostnames.get(ip, "Unknown")
        manufacturer = get_manufacturer(mac, oui_mapping)
        results.append({
            "Scan_Time": timestamp,
            "IP_Address": ip,
            "MAC_Address": mac,
            "Hostname": hostname,
            "Manufacturer": manufacturer
        })
        
    # 6. Save to CSV
    file_exists = os.path.exists(CSV_FILE)
    fieldnames = ["Scan_Time", "IP_Address", "MAC_Address", "Hostname", "Manufacturer"]
    
    try:
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            for row in results:
                writer.writerow(row)
        print(f"Successfully wrote {len(results)} records to {CSV_FILE}")
    except Exception as e:
        print(f"Error writing to CSV: {e}")
        
    return results

if __name__ == "__main__":
    perform_scan()
