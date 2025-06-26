import pandas as pd
import plotly.io as pio
from prophet import Prophet
from datetime import timedelta
import plotly.graph_objects as go
from statsmodels.tsa.seasonal import STL

class MainModel:
    def __init__(self, 
                 df: pd.DataFrame, 
                 date_col: str, 
                 metric_col: str,
                 prod_type: str,
                 back_range: int = 90, 
                 forward_range: int = 60,
                 forecast_range: int = 365):
        self.df = df
        self.date_col = date_col
        self.metric_col = metric_col
        self.prod_type = prod_type
        self.back_range = back_range
        self.forward_range = forward_range
        self.forecast_range = forecast_range

    def detect_stl_anomalies(self, 
                             start, 
                             end, 
                             threshold: float = 2.5, 
                             file_path: str = "anomalies.csv", 
                             save: bool = False):
        
        anomaly_data = self.df[self.df['software_product'] == self.prod_type].copy()
        
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
            rawname, ext = file_path.rsplit('.', 1)
            prod = self.prod_type.lower()
            merch = self.metric_col.lower().split('_')[0]
            name = f"{rawname}_{prod}_{merch}"
            file_path = f"{name}_{pd.Timestamp.now().strftime('%Y%m%d')}.{ext}"
            result_df.to_csv(file_path, index=False)
            print(f"Anomaly detection results saved to {file_path}")
            
        return result_df, file_path
    
    def forecast_with_prophet(self,
                          start: str,
                          end: str,
                          file_path: str = "forecast.csv",
                          save: bool = False,
                          sum: bool = False,):
    
        if self.df.empty:
            raise ValueError("Input dataframe is empty")
        
        if self.date_col not in self.df.columns or self.metric_col not in self.df.columns:
            raise ValueError(f"Columns {self.date_col} or {self.metric_col} not found in DataFrame.")

        forecast_data = self.df[self.df['software_product'] == self.prod_type].copy()
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
            rawname, ext = file_path.rsplit('.', 1)
            prod = self.prod_type.lower()
            merch = self.metric_col.lower().split('_')[0]
            name = f"{rawname}_{prod}_{merch}"
            file_path = f"{name}_{pd.Timestamp.now().strftime('%Y%m%d')}.{ext}"
            forecast_df.to_csv(file_path, index=False)
            print(f"Forecast results exported to: {file_path}")

        # Export model performance summary
        if len(historical_data) > 0 and sum:
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

        return forecast_df, self.model, file_path
    
    def plot_anomalies_charts(self,
                     anomaly_df,  # Can be DataFrame or file path string
                     chart_type: str = "bar",  # "bar" or "line"
                     today: pd.Timestamp = None,
                     title: str = None,
                     filepath: str = "docs/anomaly_chart.html",
                     save: bool = False):

        # Set today if not provided
        if today is None:
            today = pd.Timestamp.now().normalize()
        
        # Handle if anomaly_df is a file path string
        if isinstance(anomaly_df, str):
            try:
                anomaly_df = pd.read_csv(anomaly_df)
                # Convert date column to datetime
                if 'date' in anomaly_df.columns:
                    anomaly_df['date'] = pd.to_datetime(anomaly_df['date'])
                else:
                    raise ValueError("CSV file must contain a 'date' column")
            except Exception as e:
                raise ValueError(f"Error reading CSV file: {e}")
        
        # Validate DataFrame
        if not isinstance(anomaly_df, pd.DataFrame):
            raise ValueError("anomaly_df must be a DataFrame or a valid file path")
        
        if anomaly_df.empty:
            raise ValueError("Anomaly DataFrame is empty")
        
        # Ensure required columns exist
        required_columns = ['date', 'count(trend)', 'anomaly']
        missing_columns = [col for col in required_columns if col not in anomaly_df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Set default title based on metric and chart type
        if title is None:
            metric_name = "New Merchants" if self.metric_col == "new_merchant" else "Active Merchants"
            chart_name = "Bar Chart" if chart_type == "bar" else "Line Chart"
            title = f"{metric_name} Anomaly Detection - {chart_name} ({today.strftime('%Y-%m-%d')})"
        
        from_date = today - timedelta(days=self.back_range)
        
        recent_df = anomaly_df[(
            anomaly_df['date'] >= from_date) & 
            (anomaly_df['date'] <= today)
        ].copy()
        
        if recent_df.empty:
            print(f"Warning: No data found in date range {from_date.date()} to {today.date()}")
            return None
        
        normal_points = recent_df[recent_df['anomaly'] == 0]
        anomaly_points = recent_df[recent_df['anomaly'] == 1]
        
        fig = go.Figure()
        
        # Color scheme based on metric type
        if self.metric_col == "new_merchant":
            normal_color = 'lightblue'
            anomaly_color = 'red'
            y_title = 'New Merchant Count'
        else:  # active_merchant
            normal_color = 'lightgreen'
            anomaly_color = 'orange'
            y_title = 'Active Merchant Count'
        
        # Create charts based on chart_type
        if chart_type == "bar":
            # Bar chart implementation
            if len(normal_points) > 0:
                fig.add_trace(go.Bar(
                    x=normal_points['date'],
                    y=normal_points['count(trend)'],
                    name='Normal Data',
                    marker_color=normal_color,
                    opacity=0.7,
                    hovertemplate=f'Normal: %{{y:.0f}}<br>Date: %{{x}}<extra></extra>'
                ))
            if len(anomaly_points) > 0:
                fig.add_trace(go.Bar(
                    x=anomaly_points['date'],
                    y=anomaly_points['count(trend)'],
                    name='Anomalies',
                    marker_color=anomaly_color,
                    opacity=0.8,
                    hovertemplate=f'Anomaly: %{{y:.0f}}<br>Date: %{{x}}<extra></extra>'
                ))
            
            fig.update_layout(barmode='group')
            
        else:  # line chart
            all_data = recent_df.sort_values('date')
            
            # Add the main trend line (similar to historical data in forecast)
            fig.add_trace(go.Scatter(
                x=all_data['date'],
                y=all_data['count(trend)'],
                name='Data Trend',
                mode='lines',
                line=dict(color='#1f77b4' if self.metric_col == "new_merchant" else '#2ca02c', width=2),
                hovertemplate='Trend: %{y:.0f}<br>Date: %{x}<extra></extra>',
                showlegend=True
            ))
            
            # Add normal points as small markers
            if len(normal_points) > 0:
                normal_color = '#87CEEB' if self.metric_col == "new_merchant" else '#90EE90'  # Light colors
                
                fig.add_trace(go.Scatter(
                    x=normal_points['date'],
                    y=normal_points['count(trend)'],
                    name='Normal Data',
                    mode='markers',
                    marker=dict(
                        size=4,
                        color=normal_color,
                        line=dict(width=1, color='#1f77b4' if self.metric_col == "new_merchant" else '#2ca02c'),
                        symbol='circle'
                    ),
                    hovertemplate=f'Normal: %{{y:.0f}}<br>Date: %{{x}}<extra></extra>'
                ))
            
            # Add anomaly points as prominent markers (similar to today marker in forecast)
            if len(anomaly_points) > 0:
                anomaly_color = '#d62728' if self.metric_col == "new_merchant" else '#ff8c00'  # Red or orange
                anomaly_border = '#8c1c13' if self.metric_col == "new_merchant" else '#cc6600'
                
                fig.add_trace(go.Scatter(
                    x=anomaly_points['date'],
                    y=anomaly_points['count(trend)'],
                    name='Anomalies',
                    mode='markers',
                    marker=dict(
                        size=12,
                        color=anomaly_color,
                        symbol='diamond',
                        line=dict(width=2, color=anomaly_border)
                    ),
                    hovertemplate=f'⚠️ Anomaly: %{{y:.0f}}<br>Date: %{{x}}<extra></extra>'
                ))
                
                # Add vertical lines for anomalies (similar to today line in forecast)
                for _, row in anomaly_points.iterrows():
                    fig.add_shape(
                        type="line",
                        x0=row['date'], x1=row['date'],
                        y0=0, y1=1,
                        yref="paper",
                        line=dict(
                            color=anomaly_color,
                            width=1,
                            dash="dot"
                        ),
                        opacity=0.6
                    )

        # Update layout with forecast chart styling
        fig.update_layout(
            title=dict(
                text=f"{title}",
                x=0.02,
                font=dict(size=18, color='#111111', family='Georgia')
            ),
            xaxis_title='Date',
            yaxis_title=y_title,
            plot_bgcolor='#ffffff',
            paper_bgcolor='#f5f5f5',
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=0.98,
                xanchor="left",
                x=1.02,
                bgcolor='rgba(245, 245, 245, 0.9)',
                bordercolor='#cccccc',
                borderwidth=1,
                font=dict(size=11, color='#111111')
            ),
            height=500,
            margin=dict(t=60, b=40, l=40, r=140)
        )

        # Update axes with forecast chart styling
        fig.update_xaxes(
            showgrid=True,
            gridwidth=0.5,
            gridcolor='#e0e0e0',
            tickfont=dict(size=10, color='#555555'),
            linecolor='#a6a6a6',
            tickformat='%m/%d',
            range=[from_date, today]
        )
        
        fig.update_yaxes(
            showgrid=True,
            gridwidth=0.5,
            gridcolor='#e0e0e0',
            tickfont=dict(size=10, color='#555555'),
            tickformat=',',
            linecolor='#a6a6a6'
        )

        # Add annotations for anomaly count (styled like forecast annotations)
        anomaly_count = len(anomaly_points)
        total_count = len(recent_df)
        anomaly_rate = (anomaly_count / total_count * 100) if total_count > 0 else 0
        
        fig.add_annotation(
            text=f"Anomalies: {anomaly_count}/{total_count} ({anomaly_rate:.1f}%)",
            xref="paper", yref="paper",
            x=0.02, y=0.94,  # Positioned below title
            showarrow=False,
            font=dict(size=12, color="#111111"),
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#cccccc",
            borderwidth=1
        )

        # Export to HTML if requested
        if save:
            rawname, ext = filepath.rsplit('.', 1) if '.' in filepath else (filepath, 'html')
            prod = self.prod_type.lower()
            merch = self.metric_col.lower().split('_')[0]
            name = f"{rawname}_{prod}_{merch}"
            chart_suffix = f"_{chart_type}"
            filepath = f"{name}{chart_suffix}_{pd.Timestamp.now().strftime('%Y%m%d')}.{ext}"
            try:
                fig.write_html(filepath)
                print(f"Anomaly chart exported to: {filepath}")
            except Exception as e:
                print(f"[Warning] HTML export failed: {e}")

        #return fig, 
        return filepath, anomaly_rate

    def plot_forecast_charts(self, 
                        forecast_df: pd.DataFrame,
                        chart_type: str = "line",  # "line" or "bar"
                        today: pd.Timestamp = None,
                        title: str = None,
                        filepath: str = "docs/forecast_chart.html",
                        save: bool = False):

        if forecast_df.empty:
            raise ValueError("Forecast DataFrame is empty. Please provide a valid DataFrame.")
        
        # Set today if not provided
        if today is None:
            today = pd.Timestamp.now().normalize()
        
        # Set default title based on metric and chart type
        if title is None:
            metric_name = "New Merchants" if self.metric_col == "new_merchant" else "Active Merchants"
            chart_name = "Line Chart" if chart_type == "line" else "Bar Chart"
            title = f"{metric_name} Forecast - {chart_name} ({today.strftime('%Y-%m-%d')})"
        
        # Define color palette based on metric type
        if self.metric_col == "new_merchant":
            COLORS = {
                'historical': '#1f77b4',     # Blue
                'forecast': '#ff7f0e',       # Orange
                'confidence': '#2ca02c',     # Green
                'confidence_fill': 'rgba(44, 160, 44, 0.2)',
                'today_marker': '#d62728',   # Red
                'today_border': '#8c1c13',
                'today_line': '#d62728',
            }
            y_title = 'New Merchant Count'
        else:  # active_merchant
            COLORS = {
                'historical': '#2ca02c',     # Green
                'forecast': '#9467bd',       # Purple
                'confidence': '#17becf',     # Cyan
                'confidence_fill': 'rgba(23, 190, 207, 0.2)',
                'today_marker': '#e377c2',   # Pink
                'today_border': '#c7519c',
                'today_line': '#e377c2',
            }
            y_title = 'Active Merchant Count'
        
        # Convert ds column to datetime if it's not already
        forecast_df['ds'] = pd.to_datetime(forecast_df['ds'])
        
        # Use self.back_range to determine how far back to show historical data
        back_date = today - pd.DateOffset(days=self.back_range)
        
        # Use self.forward_range to determine how far forward to show forecast
        forward_date = today + pd.DateOffset(days=self.forward_range)
        
        # Filter data based on back_range and forward_range
        filtered_df = forecast_df[
            (forecast_df['ds'] >= back_date) & 
            (forecast_df['ds'] <= forward_date)
        ].copy()
        
        if filtered_df.empty:
            raise ValueError(f"No data found in range: {back_date.date()} to {forward_date.date()}")
        
        # Separate historical and forecast data with connection point
        historical_data = filtered_df[filtered_df['ds'] <= today]
        forecast_data = filtered_df[filtered_df['ds'] >= today]  # Include today for connection
        
        # Create the figure
        fig = go.Figure()
        
        if chart_type == "line":
            # Line chart implementation
            # Add historical actual data
            if 'y' in filtered_df.columns and len(historical_data) > 0:
                actual_historical = historical_data.dropna(subset=['y'])
                if len(actual_historical) > 0:
                    fig.add_trace(go.Scatter(
                        x=actual_historical['ds'],
                        y=actual_historical['y'],
                        name='Historical Data',
                        line=dict(color=COLORS['historical'], width=2),
                        mode='lines',
                        hovertemplate='Historical: %{y:.0f}<br>Date: %{x}<extra></extra>'
                    ))
            
            # Add forecast confidence intervals
            if len(forecast_data) > 0:
                fig.add_trace(go.Scatter(
                    x=forecast_data['ds'],
                    y=forecast_data['yhat_upper'],
                    name='Upper Bound',
                    line=dict(color=COLORS['confidence'], width=0),
                    showlegend=False,
                    hovertemplate='Upper Bound: %{y:.0f}<br>Date: %{x}<extra></extra>'
                ))
                
                fig.add_trace(go.Scatter(
                    x=forecast_data['ds'],
                    y=forecast_data['yhat_lower'],
                    name='Confidence Band',
                    line=dict(color=COLORS['confidence'], width=0),
                    fill='tonexty',
                    fillcolor=COLORS['confidence_fill'],
                    showlegend=True,
                    hovertemplate='Lower Bound: %{y:.0f}<br>Date: %{x}<extra></extra>'
                ))
            
            # Add forecast line
            if len(forecast_data) > 0:
                fig.add_trace(go.Scatter(
                    x=forecast_data['ds'],
                    y=forecast_data['yhat'],
                    name='Forecast',
                    line=dict(color=COLORS['forecast'], width=2, dash='dot'),
                    mode='lines',
                    hovertemplate='Forecast: %{y:.0f}<br>Date: %{x}<extra></extra>'
                ))
        
        else:  # bar chart
            # Bar chart implementation
            # Add historical actual data
            if 'y' in filtered_df.columns and len(historical_data) > 0:
                actual_historical = historical_data.dropna(subset=['y'])
                if len(actual_historical) > 0:
                    fig.add_trace(go.Bar(
                        x=actual_historical['ds'],
                        y=actual_historical['y'],
                        name='Historical Data',
                        marker_color=COLORS['historical'],
                        opacity=0.7,
                        hovertemplate='Historical: %{y:.0f}<br>Date: %{x}<extra></extra>'
                    ))
            
            # Add forecast bars
            if len(forecast_data) > 0:
                fig.add_trace(go.Bar(
                    x=forecast_data['ds'],
                    y=forecast_data['yhat'],
                    name='Forecast',
                    marker_color=COLORS['forecast'],
                    opacity=0.8,
                    hovertemplate='Forecast: %{y:.0f}<br>Date: %{x}<extra></extra>'
                ))
            
            fig.update_layout(barmode='group')
        
        # Add today's marker (for both chart types)
        today_point = filtered_df[filtered_df['ds'] == today]
        if len(today_point) > 0:
            today_value = today_point['y'].iloc[0] if not pd.isna(today_point['y'].iloc[0]) else today_point['yhat'].iloc[0]
            fig.add_trace(go.Scatter(
                x=[today],
                y=[today_value],
                name='Today',
                mode='markers',
                marker=dict(
                    size=12,
                    color=COLORS['today_marker'],
                    symbol='circle',
                    line=dict(width=2, color=COLORS['today_border'])
                ),
                hovertemplate=f'Today ({today.strftime("%Y-%m-%d")})<br>Value: %{{y:.0f}}<extra></extra>'
            ))
        
        # Update layout
        fig.update_layout(
            title=dict(
                text=f"{title}",
                x=0.02,
                font=dict(size=18, color='#111111', family='Georgia')
            ),
            xaxis_title='Date',
            yaxis_title=y_title,
            plot_bgcolor='#ffffff',
            paper_bgcolor='#f5f5f5',
            hovermode='x unified',
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top",
                y=0.98,
                xanchor="left",
                x=1.02,
                bgcolor='rgba(245, 245, 245, 0.9)',
                bordercolor='#cccccc',
                borderwidth=1,
                font=dict(size=11, color='#111111')
            ),
            height=500,
            margin=dict(t=60, b=40, l=40, r=140),
            shapes=[
                dict(
                    type="line",
                    x0=today,
                    x1=today,
                    y0=0,
                    y1=1,
                    yref="paper",
                    line=dict(
                        color=COLORS['today_line'],
                        width=1,
                        dash="dot"
                    ),
                    opacity=0.6
                )
            ]
        )
        
        # Update axes
        fig.update_xaxes(
            showgrid=True,
            gridwidth=0.5,
            gridcolor='#e0e0e0',
            tickfont=dict(size=10, color='#555555'),
            linecolor='#a6a6a6',
            tickformat='%m/%d',
            range=[back_date, forward_date]
        )
        
        fig.update_yaxes(
            showgrid=True,
            gridwidth=0.5,
            gridcolor='#e0e0e0',
            tickfont=dict(size=10, color='#555555'),
            tickformat=',',
            linecolor='#a6a6a6'
        )
        
        # Export to HTML if requested
        if save:
            rawname, ext = filepath.rsplit('.', 1) if '.' in filepath else (filepath, 'html')
            prod = self.prod_type.lower()
            merch = self.metric_col.lower().split('_')[0]
            name = f"{rawname}_{prod}_{merch}"
            chart_suffix = f"_{chart_type}"
            filepath = f"{name}{chart_suffix}_{pd.Timestamp.now().strftime('%Y%m%d')}.{ext}"
            try:
                pio.write_html(fig, filepath, full_html=True, include_plotlyjs="cdn")
                print(f"Forecast chart exported to: {filepath}")
            except Exception as e:
                print(f"[Warning] HTML export failed: {e}. Install kaleido with 'pip install kaleido'")

        #return fig
        return filepath