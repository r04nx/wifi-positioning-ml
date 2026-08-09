"""
ML Model training and prediction for WiFi positioning
"""
import numpy as np
import pandas as pd
import pickle
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, f1_score, classification_report, confusion_matrix
import io

class WiFiPositioningModel:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.features = []
        self.zone_mapping = {}
        self.algorithm = None
        
    def prepare_features(self, df: pd.DataFrame, feature_list: List[str]) -> pd.DataFrame:
        """Prepare and engineer features"""
        # Store feature list
        self.features = feature_list.copy()
        
        # Create copy
        data = df.copy()
        
        # Handle missing values
        for col in feature_list:
            if col in data.columns:
                data[col].fillna(data[col].median() if data[col].dtype in ['float64', 'int64'] else 0, inplace=True)
            else:
                data[col] = 0
        
        # Feature engineering
        if 'signal_dbm' in feature_list and 'signal_avg_dbm' in feature_list:
            if 'signal_variance' not in feature_list:
                # Add signal variance if not already in list
                data['signal_variance'] = abs(data['signal_dbm'] - data['signal_avg_dbm'])
        
        if 'tx_retries' in feature_list and 'tx_packets' in feature_list:
            # Packet loss ratio
            data['packet_loss_ratio'] = data['tx_retries'] / (data['tx_packets'] + 1)
            if 'packet_loss_ratio' not in self.features:
                self.features.append('packet_loss_ratio')
        
        if 'tx_failed' in feature_list and 'tx_packets' in feature_list:
            # Failure ratio
            data['failure_ratio'] = data['tx_failed'] / (data['tx_packets'] + 1)
            if 'failure_ratio' not in self.features:
                self.features.append('failure_ratio')
        
        # Connection quality score
        if 'tx_bitrate_mbps' in feature_list and 'rx_bitrate_mbps' in feature_list:
            data['avg_bitrate'] = (data['tx_bitrate_mbps'] + data['rx_bitrate_mbps']) / 2
            if 'avg_bitrate' not in self.features:
                self.features.append('avg_bitrate')
        
        return data[self.features]
    
    def train(self, X: pd.DataFrame, y: pd.Series, algorithm: str = 'random_forest',
              test_size: float = 0.2, random_state: int = 42) -> Dict:
        """Train the model"""
        self.algorithm = algorithm
        
        # Create zone mapping
        unique_zones = y.unique()
        self.zone_mapping = {zone: idx for idx, zone in enumerate(unique_zones)}
        reverse_mapping = {idx: zone for zone, idx in self.zone_mapping.items()}
        
        # Encode labels
        y_encoded = y.map(self.zone_mapping)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=test_size, random_state=random_state, stratify=y_encoded
        )
        
        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Select and train model
        if algorithm == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=random_state,
                n_jobs=-1
            )
        elif algorithm == 'gradient_boosting':
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                max_depth=5,
                random_state=random_state
            )
        elif algorithm == 'svm':
            self.model = SVC(
                kernel='rbf',
                C=10,
                gamma='scale',
                probability=True,
                random_state=random_state
            )
        elif algorithm == 'knn':
            self.model = KNeighborsClassifier(
                n_neighbors=5,
                weights='distance'
            )
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        
        # Train
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test_scaled)
        y_pred_train = self.model.predict(X_train_scaled)
        
        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average='weighted')
        train_accuracy = accuracy_score(y_train, y_pred_train)
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, X_train_scaled, y_train, cv=min(5, len(unique_zones)))
        
        # Classification report
        y_test_labels = [reverse_mapping[idx] for idx in y_test]
        y_pred_labels = [reverse_mapping[idx] for idx in y_pred]
        
        report = classification_report(y_test_labels, y_pred_labels, output_dict=True)
        conf_matrix = confusion_matrix(y_test, y_pred)
        
        # Feature importance (if available)
        feature_importance = None
        if hasattr(self.model, 'feature_importances_'):
            feature_importance = dict(zip(self.features, self.model.feature_importances_))
            feature_importance = dict(sorted(feature_importance.items(), key=lambda x: x[1], reverse=True))
        
        return {
            'accuracy': accuracy,
            'f1_score': f1,
            'train_accuracy': train_accuracy,
            'cv_scores': cv_scores.tolist(),
            'cv_mean': cv_scores.mean(),
            'cv_std': cv_scores.std(),
            'classification_report': report,
            'confusion_matrix': conf_matrix.tolist(),
            'feature_importance': feature_importance,
            'n_samples': len(X),
            'n_train': len(X_train),
            'n_test': len(X_test),
            'zone_mapping': reverse_mapping
        }
    
    def predict(self, X: pd.DataFrame) -> Tuple[List[int], np.ndarray]:
        """Predict zone for given features"""
        if self.model is None:
            raise ValueError("Model not trained yet")
        
        # Ensure features match
        X_features = X[self.features]
        
        # Handle missing values
        for col in self.features:
            if col in X_features.columns:
                X_features[col].fillna(0, inplace=True)
            else:
                X_features[col] = 0
        
        # Scale
        X_scaled = self.scaler.transform(X_features)
        
        # Predict
        predictions = self.model.predict(X_scaled)
        probabilities = self.model.predict_proba(X_scaled)
        
        return predictions.tolist(), probabilities
    
    def predict_single(self, features: Dict[str, float]) -> Tuple[int, float, Dict[int, float]]:
        """Predict zone for a single sample"""
        # Create DataFrame
        df = pd.DataFrame([features])
        
        # Predict
        predictions, probabilities = self.predict(df)
        
        predicted_zone = predictions[0]
        confidence = probabilities[0][predicted_zone]
        
        # Get all probabilities
        reverse_mapping = {idx: zone for zone, idx in self.zone_mapping.items()}
        all_probs = {reverse_mapping[i]: float(prob) for i, prob in enumerate(probabilities[0])}
        
        return predicted_zone, confidence, all_probs
    
    def serialize(self) -> Tuple[bytes, bytes]:
        """Serialize model and scaler"""
        model_buffer = io.BytesIO()
        scaler_buffer = io.BytesIO()
        
        pickle.dump(self.model, model_buffer)
        pickle.dump({
            'scaler': self.scaler,
            'features': self.features,
            'zone_mapping': self.zone_mapping,
            'algorithm': self.algorithm
        }, scaler_buffer)
        
        return model_buffer.getvalue(), scaler_buffer.getvalue()
    
    @classmethod
    def deserialize(cls, model_data: bytes, scaler_data: bytes) -> 'WiFiPositioningModel':
        """Deserialize model and scaler"""
        instance = cls()
        
        model_buffer = io.BytesIO(model_data)
        scaler_buffer = io.BytesIO(scaler_data)
        
        instance.model = pickle.load(model_buffer)
        scaler_dict = pickle.load(scaler_buffer)
        
        instance.scaler = scaler_dict['scaler']
        instance.features = scaler_dict['features']
        instance.zone_mapping = scaler_dict['zone_mapping']
        instance.algorithm = scaler_dict['algorithm']
        
        return instance


def get_available_features() -> List[str]:
    """Get list of available features for training"""
    return [
        'signal_dbm',
        'signal_avg_dbm',
        'tx_bitrate_mbps',
        'rx_bitrate_mbps',
        'tx_mcs',
        'rx_mcs',
        'tx_retries',
        'tx_failed',
        'tx_packets',
        'rx_packets',
        'beacon_loss',
        'inactive_time_ms'
    ]


def get_default_features() -> List[str]:
    """Get default feature set for training"""
    return [
        'signal_dbm',
        'signal_avg_dbm',
        'tx_bitrate_mbps',
        'rx_bitrate_mbps',
        'tx_retries',
        'tx_packets',
        'tx_failed'
    ]
