import json
import os

import numpy as np
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_embedding(text, model="text-embedding-3-small"):
    return client.embeddings.create(model=model, input=[text]).data[0].embedding

def update_embeddings():
    with open("examples.json", "r", encoding="utf-8") as f:
        examples = json.load(f)

    embeddings = []
    for item in examples:
        emb = get_embedding(item["question"])
        embeddings.append(emb)

    np.save("embeddings.npy", np.array(embeddings))
    with open("index_to_example.json", "w", encoding="utf-8") as f:
        json.dump(examples, f, ensure_ascii=False, indent=2)

    print(f"Saved {len(embeddings)} embeddings.")

if __name__ == "__main__":
    update_embeddings()
