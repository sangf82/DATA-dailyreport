import pandas as pd
from main_model import MainModel

df = pd.read_csv('data/import/sample.csv')
today = pd.to_datetime('today').normalize()

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
            filepath = 'images/forecast.html',
            save = True
        )

        if 'anomaly' in anomalies_data.columns and (anomalies_data['anomaly'].astype(int) == 1).any():
            anomalies_chart_path = model.plot_anomalies_charts(
                anomaly_df = anomalies_data,
                chart_type = chart_type,
                today = today,
                title = f"Anomalies for {client_type} - {product}",
                filepath = 'images/anomalies.html',
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
                
take_full_info(df)