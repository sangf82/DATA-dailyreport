import pandas as pd
from main_model import MainModel

df = pd.read_csv('static/input/sample.csv')

df['txn_date'] = pd.to_datetime(df['txn_date'])
today = pd.to_datetime('today').normalize()
newest_date = str(df['txn_date'].max())
oldest_date = str(df['txn_date'].min())
td_df = df.copy()

model = MainModel(
    df = td_df, 
    date_col='txn_date', 
    metric_col='new_merchant',
    prod_type='Retail',
    back_range=90,
    forward_range=60,
    forecast_range=365)

anomalies_data = model.detect_stl_anomalies( 
    start=oldest_date, 
    end=newest_date,
    file_path='static/output/anomalies.csv',  
    save=True)

forecast_data, prophet_model = model.forecast_with_prophet(
    start=oldest_date,
    end=today,
    file_path='static/output/forecast.csv',
    save=True)

model.plot_forecast_charts(
    forecast_df=forecast_data,
    chart_type='bar',
    filepath='images/forecast.html',
    save=True,
)

model.plot_anomalies_charts(
    anomaly_df=anomalies_data,
    today=today,
    chart_type='bar',
    save=True,
    filepath='images/anomalies.html'
)