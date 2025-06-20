import requests


def processing(gemini_endpoint, headers, json):
    # Đây là endpoint chính thức của Gemini API cho thế hệ nội dung
    return requests.post(gemini_endpoint, headers=headers, json=json)

def template_question(question_text):
    # return f"""
    # Bạn là một chuyên gia phân tích dữ liệu trong lĩnh vực bán lẻ. 
    # Bạn có nhiệm vụ trả lời câu hỏi về số lượng {question_text} của các loại thương nhân trong khoảng thời gian nhất định.
    # Hãy trả lời ngắn gọn và súc tích, chỉ cung cấp số lượng.
    # """
    return """Số lượng {target_entity_type} của {product} {time} là bao nhiêu?"""

def pre_process(question_text: str) -> dict:
    
    return {
        "product": "Retail",
        "time": "2025/05/01-2025/05/05",
        "target_entity_type": "new_merchant",
        "question_template": template_question(question_text),
        "is_time_range": 1,
    }

def post_process_to_sql(response_obj: dict) -> str:
    return "SELECT COUNT(*) FROM db.table where condition"

    
def sql_process(sql_query: str, output_template) -> str:
    # Giả sử bạn có một hàm để xử lý câu truy vấn SQL
    # Ở đây chỉ là một ví dụ đơn giản
    
    return f"Số lượng new merchant của Retail từ 2025/05/01 đến 2025/05/05 là: 70"
