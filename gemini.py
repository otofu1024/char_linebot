from google import genai
from google.genai import types
import config
import json
import os
from datetime import datetime, time
import requests
import jma_weather_api

GEMINI_API_KEY = config.GEMINI_API_KEY

client = genai.Client(api_key = GEMINI_API_KEY)

def generate_curriculum_response():
    """
    カリキュラム情報を生成する
    """
    now = datetime.now()
    weekdays_japanese = ["月曜日", "火曜日", "水曜日", "木曜日", "金曜日", "土曜日", "日曜日"]
    day_of_week_index = now.weekday()
    day_of_week_japanese = weekdays_japanese[day_of_week_index]
    print(f"今日の日付: {now.strftime('%Y-%m-%d')},  曜日: {day_of_week_japanese}")

    current_time = now.time()
    print(f"現在の時刻: {current_time}")
    
    try:
        with open("curriculum.json", "r", encoding="utf-8") as f:
            curriculum = json.load(f)
        with open(f"systempro.txt", "r", encoding="utf-8") as f:
            personalized_instruction = f.read()
        
        todays_curriculum = curriculum["schedule"].get(day_of_week_japanese, [])
        
        if not todays_curriculum:
            print("今日は授業がありません。")
            personalized_instruction += f"今日は授業がないようです。"
        else:
            remaining_classes = []
            for lecture in todays_curriculum:
                # 授業終了時刻をtimeオブジェクトに変換
                # lecture["time_end"] は "HH:MM" 形式と仮定
                try:
                    end_time_parts = list(map(int, lecture["time_end"].split(':')))
                    lecture_end_time = time(end_time_parts[0], end_time_parts[1])

                    # 現在時刻が授業終了時刻より前の場合、残りの授業とする
                    if current_time < lecture_end_time:
                        remaining_classes.append(lecture)
                except ValueError:
                    print(f"警告: 授業 '{lecture['subject']}' の時刻形式が無効です: {lecture['time_end']}")
                    continue # この授業をスキップして次に進む

            if remaining_classes:
                personalized_instruction += "今日の残りの授業:"
                for lecture in remaining_classes:
                    period_info = f"{lecture['period']}限"
                    location_info = lecture['location_or_detail'] if lecture['location_or_detail'] else "未定/オンラインなど"
                    personalized_instruction += f"\n  - 授業名: {lecture['subject']}"
                    personalized_instruction += f"\n    時限: {period_info}"
                    personalized_instruction += f"\n    場所/詳細: {location_info}"
                    personalized_instruction += f"\n    時間: {lecture['time_start']} - {lecture['time_end']}"
                    personalized_instruction += "\n" + "-" * 20 # 区切り線
            else:
                personalized_instruction += "今日の授業はすべて終了しました。"


        
        personalized_instruction += f"\n\n{todays_curriculum}"
        response = client.models.generate_content(
            model='gemini-2.5-flash-preview-05-20',
            contents=f"今は{current_time}です。残りの授業（授業名、開講場所について）をシャアらしく教えてください。",
            config=types.GenerateContentConfig(
                system_instruction=personalized_instruction,
                top_p= 0.7,
                temperature= 0.7,
                response_mime_type='text/plain'
            ),
        )
        return response.text
        
    except Exception as e:
        return f"カリキュラム情報の取得に失敗しました: {e}"

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
            contents="以下の天気情報を教えてください。",
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

    # カリキュラムのテスト
    print("\n=== カリキュラム情報のテスト ===")
    curriculum_response = generate_curriculum_response()
    print(f"トモさん: {curriculum_response}")