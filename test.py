import os
import requests
import pandas as pd
from dotenv import load_dotenv
from main_model import MainModel
from flask import Flask, jsonify
from datetime import datetime, timedelta
from flask_apscheduler import APScheduler

load_dotenv()
app = Flask(__name__)

class Config:
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = 'Asia/Ho_Chi_Minh'
    
app.config.from_object(Config)
scheduler = APScheduler()
scheduler.init_app(app)

def send_report(webhook_url, report):
    try:
        response = requests.post(webhook_url, json=report, timeout=30)
        response.raise_for_status()
        print(f"Report sent successfully: {response.status_code}")
    except requests.RequestException as e:
        print(f"Error sending report: {e}")

def run_forecast_and_anomaly_detection(client_type, product):
    try:
        raw_df = pd.read_csv('data/import/sample.csv')
        raw_df['txn_date'] = pd.to_datetime(raw_df['txn_date'])
        today = pd.to_datetime('today').normalize()
        newest_date = str(raw_df['txn_date'].max())
        oldest_date = str(raw_df['txn_date'].min())
        td_df = raw_df.copy()
        
        model = MainModel(
            df = td_df,
            date_col = 'txn_date',
            metric_col = client_type,
            prod_type = product,
            back_range = 90,
            forward_range = 60,
            forecast_range = 365
        )
        
        anomalies_data, anomalies_path = model.detect_stl_anomalies(
            start = oldest_date,
            end = newest_date,
            file_path = 'data/output/anomalies.csv',
            save = True
        )

        forecast_data, prophet_model, forecast_path = model.forecast_with_prophet(
            start = oldest_date,
            end = today,
            file_path = 'data/output/forecast.csv',
            save = True
        )
        
        if client_type == 'new_merchant':
            chart_type = 'bar'
        else:
            chart_type = 'line'
            
        forecast_chart_path = model.plot_forecast_charts(
            forecast_df = forecast_data,
            chart_type = chart_type,
            today = today,
            title = f"Forecast for {client_type} - {product}",
            filepath = 'images/forecast.html',
            save = True
        )
        
        if anomalies_data.isin(['1']).any():
            anomalies_chart_path = model.plot_anomalies_charts(
                anomaly_df = anomalies_data,
                chart_type = chart_type,
                today = today,
                title = f"Anomalies for {client_type} - {product}",
                filepath = 'images/anomalies.html',
                save = True
            )

        return td_df, forecast_path, anomalies_path, forecast_chart_path, anomalies_chart_path

    except Exception as e:
        print(f"Error in run_forecast_and_anomaly_detection: {e}")
        return False
    
def format_report(client_type, product):
    try: 
        gg_chat_url = os.getenv('GG_CHAT_WEBHOOK_URL')
        if not gg_chat_url:
            raise ValueError("Google Chat webhook URL is not set in environment variables.")
        
        data, forecast_path, anomalies_path, forecast_chart_path, anomalies_chart_path  = run_forecast_and_anomaly_detection(client_type, product)
        
        if not data:
            return {"error": "Failed to generate report due to data processing error."}
        
        
    
        
        