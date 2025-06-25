import requests
import os
from dotenv import load_dotenv
import json

load_dotenv()

ver_1 = {
  "cardsV2": [
    {
      "card": {
        "header": {
          "title": "📊 Báo cáo sản phẩm Booking",
          "subtitle": "Tổng quan khách hàng mới và đang hoạt động"
        },
        "sections": [
          {
            "header": "🟡 Khách hàng mới",
            "widgets": [
              {
                "textParagraph": {
                  "text": "👥 <b>Số lượng hiện tại:</b> 28"
                }
              },
              {
                "textParagraph": {
                  "text": "📅 <b>So với hôm qua:</b><br>Giảm 26.32% so với ngày hôm qua. (- 10 khách)"
                }
              },
              {
                "textParagraph": {
                  "text": "📈 <b>So với tuần trước:</b><br>Giảm 65.43% so với tuần trước. (- 53 khách)"
                }
              },
              {
                "textParagraph": {
                  "text": "📆 <b>So với tháng trước:</b><br>Tăng 180.00% so với tháng trước. (+ 18 khách)"
                }
              },
              {
                "textParagraph": {
                  "text": "🚨 <b>Tỷ lệ bất thường:</b> 5.49%"
                }
              },
              {
                "buttonList": {
                  "buttons": [
                    {
                      "text": "🔎 Xem biểu đồ dự báo",
                      "onClick": {
                        "openLink": {
                          "url": "https://sangf82.github.io/DATA-dailyreport/docs/forecast_booking_new_bar_20250625.html"
                        }
                      }
                    },
                    {
                      "text": "🚨 Xem biểu đồ bất thường",
                      "onClick": {
                        "openLink": {
                          "url": "https://sangf82.github.io/DATA-dailyreport/docs/anomalies_booking_new_bar_20250625.html"
                        }
                      }
                    }
                  ]
                }
              }
            ]
          },
          {
            "header": "🟢 Khách hàng đang hoạt động",
            "widgets": [
              {
                "textParagraph": {
                  "text": "👥 <b>Số lượng hiện tại:</b> 13,010"
                }
              },
              {
                "textParagraph": {
                  "text": "📅 <b>So với hôm qua:</b><br>Tăng 0.15% so với ngày hôm qua. (+ 19 khách)"
                }
              },
              {
                "textParagraph": {
                  "text": "📈 <b>So với tuần trước:</b><br>Tăng 0.63% so với tuần trước. (+ 82 khách)"
                }
              },
              {
                "textParagraph": {
                  "text": "📆 <b>So với tháng trước:</b><br>Tăng 2.35% so với tháng trước. (+ 299 khách)"
                }
              },
              {
                "textParagraph": {
                  "text": "🚨 <b>Tỷ lệ bất thường:</b> 10.99%"
                }
              },
              {
                "buttonList": {
                  "buttons": [
                    {
                      "text": "🔎 Xem biểu đồ dự báo",
                      "onClick": {
                        "openLink": {
                          "url": "https://sangf82.github.io/DATA-dailyreport/docs/forecast_booking_active_line_20250625.html"
                        }
                      }
                    },
                    {
                      "text": "🚨 Xem biểu đồ bất thường",
                      "onClick": {
                        "openLink": {
                          "url": "https://sangf82.github.io/DATA-dailyreport/docs/anomalies_booking_active_line_20250625.html"
                        }
                      }
                    }
                  ]
                }
              }
            ]
          }
        ]
      }
    }
  ]
}

def generate_google_chat_card(report):
    def format_client_section(title_emoji, title, count, day, week, month, anomaly_rate, forecast_url, anomaly_url):
        widgets = [
            {"textParagraph": {"text": f"👥 Số lượng hiện tại: <br> <b>{count:,}</b>"}},
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
                        "title": f"📊 Báo cáo sản phẩm {report['new_product']}",
                        "subtitle": "Tổng quan khách hàng mới và đang hoạt động"
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

with open("C:/Users/ADMIN/Downloads/projects/DATA-dailyreport/data/report/booking_20250625_report.json", "r", encoding="utf-8") as f:
    report_data = json.load(f)[0]

card_v2 = generate_google_chat_card(report_data)

WEBHOOK_URL = os.getenv("GOOGLE_CHAT_WEBHOOK_URL")
response = requests.post(WEBHOOK_URL, json=card_v2)
print("✅ Sent" if response.ok else f"❌ Error: {response.text}")
