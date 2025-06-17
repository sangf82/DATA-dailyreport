import os
import re
import json
import numpy as np
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from sklearn.metrics.pairwise import cosine_similarity
from datetime import datetime, date


load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_embedding(text, model="text-embedding-3-small"):
    return client.embeddings.create(model=model, input=[text]).data[0].embedding

def extract_dates(text):
    matches = re.findall(r"\b(\d{1,2}[/-]\d{1,2}(?:[/-]\d{4})?)\b", text)
    dates = []
    current_year = date.today().year

    for m in matches:
        parsed = None
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d/%m", "%d-%m"):
            try:
                if fmt in ("%d/%m", "%d-%m") and len(m.split("/")) == 2 or len(m.split("-")) == 2:
                    m = m + f"/{current_year}" if "/" in m else m + f"-{current_year}"
                parsed = datetime.strptime(m, fmt).date()
                break
            except:
                continue
        if parsed:
            dates.append(parsed)

    if len(dates) == 2:
        return min(dates), max(dates)
    elif len(dates) == 1:
        return dates[0], None
    return None, None

def load_knowledge():
    vectors = np.load("embeddings.npy")
    with open("index_to_example.json", "r", encoding="utf-8") as f:
        examples = json.load(f)
    return vectors, examples

def match_sql(user_question):
    vectors, examples = load_knowledge()
    user_vec = np.array(get_embedding(user_question))
    sims = cosine_similarity([user_vec], vectors)[0]
    idx = int(np.argmax(sims))
    matched = examples[idx]
    score = sims[idx]
    return matched, score

def generate_sql(user_question):
    matched, score = match_sql(user_question)
    sql_template = matched["sql"]
    tags = matched.get("tags", [])

    if "has_date_range" in tags:
        start_date, end_date = extract_dates(user_question)
        if start_date and end_date:
            sql_template = sql_template.format(
                start_date=start_date.isoformat(),
                end_date=end_date.isoformat()
            )
    return {
        "matched_question": matched["question"],
        "sql": sql_template,
        "score": score
    }
