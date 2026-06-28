#!/usr/bin/env python3
"""
LingoCast CLI - AI 即時雙語同聲對照翻譯終端機版
"""

import os
import sys
import json
import argparse
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

# 載入同目錄下的 .env 配置文件
load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

class LingoCastCLI:
    def __init__(self):
        self.api_key = GROQ_API_KEY
        self.dict_path = Path(__file__).parent / "dict.json"
        self.custom_dictionary = self._load_dictionary()

    def _load_dictionary(self):
        if self.dict_path.exists():
            try:
                return json.loads(self.dict_path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"⚠️ 載入字典配置失敗: {e}，將使用空字典。")
        return {}

    def _has_chinese(self, text):
        return any('\u4e00' <= char <= '\u9fff' for char in text)

    def translate(self, text):
        if not self.api_key:
            return "❌ 錯誤: 未設定 GROQ_API_KEY 環境變數。"
            
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        is_chinese = self._has_chinese(text)
        target_lang = "English" if is_chinese else "Traditional Chinese (繁體中文)"
        
        # 區分「對照替換」與「強制保留」詞彙
        replace_dict = {k: v for k, v in self.custom_dictionary.items() if v}
        keep_list = [k for k, v in self.custom_dictionary.items() if not v]
        
        system_prompt = (
            f"你是一位專業的高階同聲傳譯官。請將輸入的文字即時翻譯為 {target_lang}。\n"
            "規則：\n"
            "1. 僅輸出翻譯後的結果，不要包含任何解釋、備註、拼音或多餘的標點引號。\n"
            "2. 請遵守以下專有名詞對齊替換字典：" + str(replace_dict) + "\n"
            "3. 對於以下詞彙，請視為專有名詞，在轉錄和翻譯時必須強制原樣保留，不作任何語系變更或翻譯翻譯：" + str(keep_list) + "\n"
            "4. 翻譯結果必須語意精準、語調自然，符合商務與專業學術論壇場合。"
        )
        
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            "temperature": 0.2
        }
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                from opencc import OpenCC
                cc_s2t = OpenCC('s2t')
                return cc_s2t.convert(data["choices"][0]["message"]["content"].strip())
            else:
                return f"API 錯誤 ({resp.status_code}): {resp.text}"
        except Exception as e:
            return f"連線錯誤: {str(e)}"

    def run_demo(self):
        print("🎙️ === LingoCast CLI (功能展示) ===")
        print("-" * 60)
        
        demo_sentences = [
            "歡迎大家來到今天的分享會，我們今天要探討的是第一性原理與系統思考的結合。",
            "Using leverage allows a solo entrepreneur to compound their results exponentially without hiring others.",
            "我們開發的這套 AI 代理人系統，支援空中 OTA 升級，能夠自動重寫並避開歷史錯誤的進化膠囊。"
        ]
        
        for sentence in demo_sentences:
            print(f"\n[輸入] ➔ {sentence}")
            time.sleep(1)
            print("⚡ 翻譯中...")
            result = self.translate(sentence)
            print(f"[輸出] ➔ {result}")
            print("-" * 50)
            time.sleep(1)

    def run_interactive(self):
        print("🎙️ === LingoCast CLI 即時對照翻譯系統 ===")
        print("💡 提示：直接輸入中文或英文句子，系統將自動進行智慧雙向同聲翻譯。")
        print("💡 輸入 'exit' 退出。自訂字典可於同目錄下的 dict.json 中隨時編輯。")
        print("-" * 60)
        
        while True:
            try:
                user_input = input("\n輸入文字 ➔ ").strip()
                if not user_input or user_input.lower() == 'exit':
                    break
                
                start_time = time.time()
                print("⚡ 翻譯中...")
                result = self.translate(user_input)
                elapsed = time.time() - start_time
                
                print(f"[輸出] ➔ {result}")
                print(f"⏱️ 耗時: {elapsed:.2f}秒")
                print("-" * 50)
            except (KeyboardInterrupt, EOFError):
                break
        print("\n👋 感謝使用 LingoCast CLI！")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LingoCast CLI 翻譯系統")
    parser.add_argument("--demo", action="store_true", help="執行功能演示模式")
    args = parser.parse_args()

    cli = LingoCastCLI()
    if args.demo:
        cli.run_demo()
    else:
        cli.run_interactive()
