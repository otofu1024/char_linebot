from google import genai
from google.genai import types
import config
import json
import os
from datetime import datetime
import requests
import jma_weather_api

GEMINI_API_KEY = config.GEMINI_API_KEY

client = genai.Client(api_key = GEMINI_API_KEY)

def generate_weather_response(day, city):
    """
    指定された日と都市の天気情報を生成する
    """
    try:
        weather_info = jma_weather_api.get_weather(day, city)
        with open(f"systempro.txt", "r", encoding="utf-8") as f:
            personalized_instruction = f.read()
        personalized_instruction += f"\n\n{weather_info}"

        response = client.models.generate_content(
            model='gemini-2.5-flash-preview-05-20',
            contents="以下の天気情報をシャアらしく教えてください。",
            config=types.GenerateContentConfig(
                system_instruction=personalized_instruction,
                top_p= 0.7,
                temperature= 0.7,
                response_mime_type='text/plain'
            ),
        )
        return response.text
    except Exception as e:
        return f"天気情報の取得に失敗しました: {e}"

def generate_response_with_history(prompt, user_name, user_id, message_id, group_id=None, quoted_id=None):
    """
    会話履歴を考慮してパーソナライズされた応答を生成する
    """
    # 過去の会話履歴を読み込み
    history = load_conversation_history(user_id, group_id)
    context = format_conversation_context(history)
    context += "\n\n引用された会話:\n"
    if not(quoted_id == None):
        #print(f"履歴：{history}")
        for entry in history:
            #print(entry["message_id"])
            if entry['message_id'] == str(quoted_id):
                context += f"ユーザー: {entry['user_message']}\n"
                context += f"トモさん: {entry['bot_response']}\n\n"
    # ユーザー名と会話履歴を含めたシステム指示を作成
    with open(f"systempro.txt", "r", encoding="utf-8") as f:
        personalized_instruction = f.read()
    personalized_instruction += f"\n\nユーザー名: {user_name}\n\n過去の会話履歴:\n{context}"

    response = client.models.generate_content(
        model='gemini-2.5-flash-preview-05-20',
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=personalized_instruction,
            top_p= 0.7,
            temperature= 0.7,
            response_mime_type='text/plain'
        ),
    )
    
    bot_response = response.text
    
    # 会話履歴を保存
    save_conversation_to_file(user_id, prompt, bot_response, message_id, group_id)

    return bot_response

# 会話履歴を保存するためのディクショナリ（メモリ上での保存）
conversation_history = {}

def save_conversation_to_file(user_id, user_message, bot_response, message_id, group_id=None):
    """
    会話履歴をファイルに保存する
    """
    if group_id:
        history_file = f"conversations/{group_id}.json"
    else:
        history_file = f"conversations/{user_id}.json"

    # conversationsディレクトリが存在しない場合は作成
    os.makedirs("conversations", exist_ok=True)
    
    # 会話データ
    conversation_entry = {
        "user_id": user_id,
        "timestamp": datetime.now().isoformat(),
        "user_message": user_message,
        "bot_response": bot_response,
        "message_id": message_id
    }
    
    # 既存の履歴を読み込み
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
    else:
        history = []
    
    # 新しい会話を追加
    history.append(conversation_entry)
    
    # 履歴が20件を超えたら古いものから削除
    if len(history) > 20:
        history = history[-20:]
    
    # ファイルに保存
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_conversation_history(user_id, group_id=False):
    """
    ユーザーの会話履歴をファイルから読み込む
    """
    if group_id:
        history_file = f"conversations/{group_id}.json"
    else:
        history_file = f"conversations/{user_id}.json"

    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return []

def format_conversation_context(history):
    """
    会話履歴をコンテキストとして整形する
    """
    if not history:
        return ""
    
    context = "\n\n過去の会話:\n"
    # 最新5件の会話履歴を使用
    recent_history = history[-5:] if len(history) > 5 else history
    
    for entry in recent_history:
        context += f"ユーザー: {entry['user_message']}\n"
        context += f"トモさん: {entry['bot_response']}\n\n"
        

    return context


if __name__ == '__main__':
    # 会話履歴機能のテスト
    print("=== 会話履歴機能のテスト ===")
    test_user_id = "test_user_123"
    test_user_name = "太郎くん"
    
    response1 = generate_response_with_history("こんにちは、トモさん！", test_user_name, test_user_id)
    print(f"太郎くん: こんにちは、トモさん！")
    print(f"トモさん: {response1}")