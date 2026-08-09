"""
Database models and operations for WiFi positioning system
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import pandas as pd

class DatabaseManager:
    def __init__(self, db_path: str = "wifi_positioning.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        """Initialize database schema"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Zones table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS zones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                color TEXT NOT NULL,
                x_min REAL,
                y_min REAL,
                x_max REAL,
                y_max REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Training data table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                zone_id INTEGER NOT NULL,
                mac_address TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                signal_dbm REAL,
                signal_avg_dbm REAL,
                tx_bitrate_mbps REAL,
                rx_bitrate_mbps REAL,
                tx_mcs INTEGER,
                rx_mcs INTEGER,
                tx_packets INTEGER,
                rx_packets INTEGER,
                tx_retries INTEGER,
                tx_failed INTEGER,
                beacon_loss INTEGER,
                connected_time_sec INTEGER,
                inactive_time_ms INTEGER,
                FOREIGN KEY (zone_id) REFERENCES zones (id)
            )
        """)
        
        # Models table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                algorithm TEXT NOT NULL,
                features TEXT NOT NULL,
                accuracy REAL,
                f1_score REAL,
                training_samples INTEGER,
                model_data BLOB,
                scaler_data BLOB,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active INTEGER DEFAULT 0
            )
        """)
        
        # Predictions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER NOT NULL,
                mac_address TEXT NOT NULL,
                predicted_zone_id INTEGER NOT NULL,
                confidence REAL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                signal_dbm REAL,
                signal_avg_dbm REAL,
                FOREIGN KEY (model_id) REFERENCES models (id),
                FOREIGN KEY (predicted_zone_id) REFERENCES zones (id)
            )
        """)
        
        # Room layout table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS room_layout (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                width REAL NOT NULL,
                height REAL NOT NULL,
                description TEXT,
                layout_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    # Zone operations
    def add_zone(self, name: str, color: str, description: str = "", 
                 x_min: float = 0, y_min: float = 0, 
                 x_max: float = 1, y_max: float = 1) -> int:
        """Add a new zone"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO zones (name, description, color, x_min, y_min, x_max, y_max)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (name, description, color, x_min, y_min, x_max, y_max))
        zone_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return zone_id
    
    def get_zones(self) -> List[Dict]:
        """Get all zones"""
        conn = self.get_connection()
        df = pd.read_sql_query("SELECT * FROM zones ORDER BY name", conn)
        conn.close()
        return df.to_dict('records')
    
    def get_zone_by_id(self, zone_id: int) -> Optional[Dict]:
        """Get zone by ID"""
        conn = self.get_connection()
        df = pd.read_sql_query("SELECT * FROM zones WHERE id = ?", conn, params=(zone_id,))
        conn.close()
        if len(df) > 0:
            return df.iloc[0].to_dict()
        return None
    
    def update_zone(self, zone_id: int, **kwargs):
        """Update zone properties"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        allowed_fields = ['name', 'description', 'color', 'x_min', 'y_min', 'x_max', 'y_max']
        updates = []
        values = []
        
        for key, value in kwargs.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                values.append(value)
        
        if updates:
            values.append(zone_id)
            query = f"UPDATE zones SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
        
        conn.close()
    
    def delete_zone(self, zone_id: int):
        """Delete a zone"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM training_data WHERE zone_id = ?", (zone_id,))
        cursor.execute("DELETE FROM zones WHERE id = ?", (zone_id,))
        conn.commit()
        conn.close()
    
    # Training data operations
    def add_training_data(self, zone_id: int, data: pd.DataFrame):
        """Add training data from DataFrame"""
        conn = self.get_connection()
        
        # Add zone_id to dataframe
        data['zone_id'] = zone_id
        
        # Ensure timestamp is in correct format
        if 'timestamp' not in data.columns:
            data['timestamp'] = datetime.now()
        
        # Select relevant columns
        columns = [
            'zone_id', 'mac_address', 'timestamp', 'signal_dbm', 'signal_avg_dbm',
            'tx_bitrate_mbps', 'rx_bitrate_mbps', 'tx_mcs', 'rx_mcs',
            'tx_packets', 'rx_packets', 'tx_retries', 'tx_failed',
            'beacon_loss', 'connected_time_sec', 'inactive_time_ms'
        ]
        
        # Only keep columns that exist
        available_columns = [col for col in columns if col in data.columns or col == 'zone_id']
        data_to_insert = data[available_columns]
        
        data_to_insert.to_sql('training_data', conn, if_exists='append', index=False)
        conn.close()
    
    def get_training_data(self, zone_id: Optional[int] = None) -> pd.DataFrame:
        """Get training data, optionally filtered by zone"""
        conn = self.get_connection()
        if zone_id:
            query = "SELECT * FROM training_data WHERE zone_id = ?"
            df = pd.read_sql_query(query, conn, params=(zone_id,))
        else:
            df = pd.read_sql_query("SELECT * FROM training_data", conn)
        conn.close()
        return df
    
    def get_training_summary(self) -> pd.DataFrame:
        """Get summary of training data by zone"""
        conn = self.get_connection()
        query = """
            SELECT 
                z.name as zone_name,
                z.color,
                COUNT(t.id) as sample_count,
                AVG(t.signal_dbm) as avg_signal,
                MIN(t.signal_dbm) as min_signal,
                MAX(t.signal_dbm) as max_signal
            FROM zones z
            LEFT JOIN training_data t ON z.id = t.zone_id
            GROUP BY z.id, z.name, z.color
            ORDER BY z.name
        """
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def clear_training_data(self, zone_id: Optional[int] = None):
        """Clear training data"""
        conn = self.get_connection()
        cursor = conn.cursor()
        if zone_id:
            cursor.execute("DELETE FROM training_data WHERE zone_id = ?", (zone_id,))
        else:
            cursor.execute("DELETE FROM training_data")
        conn.commit()
        conn.close()
    
    # Model operations
    def save_model(self, name: str, algorithm: str, features: List[str],
                   model_data: bytes, scaler_data: bytes,
                   accuracy: float, f1_score: float, training_samples: int,
                   metadata: Dict = None):
        """Save trained model"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        features_json = json.dumps(features)
        metadata_json = json.dumps(metadata) if metadata else "{}"
        
        # Deactivate other models
        cursor.execute("UPDATE models SET is_active = 0")
        
        # Insert new model
        cursor.execute("""
            INSERT INTO models 
            (name, algorithm, features, accuracy, f1_score, training_samples,
             model_data, scaler_data, metadata, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (name, algorithm, features_json, accuracy, f1_score, training_samples,
              model_data, scaler_data, metadata_json))
        
        conn.commit()
        conn.close()
    
    def get_active_model(self) -> Optional[Dict]:
        """Get currently active model"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, name, algorithm, features, accuracy, f1_score, 
                   training_samples, model_data, scaler_data, metadata, created_at
            FROM models 
            WHERE is_active = 1
            ORDER BY created_at DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'name': row[1],
                'algorithm': row[2],
                'features': json.loads(row[3]),
                'accuracy': row[4],
                'f1_score': row[5],
                'training_samples': row[6],
                'model_data': row[7],
                'scaler_data': row[8],
                'metadata': json.loads(row[9]),
                'created_at': row[10]
            }
        return None
    
    def get_all_models(self) -> List[Dict]:
        """Get all models"""
        conn = self.get_connection()
        df = pd.read_sql_query("""
            SELECT id, name, algorithm, accuracy, f1_score, training_samples, 
                   created_at, is_active
            FROM models
            ORDER BY created_at DESC
        """, conn)
        conn.close()
        return df.to_dict('records')
    
    def activate_model(self, model_id: int):
        """Set a model as active"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE models SET is_active = 0")
        cursor.execute("UPDATE models SET is_active = 1 WHERE id = ?", (model_id,))
        conn.commit()
        conn.close()
    
    # Prediction operations
    def save_prediction(self, model_id: int, mac_address: str, 
                       predicted_zone_id: int, confidence: float,
                       signal_dbm: float, signal_avg_dbm: float):
        """Save a prediction"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO predictions 
            (model_id, mac_address, predicted_zone_id, confidence, signal_dbm, signal_avg_dbm)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (model_id, mac_address, predicted_zone_id, confidence, signal_dbm, signal_avg_dbm))
        conn.commit()
        conn.close()
    
    def get_predictions(self, limit: int = 100) -> pd.DataFrame:
        """Get recent predictions"""
        conn = self.get_connection()
        query = """
            SELECT 
                p.timestamp,
                p.mac_address,
                z.name as predicted_zone,
                p.confidence,
                p.signal_dbm,
                p.signal_avg_dbm,
                m.name as model_name
            FROM predictions p
            JOIN zones z ON p.predicted_zone_id = z.id
            JOIN models m ON p.model_id = m.id
            ORDER BY p.timestamp DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(limit,))
        conn.close()
        return df
    
    # Room layout operations
    def save_room_layout(self, name: str, width: float, height: float, 
                        description: str = "", layout_data: Dict = None):
        """Save room layout configuration"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        layout_json = json.dumps(layout_data) if layout_data else "{}"
        
        cursor.execute("""
            INSERT OR REPLACE INTO room_layout (name, width, height, description, layout_data)
            VALUES (?, ?, ?, ?, ?)
        """, (name, width, height, description, layout_json))
        
        conn.commit()
        conn.close()
    
    def get_room_layout(self, name: str = "default") -> Optional[Dict]:
        """Get room layout"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM room_layout WHERE name = ?", (name,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'name': row[1],
                'width': row[2],
                'height': row[3],
                'description': row[4],
                'layout_data': json.loads(row[5]) if row[5] else {},
                'created_at': row[6]
            }
        return None
