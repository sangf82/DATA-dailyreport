import numpy as np
import pandas as pd
import plotly.io as pio
from prophet import Prophet
from datetime import timedelta
import plotly.graph_objects as go
from statsmodels.tsa.seasonal import STL
from plotly.subplots import make_subplots

class MainModel:
    def __init__(self, 
                 df: pd.DataFrame, 
                 date_col: str, 
                 metric_col: str, 
                 back_range:int, 
                 forward_range: int,
                 forecast_range: int):
        self.df = df
        self.date_col = date_col
        self.metric_col = metric_col
        self.back_range = back_range
        self.forward_range = forward_range
        self.forecast_range = forecast_range
    
    def detect_stl_anomalies(self, threshold: float, start, end, file_path: str, save: bool):
        df = self.df.copy()
        
        if df.empty:
            raise ValueError("DataFrame is empty. Please provide a valid DataFrame.")
        if self.date_col not in df.columns or self.metric_col not in df.columns:
            raise ValueError(f"Columns {self.date_col} or {self.metric_col} not found in DataFrame.")
        
        df[self.date_col] = pd.to_datetime(df[self.date_col])
        
        if start:
            df = df[df[self.date_col] >= pd.to_datetime(start)]
        if end:
            df = df[df[self.date_col] <= pd.to_datetime(end)]
            
        if df.empty:
            raise ValueError("No data remaining after applying date filters")

        if df.duplicated(subset=[self.date_col]).any():
            df = df.groupby(self.date_col).sum().reset_index()
            
        df = df.sort_values(by=self.date_col)
        ts = df.set_index(self.date_col)[self.metric_col].ffill().bfill()
        
        if len(ts) < 20:
            ts_std = ts.std()
            if ts_std < 1e-10:
                ts_std = 1.0
            z = (ts - ts.mean()) / ts_std
            anomalies = z[abs(z) > threshold]
            anomalies_df = pd.DataFrame({
                'date': ts.index,
                'count(trend)': ts.values,
                'seasonal': 0,
                'residual': ts - ts.mean(),
                'anomaly': anomalies.values,
                }).reset_index(drop=True)
        else:
            try:
                stl = STL(ts, )
        