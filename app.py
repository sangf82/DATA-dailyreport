import pandas as pd
from dotenv import load_dotenv
from flask import Flask, jsonify
from datetime import datetime
from message import FinalMessage
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

@scheduler.task('cron', id='forecast_and_anomaly_generation', hour=9, minute=10, max_instances=1)
def forecast_and_anomaly_generation():
    print("Running daily report generation at", datetime.now())
    try:
        GenerateForecastAndAnomalies.take_full_info(df, mode = 'prod', push = True)
        print("Daily report generation completed successfully")
    except Exception as e:
        print(f"Error in daily report generation: {str(e)}")

@scheduler.task('cron', id='daily_report', hour=9, minute=15, max_instances=1)
def scheduled_daily_report():
    print("Sending daily report at", datetime.now())
    try:
        final_message = FinalMessage()
        final_message.final_message()
        print("Daily report sent successfully")
    except Exception as e:
        print(f"Error sending daily report: {str(e)}")
    
@app.route("/", methods=['GET'])
def home():
    return jsonify({"message": "Daily Report Webhook with Scheduler is running!", "status": "OK"})

@app.route("/start", methods=['GET'])
def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        return jsonify({"message": "Scheduler started successfully!"}), 200
    else:
        return jsonify({"message": "Scheduler is already running!"}), 400

@app.route("/stop", methods=['GET'])
def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        return jsonify({"message": "Scheduler stopped successfully!"}), 200
    else:
        return jsonify({"message": "Scheduler is not running!"}), 400

@app.route("/status", methods=['GET'])
def scheduler_status():
    return jsonify({
        "scheduler_running": scheduler.running,
        "jobs": [{"id": job.id, "next_run": str(job.next_run_time)} for job in scheduler.get_jobs()]
    })

@app.route("/test-report", methods=['GET'])
def test_report():
    """Manual trigger for testing the report generation"""
    try:
        final_message = FinalMessage()
        final_message.final_message()
        return jsonify({"message": "Test report sent successfully!"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to send test report: {str(e)}"}), 500

@app.route("/test-generation", methods=['GET'])
def test_generation():
    """Manual trigger for testing the forecast and anomaly generation"""
    try:
        GenerateForecastAndAnomalies.take_full_info(df, mode = 'prod', push = True)
        return jsonify({"message": "Test generation completed successfully!"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to generate test data: {str(e)}"}), 500

if __name__ == '__main__':
    scheduler.start()
    app.run(host='0.0.0.0', port=8080, debug=True)








