import os
import sys
import json
import re
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
from dotenv import load_dotenv
# 載入同目錄或上級目錄下的 .env 配置文件
BASE_DIR = Path(__file__).parent
load_dotenv(dotenv_path=BASE_DIR.parent / ".env")
load_dotenv(dotenv_path=BASE_DIR / ".env")

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

try:
    from opencc import OpenCC
    cc_s2t = OpenCC('s2t')
except Exception as e:
    print(f"⚠️ OpenCC 載入失敗（可能是 Vercel Serverless 環境限制）: {e}")
    cc_s2t = None

def convert_to_traditional(text):
    if cc_s2t:
        try:
            return cc_s2t.convert(text)
        except Exception:
            pass
    return text

app = FastAPI(title="LingoCast - AI 即時雙語同聲翻譯與投屏系統")

# 允許跨網域訪問，便於 iPad 等其他設備在同區域網下連線
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定義相對路徑，完全內聚於 api/ 目錄下以支援 Vercel 部署
DICT_PATH = BASE_DIR / "dict.json"
TEMPLATE_PATH = BASE_DIR / "templates" / "index.html"

_memory_dict = {}

def load_dictionary():
    global _memory_dict
    if _memory_dict:
        return _memory_dict
    if DICT_PATH.exists():
        try:
            dct = json.loads(DICT_PATH.read_text(encoding="utf-8"))
            _memory_dict = dct
            return dct
        except Exception:
            pass
    return {}

def save_dictionary(dct):
    global _memory_dict
    _memory_dict = dct
    try:
        DICT_PATH.write_text(json.dumps(dct, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        print(f"⚠️ 無法寫入字典設定檔（可能為 Serverless 唯讀磁碟環境）: {e}")

def has_chinese(text):
    return any('\u4e00' <= char <= '\u9fff' for char in text)

def translate_text(text: str, custom_dict: dict) -> str:
    if not groq_client:
        return "❌ 錯誤: 未配置 GROQ_API_KEY 環境變數。"
        
    is_chinese = has_chinese(text)
    target_lang = "English" if is_chinese else "Traditional Chinese (繁體中文)"
    
    # 區分「對照替換」與「強制保留」詞彙
    replace_dict = {k: v for k, v in custom_dict.items() if v}
    keep_list = [k for k, v in custom_dict.items() if not v]
    
    system_prompt = (
        f"你是一位專業的高階同聲傳譯官。請將輸入的文字即時翻譯為 {target_lang}。\n"
        "規則：\n"
        "1. 僅輸出翻譯後的結果，不要包含任何解釋、備註、拼音或多餘的標點引號。\n"
        "2. 請遵守以下專有名詞對齊替換字典：" + str(replace_dict) + "\n"
        "3. 對於以下詞彙，請視為專有名詞，在轉錄和翻譯時必須強制原樣保留，不作任何語系變更或翻譯翻譯：" + str(keep_list) + "\n"
        "4. 翻譯結果必須語意精準、語調自然，符合商務與專業學術論壇場合。"
    )
    
    try:
        completion = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.2
        )
        translated_result = completion.choices[0].message.content.strip()
        return cc_s2t.convert(translated_result)
    except Exception as e:
        return f"翻譯失敗: {str(e)}"

@app.get("/", response_class=HTMLResponse)
async def get_index():
    if TEMPLATE_PATH.exists():
        return TEMPLATE_PATH.read_text(encoding="utf-8")
    return "<h3>❌ 找不到 templates/index.html 網頁範本檔案。</h3>"

@app.get("/api/dictionary")
async def get_dict():
    return load_dictionary()

@app.post("/api/dictionary")
async def post_dict(req: Request):
    try:
        data = await req.json()
        save_dictionary(data)
        return {"status": "success", "data": data}
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": str(e)})

@app.post("/api/translate-audio")
async def translate_audio(file: UploadFile = File(...)):
    if not groq_client:
        return JSONResponse(status_code=500, content={"error": "GROQ_API_KEY 未設定"})
        
    try:
        audio_bytes = await file.read()
        if not audio_bytes or len(audio_bytes) < 100:
            return {"original": "", "translated": ""}
            
        # 呼叫 Groq Whisper API 進行轉錄
        transcription = groq_client.audio.transcriptions.create(
            file=("audio.webm", audio_bytes, "audio/webm"),
            model="whisper-large-v3-turbo",
            language="zh",
            response_format="verbose_json"
        )
        
        transcript = cc_s2t.convert(transcription.text.strip())
        if not transcript:
            return {"original": "", "translated": ""}
            
        # 載入自訂字典進行翻譯
        custom_dict = load_dictionary()
        translated = translate_text(transcript, custom_dict)
        
        return {
            "original": transcript,
            "translated": translated
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import uvicorn
    print("🚀 LingoCast 正在啟動中...")
    print("📡 預設監聽 0.0.0.0:8090，您可以在同區域網下的 iPad/手機上透過 Mac IP 直接連線。")
    uvicorn.run(app, host="0.0.0.0", port=8090)
