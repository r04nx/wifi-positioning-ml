"""
WiFi Indoor Positioning System - Streamlit Application
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import time
import json

from database import DatabaseManager
from ml_model import WiFiPositioningModel, get_available_features, get_default_features
from data_collector import RadxaDataCollector

# Page config
st.set_page_config(
    page_title="WiFi Indoor Positioning System",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for sans-serif font
st.markdown("""
<style>
    * {
        font-family: 'Segoe UI', 'Arial', sans-serif !important;
    }
    .big-font {
        font-size: 24px !important;
        font-weight: 600;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = DatabaseManager()

if 'collector' not in st.session_state:
    st.session_state.collector = RadxaDataCollector()

if 'model' not in st.session_state:
    st.session_state.model = None

# Sidebar navigation
st.sidebar.title("📡 WiFi Positioning")
page = st.sidebar.radio(
    "Navigation",
    ["🏠 Dashboard", "🗺️ Zone Management", "📊 Data Collection", "🤖 Model Training", "🎯 Live Prediction"],
    label_visibility="collapsed"
)

# ============================================================================
# Dashboard Page
# ============================================================================
if page == "🏠 Dashboard":
    st.title("📡 WiFi Indoor Positioning System")
    st.markdown("---")
    
    # Overview metrics
    col1, col2, col3, col4 = st.columns(4)
    
    zones = st.session_state.db.get_zones()
    training_summary = st.session_state.db.get_training_summary()
    models = st.session_state.db.get_all_models()
    
    with col1:
        st.metric("Total Zones", len(zones))
    
    with col2:
        total_samples = training_summary['sample_count'].sum() if len(training_summary) > 0 else 0
        st.metric("Training Samples", int(total_samples))
    
    with col3:
        st.metric("Trained Models", len(models))
    
    with col4:
        active_model = st.session_state.db.get_active_model()
        accuracy = f"{active_model['accuracy']*100:.1f}%" if active_model else "N/A"
        st.metric("Model Accuracy", accuracy)
    
    st.markdown("---")
    
    # Zone distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Zone Training Data Distribution")
        if len(training_summary) > 0:
            fig = px.bar(
                training_summary,
                x='zone_name',
                y='sample_count',
                color='zone_name',
                color_discrete_map={row['zone_name']: row['color'] for _, row in training_summary.iterrows()},
                labels={'sample_count': 'Sample Count', 'zone_name': 'Zone'}
            )
            fig.update_layout(showlegend=False, font=dict(family="sans-serif"))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No training data available yet")
    
    with col2:
        st.subheader("Signal Strength by Zone")
        if len(training_summary) > 0 and 'avg_signal' in training_summary.columns:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=training_summary['zone_name'],
                y=training_summary['avg_signal'],
                marker=dict(color=[row['color'] for _, row in training_summary.iterrows()]),
                error_y=dict(
                    type='data',
                    array=training_summary['max_signal'] - training_summary['avg_signal'],
                    arrayminus=training_summary['avg_signal'] - training_summary['min_signal']
                )
            ))
            fig.update_layout(
                xaxis_title="Zone",
                yaxis_title="Signal Strength (dBm)",
                showlegend=False,
                font=dict(family="sans-serif")
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No signal data available yet")
    
    # Recent predictions
    st.markdown("---")
    st.subheader("Recent Predictions")
    predictions = st.session_state.db.get_predictions(limit=10)
    if len(predictions) > 0:
        st.dataframe(predictions, use_container_width=True)
    else:
        st.info("No predictions made yet")

# ============================================================================
# Zone Management Page
# ============================================================================
elif page == "🗺️ Zone Management":
    st.title("🗺️ Zone Management")
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["📋 View Zones", "➕ Add Zone", "🏢 Room Layout"])
    
    with tab1:
        st.subheader("Existing Zones")
        zones = st.session_state.db.get_zones()
        
        if len(zones) > 0:
            for zone in zones:
                col1, col2, col3 = st.columns([3, 1, 1])
                
                with col1:
                    st.markdown(f"### {zone['name']}")
                    st.write(f"Description: {zone['description']}")
                    st.write(f"Position: ({zone['x_min']:.2f}, {zone['y_min']:.2f}) to ({zone['x_max']:.2f}, {zone['y_max']:.2f})")
                
                with col2:
                    st.color_picker("Color", zone['color'], key=f"color_{zone['id']}", disabled=True)
                
                with col3:
                    if st.button("🗑️ Delete", key=f"del_{zone['id']}"):
                        st.session_state.db.delete_zone(zone['id'])
                        st.rerun()
                
                st.markdown("---")
        else:
            st.info("No zones defined yet. Add your first zone!")
    
    with tab2:
        st.subheader("Add New Zone")
        
        with st.form("add_zone_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                zone_name = st.text_input("Zone Name *", placeholder="e.g., Living Room")
                zone_description = st.text_area("Description", placeholder="Enter zone description")
                zone_color = st.color_picker("Zone Color", "#FF6B6B")
            
            with col2:
                st.write("**Zone Boundaries (0-1 normalized)**")
                x_min = st.number_input("X Min", 0.0, 1.0, 0.0, 0.1)
                x_max = st.number_input("X Max", 0.0, 1.0, 0.3, 0.1)
                y_min = st.number_input("Y Min", 0.0, 1.0, 0.0, 0.1)
                y_max = st.number_input("Y Max", 0.0, 1.0, 0.3, 0.1)
            
            submitted = st.form_submit_button("Add Zone")
            
            if submitted:
                if zone_name:
                    try:
                        st.session_state.db.add_zone(
                            name=zone_name,
                            description=zone_description,
                            color=zone_color,
                            x_min=x_min,
                            y_min=y_min,
                            x_max=x_max,
                            y_max=y_max
                        )
                        st.success(f"Zone '{zone_name}' added successfully!")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding zone: {e}")
                else:
                    st.error("Zone name is required!")
    
    with tab3:
        st.subheader("Room Layout Visualization")
        
        # Room layout configuration
        with st.expander("Configure Room Layout"):
            col1, col2 = st.columns(2)
            with col1:
                room_width = st.number_input("Room Width (m)", 1.0, 50.0, 10.0, 0.5)
            with col2:
                room_height = st.number_input("Room Height (m)", 1.0, 50.0, 8.0, 0.5)
            
            if st.button("Save Room Layout"):
                st.session_state.db.save_room_layout(
                    name="default",
                    width=room_width,
                    height=room_height,
                    description="Main room layout"
                )
                st.success("Room layout saved!")
        
        # Visualize zones
        zones = st.session_state.db.get_zones()
        if len(zones) > 0:
            fig = go.Figure()
            
            # Add room boundary
            fig.add_shape(
                type="rect",
                x0=0, y0=0, x1=1, y1=1,
                line=dict(color="black", width=2),
                fillcolor="white"
            )
            
            # Add zones
            for zone in zones:
                fig.add_shape(
                    type="rect",
                    x0=zone['x_min'], y0=zone['y_min'],
                    x1=zone['x_max'], y1=zone['y_max'],
                    fillcolor=zone['color'],
                    opacity=0.5,
                    line=dict(color=zone['color'], width=2)
                )
                
                # Add zone label
                center_x = (zone['x_min'] + zone['x_max']) / 2
                center_y = (zone['y_min'] + zone['y_max']) / 2
                fig.add_annotation(
                    x=center_x, y=center_y,
                    text=zone['name'],
                    showarrow=False,
                    font=dict(size=14, color="black", family="sans-serif")
                )
            
            fig.update_layout(
                xaxis=dict(range=[0, 1], showgrid=True, title="X Position"),
                yaxis=dict(range=[0, 1], showgrid=True, title="Y Position"),
                height=600,
                title="Room Layout with Zones",
                font=dict(family="sans-serif")
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No zones to display. Add zones first!")

# ============================================================================
# Data Collection Page
# ============================================================================
elif page == "📊 Data Collection":
    st.title("📊 Data Collection & Labeling")
    st.markdown("---")
    
    zones = st.session_state.db.get_zones()
    
    if len(zones) == 0:
        st.warning("⚠️ Please create zones first before collecting training data!")
    else:
        tab1, tab2, tab3 = st.tabs(["🔴 Live Collection", "📁 Import CSV", "📈 View Data"])
        
        with tab1:
            st.subheader("Collect Training Data from Radxa")
            
            col1, col2 = st.columns(2)
            
            with col1:
                selected_zone = st.selectbox(
                    "Select Zone for Data Collection",
                    options=[z['name'] for z in zones],
                    help="Place your client device in this zone before collecting data"
                )
                
                duration = st.slider("Collection Duration (seconds)", 5, 300, 30)
                interval = st.slider("Sampling Interval (seconds)", 0.1, 5.0, 1.0, 0.1)
            
            with col2:
                st.info(
                    "**Instructions:**\n\n"
                    "1. Select the zone where the client is located\n"
                    "2. Set collection duration and interval\n"
                    "3. Click 'Start Collection'\n"
                    "4. Keep the client stationary during collection"
                )
            
            if st.button("🔴 Start Collection", type="primary"):
                zone_id = next((z['id'] for z in zones if z['name'] == selected_zone), None)
                
                if zone_id:
                    with st.spinner(f"Collecting data for {duration} seconds..."):
                        data = st.session_state.collector.collect_live_data(duration=duration, interval=interval)
                        
                        if data is not None and len(data) > 0:
                            st.success(f"✅ Collected {len(data)} samples!")
                            st.dataframe(data.head(), use_container_width=True)
                            
                            # Save to database
                            st.session_state.db.add_training_data(zone_id, data)
                            st.success(f"✅ Data saved to zone '{selected_zone}'")
                        else:
                            st.error("❌ Failed to collect data. Check Radxa connection!")
        
        with tab2:
            st.subheader("Import Training Data from CSV")
            
            selected_zone = st.selectbox(
                "Select Zone",
                options=[z['name'] for z in zones],
                key="import_zone"
            )
            
            uploaded_file = st.file_uploader("Choose CSV file", type=['csv'])
            
            if uploaded_file is not None:
                try:
                    data = pd.read_csv(uploaded_file)
                    st.write(f"Preview ({len(data)} rows):")
                    st.dataframe(data.head(10), use_container_width=True)
                    
                    if st.button("Import Data"):
                        zone_id = next((z['id'] for z in zones if z['name'] == selected_zone), None)
                        st.session_state.db.add_training_data(zone_id, data)
                        st.success(f"✅ Imported {len(data)} samples to zone '{selected_zone}'")
                except Exception as e:
                    st.error(f"Error reading CSV: {e}")
        
        with tab3:
            st.subheader("Training Data Summary")
            
            summary = st.session_state.db.get_training_summary()
            
            if len(summary) > 0:
                st.dataframe(summary, use_container_width=True)
                
                # Visualize data distribution
                fig = px.pie(
                    summary,
                    values='sample_count',
                    names='zone_name',
                    title='Training Data Distribution',
                    color='zone_name',
                    color_discrete_map={row['zone_name']: row['color'] for _, row in summary.iterrows()}
                )
                fig.update_layout(font=dict(family="sans-serif"))
                st.plotly_chart(fig, use_container_width=True)
                
                # Clear data option
                st.markdown("---")
                if st.button("🗑️ Clear All Training Data", type="secondary"):
                    if st.checkbox("I understand this will delete all training data"):
                        st.session_state.db.clear_training_data()
                        st.success("Training data cleared!")
                        st.rerun()
            else:
                st.info("No training data available yet")

# ============================================================================
# Model Training Page
# ============================================================================
elif page == "🤖 Model Training":
    st.title("🤖 Model Training")
    st.markdown("---")
    
    training_data = st.session_state.db.get_training_data()
    
    if len(training_data) < 10:
        st.warning("⚠️ Need at least 10 training samples. Please collect more data!")
    else:
        tab1, tab2, tab3 = st.tabs(["⚙️ Train New Model", "📊 Model Evaluation", "💾 Saved Models"])
        
        with tab1:
            st.subheader("Train New Model")
            
            col1, col2 = st.columns(2)
            
            with col1:
                model_name = st.text_input(
                    "Model Name",
                    value=f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                
                algorithm = st.selectbox(
                    "Algorithm",
                    ["random_forest", "gradient_boosting", "svm", "knn"],
                    format_func=lambda x: {
                        'random_forest': 'Random Forest',
                        'gradient_boosting': 'Gradient Boosting',
                        'svm': 'Support Vector Machine',
                        'knn': 'K-Nearest Neighbors'
                    }[x]
                )
                
                test_size = st.slider("Test Set Size", 0.1, 0.4, 0.2, 0.05)
            
            with col2:
                st.write("**Select Features:**")
                available_features = get_available_features()
                default_features = get_default_features()
                
                selected_features = st.multiselect(
                    "Features to use",
                    options=available_features,
                    default=default_features
                )
            
            if st.button("🚀 Train Model", type="primary"):
                if len(selected_features) == 0:
                    st.error("Please select at least one feature!")
                else:
                    with st.spinner("Training model..."):
                        try:
                            # Get zones
                            zones = st.session_state.db.get_zones()
                            zone_id_to_name = {z['id']: z['name'] for z in zones}
                            
                            # Prepare data
                            training_data['zone_name'] = training_data['zone_id'].map(zone_id_to_name)
                            
                            # Train model
                            model = WiFiPositioningModel()
                            X = model.prepare_features(training_data, selected_features)
                            y = training_data['zone_name']
                            
                            results = model.train(X, y, algorithm=algorithm, test_size=test_size)
                            
                            # Save model
                            model_data, scaler_data = model.serialize()
                            st.session_state.db.save_model(
                                name=model_name,
                                algorithm=algorithm,
                                features=model.features,
                                model_data=model_data,
                                scaler_data=scaler_data,
                                accuracy=results['accuracy'],
                                f1_score=results['f1_score'],
                                training_samples=results['n_samples'],
                                metadata=results
                            )
                            
                            st.session_state.model = model
                            st.success(f"✅ Model trained successfully!")
                            
                            # Display results
                            st.markdown("---")
                            st.subheader("Training Results")
                            
                            col1, col2, col3, col4 = st.columns(4)
                            col1.metric("Accuracy", f"{results['accuracy']*100:.2f}%")
                            col2.metric("F1 Score", f"{results['f1_score']:.3f}")
                            col3.metric("Train Accuracy", f"{results['train_accuracy']*100:.2f}%")
                            col4.metric("CV Score", f"{results['cv_mean']*100:.2f}% ± {results['cv_std']*100:.2f}%")
                            
                            # Feature importance
                            if results['feature_importance']:
                                st.subheader("Feature Importance")
                                feat_df = pd.DataFrame({
                                    'Feature': list(results['feature_importance'].keys()),
                                    'Importance': list(results['feature_importance'].values())
                                })
                                fig = px.bar(feat_df, x='Importance', y='Feature', orientation='h')
                                fig.update_layout(font=dict(family="sans-serif"))
                                st.plotly_chart(fig, use_container_width=True)
                            
                        except Exception as e:
                            st.error(f"Error training model: {e}")
                            import traceback
                            st.code(traceback.format_exc())
        
        with tab2:
            st.subheader("Model Evaluation")
            
            active_model_info = st.session_state.db.get_active_model()
            
            if active_model_info:
                st.write(f"**Active Model:** {active_model_info['name']}")
                st.write(f"**Algorithm:** {active_model_info['algorithm']}")
                st.write(f"**Training Samples:** {active_model_info['training_samples']}")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Accuracy", f"{active_model_info['accuracy']*100:.2f}%")
                col2.metric("F1 Score", f"{active_model_info['f1_score']:.3f}")
                col3.metric("Features", len(active_model_info['features']))
                
                # Load metadata
                metadata = active_model_info['metadata']
                
                if 'confusion_matrix' in metadata:
                    st.subheader("Confusion Matrix")
                    conf_matrix = np.array(metadata['confusion_matrix'])
                    zone_labels = list(metadata['zone_mapping'].values())
                    
                    fig = px.imshow(
                        conf_matrix,
                        x=zone_labels,
                        y=zone_labels,
                        labels=dict(x="Predicted", y="Actual"),
                        color_continuous_scale="Blues",
                        text_auto=True
                    )
                    fig.update_layout(font=dict(family="sans-serif"))
                    st.plotly_chart(fig, use_container_width=True)
                
                if 'classification_report' in metadata:
                    st.subheader("Classification Report")
                    report_df = pd.DataFrame(metadata['classification_report']).transpose()
                    st.dataframe(report_df, use_container_width=True)
            else:
                st.info("No active model. Train a model first!")
        
        with tab3:
            st.subheader("Saved Models")
            
            models = st.session_state.db.get_all_models()
            
            if len(models) > 0:
                for model in models:
                    col1, col2, col3 = st.columns([3, 1, 1])
                    
                    with col1:
                        status = "🟢 Active" if model['is_active'] else "⚪ Inactive"
                        st.write(f"**{model['name']}** {status}")
                        st.write(f"Algorithm: {model['algorithm']} | Accuracy: {model['accuracy']*100:.2f}% | Samples: {model['training_samples']}")
                    
                    with col2:
                        if not model['is_active']:
                            if st.button("Activate", key=f"activate_{model['id']}"):
                                st.session_state.db.activate_model(model['id'])
                                st.rerun()
                    
                    st.markdown("---")
            else:
                st.info("No models saved yet")

# ============================================================================
# Live Prediction Page
# ============================================================================
elif page == "🎯 Live Prediction":
    st.title("🎯 Live Zone Prediction")
    st.markdown("---")
    
    active_model_info = st.session_state.db.get_active_model()
    
    if not active_model_info:
        st.warning("⚠️ No active model. Please train a model first!")
    else:
        # Load model
        if st.session_state.model is None:
            st.session_state.model = WiFiPositioningModel.deserialize(
                active_model_info['model_data'],
                active_model_info['scaler_data']
            )
        
        st.write(f"**Active Model:** {active_model_info['name']}")
        st.write(f"**Accuracy:** {active_model_info['accuracy']*100:.2f}%")
        
        tab1, tab2 = st.tabs(["🔴 Real-time Prediction", "📊 Prediction History"])
        
        with tab1:
            st.subheader("Real-time Zone Prediction")
            
            col1, col2 = st.columns([2, 1])
            
            with col2:
                prediction_interval = st.number_input("Update Interval (seconds)", 1, 10, 3)
                
                if 'predicting' not in st.session_state:
                    st.session_state.predicting = False
                
                if st.button("▶️ Start Prediction" if not st.session_state.predicting else "⏸️ Stop Prediction"):
                    st.session_state.predicting = not st.session_state.predicting
            
            with col1:
                prediction_placeholder = st.empty()
                layout_placeholder = st.empty()
            
            # Prediction loop
            if st.session_state.predicting:
                while st.session_state.predicting:
                    # Collect live data
                    data = st.session_state.collector.collect_live_data(duration=2, interval=0.5)
                    
                    if data is not None and len(data) > 0:
                        # Get latest sample
                        latest = data.iloc[-1]
                        
                        # Prepare features
                        features = {f: latest.get(f, 0) for f in st.session_state.model.features}
                        
                        # Predict
                        predicted_zone_idx, confidence, all_probs = st.session_state.model.predict_single(features)
                        
                        # Get zone info
                        reverse_mapping = {idx: zone for zone, idx in st.session_state.model.zone_mapping.items()}
                        predicted_zone_name = reverse_mapping[predicted_zone_idx]
                        zones = st.session_state.db.get_zones()
                        predicted_zone_info = next((z for z in zones if z['name'] == predicted_zone_name), None)
                        
                        # Save prediction
                        if predicted_zone_info:
                            st.session_state.db.save_prediction(
                                model_id=active_model_info['id'],
                                mac_address=latest.get('mac_address', 'unknown'),
                                predicted_zone_id=predicted_zone_info['id'],
                                confidence=confidence,
                                signal_dbm=latest.get('signal_dbm', 0),
                                signal_avg_dbm=latest.get('signal_avg_dbm', 0)
                            )
                        
                        # Display prediction
                        with prediction_placeholder.container():
                            st.markdown(f"### Predicted Zone: **{predicted_zone_name}**")
                            st.metric("Confidence", f"{confidence*100:.1f}%")
                            st.write(f"Signal: {latest.get('signal_dbm', 'N/A')} dBm")
                            
                            # Show probabilities
                            prob_df = pd.DataFrame({
                                'Zone': list(all_probs.keys()),
                                'Probability': [v*100 for v in all_probs.values()]
                            }).sort_values('Probability', ascending=False)
                            
                            fig = px.bar(prob_df, x='Zone', y='Probability',
                                        title="Zone Probabilities")
                            fig.update_layout(font=dict(family="sans-serif"))
                            st.plotly_chart(fig, use_container_width=True)
                        
                        # Display layout
                        with layout_placeholder.container():
                            zones = st.session_state.db.get_zones()
                            fig = go.Figure()
                            
                            # Room boundary
                            fig.add_shape(
                                type="rect",
                                x0=0, y0=0, x1=1, y1=1,
                                line=dict(color="black", width=2)
                            )
                            
                            # Zones
                            for zone in zones:
                                opacity = 0.8 if zone['name'] == predicted_zone_name else 0.3
                                fig.add_shape(
                                    type="rect",
                                    x0=zone['x_min'], y0=zone['y_min'],
                                    x1=zone['x_max'], y1=zone['y_max'],
                                    fillcolor=zone['color'],
                                    opacity=opacity,
                                    line=dict(color=zone['color'], width=2)
                                )
                                
                                center_x = (zone['x_min'] + zone['x_max']) / 2
                                center_y = (zone['y_min'] + zone['y_max']) / 2
                                fig.add_annotation(
                                    x=center_x, y=center_y,
                                    text=zone['name'],
                                    showarrow=False,
                                    font=dict(size=14, color="black", family="sans-serif")
                                )
                            
                            fig.update_layout(
                                xaxis=dict(range=[0, 1], showgrid=True),
                                yaxis=dict(range=[0, 1], showgrid=True),
                                height=500,
                                title="Current Location",
                                font=dict(family="sans-serif")
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                    
                    time.sleep(prediction_interval)
                    
                    if not st.session_state.predicting:
                        break
        
        with tab2:
            st.subheader("Prediction History")
            
            predictions = st.session_state.db.get_predictions(limit=50)
            
            if len(predictions) > 0:
                st.dataframe(predictions, use_container_width=True)
                
                # Visualization
                fig = px.scatter(
                    predictions,
                    x='timestamp',
                    y='signal_dbm',
                    color='predicted_zone',
                    size='confidence',
                    title="Prediction Timeline"
                )
                fig.update_layout(font=dict(family="sans-serif"))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No predictions yet")

# Footer
st.sidebar.markdown("---")
st.sidebar.info(
    "**WiFi Indoor Positioning System**\n\n"
    "Train ML models to predict client location\n"
    "based on WiFi signal metrics"
)
