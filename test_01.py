from chatbot_sql import generate_sql

query = "Lấy đơn hàng từ 01/05/2025 đến 05/05/2025"
result = generate_sql(query)

print("match:", result["matched_question"])
print("sql:\n", result["sql"])
print("score:", round(result["score"], 4))
