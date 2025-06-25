import pandas as pd
from main_model import MainModel
import git
import subprocess
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

def final_message():
    url = os.getenv("GOOGLE_CHAT_WEBHOOK_URL")
    reports = os.listdir("data/report")
    images = os.listdir("docs")
    
    
    pass