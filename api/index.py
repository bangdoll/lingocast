import os
import sys
import json
import re
import traceback
from pathlib import Path

# 初始化全域備用 app，防止 module 級別崩潰導致 Vercel 直接 Function Crash
app = None
error_stack = None

try:
    from fastapi import FastAPI, File, UploadFile, Request, Header
    from typing import Optional
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from groq import Groq
    
    # 嘗試防禦性載入 dotenv
    try:
        from dotenv import load_dotenv
        BASE_DIR = Path(__file__).parent
        load_dotenv(dotenv_path=BASE_DIR.parent / ".env")
        load_dotenv(dotenv_path=BASE_DIR / ".env")
    except Exception:
        pass

    BASE_DIR = Path(__file__).parent
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
    
    # 防禦性初始化 Groq
    groq_client = None
    if GROQ_API_KEY:
        try:
            groq_client = Groq(api_key=GROQ_API_KEY)
        except Exception as e:
            print(f"⚠️ Groq 客戶端初始化失敗: {e}")

    # 防禦性載入 OpenCC
    try:
        from opencc import OpenCC
        cc_s2t = OpenCC('s2t')
    except Exception as e:
        print(f"⚠️ OpenCC 載入失敗（正常退化）: {e}")
        cc_s2t = None

    # 常用簡繁體口語字對照表，做為雙保險兜底
    FALLBACK_S2T = {
        "们": "們", "会": "會", "个": "個", "这": "這", "东": "東", "西": "西",
        "为": "為", "因": "因", "国": "國", "时": "時", "对": "對", "应": "應",
        "来": "來", "经": "經", "说": "說", "么": "麼", "听": "聽", "译": "譯",
        "语": "語", "话": "話", "认": "認", "识": "識", "现": "現", "实": "實",
        "终": "終", "端": "端", "记": "記", "录": "錄", "净": "淨", "洁": "潔",
        "简": "簡", "繁": "繁", "体": "體", "中": "中", "文": "文", "处": "處",
        "么": "麼", "办": "辦", "发": "發", "开": "開", "关": "關", "无": "無",
        "后": "後", "面": "面", "样": "樣", "没": "沒", "电": "電", "机": "機",
        "气": "氣", "点": "點", "确": "確", "认": "認", "词": "詞", "典": "典",
        "库": "庫", "存": "存", "写": "寫", "输": "輸", "出": "出", "单": "單",
        "双": "雙", "幕": "幕", "影": "影", "头": "頭", "声": "聲", "动": "動",
        "画": "畫", "清": "清", "除": "除", "网": "網", "页": "頁", "设": "設",
        "定": "定", "金": "金", "钥": "鑰", "制": "製", "片": "片", "厂": "廠",
        "录": "錄", "音": "音", "仅": "僅", "保": "保", "存": "存", "浏": "瀏",
        "览": "覽", "器": "器", "與": "與", "内": "內", "聚": "聚", "目": "目",
        "录": "錄", "下": "下", "以": "以", "支": "支", "援": "援", "部": "部",
        "署": "署", "进": "進", "程": "程", "实": "實", "施": "施", "简": "簡",
        "繁": "繁", "体": "體", "化": "化", "保": "保", "护": "護", "防": "防",
        "线": "線", "稳": "穩", "固": "固", "们": "們", "会": "會", "个": "個",
        "这": "這", "东": "東", "西": "西", "为": "為", "因": "因", "国": "國",
        "时": "時", "对": "對", "应": "應"
    }

    def convert_to_traditional(text):
        if not text:
            return text
        # 第一層：如果 OpenCC 成功載入，使用 OpenCC 進行 100% 精準轉換
        if cc_s2t:
            try:
                return cc_s2t.convert(text)
            except Exception:
                pass
        # 第二層：如果 OpenCC 載入失敗，使用自訂口語常用字查表進行防禦性替換
        translated = []
        for char in text:
            translated.append(FALLBACK_S2T.get(char, char))
        return "".join(translated)

    app = FastAPI(title="LingoCast - AI 即時雙語同聲翻譯與投屏系統")

    # 允許跨網域訪問
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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

    def translate_text(text: str, custom_dict: dict, client: Groq) -> str:
        if not client:
            return "❌ 錯誤: 未配置有效的 Groq API 金鑰。"
            
        is_chinese = has_chinese(text)
        target_lang = "English" if is_chinese else "Traditional Chinese (繁體中文)"
        
        replace_dict = {k: v for k, v in custom_dict.items() if v}
        keep_list = [k for k, v in custom_dict.items() if not v]
        
        system_prompt = (
            f"你是一位專業的高階同聲傳譯官。請將輸入的文字即時翻譯為 {target_lang}。\n"
            "規則：\n"
            "1. 僅輸出翻譯後的結果，不要包含任何解釋、備註、拼音或多餘的標點引號。\n"
            "2. 請遵守以下專有名詞對齊替換字典：" + str(replace_dict) + "\n"
            "3. 對於以下詞彙，請視為專有名詞，在轉錄和翻譯時必須強制原樣保留，不作 any 語系變更或翻譯：" + str(keep_list) + "\n"
            "4. 翻譯結果必須語意精準、語調自然，符合商務與專業學術論壇場合。"
        )
        
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.2
            )
            translated_result = completion.choices[0].message.content.strip()
            return convert_to_traditional(translated_result)
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
    async def translate_audio(
        file: UploadFile = File(...),
        x_groq_api_key: Optional[str] = Header(None)
    ):
        # 優先使用請求 Header 中帶入的 API 金鑰，若無則使用後端環境變數
        api_key = x_groq_api_key or GROQ_API_KEY
        if not api_key:
            return JSONResponse(
                status_code=400,
                content={"error": "未偵測到 Groq API 金鑰。請點選網頁右上角「🔑 設定金鑰」按鈕進行配置。"}
            )
            
        try:
            # 動態建立該請求的 Groq 客戶端實例
            client = Groq(api_key=api_key)
        except Exception as e:
            return JSONResponse(
                status_code=400,
                content={"error": f"Groq API 金鑰格式不正確或無效: {str(e)}"}
            )
            
        try:
            audio_bytes = await file.read()
            if not audio_bytes or len(audio_bytes) < 100:
                return {"original": "", "translated": ""}
                
            transcription = client.audio.transcriptions.create(
                file=("audio.webm", audio_bytes, "audio/webm"),
                model="whisper-large-v3-turbo",
                language="zh",
                response_format="verbose_json"
            )
            
            transcript = convert_to_traditional(transcription.text.strip())
            if not transcript:
                return {"original": "", "translated": ""}
                
            custom_dict = load_dictionary()
            translated = translate_text(transcript, custom_dict, client)
            
            return {
                "original": transcript,
                "translated": translated
            }
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})

except Exception as e:
    # 捕獲 Module 級別啟動崩潰，建立備用偵錯 App
    error_stack = traceback.format_exc()
    try:
        from fastapi import FastAPI
        from fastapi.responses import HTMLResponse
        app = FastAPI(title="LingoCast 雲端偵錯模式")
        
        @app.get("/{path:path}", response_class=HTMLResponse)
        async def debug_error(path: str):
            return f"""
            <html>
            <head>
                <title>LingoCast 雲端偵錯器</title>
                <meta charset="utf-8">
            </head>
            <body style="font-family: monospace; padding: 30px; background: #1a1a1a; color: #ff5555; line-height: 1.5;">
                <h2>❌ LingoCast 在 Vercel 啟動時發生崩潰</h2>
                <p style="color: #bbb;">本頁面由自癒偵錯器動態產生，用於擷取 Serverless 啟動時的 Stack Trace。</p>
                <hr style="border: 1px solid #333; margin: 20px 0;"/>
                <h3 style="color: #ffaa00;">錯誤堆疊軌跡：</h3>
                <pre style="background: #2a2a2a; padding: 20px; border-radius: 5px; overflow-x: auto; color: #00ff66; border: 1px solid #444;">{error_stack}</pre>
            </body>
            </html>
            """
    except Exception as fatal_err:
        # 如果連 FastAPI 都載入失敗，就只能讓進程自然崩潰
        pass

if __name__ == "__main__":
    if app and not error_stack:
        import uvicorn
        print("🚀 LingoCast 正在啟動中...")
        print("📡 預設監聽 0.0.0.0:8090，您可以在同區域網下的 iPad/手機上透過 Mac IP 直接連線。")
        uvicorn.run(app, host="0.0.0.0", port=8090)
    else:
        print("❌ 偵錯模式啟動，錯誤如下：")
        print(error_stack)
