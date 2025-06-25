import pandas as pd
from main_model import MainModel
import git
import subprocess
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

df = pd.read_csv('data/import/sample.csv')
today = pd.to_datetime('today').normalize()

class GenerateForecastAndAnomalies:
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
                anomalies_chart_path, anomaly_rate = model.plot_anomalies_charts(
                    anomaly_df = anomalies_data,
                    chart_type = chart_type,
                    today = today,
                    title = f"Anomalies for {client_type} - {product}",
                    filepath = 'docs/anomalies.html',
                    save = True
                )  
            else:
                anomalies_chart_path = None

            return td_df, forecast_chart_path, anomalies_chart_path, anomaly_rate

        except Exception as e:
            print(f"Error in run_forecast_and_anomaly_detection: {e}")
            return False
        
    def format_report(main_df, client_type, product):
        try:
            result = GenerateForecastAndAnomalies.run_forecast_and_anomaly_detection(main_df, client_type, product)
            if not result:
                return False
            else:
                data, forecast_chart_path, anomalies_chart_path, anomaly_rate = result

            if client_type == 'new_merchant':
                client_name = 'Khách hàng mới'
            elif client_type == 'active_merchant':
                client_name = 'Khách hàng đang hoạt động'
            
            # Hôm nay
            today_filter = (data['txn_date'] == today) & (data['software_product'] == product)
            client_count_today = data[today_filter][client_type].iloc[0] if len(data[today_filter]) > 0 else 0

            yesterday_filter = (data['txn_date'] == today - pd.Timedelta(days=1)) & (data['software_product'] == product)
            client_count_yesterday = data[yesterday_filter][client_type].iloc[0] if len(data[yesterday_filter]) > 0 else 0
            
            if client_count_today > client_count_yesterday:
                trend = "Tăng"
                diff_day = client_count_today - client_count_yesterday
                rate = diff_day / client_count_yesterday * 100 if client_count_yesterday != 0 else 0
                insight_day = f"{trend} {rate:.2f}% so với ngày hôm qua. (+ {diff_day} khách)"
            elif client_count_today < client_count_yesterday:
                trend = "Giảm"
                diff_day = client_count_yesterday - client_count_today
                rate = diff_day / client_count_yesterday * 100 if client_count_yesterday != 0 else 0
                insight_day = f"{trend} {rate:.2f}% so với ngày hôm qua. (- {diff_day} khách)"
            else:
                insight_day = f"Hôm nay không thay đổi so với ngày hôm qua."

            # Tuần trước
            lastweek_filter = (data['txn_date'] == today - pd.Timedelta(days=7)) & (data['software_product'] == product)
            client_lastweek = data[lastweek_filter][client_type].iloc[0] if len(data[lastweek_filter]) > 0 else 0
            
            if client_count_today > client_lastweek:
                trend = "Tăng"
                diff_week = client_count_today - client_lastweek
                rate = diff_week / client_lastweek * 100 if client_lastweek != 0 else 0
                insight_week = f"{trend} {rate:.2f}% so với tuần trước. (+ {diff_week} khách)"
            elif client_count_today < client_lastweek:
                trend = "Giảm"
                diff_week = client_lastweek - client_count_today
                rate = diff_week / client_lastweek * 100 if client_lastweek != 0 else 0
                insight_week = f"{trend} {rate:.2f}% so với tuần trước. (- {diff_week} khách)"
            else:
                insight_week = f"Hôm nay không thay đổi so với tuần trước."

            # Tháng trước
            lastmonth_filter = (data['txn_date'] == today - pd.Timedelta(days=30)) & (data['software_product'] == product)
            client_lastmonth = data[lastmonth_filter][client_type].iloc[0] if len(data[lastmonth_filter]) > 0 else 0

            if client_count_today > client_lastmonth:
                trend = "Tăng"
                diff_month = client_count_today - client_lastmonth
                rate = diff_month / client_lastmonth * 100 if client_lastmonth != 0 else 0
                insight_month = f"{trend} {rate:.2f}% so với tháng trước. (+ {diff_month} khách)"
            elif client_count_today < client_lastmonth:
                trend = "Giảm"
                diff_month = client_lastmonth - client_count_today
                rate = diff_month / client_lastmonth * 100 if client_lastmonth != 0 else 0
                insight_month = f"{trend} {rate:.2f}% so với tháng trước. (- {diff_month} khách)"
            else:
                insight_month = f"Hôm nay không thay đổi so với tháng trước."
                
            # Tỉ lệ bất thường
            if anomaly_rate is not None:
                if anomaly_rate > 0:
                    anomaly_rate = f"{anomaly_rate:.2f}%"
                else:
                    anomaly_rate = "Không có bất thường"

            insight_day = insight_day.encode('utf-8').decode('utf-8')
            insight_week = insight_week.encode('utf-8').decode('utf-8')
            insight_month = insight_month.encode('utf-8').decode('utf-8')

            return client_count_today, insight_day, insight_week, insight_month, forecast_chart_path, anomalies_chart_path, anomaly_rate

        except Exception as e:
            print(f"Error in format_report: {e}")
            return False

    def setup_git_config():
        try:
            git_user_name = os.getenv('GIT_USER_NAME', '').strip()
            git_user_email = os.getenv('GIT_USER_EMAIL', '').strip()

            subprocess.run(['git', 'config', '--global', 'user.name', git_user_name], check=True)
            subprocess.run(['git', 'config', '--global', 'user.email', git_user_email], check=True)

            print("Git config set successfully.")
        except subprocess.CalledProcessError as e:
            print(f"Error setting up git config: {e}")
            
    def setup_repo_auth():
        try:
            repo_url = os.getenv('GIT_REPO_URL', '').strip()
            git_token = os.getenv('GIT_TOKEN', '').strip()
            git_user = os.getenv('GIT_USER_NAME', '').strip()

            if not repo_url or not git_token:
                print('REPO_URL or GIT_TOKEN is not set in the environment variables.')
                return None

            if 'github.com' in repo_url:
                if repo_url.startswith('https://'):
                    if '@' in repo_url:
                        repo_url = repo_url.split('@')[-1]
                    auth_url = f"https://{git_user or 'git'}:{git_token}@{repo_url[8:]}"
                else:
                    auth_url = repo_url
            else:
                auth_url = repo_url

            return auth_url

        except Exception as e:
            print(f"Error setting up repository authentication: {e}")
            return None

    def commit_and_push(commit_message = None):
        try:
            GenerateForecastAndAnomalies.setup_git_config()

            git_branch = os.getenv('GIT_BRANCH', 'main')
            auth_url = GenerateForecastAndAnomalies.setup_repo_auth()

            if not auth_url:
                print("Authentication URL is not set. Exiting commit and push.")
                return False

            repo = git.Repo('.')

            if not commit_message:
                commit_message = f"Update report {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            if repo.is_dirty(untracked_files=True):
                repo.git.add('.')
                print("Changes detected, preparing to commit...")

                commit = repo.index.commit(commit_message)
                print(f"Changes committed: {commit.hexsha[:8]} - {commit_message}")

                origin = repo.remote('origin')
                origin.set_url(auth_url)
                print(f"Remote URL set to {auth_url}")

                push_refspec = f'HEAD:{git_branch}'
                origin.push(refspec=push_refspec)
                print(f"Changes pushed to branch '{git_branch}'")

                return True

        except Exception as e:
            print(f"Error in commit_and_push: {e}")
            return False

    def take_full_info(df, mode: str = 'test', push: bool = False):
        products = df['software_product'].unique()
        client_types = ['new_merchant', 'active_merchant']
        
        if mode == 'test':
            product = products[0]
            client_type = client_types[0]
            result = GenerateForecastAndAnomalies.format_report(df, client_type, product)
            if result:
                client_count, insight_day, insight_week, insight_month, forecast_chart_path, anomalies_chart_path, anomaly_rate = result
                full_info = {
                    'product': product,
                    'client_type': client_type,
                    'client_count': client_count,
                    'insight_day': insight_day,
                    'insight_week': insight_week,
                    'insight_month': insight_month,
                    'forecast_chart_path': forecast_chart_path,
                    'anomalies_chart_path': anomalies_chart_path,
                    'anomaly_rate': anomaly_rate
                }
                full_info_df = pd.DataFrame([full_info])
                full_info_df.to_json(f'data/report/{product.lower()}_{client_type}_{pd.Timestamp.now().strftime('%Y%m%d')}_report.json', orient='records', force_ascii=False)

        elif mode == 'prod':
            for i in range(len(products)):
                product = products[i]
                full_info = {}
                for j in range(len(client_types)):
                    client_type = client_types[j]
                    if client_type == 'new_merchant':
                        cli = 'new'
                    elif client_type == 'active_merchant':
                        cli = 'active'
                    
                    print(f"Processing {client_type} for {product}...")
                    result = GenerateForecastAndAnomalies.format_report(df, client_type, product)
                    if result:
                        client_count, insight_day, insight_week, insight_month, forecast_chart_path, anomalies_chart_path, anomaly_rate = result
                        info = {
                            f'{cli}_product': product,
                            f'{cli}_client_type': client_type,
                            f'{cli}_client_count': client_count,
                            f'{cli}_insight_day': insight_day,
                            f'{cli}_insight_week': insight_week,
                            f'{cli}_insight_month': insight_month,
                            f'{cli}_forecast_chart_path': forecast_chart_path,
                            f'{cli}_anomalies_chart_path': anomalies_chart_path,
                            f'{cli}_anomaly_rate': anomaly_rate
                        }
                        full_info.update(info)
                    else:
                        print(f"Failed to process {client_type} for {product}.")
                
                full_info_df = pd.DataFrame([full_info])
                full_info_df.to_json(f'data/report/{product.lower()}_{pd.Timestamp.now().strftime("%Y%m%d")}_report.json', orient='records', force_ascii=False)
            if push:
                GenerateForecastAndAnomalies.commit_and_push()

GenerateForecastAndAnomalies.take_full_info(df, mode = 'prod', push = False)