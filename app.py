from flask import Flask
from flask_apscheduler import APScheduler
from authentication_utils import create_client_with_app_credentials
from google.cloud import chat_v1 as google_chat
from main_model import MainModel
import pandas as pd
import os

app = Flask(__name__)

class Config:
    SCHEDULER_API_ENABLED = True

app.config.from_object(Config())
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

DATA_FILE = "sample.csv"
SPACE_NAME = "spaces/XXX"  # Replace with your space ID

def run_forecast_and_anomaly():
    df = pd.read_csv(DATA_FILE)

    model = MainModel(
        df=df,
        date_col='date',
        metric_col='sales',
        back_range=30,
        forward_range=7,
        forecast_range=7
    )

    # Forecast image
    forecast_img_path = "static/forecast.png"
    model.detect_stl_anomalies(
        threshold=2.0,
        start=None,
        end=None,
        file_path=forecast_img_path,
        save=True
    )

    # Assume anomaly is same image OR generate a separate one
    anomaly_img_path = "static/anomaly.png"
    has_anomaly = os.path.exists(anomaly_img_path)

    send_google_chat_message(forecast_img_path, anomaly_img_path if has_anomaly else None)

def send_google_chat_message(forecast_image, anomaly_image=None):
    client = create_client_with_app_credentials()

    # Create message
    message = google_chat.CreateMessageRequest(
        parent=SPACE_NAME,
        message={
            "text": "📊 *Daily KPI Report*",
            "cards_v2": [{
                "card": {
                    "header": {
                        "title": "📈 Forecast & Anomaly Detection",
                        "subtitle": "Auto-generated daily report"
                    },
                    "sections": [{
                        "header": "📅 Forecast",
                        "widgets": [{
                            "image": {
                                "imageUrl": f"https://your-domain.com/{forecast_image}",
                                "altText": "Forecast Chart"
                            }
                        }]
                    }] + (
                        [{
                            "header": "🚨 Anomalies",
                            "widgets": [{
                                "image": {
                                    "imageUrl": f"https://your-domain.com/{anomaly_image}",
                                    "altText": "Anomaly Chart"
                                }
                            }]
                        }] if anomaly_image else []
                    )
                }
            }]
        }
    )

    response = client.create_message(request=message)
    print("✅ Sent message:", response)

@scheduler.task('cron', id='daily_kpi_report', hour=8, minute=0)
def scheduled_job():
    run_forecast_and_anomaly()

@app.route("/")
def home():
    return "✅ KPI Report Bot Running"

if __name__ == "__main__":
    app.run(port=8080)
