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
        
        if anomalies_data.isin(['1']).any():
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

        return td_df, forecast_path, anomalies_path, forecast_chart_path, anomalies_chart_path

    except Exception as e:
        print(f"Error in run_forecast_and_anomaly_detection: {e}")
        return False
    
def format_report(main_df, client_type, product):
    try: 
        data, forecast_path, anomalies_path, forecast_chart_path, anomalies_chart_path  = run_forecast_and_anomaly_detection(main_df, client_type, product)
        
        # Hôm qua
        client_count_today = data[(data['txn_date'] == today) & 
                   (data['software_product'] == product)][client_type]

        client_count_yesterday = data[(data['txn_date'] == today - pd.Timedelta(days=1)) & 
                   (data['software_product'] == product)][client_type]
        
        if client_count_today > client_count_yesterday:
            trend = "tăng"
            rate = (client_count_today - client_count_yesterday) / client_count_yesterday * 100
            insight_day = f"Số lượng {client_type} hôm nay {trend} {rate:.2f}% so với ngày hôm qua."
        elif client_count_today < client_count_yesterday:
            trend = "giảm"
            rate = (client_count_yesterday - client_count_today) / client_count_yesterday * 100
            insight_day = f"Số lượng {client_type} hôm nay {trend} {rate:.2f}% so với ngày hôm qua."
            
        # Tuần trước
        client_lastweek = data[(data['txn_date'] >= today - pd.Timedelta(days=7)) &
                   (data['txn_date'] < today) &
                   (data['software_product'] == product)][client_type].sum()
        
        if client_count_today > client_lastweek:
            trend = "tăng"
            rate = (client_count_today - client_lastweek) / client_lastweek * 100
            insight_week = f"Số lượng {client_type} hôm nay {trend} {rate:.2f}% so với tuần trước."
        elif client_count_today < client_lastweek:
            trend = "giảm"
            rate = (client_lastweek - client_count_today) / client_lastweek * 100
            insight_week = f"Số lượng {client_type} hôm nay {trend} {rate:.2f}% so với tuần trước."

        # Tháng trước
        client_lastmonth = data[(data['txn_date'] >= today - pd.Timedelta(days=30)) & 
                   (data['txn_date'] < today) & 
                   (data['software_product'] == product)][client_type].sum()
        
        if client_count_today > client_lastmonth:
            trend = "tăng"
            rate = (client_count_today - client_lastmonth) / client_lastmonth * 100
            insight_month = f"Số lượng {client_type} hôm nay {trend} {rate:.2f}% so với tháng trước."
        elif client_count_today < client_lastmonth:
            trend = "giảm"
            rate = (client_lastmonth - client_count_today) / client_lastmonth * 100
            insight_month = f"Số lượng {client_type} hôm nay {trend} {rate:.2f}% so với tháng trước."
            
        

    except Exception as e:
        print(f"Error in format_report: {e}")
        return False