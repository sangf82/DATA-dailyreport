from flask import Flask, request, jsonify
from flask_apscheduler import APScheduler
import os
import pandas as pd
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from main_model import MainModel

load_dotenv()

app = Flask(__name__)

# Configure scheduler
class Config:
    SCHEDULER_API_ENABLED = True
    SCHEDULER_TIMEZONE = "Asia/Ho_Chi_Minh"

app.config.from_object(Config())
scheduler = APScheduler()
scheduler.init_app(app)

def send_message(webhook_url, message):
    """Send message to Google Chat"""
    try:
        response = requests.post(webhook_url, json=message, timeout=30)
        response.raise_for_status()
        print(f"✅ Message sent successfully: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to send message: {e}")

def run_forecast_and_anomaly_detection():
    """Run forecasting and anomaly detection"""
    try:
        print("🔮 Starting forecast and anomaly detection...")
        
        # Load data
        df = pd.read_csv('data/import/sample.csv')
        df['txn_date'] = pd.to_datetime(df['txn_date'])
        today = pd.to_datetime('today').normalize()
        newest_date = str(df['txn_date'].max())
        oldest_date = str(df['txn_date'].min())
        td_df = df.copy()

        # Active merchant analysis
        print("📊 Running active merchant analysis...")
        active_model = MainModel(
            df=td_df, 
            date_col='txn_date', 
            metric_col='active_merchant',
            prod_type='Retail',
            back_range=90,
            forward_range=60,
            forecast_range=365
        )

        anomalies_active = active_model.detect_stl_anomalies( 
            start=oldest_date, 
            end=newest_date,
            file_path=f'data/output/anomalies.csv',  
            save=True
        )

        forecast_active, prophet_model_active = active_model.forecast_with_prophet(
            start=oldest_date,
            end=today,
            file_path=f'data/output/forecast.csv',
            save=True
        )

        active_model.plot_forecast_charts(
            forecast_df=forecast_active,
            chart_type='line',
            filepath=f'images/forecast.html',
            save=True,
        )

        active_model.plot_anomalies_charts(
            anomaly_df=anomalies_active,
            today=today,
            chart_type='line',
            save=True,
            filepath=f'images/anomalies.html'
        )

        # New merchant analysis
        print("🆕 Running new merchant analysis...")
        new_model = MainModel(
            df=td_df, 
            date_col='txn_date', 
            metric_col='new_merchant',
            prod_type='Retail',
            back_range=90,
            forward_range=60,
            forecast_range=365
        )

        anomalies_new = new_model.detect_stl_anomalies( 
            start=oldest_date, 
            end=newest_date,
            file_path=f'data/output/anomalies.csv',  
            save=True
        )

        forecast_new, prophet_model_new = new_model.forecast_with_prophet(
            start=oldest_date,
            end=today,
            file_path=f'data/output/forecast.csv',
            save=True
        )

        new_model.plot_forecast_charts(
            forecast_df=forecast_new,
            chart_type='line',
            filepath=f'images/forecast.html',
            save=True,
        )

        new_model.plot_anomalies_charts(
            anomaly_df=anomalies_new,
            today=today,
            chart_type='line',
            save=True,
            filepath=f'images/anomalies.html'
        )

        print("✅ Forecast and anomaly detection completed successfully")
        return True

    except Exception as e:
        print(f"❌ Error in forecast and anomaly detection: {e}")
        return False

def generate_daily_report():
    """Generate and send daily report"""
    try:
        webhook_url = os.getenv("GOOGLE_CHAT_WEBHOOK_URL")
        if not webhook_url:
            print("❌ GOOGLE_CHAT_WEBHOOK_URL not configured")
            return

        # Run forecast first
        forecast_success = run_forecast_and_anomaly_detection()

        # Load data
        data_file_path = "data/import/sample.csv"
        if not os.path.exists(data_file_path):
            print("❌ Data file not found")
            return

        df = pd.read_csv(data_file_path)
        df['txn_date'] = pd.to_datetime(df['txn_date'])
        
        latest_date = df['txn_date'].max()
        previous_date = latest_date - timedelta(days=1)
        
        retail_data = df[df['software_product'] == 'Retail']
        today_data = retail_data[retail_data['txn_date'] == latest_date]
        yesterday_data = retail_data[retail_data['txn_date'] == previous_date]
        
        if today_data.empty:
            print("❌ No data found for latest date")
            return
            
        # Extract metrics
        today_active = today_data['active_merchant'].iloc[0]
        today_new = today_data['new_merchant'].iloc[0]
        
        # Calculate changes
        if not yesterday_data.empty:
            yesterday_active = yesterday_data['active_merchant'].iloc[0]
            yesterday_new = yesterday_data['new_merchant'].iloc[0]
            
            active_change = ((today_active - yesterday_active) / yesterday_active) * 100
            new_change = ((today_new - yesterday_new) / yesterday_new) * 100
            
            active_trend = "tăng" if active_change > 0 else "giảm" if active_change < 0 else "➡️"
            new_trend = "tăng" if new_change > 0 else "giảm" if new_change < 0 else "➡️"
        else:
            active_change = 0
            new_change = 0
            active_trend = "➡️"
            new_trend = "➡️"

        report_date = latest_date.strftime("%d/%m/%Y")
        date_str = datetime.now().strftime('%Y%m%d')
        
        # Check for anomaly files
        anomaly_present = (os.path.exists(f"data/output/anomalies_retail_active_{date_str}.csv") or 
                          os.path.exists(f"data/output/anomalies_retail_new_{date_str}.csv"))

        # Create message
        card_message = {
            "cardsV2": [
                {
                    "card": {
                        "header": {
                            "title": "📊 Daily Retail Report",
                            "subtitle": report_date
                        },
                        "sections": [
                            {
                                "widgets": [
                                    {
                                        "textParagraph": {
                                            "text": f"🏪 <b>Active:</b> {today_active:,} {active_trend} {abs(active_change):.1f}%\n🆕 <b>New:</b> {today_new:,} {new_trend} {abs(new_change):.1f}%"
                                        }
                                    }
                                ]
                            },
                            {
                                "widgets": [
                                    {
                                        "buttonList": {
                                            "buttons": [
                                                {
                                                    "text": "📊 Forecast",
                                                    "onClick": {
                                                        "openLink": {
                                                            "url": f"https://sangf82.github.io/divevin-swimmingclub/images/forecast_retail_active_line_{date_str}.html"
                                                        }
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                }
            ]
        }

        # Add anomaly button if anomalies detected
        if anomaly_present:
            anomaly_button = {
                "text": "🚨 Anomalies",
                "onClick": {
                    "openLink": {
                        "url": f"https://sangf82.github.io/divevin-swimmingclub/images/anomalies_retail_active_line_{date_str}.html"
                    }
                }
            }
            card_message["cardsV2"][0]["card"]["sections"][1]["widgets"][0]["buttonList"]["buttons"].append(anomaly_button)

        send_message(webhook_url, card_message)
        print(f"✅ Scheduled daily report sent at {datetime.now()}")
        
    except Exception as e:
        print(f"❌ Error in scheduled report: {e}")

# Scheduled jobs
@scheduler.task('cron', id='daily_report', hour=8, minute=0)
def scheduled_daily_report():
    print(f"🕒 Running scheduled daily report at {datetime.now()}")
    generate_daily_report()

@scheduler.task('cron', id='forecast_generation', hour=7, minute=30)
def scheduled_forecast_generation():
    print(f"🔮 Running scheduled forecast generation at {datetime.now()}")
    run_forecast_and_anomaly_detection()

# Routes
@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "AI Chatbot Webhook with Scheduler is running!", "status": "OK"})

@app.route("/webhook", methods=["POST"])
def webhook():
    generate_daily_report()
    return jsonify({"status": "Manual report sent successfully."})

@app.route("/forecast", methods=["POST"])
def run_forecast():
    success = run_forecast_and_anomaly_detection()
    return jsonify({"status": "Forecast completed successfully." if success else "Forecast failed."})

@app.route("/scheduler/jobs", methods=["GET"])
def list_jobs():
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    return jsonify({"jobs": jobs})

@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    try:
        data_exists = os.path.exists("data/import/sample.csv")
        webhook_configured = bool(os.getenv("GOOGLE_CHAT_WEBHOOK_URL"))
        scheduler_running = scheduler.running
        
        os.makedirs('data/output', exist_ok=True)
        os.makedirs('images', exist_ok=True)
        
        status = {
            "status": "healthy" if all([data_exists, webhook_configured, scheduler_running]) else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "checks": {
                "data_file": data_exists,
                "webhook_configured": webhook_configured,
                "scheduler_running": scheduler_running
            }
        }
        
        return jsonify(status), 200 if status["status"] == "healthy" else 503
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    os.makedirs('data/output', exist_ok=True)
    os.makedirs('images', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    
    scheduler.start()
    app.run(host="0.0.0.0", port=8080, debug=True)
