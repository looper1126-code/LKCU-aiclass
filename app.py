"""
Jerry 老師「AI智慧生活應用」課程網站
Flask 後端 + 密碼登入 + MiniMax 課程內容產生
"""

import os
import re
import hashlib
import hmac
import time
import json
import urllib.request
import urllib.parse
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", os.urandom(32))

# ========== 設定 ==========
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_ADMIN_IDS = set(os.environ.get("TELEGRAM_ADMIN_IDS", "").split(",")) - {""}
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "jerry")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "jerry1234")
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "sk-cp-...")
MINIMAX_API_HOST = os.environ.get("MINIMAX_API_HOST", "https://api.minimax.io")

# ========== 靜態檔案 ==========
@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    """處理所有靜態檔案請求"""
    root_dirs = [".", "public"]
    for d in root_dirs:
        try:
            return send_from_directory(d, filename)
        except Exception as e:
            continue
    # 最後嘗試根目錄
    return send_from_directory(".", filename)

# ========== API ==========
