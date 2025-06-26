import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class FinalMessage:
    def __init__(self, mode: str):
        if mode == 'test':
            self.url = os.getenv("GOOGLE_CHAT_WEBHOOK_URL_1")
        elif mode == 'prod':
            self.url = os.getenv("GOOGLE_CHAT_WEBHOOK_URL")
        self.reports = [report for report in os.listdir("data/report") if report != 'sample.txt']
    
    def generate_google_chat_card(self, report):
        def format_client_section(title_emoji, title, count, day, week, month, anomaly_rate, forecast_url, anomaly_url):
            widgets = [
                {"textParagraph": {"text": f"👥 Số lượng hiện tại: <b>{count:,}</b>"}},
                {"textParagraph": {"text": f"📅 So với hôm qua: <br> <b>{day}</b>"}},
                {"textParagraph": {"text": f"📈 So với tuần trước: <br> <b>{week}</b>"}},
                {"textParagraph": {"text": f"📆 So với tháng trước: <br> <b>{month}</b>"}},
            ]

            if anomaly_rate and anomaly_rate != "0%" and anomaly_rate != "0.00%":
                widgets.append({"textParagraph": {"text": f"🚨 Tỷ lệ bất thường: <b>{anomaly_rate}</b>"}})
                widgets.append({
                    "buttonList": {
                        "buttons": [
                            {
                                "text": "🔎 Xem biểu đồ dự báo",
                                "onClick": {"openLink": {"url": f"https://sangf82.github.io/DATA-dailyreport/{forecast_url}"}}
                            },
                            {
                                "text": "🚨 Xem biểu đồ bất thường",
                                "onClick": {"openLink": {"url": f"https://sangf82.github.io/DATA-dailyreport/{anomaly_url}"}}
                            }
                        ]
                    }
                })
            else:
                widgets.append({
                    "buttonList": {
                        "buttons": [
                            {
                                "text": "🔎 Xem biểu đồ dự báo",
                                "onClick": {"openLink": {"url": f"https://sangf82.github.io/DATA-dailyreport/{forecast_url}"}}
                            }
                        ]
                    }
                })

            return {
                "header": f"{title_emoji} {title}",
                "widgets": widgets
            }

        return {
            "cardsV2": [
                {
                    "card": {
                        "header": {
                            "title": f"📊 Báo cáo sản phẩm {report['new_product']} (Cập nhật ngày: {report.get('report_date', 'Không xác định')})",
                            "subtitle": "Tổng quan khách hàng mới và đang hoạt động các sản phẩm của KiotViet"
                        },
                        "sections": [
                            format_client_section(
                                "🟡", "Khách hàng mới",
                                report["new_client_count"],
                                report["new_insight_day"],
                                report["new_insight_week"],
                                report["new_insight_month"],
                                report.get("new_anomaly_rate", ""),
                                report["new_forecast_chart_path"],
                                report["new_anomalies_chart_path"]
                            ),
                            format_client_section(
                                "🟢", "Khách hàng đang hoạt động",
                                report["active_client_count"],
                                report["active_insight_day"],
                                report["active_insight_week"],
                                report["active_insight_month"],
                                report.get("active_anomaly_rate", ""),
                                report["active_forecast_chart_path"],
                                report["active_anomalies_chart_path"]
                            )
                        ]
                    }
                }
            ]
        }

    def final_message(self):
        if not self.url:
            print("Error: GOOGLE_CHAT_WEBHOOK_URL not found in environment variables")
            return
            
        for report_file in self.reports:
            if not report_file.endswith('.json'):
                continue
                
            today = datetime.now().strftime("%Y%m%d")
            take_report_date = report_file.replace('_report.json', '')
            
            if take_report_date.endswith(today):
                try:
                    with open(f"data/report/{report_file}", "r", encoding="utf-8") as file:
                        report = json.load(file)[0]
                    
                    card_v2 = self.generate_google_chat_card(report)
                    response = requests.post(self.url, json=card_v2)
                    
                    if response.ok:
                        print(f"Sent report for {report['new_product']}")
                    else:
                        print(f"Error sending {report['new_product']}: {response.status_code} - {response.text}")
                        
                except Exception as e:
                    print(f"Error processing {report_file}: {str(e)}")


