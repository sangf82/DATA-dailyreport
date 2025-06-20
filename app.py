import os

import requests  # Nhập thư viện requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request

from utils.post_process_to_sql import post_process_to_sql
from utils.pre_processing import pre_process
from utils.sql_process import sql_process

# Tải biến môi trường từ tệp .env
load_dotenv()

app = Flask(__name__)

# Cấu hình API Key và Endpoint của Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY not found in environment variables. Please set it in .env file.")

# Đây là endpoint chính thức của Gemini API cho thế hệ nội dung
# Lưu ý: Có thể cần điều chỉnh model nếu bạn dùng các model khác (ví dụ: gemini-1.5-pro-latest)
GEMINI_API_ENDPOINT = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={GOOGLE_API_KEY}"

@app.route('/')
def home():
    return "Chào mừng đến với API hỏi đáp Gemini (sử dụng requests)!"

@app.route('/ask', methods=['POST'])
def ask_gemini_with_requests():
    data = request.get_json()
    question_text = data.get('question')

    if not question_text:
        return jsonify({"error": "Please provide 'question' in body of the request."}), 400

    try:
        # # Chuẩn bị body của yêu cầu POST cho Gemini API
        # # Cấu trúc này tuân theo định dạng của Gemini API cho generateContent
        # request_body = {
        #     "contents": [
        #         {
        #             "parts": [
        #                 {
        #                     "text": f"""{question_text}
        #                     """
        #                     # Hãy trả lời câu hỏi trên một cách ngắn gọn và súc tích.
        #                 }
        #             ]
        #         }
        #     ]
        # }

        # # Gửi yêu cầu POST đến Gemini API
        # headers = {
        #     "Content-Type": "application/json"
        # }
        
        pre_processed_question = pre_process(question_text)
        # sql_processed = post_process_to_sql(pre_processed_question)
        # output_response = sql_process(sql_processed)
        
        output_response = pre_processed_question

        # # Kiểm tra mã trạng thái HTTP
        # response.raise_for_status() # Sẽ ném ra lỗi HTTPError nếu trạng thái là 4xx hoặc 5xx

        # Phân tích phản hồi JSON
        # gemini_response = response.json()


        return jsonify({"question": question_text, "answer": output_response})

    except requests.exceptions.RequestException as req_err:
        print(f"Lỗi kết nối hoặc HTTP: {req_err}")
        return jsonify({"error": f"Lỗi kết nối hoặc HTTP khi gọi Gemini API: {str(req_err)}"}), 500
    except ValueError as val_err: # JSON decoding error
        print(f"Lỗi phân tích JSON: {val_err}")
        return jsonify({"error": f"Lỗi phân tích phản hồi từ Gemini API: {str(val_err)}"}), 500
    except Exception as e:
        print(f"Lỗi không xác định: {e}")
        return jsonify({"error": f"Đã xảy ra lỗi khi xử lý yêu cầu: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)