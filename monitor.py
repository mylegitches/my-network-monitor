import subprocess
import json
import sqlite3
import time
import os
import argparse
import socket
import re
from datetime import datetime, timezone

DB_NAME = "speedtest_data.db"
# INTERVAL_SECONDS = 1800  # 30 minutes
INTERVAL_SECONDS = 30  # 30 seconds

ROUTER_IP = "192.168.1.1"
INTERNET_IP = "8.8.8.8"
DNS_DOMAIN = "google.com"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            ping_latency_ms REAL,
            download_bandwidth_bps INTEGER,
            upload_bandwidth_bps INTEGER,
            packet_loss REAL,
            isp TEXT,
            server_name TEXT,
            result_url TEXT,
            ping_router_ms REAL,
            ping_internet_ms REAL,
            dns_resolution_ms REAL
        )
    ''')
    
    # Simple migration: add columns if they don't exist
    try:
        cursor.execute("ALTER TABLE results ADD COLUMN ping_router_ms REAL")
    except sqlite3.OperationalError:
        pass # Column likely exists
    try:
        cursor.execute("ALTER TABLE results ADD COLUMN ping_internet_ms REAL")
    except sqlite3.OperationalError:
        pass # Column likely exists
    try:
        cursor.execute("ALTER TABLE results ADD COLUMN dns_resolution_ms REAL")
    except sqlite3.OperationalError:
        pass # Column likely exists

    conn.commit()
    conn.close()

def run_speedtest():
    try:
        # Run the speedtest CLI and get JSON output
        result = subprocess.run(
            [".\\speedtest.exe", "-f", "json", "--accept-license", "--accept-gdpr"],
            capture_output=True,
            text=True,
            check=False
        )
        
        # The CLI might output license info on the first run, so we grab the last non-empty line
        lines = [line for line in result.stdout.strip().split('\n') if line]
        if not lines:
            print("No output from speedtest CLI.")
            print("Error output:", result.stderr)
            return None
            
        json_output = lines[-1]
        data = json.loads(json_output)
        return data
        
    except Exception as e:
        print(f"Error running speedtest: {e}")
        return None

def check_ping(host):
    try:
        # Run ping command
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "2000", host],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            return None
            
        # Parse output for time=XXms or time<1ms
        match = re.search(r"time(?:=|<)([0-9]+)ms", result.stdout)
        if match:
            return float(match.group(1))
        return None
    except Exception as e:
        print(f"Error pinging {host}: {e}")
        return None

def check_dns(domain):
    try:
        start_time = time.time()
        socket.gethostbyname(domain)
        end_time = time.time()
        return (end_time - start_time) * 1000.0  # Convert to ms
    except Exception as e:
        print(f"Error resolving DNS for {domain}: {e}")
        return None

def save_result(data, ping_router, ping_internet, dns_res):
    if not data or "type" not in data or data["type"] != "result":
        print("Invalid data format received.")
        return
        
    try:
        # Extract fields based on Speedtest CLI JSON documentation
        timestamp = data.get("timestamp", datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'))
        ping = data.get("ping", {}).get("latency", 0.0)
        download = data.get("download", {}).get("bandwidth", 0)
        upload = data.get("upload", {}).get("bandwidth", 0)
        packet_loss = data.get("packetLoss", 0.0)
        isp = data.get("isp", "")
        server_name = data.get("server", {}).get("name", "")
        result_url = data.get("result", {}).get("url", "")
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO results (
                timestamp, ping_latency_ms, download_bandwidth_bps, 
                upload_bandwidth_bps, packet_loss, isp, server_name, result_url,
                ping_router_ms, ping_internet_ms, dns_resolution_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (timestamp, ping, download, upload, packet_loss, isp, server_name, result_url, ping_router, ping_internet, dns_res))
        
        conn.commit()
        conn.close()
        
        d_mbps = download * 8 / 1_000_000
        u_mbps = upload * 8 / 1_000_000
        print(f"[{timestamp}] Logged: ST Ping={ping:.2f}ms, Router Ping={ping_router or -1}ms, 8.8.8.8 Ping={ping_internet or -1}ms, DNS={dns_res or -1:.2f}ms, DL={d_mbps:.2f}Mbps, UL={u_mbps:.2f}Mbps")
        
    except Exception as e:
        print(f"Error saving result to database: {e}")

def main():
    parser = argparse.ArgumentParser(description="Perpetual Speedtest Monitor")
    parser.add_argument("--once", action="store_true", help="Run the test once and exit")
    args = parser.parse_args()
    
    print("Starting speedtest monitor...")
    if not args.once:
        print(f"Tests will run every {INTERVAL_SECONDS / 60:.1f} minutes.")
    init_db()
    
    import ip_scanner
    loop_count = 0
    while True:
        # Run IP scan every 10 loops (approx 5 minutes)
        if loop_count % 10 == 0:
            print(f"[{datetime.now().isoformat()}] Running IP scan...")
            try:
                ip_scanner.perform_scan()
            except Exception as e:
                print(f"IP scan failed: {e}")
        loop_count += 1
        
        # Perform network checks
        print(f"[{datetime.now().isoformat()}] Running network checks...")
        ping_router = check_ping(ROUTER_IP)
        ping_internet = check_ping(INTERNET_IP)
        dns_res = check_dns(DNS_DOMAIN)
        
        # Run speedtest
        data = run_speedtest()
        
        if data:
            save_result(data, ping_router, ping_internet, dns_res)
        else:
            print(f"[{datetime.now().isoformat()}] Test failed or returned no valid data.")
            
        if args.once:
            print("Finished single run (--once flag detected).")
            break
            
        print(f"Sleeping for {INTERVAL_SECONDS} seconds...")
        time.sleep(INTERVAL_SECONDS)

if __name__ == "__main__":
    main()
