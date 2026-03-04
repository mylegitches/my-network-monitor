import sqlite3
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

DB_NAME = "speedtest_data.db"

def generate_graph():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Read the latest 100 results ordered by timestamp
        cursor.execute('''
            SELECT timestamp, ping_latency_ms, download_bandwidth_bps, upload_bandwidth_bps,
                   ping_router_ms, ping_internet_ms, dns_resolution_ms
            FROM results 
            ORDER BY timestamp ASC
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            print("No data found in the database. Run the monitor first.")
            return

        timestamps = []
        pings = []
        downloads_mbps = []
        uploads_mbps = []
        pings_router = []
        pings_internet = []
        dns_resolutions = []

        for row in rows:
            # Parse ISO 8601 timestamp (assuming UTC from Speedtest CLI)
            ts = datetime.fromisoformat(row[0].replace('Z', '+00:00'))
            timestamps.append(ts)
            
            pings.append(row[1])
            # CLI returns bytes per second (bandwidth). Convert to Mbps:
            # bytes/sec * 8 bits/byte / 1,000,000 = Mbps
            downloads_mbps.append(row[2] * 8 / 1_000_000)
            uploads_mbps.append(row[3] * 8 / 1_000_000)
            pings_router.append(row[4])
            pings_internet.append(row[5])
            dns_resolutions.append(row[6])

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
        fig.suptitle('Speedtest Results Over Time', fontsize=16)

        # Plot Bandwidth
        ax1.plot(timestamps, downloads_mbps, marker='o', label='Download (Mbps)', color='blue')
        ax1.plot(timestamps, uploads_mbps, marker='s', label='Upload (Mbps)', color='green')
        ax1.set_ylabel('Speed (Mbps)')
        ax1.grid(True, linestyle='--', alpha=0.7)
        ax1.legend()

        # Plot Ping
        ax2.plot(timestamps, pings, marker='^', label='ST Ping (ms)', color='red')
        ax2.plot(timestamps, pings_router, marker='v', label='Router (ms)', color='orange')
        ax2.plot(timestamps, pings_internet, marker='>', label='8.8.8.8 (ms)', color='purple')
        ax2.plot(timestamps, dns_resolutions, marker='<', label='DNS (ms)', color='brown')
        ax2.set_ylabel('Latency (ms)')
        ax2.set_xlabel('Time')
        ax2.grid(True, linestyle='--', alpha=0.7)
        ax2.legend()
        
        # Format the x-axis for dates
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d %H:%M'))
        fig.autofmt_xdate()

        plt.tight_layout()
        timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
        output_image = f"speed_graph-{timestamp_str}.png"
        plt.savefig(output_image, dpi=300)
        print(f"Graph saved successfully to {output_image}")
        
    except sqlite3.OperationalError:
        print(f"Could not open {DB_NAME}. Does it exist yet?")
    except Exception as e:
        print(f"Error generating graph: {e}")

if __name__ == "__main__":
    generate_graph()
