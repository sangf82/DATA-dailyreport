import pandas as pd
from prophet import Prophet
import plotly.graph_objs as go
import plotly.io as pio
from plotly.subplots import make_subplots
from statsmodels.tsa.seasonal import STL
import numpy as np
from datetime import timedelta

class ForecastAnomalyDetector:
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.model = None
        self.stl = None
    
    def detect_stl_anomalies(self, date_col='txn_date', metric_col='active_merchant',
                             threshold=2.5, period=7, start_date=None, end_date=None, 
                             export_csv=True, csv_filename=None):
        """Detect anomalies using STL decomposition"""
        df = self.data.copy()
        
        # Check if dataframe is empty
        if df.empty:
            raise ValueError("Input dataframe is empty")
        
        # Check if required columns exist
        if date_col not in df.columns:
            raise ValueError(f"Date column '{date_col}' not found in dataframe")
        if metric_col not in df.columns:
            raise ValueError(f"Metric column '{metric_col}' not found in dataframe")
        
        df[date_col] = pd.to_datetime(df[date_col])

        # Filter by date range if specified
        if start_date:
            df = df[df[date_col] >= pd.to_datetime(start_date)]
        if end_date:
            df = df[df[date_col] <= pd.to_datetime(end_date)]
        
        # Check if dataframe is empty after filtering
        if df.empty:
            raise ValueError("No data remaining after applying date filters")

        # Group if duplicate dates
        if df.duplicated(subset=[date_col]).any():
            df = df.groupby(date_col)[metric_col].sum().reset_index()

        df = df.sort_values(date_col)
        ts = df.set_index(date_col)[metric_col].ffill().bfill()

        if len(ts) < 20:
            # fallback Z-score
            ts_std = ts.std()
            if ts_std < 1e-10:  # Handle near-zero standard deviation
                ts_std = 1.0  # Use default value to avoid division by zero
            z = (ts - ts.mean()) / ts_std
            anomalies = np.abs(z) > threshold
            result_df = pd.DataFrame({
                'ds': ts.index,
                'y': ts.values,
                'trend': ts.values,
                'seasonal': 0,
                'residual': ts - ts.mean(),
                'anomaly': anomalies.values,
            }).reset_index(drop=True)
        else:
            try:
                stl = STL(ts, period=period, seasonal=21, robust=True)
                result = stl.fit()
                trend, seasonal, residual = result.trend, result.seasonal, result.resid
            except Exception as e:
                print(f"[Warning] STL error: {e}")
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
                'ds': ts.index,
                'y': ts.values,
                'trend': trend.values,
                'seasonal': seasonal.values,
                'residual': residual.values,
                'anomaly': anomalies.values,
                'residual_threshold_upper': upper,
                'residual_threshold_lower': lower
            }).reset_index(drop=True)

        # Export to CSV if requested
        if export_csv:
            if csv_filename is None:
                csv_filename = f"anomaly_detection_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
            result_df.to_csv(csv_filename, index=False)
            print(f"Anomaly detection results exported to: {csv_filename}")

        return result_df

    def forecast_with_prophet(self, data, date_col='ds', metric_col='y',
                              predict_periods=60, train_start=None, train_end=None,
                              export_csv=True, csv_filename=None):
        """Forecast using Prophet model"""
        if data.empty:
            raise ValueError("Input dataframe is empty")
        
        # Check if required columns exist
        if date_col not in data.columns:
            raise ValueError(f"Date column '{date_col}' not found in dataframe")
        if metric_col not in data.columns:
            raise ValueError(f"Metric column '{metric_col}' not found in dataframe")
        
        df = data.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.rename(columns={date_col: 'ds', metric_col: 'y'})
        df['y'] = df['y'].ffill().bfill()

        # Filter by date range if specified
        if train_start:
            df = df[df['ds'] >= pd.to_datetime(train_start)]
        if train_end:
            df = df[df['ds'] <= pd.to_datetime(train_end)]
        
        # Check if dataframe is empty after filtering
        if df.empty:
            raise ValueError("No data remaining after applying date filters")
        
        # Check if we have enough data points for Prophet
        if len(df) < 2:
            raise ValueError("Prophet requires at least 2 data points for training")

        self.model = Prophet(
            daily_seasonality=True,
            weekly_seasonality=True,
            yearly_seasonality=True
        )
        self.model.fit(df)

        future = self.model.make_future_dataframe(periods=predict_periods, freq='D')
        forecast = self.model.predict(future)

        forecast_df = forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].merge(df, on='ds', how='left')
        
        # Export to CSV if requested
        if export_csv:
            if csv_filename is None:
                csv_filename = f"prophet_forecast_results_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
            forecast_df.to_csv(csv_filename, index=False)
            print(f"Prophet forecast results exported to: {csv_filename}")

        return forecast_df, self.model

    def plot_forecast_line(self, forecast_df, title="Forecast Line Chart", 
                          export_png=True, png_filename=None):
        """Plot forecast results as line chart"""
        fig = go.Figure()

        if 'y' in forecast_df.columns:
            fig.add_trace(go.Scatter(
                x=forecast_df['ds'],
                y=forecast_df['y'],
                name='Actual',
                line=dict(color='blue')
            ))

        fig.add_trace(go.Scatter(
            x=forecast_df['ds'],
            y=forecast_df['yhat'],
            name='Forecast',
            line=dict(color='green')
        ))

        fig.add_trace(go.Scatter(
            x=forecast_df['ds'],
            y=forecast_df['yhat_upper'],
            name='Upper Bound',
            line=dict(color='lightgreen', dash='dot'),
            showlegend=False
        ))

        fig.add_trace(go.Scatter(
            x=forecast_df['ds'],
            y=forecast_df['yhat_lower'],
            name='Lower Bound',
            line=dict(color='lightgreen', dash='dot'),
            fill='tonexty',
            fillcolor='rgba(144,238,144,0.2)',
            showlegend=True
        ))

        fig.update_layout(
            title=title,
            xaxis_title='Date',
            yaxis_title='Value',
            template='plotly_white'
        )

        # Export to PNG if requested
        if export_png:
            if png_filename is None:
                png_filename = f"forecast_chart_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.png"
            try:
                fig.write_image(png_filename, format='png')
                print(f"Forecast chart exported to: {png_filename}")
            except Exception as e:
                print(f"[Warning] PNG export failed: {e}. Install kaleido with 'pip install kaleido'")

        return fig

    def plot_recent_anomalies_bar(self, anomaly_df, days_back=30, title="Recent Anomalies",
                                 export_png=True, png_filename=None):
        """Plot recent anomalies with proper visualization"""
        latest_date = anomaly_df['ds'].max()
        from_date = latest_date - timedelta(days=days_back)

        # Filter recent data
        recent_df = anomaly_df[
            (anomaly_df['ds'] >= from_date) & 
            (anomaly_df['ds'] <= latest_date)
        ].copy()

        # Separate normal and anomaly points
        normal_points = recent_df[~recent_df['anomaly']]
        anomaly_points = recent_df[recent_df['anomaly']]

        fig = go.Figure()

        # Add normal data points
        if len(normal_points) > 0:
            fig.add_trace(go.Bar(
                x=normal_points['ds'],
                y=normal_points['y'],
                name='Normal Data',
                marker_color='lightblue',
                opacity=0.7
            ))

        # Add anomaly points with different color
        if len(anomaly_points) > 0:
            fig.add_trace(go.Bar(
                x=anomaly_points['ds'],
                y=anomaly_points['y'],
                name='Anomalies',
                marker_color='red',
                opacity=0.7
            ))

        # Update layout
        fig.update_layout(
            title=title,
            xaxis_title='Date',
            yaxis_title='New Merchant Count',
            barmode='group',
            template='plotly_white',
            showlegend=True,
            height=500
        )

        # Add annotations for anomaly count
        anomaly_count = len(anomaly_points)
        total_count = len(recent_df)
        anomaly_rate = (anomaly_count / total_count * 100) if total_count > 0 else 0
        
        fig.add_annotation(
            text=f"Anomalies: {anomaly_count}/{total_count} ({anomaly_rate:.1f}%)",
            xref="paper", yref="paper",
            x=0.02, y=0.98,
            showarrow=False,
            font=dict(size=12, color="black"),
            bgcolor="rgba(255,255,255,0.8)",
            bordercolor="black",
            borderwidth=1
        )

        # Export to PNG if requested
        if export_png:
            if png_filename is None:
                png_filename = f"anomaly_chart_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.png"
            try:
                fig.write_image(png_filename, format='png')
                print(f"Anomaly chart exported to: {png_filename}")
            except Exception as e:
                print(f"[Warning] PNG export failed: {e}. Install kaleido with 'pip install kaleido'")

        return fig


if __name__ == "__main__":

    # Example usage - can be run when this script is executed directly
    try:
        df = pd.read_csv('sample.csv')
        today = pd.to_datetime('today').normalize()

        take_df = df[df['software_product'] == 'Retail']
        a = ForecastAnomalyDetector(take_df)
        anomalies_result = a.detect_stl_anomalies(date_col='txn_date', metric_col='new_merchant', threshold=2.5, period=7, start_date='2025-03-30', end_date='2025-05-20')
        fig_anomalies = a.plot_recent_anomalies_bar(anomalies_result, days_back=60, title="Anomaly Detection Results")

        take_df = df[df['software_product'] == 'Retail']
        a2 = ForecastAnomalyDetector(take_df)
        anomalies_result = a2.detect_stl_anomalies(date_col='txn_date', metric_col='active_merchant', threshold=2.5, period=7, start_date='2024-01-01', end_date=today)
        forecast_df, model = a2.forecast_with_prophet(anomalies_result, date_col='ds', metric_col='y', predict_periods=60, train_start='2024-01-01', train_end=today)

        fig_forecast = a2.plot_forecast_line(forecast_df, title="Forecast for New Merchant Count")

    except FileNotFoundError:
        print("Error: sample.csv file not found. Please ensure the file exists in the current directory.")
    except Exception as e:
        print(f"Error running example: {e}")