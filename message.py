import os
import json
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class FinalMessage:
    def __init__(self):
        self.url = os.getenv("GOOGLE_CHAT_WEBHOOK_URL")
        self.reports = [report for report in os.listdir("data/report") if report != 'sample.txt']
        self.docs = [doc for doc in os.listdir("docs") if doc != 'sample.txt']
    
    def final_message(self):
        
        pass

    
