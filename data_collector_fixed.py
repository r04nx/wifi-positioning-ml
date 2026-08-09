"""
Data collection integration with local WiFi monitoring
"""
import subprocess
import pandas as pd
import io
from typing import Optional
import os

class RadxaDataCollector:
    def __init__(self, host: str = "localhost", user: str = "vista", password: str = "vista"):
        self.host = host
        self.user = user
        self.password = password
        self.is_local = (host == "localhost" or host == "127.0.0.1")
    
    def collect_live_data(self, duration: int = 10, interval: float = 1.0) -> Optional[pd.DataFrame]:
        """Collect live data from WiFi monitoring"""
        try:
            output_file = "/tmp/wifi_data_temp.csv"
            
            if self.is_local:
                # Running on the device itself - use local command
                cmd = [
                    "sudo", "python3", "/home/vista/wifi_monitor.py",
                    "-t", str(interval),
                    "-d", str(duration),
                    "-o", output_file
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 30)
                
                if result.returncode == 0:
                    # Read the file
                    if os.path.exists(output_file):
                        df = pd.read_csv(output_file)
                        # Clean up
                        os.remove(output_file)
                        
                        if len(df) > 0:
                            return df
                        else:
                            print("No data collected - no WiFi clients connected to AP")
                            return None
                    else:
                        print(f"Output file not created: {output_file}")
                        return None
                else:
                    print(f"Error running monitoring script: {result.stderr}")
                    return None
            else:
                # Remote collection via SSH
                cmd = [
                    "sshpass", "-p", self.password,
                    "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
                    f"{self.user}@{self.host}",
                    f"sudo python3 /home/vista/wifi_monitor.py -t {interval} -d {duration} -o /tmp/temp_data.csv && cat /tmp/temp_data.csv"
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 30)
                
                if result.returncode == 0:
                    csv_data = result.stdout
                    df = pd.read_csv(io.StringIO(csv_data))
                    return df
                else:
                    print(f"Error collecting data: {result.stderr}")
                    return None
        
        except Exception as e:
            print(f"Exception during data collection: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download a file from device"""
        try:
            if self.is_local:
                # Just copy the file
                import shutil
                shutil.copy(remote_path, local_path)
                return True
            else:
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
