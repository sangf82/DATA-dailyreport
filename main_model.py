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
                 back_range: int = 0, 
                 forward_range: int = 0,
                 forecast_range: int = 0):
        self.df = df
        self.date_col = date_col
        self.metric_col = metric_col
        self.back_range = back_range
        self.forward_range = forward_range
        self.forecast_range = forecast_range

    def detect_stl_anomalies(self, 
                             type: str, 
                             start, 
                             end, 
                             threshold: float = 2.5, 
                             file_path: str = "anomalies.csv", 
                             save: bool = False):
        
        anomaly_data = self.df[self.df['software_product'] == type].copy()
        
        if anomaly_data.empty:
            raise ValueError("DataFrame is empty. Please provide a valid DataFrame.")
        if self.date_col not in anomaly_data.columns or self.metric_col not in anomaly_data.columns:
            raise ValueError(f"Columns {self.date_col} or {self.metric_col} not found in DataFrame.")
        
        anomaly_data[self.date_col] = pd.to_datetime(anomaly_data[self.date_col])
        
        if start:
            anomaly_data = anomaly_data[anomaly_data[self.date_col] >= pd.to_datetime(start)]
        if end:
            anomaly_data = anomaly_data[anomaly_data[self.date_col] <= pd.to_datetime(end)]
            
        if anomaly_data.empty:
            raise ValueError("No data remaining after applying date filters")

        if anomaly_data.duplicated(subset=[self.date_col]).any():
            anomaly_data = anomaly_data.groupby(self.date_col).sum().reset_index()
            
        anomaly_data = anomaly_data.sort_values(by=self.date_col)
        ts = anomaly_data.set_index(self.date_col)[self.metric_col].ffill().bfill()
        
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
                stl = STL(ts, period=7, seasonal=15, trend=None, robust=True, seasonal_deg=1, trend_deg=1, low_pass_deg=1)
                result = stl.fit()
                trend, seasonal, residual = result.trend, result.seasonal, result.resid
            except Exception as e:
                print(f"[Warning] STL Error: {e}")
                trend = ts.rolling(7, center=True).mean().fillna(ts.mean())
                seasonal = pd.Series(0, index=ts.index)
                residual = (ts - trend).fillna(0)
            
            res_mean, res_std = residual.mean(), residual.std()
            if res_std < 1e-10:
                res_std = ts.std() * 0.1
                
            upper = res_mean + threshold * res_std
            lower = res_mean - threshold * res_std
            anomalies = (residual > upper) | (residual < lower)
            
            result_df = pd.DataFrame({
                'date': ts.index,
                'count(trend)': trend.values,
                'seasonal': seasonal.values,
                'residual': residual.values,
                'anomaly': anomalies.astype(int).values,
                'threshold_upper': upper,
                'threshold_lower': lower
            }).reset_index(drop=True)
            
        if save:
            name, ext = file_path.rsplit('.', 1)
            file_path = f"{name}_{pd.Timestamp.now().strftime('%Y%m%d')}.{ext}"
            result_df.to_csv(file_path, index=False)
            print(f"Anomaly detection results saved to {file_path}")
            
        return result_df
    
    def forecast_with_prophet(self,
                          type: str,
                          start: str,
                          end: str,
                          file_path: str = "forecast.csv",
                          save: bool = False):
    
        if self.df.empty:
            raise ValueError("Input dataframe is empty")
        
        if self.date_col not in self.df.columns or self.metric_col not in self.df.columns:
            raise ValueError(f"Columns {self.date_col} or {self.metric_col} not found in DataFrame.")

        forecast_data = self.df[self.df['software_product'] == type].copy()
        forecast_data[self.date_col] = pd.to_datetime(forecast_data[self.date_col])
        forecast_data[self.metric_col] = forecast_data[self.metric_col].ffill().bfill()
        
        if start:
            forecast_data = forecast_data[forecast_data[self.date_col] >= pd.to_datetime(start)]
        if end:
            forecast_data = forecast_data[forecast_data[self.date_col] <= pd.to_datetime(end)]
            
        if forecast_data.empty:
            raise ValueError("No data remaining after applying date filters")
        if len(forecast_data) < 30:
            raise ValueError("Not enough data points for forecasting. Minimum is 30.")
        
        # FIXED: Use 'ds' and 'y' column names for Prophet
        prophet_data = forecast_data.rename(columns={self.date_col: 'ds', self.metric_col: 'y'})

        #========== Training Prophet Model ==========#
        self.model = Prophet(
            # Growth parameters
            growth='linear',                    # Linear growth for merchant counts
            # Seasonality parameters
            yearly_seasonality=True,            # Annual business cycles
            weekly_seasonality=True,            # Weekly business patterns
            daily_seasonality=False,            # Not needed for daily aggregated data
            # Advanced seasonality settings
            seasonality_mode='additive',        # Additive seasonality for merchant data
            seasonality_prior_scale=15.0,       # Higher flexibility for seasonality (default: 10)
            # Trend parameters
            changepoint_prior_scale=0.08,       # Moderate trend flexibility (default: 0.05)
            changepoint_range=0.9,              # Consider changepoints in 90% of data
            n_changepoints=35,                  # More changepoints for better trend capture
            # Holiday effects
            holidays_prior_scale=15.0,          # Higher holiday impact
            # Uncertainty and intervals
            interval_width=0.90,                # 90% confidence intervals
            uncertainty_samples=1500,           # More samples for better uncertainty
            # Optimization
            mcmc_samples=0,                     # Use MAP estimation (faster)
            stan_backend=None                   # Use default cmdstan
        )
        
        # Add custom seasonalities for business patterns
        # Monthly seasonality (business cycles, promotions)
        self.model.add_seasonality(
            name='monthly',
            period=30.5,
            fourier_order=8,
            prior_scale=12.0
        )
        # Quarterly seasonality (quarterly business reporting)
        self.model.add_seasonality(
            name='quarterly',
            period=91.25,
            fourier_order=6,
            prior_scale=10.0
        )
        # Semi-annual seasonality (bi-annual business cycles)
        self.model.add_seasonality(
            name='semi_annual',
            period=182.5,
            fourier_order=4,
            prior_scale=8.0
        )
        
        # FIXED: Use 'ds' column name for holidays
        vn_holidays = pd.DataFrame({
            'holiday': 'vn_national_holidays',
            'ds': pd.to_datetime([  # Changed from 'date' to 'ds'
                # Tết 2024: Feb 8–14
                '2024-02-08', '2024-04-18', '2024-04-30', '2024-05-01', '2024-09-02',
                # Tết 2025: Jan 28–Feb 3 (example)
                '2025-01-28', '2025-04-07', '2025-04-30', '2025-05-01', '2025-09-02',
                # Tết 2026: Feb 16–22 (example)
                '2026-02-16', '2026-04-26', '2026-04-30', '2026-05-01', '2026-09-02',
            ]),
            'lower_window': -2,  # Extend range for impact buffer
            'upper_window': 2,
        })

        # Common promotional periods in Vietnam (e.g. Black Friday, 12.12)
        vn_promos = pd.DataFrame({
            'holiday': 'vn_promotions',
            'ds': pd.to_datetime([  # Changed from 'date' to 'ds'
                '2024-11-29', '2024-12-12',
                '2025-11-28', '2025-12-12',
                '2026-11-27', '2026-12-12'
            ]),
            'lower_window': -3,
            'upper_window': 7,
        })

        # Combine into single holiday table for Prophet
        all_holidays = pd.concat([vn_holidays, vn_promos], ignore_index=True)
        self.model.holidays = all_holidays

        # FIXED: Fit with correct column names
        self.model.fit(prophet_data)

        #========== Predict Future Trends ==========#
        # Create future dataframe with business day frequency for better predictions
        future = self.model.make_future_dataframe(
            periods=self.forecast_range, 
            freq='D',
            include_history=True
        )
        
        # Generate forecast
        forecast = self.model.predict(future)
        forecast['yhat'] = forecast['yhat'].clip(lower=0)
        forecast['yhat_lower'] = forecast['yhat_lower'].clip(lower=0)
        forecast['yhat_upper'] = forecast['yhat_upper'].clip(lower=0)
        
        # FIXED: Use 'ds' for merging and include correct columns
        try:
            cols = ['ds', 'yhat', 'yhat_lower', 'yhat_upper', 'trend', 'weekly', 'yearly', 'monthly', 'quarterly', 'semi_annual']
            forecast_df = forecast[cols].merge(prophet_data, on='ds', how='left')
        except KeyError:
            # Fallback if custom seasonalities don't exist
            cols = ['ds', 'yhat', 'yhat_lower', 'yhat_upper', 'trend', 'weekly', 'yearly']
            forecast_df = forecast[cols].merge(prophet_data, on='ds', how='left')
        
        # Calculate additional metrics
        forecast_df['forecast_date'] = pd.Timestamp.now()
        forecast_df['is_forecast'] = forecast_df['y'].isna()
        forecast_df['confidence_width'] = forecast_df['yhat_upper'] - forecast_df['yhat_lower']
        
        # Add performance metrics for historical data
        historical_data = forecast_df[~forecast_df['is_forecast']].copy()
        if len(historical_data) > 0:
            historical_data['residual'] = historical_data['y'] - historical_data['yhat']
            historical_data['abs_error'] = abs(historical_data['residual'])
            historical_data['pct_error'] = (historical_data['residual'] / historical_data['y'] * 100).fillna(0)
            
            # Add metrics to forecast_df
            forecast_df = forecast_df.merge(
                historical_data[['ds', 'residual', 'abs_error', 'pct_error']], 
                on='ds', how='left'
            )
        
        # Export to CSV if requested
        if save:
            name, ext = file_path.rsplit('.', 1)
            file_path = f"{name}_{pd.Timestamp.now().strftime('%Y%m%d')}.{ext}"
            forecast_df.to_csv(file_path, index=False)
            print(f"Forecast results exported to: {file_path}")

            # Export model performance summary
            if len(historical_data) > 0:
                summary_filename = file_path.replace('.csv', '_summary.csv')
                summary_stats = pd.DataFrame({
                    'Metric': ['MAE', 'RMSE', 'MAPE', 'Data Points', 'Forecast Points'],
                    'Value': [
                        historical_data['abs_error'].mean(),
                        (historical_data['residual'] ** 2).mean() ** 0.5,
                        abs(historical_data['pct_error']).mean(),
                        len(historical_data),
                        self.forecast_range
                    ]
                })
                summary_stats.to_csv(summary_filename, index=False)
                print(f"Model performance summary exported to: {summary_filename}")

        return forecast_df, self.model
    
    def plot_anomalies_charts():
        pass
    
    def plot_forecast_charts(self):
        pass