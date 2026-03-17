import time
import subprocess
import os
import ctypes

def keep_alive():
    print("🚀 Network Keep-Alive is running...")
    # Prevent system sleep (ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_AWAYMODE_REQUIRED)
    # This might help on some Windows versions to keep things active
    try:
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001 | 0x00000040)
    except:
        pass

    while True:
        try:
            # Ping a common server to keep the network adapter active
            subprocess.run(["ping", "-n", "1", "8.8.8.8"], capture_output=True, text=True)
            print(f"[{time.strftime('%H:%M:%S')}] Heartbeat sent...")
        except Exception as e:
            print(f"Error: {e}")
        
        # Sleep for 60 seconds
        time.sleep(60)

if __name__ == "__main__":
    keep_alive()
