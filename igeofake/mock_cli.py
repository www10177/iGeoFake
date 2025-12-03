import sys
import time
import argparse
import random
import signal
import os

def mock_tunnel_a():
    print("INFO:     Started server process [26252]")
    print("INFO:     Waiting for application startup.")
    print("INFO:     Application startup complete.")
    print("INFO:     Uvicorn running on http://127.0.0.1:49151 (Press CTRL+C to quit)")
    print("2025-12-03 22:16:32 9950X3D pymobiledevice3.tunneld.server[26252] INFO [start-tunnel-task-usbmux-00008150-001E6CE20228401C-USB] Created tunnel --rsd fdae:4871:a659::1 55082")
    sys.stdout.flush()
    while True:
        time.sleep(1)

def mock_tunnel_b():
    print("2025-12-03 22:16:56 9950X3D pymobiledevice3.cli.remote[31416] INFO tunnel created")
    print("Identifier: 00008150-001E6CE20228401C")
    print("Interface: pymobiledevice3-tunnel-00008150-001E6CE20228401C")
    print("Protocol: TunnelProtocol.TCP")
    print("RSD Address: fd0b:d15a:eebf::1")
    print("RSD Port: 55083")
    print("Use the follow connection option:")
    print("--rsd fd0b:d15a:eebf::1 55083")
    sys.stdout.flush()
    while True:
        time.sleep(1)

def mock_set_location(lat, lon):
    print(f"Setting location to LAT:{lat}, LON:{lon}")
    print("Press ENTER to exit>\\")
    sys.stdout.flush()
    # Simulate blocking process
    while True:
        time.sleep(1)

def mock_clear_location():
    print("Clearing location...")
    time.sleep(1)
    print("Location cleared.")

def main():
    # Ignore SIGTERM to simulate stubborn process if needed,
    # but for now let's just run.
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='command')

    # Structure matches: pymobiledevice3 <command> <subcommand> ...
    # But since we call this script directly, we just need to differentiate the modes.
    # We will invoke this script like: python mock_cli.py [mode] [args...]

    # We'll use a simplified argument parsing for the mock:
    if len(sys.argv) < 2:
        print("Usage: mock_cli.py <mode> [args]")
        sys.exit(1)

    mode = sys.argv[1]

    if mode == "tunnel_a":
        mock_tunnel_a()
    elif mode == "tunnel_b":
        time.sleep(2) # simulate delay
        mock_tunnel_b()
    elif mode == "set_location":
        # args expected: -- <LAT> <LON>
        # sys.argv might look like: ['mock_cli.py', 'set_location', '--', '25.0', '121.0']
        try:
            # Find '--'
            if '--' in sys.argv:
                dash_index = sys.argv.index('--')
                lat = sys.argv[dash_index+1]
                lon = sys.argv[dash_index+2]
            else:
                # Fallback if no -- provided in mock call (though real app will provide it)
                lat = "0.0"
                lon = "0.0"
            mock_set_location(lat, lon)
        except Exception as e:
            print(f"Error parsing args: {e}")
            mock_set_location("0.0", "0.0")

    elif mode == "clear_location":
        mock_clear_location()
    else:
        print(f"Unknown mode: {mode}")

if __name__ == "__main__":
    main()
