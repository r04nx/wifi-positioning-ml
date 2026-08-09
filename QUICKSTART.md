# Quick Start Guide - WiFi Indoor Positioning System

## Installation on Radxa Device

### 1. Deploy Application to Radxa

From your local machine, run:
```bash
cd /home/rohan/wifi_positioning_ml
sshpass -p vista scp -r ./* vista@10.0.0.1:/home/vista/wifi_positioning_ml/
```

### 2. Install Dependencies on Radxa

SSH into the device and install requirements:
```bash
sshpass -p vista ssh vista@10.0.0.1
cd /home/vista/wifi_positioning_ml
sudo apt-get update
sudo apt-get install -y python3-pip
pip3 install -r requirements.txt
```

### 3. Start the Web Application

On Radxa device:
```bash
cd /home/vista/wifi_positioning_ml
streamlit run app.py --server.port 8501 --server.address 0.0.0.0
```

Access from browser: **http://10.0.0.1:8501**

## Features Overview

### Algorithm Selection
The app includes dropdown to select from:
- ✅ **Random Forest** - Best for general use
- ✅ **Gradient Boosting** - Highest accuracy
- ✅ **SVM** - Good for small datasets
- ✅ **K-Nearest Neighbors** - Fast predictions

### Training & Evaluation Visualizations
- **Accuracy Metrics**: Test accuracy, training accuracy, F1 score
- **Cross-Validation Scores**: Mean ± standard deviation
- **Confusion Matrix**: Heatmap visualization
- **Feature Importance**: Bar chart showing most important features
- **Classification Report**: Precision, recall, F1 for each zone
- **Signal Strength Distribution**: Bar charts by zone

### Live Prediction Display
- Real-time zone prediction with confidence percentage
- Probability distribution across all zones (bar chart)
- Room layout visualization with highlighted current zone
- Prediction history timeline

## Workflow

### Step 1: Define Zones
1. Navigate to **Zone Management** → **Add Zone**
2. Create zones (e.g., "Living Room", "Kitchen", "Bedroom")
3. Assign colors and boundaries (0-1 normalized coordinates)
4. View room layout with all zones

### Step 2: Collect Training Data
1. Go to **Data Collection** → **Live Collection**
2. Place WiFi client in first zone
3. Select zone from dropdown
4. Set duration (30-60 seconds recommended)
5. Click "Start Collection"
6. Repeat for each zone

### Step 3: Train Model
1. Navigate to **Model Training** → **Train New Model**
2. **Select Algorithm** from dropdown:
   - Random Forest (default, reliable)
   - Gradient Boosting (more accurate, slower)
   - SVM (linear/non-linear separation)
   - KNN (distance-based)
3. **Select Features** (default includes signal_dbm, signal_avg_dbm, etc.)
4. Click "Train Model"
5. View results:
   - Accuracy percentage
   - F1 Score
   - Cross-validation score
   - **Confusion Matrix** (visual heatmap)
   - **Feature Importance** (bar chart)

### Step 4: Evaluate Model
1. Go to **Model Training** → **Model Evaluation**
2. View comprehensive metrics:
   - Confusion matrix heatmap
   - Classification report table
   - Per-zone precision/recall/F1
3. Compare multiple models in **Saved Models** tab
4. Activate best performing model

### Step 5: Live Prediction
1. Navigate to **Live Prediction**
2. Click "Start Prediction"
3. Watch real-time:
   - Predicted zone name
   - Confidence percentage
   - Probability bar chart for all zones
   - Room layout with highlighted zone
4. View prediction history in second tab

## Running as Background Service

Create systemd service for auto-start:

```bash
sudo tee /etc/systemd/system/wifi-positioning.service << 'SERVICE'
[Unit]
Description=WiFi Indoor Positioning Web App
After=network.target

[Service]
Type=simple
User=vista
WorkingDirectory=/home/vista/wifi_positioning_ml
ExecStart=/usr/local/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl enable wifi-positioning
sudo systemctl start wifi-positioning
sudo systemctl status wifi-positioning
```

Access: **http://10.0.0.1:8501**

## Tips for Best Accuracy

1. **Collect More Data**: 50-100 samples per zone minimum
2. **Consistent Client**: Use same device for training
3. **Feature Selection**: Include signal_dbm, signal_avg_dbm, tx_bitrate_mbps
4. **Algorithm Choice**:
   - Start with Random Forest (balanced)
   - Try Gradient Boosting for higher accuracy
   - Use KNN for real-time performance
5. **Cross-Validation**: Check CV score to detect overfitting
6. **Confusion Matrix**: Identify which zones are confused

## Troubleshooting

### Cannot Access Web UI
```bash
# Check if service is running
sudo systemctl status wifi-positioning

# Check firewall
sudo ufw allow 8501

# View logs
journalctl -u wifi-positioning -f
```

### Model Training Fails
- Ensure at least 10 samples per zone
- Check feature availability in collected data
- Try simpler algorithm (KNN) first

### No Data Collection
- Verify Radxa AP is running: `sudo systemctl status hostapd`
- Check client is connected: `sudo iw dev wlan0 station dump`
- Run monitoring script manually: `sudo python3 /home/vista/wifi_monitor.py -d 5`

## Algorithm Comparison

| Algorithm | Training Speed | Accuracy | Interpretability | Best For |
|-----------|---------------|----------|------------------|----------|
| Random Forest | Fast | High | Good | General use |
| Gradient Boosting | Slow | Highest | Moderate | Maximum accuracy |
| SVM | Medium | High | Low | Complex boundaries |
| KNN | Very Fast | Medium | High | Quick prototyping |

## Database Location

All data stored in: `/home/vista/wifi_positioning_ml/wifi_positioning.db`

Backup regularly:
```bash
cp wifi_positioning.db wifi_positioning_backup_$(date +%Y%m%d).db
```
