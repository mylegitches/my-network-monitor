# LAN Uptime Monitor

A perpetual speedtest monitor built with Python and the official Ookla Speedtest CLI.

## Setup
1. Ensure Python is installed.
2. Install the requirements:
   `pip install -r requirements.txt`
3. Download the Speedtest CLI executable `speedtest.exe` directly from the [official Ookla site](https://www.speedtest.net/apps/cli) and place it in this folder.

## Running the Monitor
You can simply run the Python script to start monitoring:
```bash
python monitor.py
```
This will run an initial speedtest, log the result to `speedtest_data.db`, and then sleep for 30 minutes before running again. It runs perpetually as long as this process is alive.

## Graphing the Data
To visualize the historic log:
```bash
python graph.py
```
This will generate `speed_graph-YYYYMMDDHHMMSS.png` showing download/upload speeds and ping latency over time.

## Running as a Background Service in Windows
To ensure it runs persistently even if you close the terminal, you can set it up via Windows Task Scheduler or use a background runner like `pythonw`.

### Option 1: pythonw (Simple Hidden Process)
Run the script using `pythonw.exe` (part of standard Python installations) to run without a console window:
```cmd
pythonw.exe monitor.py
```
*Note: To kill this, you will need to open Task Manager and end the `pythonw.exe` process.*

### Option 2: Windows Task Scheduler
If you want to run exactly one test every hour without relying on Python's `time.sleep`:
1. Modify `monitor.py` to remove the `while True` loop and `time.sleep()`. Just call `data = run_speedtest()` and `save_result(data)` once in `main()`.
2. Open **Task Scheduler**.
3. Create a **Basic Task**, name it "Speedtest Monitor".
4. Trigger: **Daily** -> Recur every 1 days.
5. Action: **Start a program**.
6. Program/script: `C:\path\to\your\python.exe`
7. Add arguments: `monitor.py`
8. Start in: `F:\projects\lan-uptime-monitor\`
9. After creation, open the task properties, and go to **Triggers**. Edit the trigger to repeat the task every 30 minutes. 
