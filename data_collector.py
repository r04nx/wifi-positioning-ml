"""
Data collection integration with Radxa device
"""
import subprocess
import pandas as pd
import io
from typing import Optional

class RadxaDataCollector:
    def __init__(self, host: str = "10.0.0.1", user: str = "vista", password: str = "vista"):
        self.host = host
        self.user = user
        self.password = password
    
    def collect_live_data(self, duration: int = 10, interval: float = 1.0) -> Optional[pd.DataFrame]:
        """Collect live data from Radxa device"""
        try:
            # Run monitoring script on device
            cmd = [
                "sshpass", "-p", self.password,
                "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
                f"{self.user}@{self.host}",
                f"sudo python3 /home/vista/wifi_monitor.py -t {interval} -d {duration} -o /tmp/temp_data.csv && cat /tmp/temp_data.csv"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 30)
            
            if result.returncode == 0:
                # Parse CSV output
                csv_data = result.stdout
                df = pd.read_csv(io.StringIO(csv_data))
                return df
            else:
                print(f"Error collecting data: {result.stderr}")
                return None
        
        except Exception as e:
            print(f"Exception during data collection: {e}")
            return None
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download a file from Radxa device"""
        try:
            cmd = [
                "sshpass", "-p", self.password,
                "scp", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
                f"{self.user}@{self.host}:{remote_path}",
                local_path
            ]
            
            result = subprocess.run(cmd, capture_output=True)
            return result.returncode == 0
        
        except Exception as e:
            print(f"Error downloading file: {e}")
            return False
