"""
Jerry 老師「AI智慧生活應用」課程網站 API 服務
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

# ========== Telegram 驗證 ==========

def verify_telegram(init_data: str) -> dict | None:
    """驗證 Telegram Login widget 的 initData"""
    try:
        parsed = dict(urllib.parse.parse_qsl(init_data))
        hash_str = parsed.pop("hash", "")
        data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
        secret_key = hmac.new(b"WebAppData", TELEGRAM_BOT_TOKEN.encode(), hashlib.sha256).digest()
        calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
        if calculated_hash != hash_str:
            return None
        auth_date = int(parsed.get("auth_date", 0))
        if time.time() - auth_date > 48 * 3600:
            return None
        user = json.loads(parsed.get("user", "{}"))
        return user
    except Exception:
        return None

# ========== 登入驗證（密碼 + Telegram） ==========

def verify_login() -> bool:
    """檢查是否已登入（密碼登入或 Telegram 登入）"""
    if session.get("logged_in"):
        return True
    init_data = request.cookies.get("telegram_init_data", "")
    user = verify_telegram(init_data)
    if not user:
        return False
    user_id = str(user.get("id", ""))
    return user_id in TELEGRAM_ADMIN_IDS or "*" in TELEGRAM_ADMIN_IDS

def admin_required(f):
    """裝飾器：只有管理員才能存取"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not verify_login():
            return jsonify({"error": "未授權，請先登入"}), 401
        return f(*args, **kwargs)
    return decorated

# ========== MiniMax 課程內容產生 ==========

COURSE_WEEKS = {
    1: "認識 AI：聊天機器的原理",
    2: "LINE AI 機器人：製作你的第一個客服",
    3: "AI 影像生成：從文字變出圖片",
    4: "AI 音樂創作：用 AI 譜曲",
    5: "AI 簡報助手：快速製作專業簡報",
    6: "AI 翻譯與文案：跨語言溝通無障礙",
    7: "手機 AI App：把 AI 帶在身上走",
    8: "AI 與生活：智慧管家應用",
    9: "AI 學習術：打造個人化學習地圖",
    10: "AI 職場應用：提升工作效率的秘密武器",
    11: "AI 創意實作：結合烹飪與科技",
    12: "AI 倫理與安全：負責任地使用 AI",
    13: "成果展現：AI 應用總整理與未來展望",
}

def generate_week_content(week: int, topic: str) -> dict:
    """用 MiniMax M2.7 產生本週課程內容"""
    week_title = COURSE_WEEKS.get(week, f"第{week}週：{topic}")
    prompt = f"""你是「AI智慧生活應用」課程的老師，請為學員產生本週（第{week}週）的課程內容。

本週主題：「{week_title}」（老師指定：{topic}）

請產生以下內容（用繁體中文，適合樂齡族學習）：

## 本週課程摘要
（3-4句話，說明這週學什麼、有什麼重點）

## 延伸學習資源
（2-3個推薦資源，格式：標題 | 說明 | 連結）

## 隨堂練習
（1-2個實作題，讓學員回家可以練習）

## 學習小提示
（1句話鼓勵或提醒）

請用 JSON 格式回覆：
{{
  "summary": "...",
  "resources": ["標題 | 說明 | 連結", "..."],
  "exercises": ["...", "..."],
  "tip": "..."
}}"""

    payload = {
        "model": "MiniMax-M2.7",
        "max_tokens": 1500,
        "messages": [{"role": "user", "content": prompt}]
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{MINIMAX_API_HOST}/anthropic/v1/messages",
        data=data,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {MINIMAX_API_KEY}"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            # Anthropic 格式：{"content": [{"type": "text", "text": "..."}]}
            content_blocks = result.get("content", [])
            text = ""
            texts = []
            for block in content_blocks:
                if isinstance(block, dict) and block.get("type") == "text":
                    t = block.get("text", "")
                    if t:
                        texts.append(t)
            text = "\n".join(texts)
            try:
                json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(1))
                brace_match = re.search(r"\{.*\}", text, re.DOTALL)
                if brace_match:
                    return json.loads(brace_match.group())
            except json.JSONDecodeError:
                pass
            return {"raw": text}
    except Exception as e:
        return {"error": str(e)}

# ========== API 路由 ==========

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/api/login", methods=["POST"])
def login():
    """密碼登入"""
    data = request.get_json()
    username = data.get("username", "")
    password = data.get("password", "")
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session["logged_in"] = True
        session.permanent = True
        return jsonify({"ok": True})
    return jsonify({"ok": False, "error": "帳號或密碼錯誤"}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    """登出"""
    session.clear()
    return jsonify({"ok": True})

@app.route("/api/telegram-login")
def telegram_login():
    """驗證 Telegram initData"""
    init_data = request.args.get("init_data", "")
    user = verify_telegram(init_data)
    if not user:
        return jsonify({"ok": False, "error": "驗證失敗"})
    resp = jsonify({
        "ok": True,
        "user": {
            "id": user.get("id"),
            "first_name": user.get("first_name"),
            "username": user.get("username"),
        }
    })
    resp.set_cookie("telegram_init_data", init_data, max_age=48*3600, httponly=True, samesite="Lax")
    return resp

@app.route("/api/check-admin")
def check_admin():
    """檢查是否為管理員"""
    if session.get("logged_in"):
        return jsonify({"admin": True, "user": {"first_name": "Admin"}})
    init_data = request.cookies.get("telegram_init_data", "")
    user = verify_telegram(init_data)
    if not user:
        return jsonify({"admin": False})
    user_id = str(user.get("id", ""))
    admin = user_id in TELEGRAM_ADMIN_IDS or "*" in TELEGRAM_ADMIN_IDS
    return jsonify({"admin": admin, "user": user})

@app.route("/api/generate", methods=["POST"])
@admin_required
def generate():
    """產生課程內容（需管理員權限）"""
    data = request.get_json()
    week = int(data.get("week", 1))
    topic = data.get("topic", "")
    result = generate_week_content(week, topic)
    return jsonify({"ok": True, "week": week, "topic": topic, "content": result})

@app.route("/api/week-content/<int:week>")
def get_week_content(week):
    """取得已產生的課程內容（公開）"""
    path = f"content/week{week:02d}.json"
    if os.path.exists(path):
        with open(path) as f:
            return jsonify(json.load(f))
    return jsonify({"error": "尚無內容"}), 404

# ========== 靜態檔案 ==========
@app.route("/week-images/<path:filename>")
def week_images(filename):
    return send_from_directory("week-images", filename)

@app.route("/week-images-fixed/<path:filename>")
def week_images_fixed(filename):
    return send_from_directory("week-images-fixed", filename)

@app.route("/lecture-notes/<path:filename>")
def lecture_notes(filename):
    return send_from_directory("../lecture-notes", filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    app.run("0.0.0.0", port)
