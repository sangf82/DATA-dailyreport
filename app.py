import os
import git
import requests
import subprocess
import pandas as pd
from dotenv import load_dotenv
from flask import Flask, jsonify
from datetime import datetime
from flask_apscheduler import APScheduler
from gen_forecast_anomaly import GenerateForecastAndAnomalies

load_dotenv()
app = Flask(__name__)

class Config:
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = 'Asia/Ho_Chi_Minh'
    
app.config.from_object(Config)
scheduler = APScheduler()
scheduler.init_app(app)

df = pd.read_csv('data/import/sample.csv')

def final_message():
    url = os.getenv('WEBHOOK_URL')
    reports = os.listdir('data/report')
    images = os.listdir('docs')
    pass

@scheduler.task('cron', id = 'forecast_and_anomaly_generation', hour = 7, minute = 30)
def forecast_and_anomaly_generation():
    print("Running daily report generation at", datetime.now())
    GenerateForecastAndAnomalies.take_full_info(df)

@scheduler.task('cron', id = 'daily_report', hour = 8, minute = 0)
def scheduled_daily_report():
    print("Sending daily report at", datetime.now())
    final_message()
    
@app.route("/", methods=['GET'])
def home():
    return  jsonify({"message": "Daily Report Webhook with Scheduler is running!", "status": "OK"})




        
        
    
        
        