# WiFi Indoor Positioning System

Complete end-to-end ML training and evaluation system for indoor positioning using WiFi signal metrics.

## Features

- 🗺️ **Zone Management**: Define and visualize zones in your indoor environment
- 📊 **Data Collection**: Collect training data from Radxa device with zone labels
- 🤖 **ML Training**: Train models with multiple algorithms (Random Forest, Gradient Boosting, SVM, KNN)
- 🎯 **Live Prediction**: Real-time zone prediction with visual feedback
- 📈 **Comprehensive Evaluation**: Confusion matrices, feature importance, classification reports
- 💾 **SQLite Database**: Persistent storage for zones, training data, models, and predictions

## Installation

```bash
cd /home/rohan/wifi_positioning_ml
pip install -r requirements.txt
```

## Quick Start

1. **Start the application:**
   ```bash
   streamlit run app.py
   ```

2. **Create Zones:**
   - Navigate to "Zone Management"
   - Add zones with names, colors, and boundaries
   - Visualize zones on room layout

3. **Collect Training Data:**
   - Go to "Data Collection"
   - Place client device in a zone
   - Select zone and collect data
   - Repeat for all zones

4. **Train Model:**
   - Navigate to "Model Training"
   - Select algorithm and features
   - Train model and view evaluation metrics

5. **Live Prediction:**
   - Go to "Live Prediction"
   - Start real-time prediction
   - View predicted zone on layout

## Project Structure

```
wifi_positioning_ml/
├── app.py                   # Main Streamlit application
├── database.py              # Database operations
├── ml_model.py              # ML training and prediction
├── data_collector.py        # Radxa data collection
├── requirements.txt         # Python dependencies
├── README.md               # This file
└── wifi_positioning.db     # SQLite database (created on first run)
```

## Supported Algorithms

- **Random Forest**: Ensemble method, good default choice
- **Gradient Boosting**: High accuracy, slower training
- **SVM**: Good for smaller datasets
- **K-Nearest Neighbors**: Simple, fast predictions

## Features for Training

- `signal_dbm`: Instantaneous signal strength
- `signal_avg_dbm`: Average signal strength
- `tx_bitrate_mbps`: Transmit bitrate
- `rx_bitrate_mbps`: Receive bitrate
- `tx_retries`: Packet retransmissions
- `tx_failed`: Failed transmissions
- `tx_packets`: Total transmitted packets
- And more...

## Tips for Best Results

1. Collect at least 50-100 samples per zone
2. Use consistent client device for training
3. Include features: signal_dbm, signal_avg_dbm, tx_bitrate_mbps
4. Try Random Forest first (good balance of accuracy and speed)
5. Place client in center of zone during collection

## Database Schema

- **zones**: Zone definitions
- **training_data**: Labeled WiFi metrics
- **models**: Trained ML models
- **predictions**: Prediction history
- **room_layout**: Room configuration

## Sans-Serif Font

The UI uses sans-serif fonts (Segoe UI, Arial) throughout for clean, modern appearance.

## License

MIT License
