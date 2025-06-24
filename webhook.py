from flask import Flask, request, jsonify
import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

@app.route("/")
def home():
    return jsonify({"status": "Daily Report Bot is running"})

def send_message(webhook_url, message_text):
    try:
        requests.post(webhook_url, json={"text": message_text}).raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error sending message: {e}")

@app.route("/webhook", methods=["POST"])
def webhook():
    try:
        webhook_url = os.getenv("GOOGLE_CHAT_WEBHOOK_URL")

        if not webhook_url:
            return jsonify({"status": "error", "message": "Webhook URL not configured."}), 500

        # Check for anomaly file to be included in the report
        # Note: The date is hardcoded for now, matching available data.
        anomaly_file_path = "data/output/anomalies_retail_active_20250623.csv"
        anomaly_present = os.path.exists(anomaly_file_path)

        message_parts = [
            "📊 *Tổng quan khách hàng Retail Active*",
            "",
            "🔹 *Hiện tại*: Số lượng khách hàng đang active ~ *227,079* người (ngày 23/06/2025)",
            "",
            "📈 *Dự báo*: Trong vòng *30 ngày tới*, số lượng khách hàng active được dự báo tiếp tục duy trì xu hướng tăng nhẹ, với giá trị trung bình dao động từ *151K đến 304K*.",
            "",
            "🔗 [Click to view Forecast](https://sangf82.github.io/divevin-swimmingclub/images/forecast_retail_active_line_20250623.html)"
        ]

        if anomaly_present:
            message_parts += [
                "",
                "🚨 *Cảnh báo bất thường*: Hệ thống đã phát hiện một số điểm bất thường trong hành vi khách hàng Retail active, có thể do chiến dịch marketing hoặc sự kiện đặc biệt gây biến động.",
                "",
                "🔗 [Click to view Anomalies](https://sangf82.github.io/divevin-swimmingclub/images/anomalies_retail_active_line_20250623.html)"
            ]

        full_message_text = "\n".join(message_parts)
        send_message(webhook_url, full_message_text)
        
        return jsonify({"status": "Report sent successfully."})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/test-send")
def test_send():
    webhook_url = os.getenv("GOOGLE_CHAT_WEBHOOK_URL")
    if not webhook_url:
        return "GOOGLE_CHAT_WEBHOOK_URL environment variable is not set.", 500
    
    send_message(webhook_url, "👋 This is a test message from the webhook's test endpoint.")
    return "Test message sent."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
