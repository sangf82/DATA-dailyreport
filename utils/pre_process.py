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