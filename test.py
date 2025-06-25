import os
import git
import requests
import subprocess
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

df = pd.read_csv('data/import/sample.csv')
today = pd.to_datetime('today').normalize()

def send_report(webhook_url, report):
    try:
        response = requests.post(webhook_url, json=report, timeout=30)
        response.raise_for_status()
        print(f"Report sent successfully: {response.status_code}")
    except requests.RequestException as e:
        print(f"Error sending report: {e}")

def run_forecast_and_anomaly_detection(raw_df, client_type, product):
    try:
        raw_df['txn_date'] = pd.to_datetime(raw_df['txn_date'])
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
            filepath = 'docs/forecast.html',
            save = True
        )

        if 'anomaly' in anomalies_data.columns and (anomalies_data['anomaly'].astype(int) == 1).any():
            anomalies_chart_path = model.plot_anomalies_charts(
                anomaly_df = anomalies_data,
                chart_type = chart_type,
                today = today,
                title = f"Anomalies for {client_type} - {product}",
                filepath = 'docs/anomalies.html',
                save = True
            )  
        else:
            anomalies_chart_path = None

        return td_df, forecast_chart_path, anomalies_chart_path

    except Exception as e:
        print(f"Error in run_forecast_and_anomaly_detection: {e}")
        return False
    
def format_report(main_df, client_type, product):
    try:
        result = run_forecast_and_anomaly_detection(main_df, client_type, product)
        if not result:
            return False
        else:
            data, forecast_chart_path, anomalies_chart_path = result
        
        # Hôm nay
        today_filter = (data['txn_date'] == today) & (data['software_product'] == product)
        client_count_today = data[today_filter][client_type].iloc[0] if len(data[today_filter]) > 0 else 0

        yesterday_filter = (data['txn_date'] == today - pd.Timedelta(days=1)) & (data['software_product'] == product)
        client_count_yesterday = data[yesterday_filter][client_type].iloc[0] if len(data[yesterday_filter]) > 0 else 0
        
        if client_count_today > client_count_yesterday:
            trend = "tăng"
            diff_day = client_count_today - client_count_yesterday
            rate = diff_day / client_count_yesterday * 100 if client_count_yesterday != 0 else 0
            insight_day = f"Số lượng {client_type} hôm nay {trend} {rate:.2f}% so với ngày hôm qua. (+ {diff_day} merchants)"
        elif client_count_today < client_count_yesterday:
            trend = "giảm"
            diff_day = client_count_yesterday - client_count_today
            rate = diff_day / client_count_yesterday * 100 if client_count_yesterday != 0 else 0
            insight_day = f"Số lượng {client_type} hôm nay {trend} {rate:.2f}% so với ngày hôm qua. (- {diff_day} merchants)"
        else:
            insight_day = f"Số lượng {client_type} hôm nay không thay đổi so với ngày hôm qua."

        # Tuần trước
        lastweek_filter = (data['txn_date'] == today - pd.Timedelta(days=7)) & (data['software_product'] == product)
        client_lastweek = data[lastweek_filter][client_type].iloc[0] if len(data[lastweek_filter]) > 0 else 0
        
        if client_count_today > client_lastweek:
            trend = "tăng"
            diff_week = client_count_today - client_lastweek
            rate = diff_week / client_lastweek * 100 if client_lastweek != 0 else 0
            insight_week = f"Số lượng {client_type} hôm nay {trend} {rate:.2f}% so với tuần trước. (+ {diff_week} merchants)"
        elif client_count_today < client_lastweek:
            trend = "giảm"
            diff_week = client_lastweek - client_count_today
            rate = diff_week / client_lastweek * 100 if client_lastweek != 0 else 0
            insight_week = f"Số lượng {client_type} hôm nay {trend} {rate:.2f}% so với tuần trước. (- {diff_week} merchants)"
        else:
            insight_week = f"Số lượng {client_type} hôm nay không thay đổi so với tuần trước."

        # Tháng trước
        lastmonth_filter = (data['txn_date'] == today - pd.Timedelta(days=30)) & (data['software_product'] == product)
        client_lastmonth = data[lastmonth_filter][client_type].iloc[0] if len(data[lastmonth_filter]) > 0 else 0

        if client_count_today > client_lastmonth:
            trend = "tăng"
            diff_month = client_count_today - client_lastmonth
            rate = diff_month / client_lastmonth * 100 if client_lastmonth != 0 else 0
            insight_month = f"Số lượng {client_type} hôm nay {trend} {rate:.2f}% so với tháng trước. (+ {diff_month} merchants)"
        elif client_count_today < client_lastmonth:
            trend = "giảm"
            diff_month = client_lastmonth - client_count_today
            rate = diff_month / client_lastmonth * 100 if client_lastmonth != 0 else 0
            insight_month = f"Số lượng {client_type} hôm nay {trend} {rate:.2f}% so với tháng trước. (- {diff_month} merchants)"
        else:
            insight_month = f"Số lượng {client_type} hôm nay không thay đổi so với tháng trước."

        return insight_day, insight_week, insight_month, forecast_chart_path, anomalies_chart_path
            
    except Exception as e:
        print(f"Error in format_report: {e}")
        return False

def setup_git_config():
    try:
        subprocess.run(['git', 'config', '--global', 'user.name', 'sangf82'], check=True)
        subprocess.run(['git', 'config', '--global', 'user.email', 'sluongtran@gmail.com'], check=True)
        print("Git config set successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error setting up git config: {e}")

def commit_and_push(commit_message = None):
    try:
        setup_git_config()
        repo = git.Repo('.')
        
        if not commit_message:
            commit_message = f"Update report {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        if repo.is_dirty(untracked_files=True):
            repo.git.add('.')
            
            commit = repo.index.commit(commit_message)
            print(f"Changes committed: {commit.hexsha[:8]} - {commit_message}")
            
            origin = repo.remote('origin')
            origin.push(refspec='HEAD:sang.lt_daily_report')
            print(f"Changes pushed to branch 'sang.lt_daily_report'")
            
            return True
        
    except Exception as e:
        print(f"Error in commit_and_push: {e}")
        return False
  
def take_full_info(df):
    products = df['software_product'].unique()
    client_types = ['new_merchant', 'active_merchant']
    
    for i in range(len(products)):
        product = products[i]
        for j in range(len(client_types)):
            client_type = client_types[j]
            print(f"Processing {client_type} for {product}...")
            result = format_report(df, client_type, product)
            if result:
                insight_day, insight_week, insight_month, forecast_chart_path, anomalies_chart_path = result
                full_info = {
                    'product': product,
                    'client_type': client_type,
                    'insight_day': insight_day,
                    'insight_week': insight_week,
                    'insight_month': insight_month,
                    'forecast_chart_path': forecast_chart_path,
                    'anomalies_chart_path': anomalies_chart_path
                }
                
                full_info_df = pd.DataFrame([full_info])
                full_info_df.to_json(f'data/report/{product}_{client_type}_report.json', orient='records', lines=True)
            else:
                print(f"Failed to process {client_type} for {product}.")
    commit_and_push()
           
def final_message():
    url = os.getenv('WEBHOOK_URL')
    reports = os.listdir('data/report')
    images = os.listdir('docs')
    pass

@scheduler.task('cron', id = 'daily_report', hour = 7, minute = 30)
def forecast_and_anomaly_generation():
    print("Running daily report generation at", datetime.now())
    take_full_info(df)

@scheduler.task('cron', id = 'daily_report', hour = 8, minute = 0)
def scheduled_daily_report():
    print("Sending daily report at", datetime.now())
    final_message()
    
@app.route("/", methods=['GET'])
def home():
    return  jsonify({"message": "Daily Report Webhook with Scheduler is running!", "status": "OK"})




        
        
    
        
        