from google import genai
from google.genai import types
import config
import json
import os
from datetime import datetime

GEMINI_API_KEY = config.GEMINI_API_KEY

client = genai.Client(api_key = GEMINI_API_KEY)

def generate_response(prompt):
    
    response = client.models.generate_content(
        model='gemini-2.5-flash-preview-05-20',
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction='あなたは物知りな昭和レトロな世話焼きおばあちゃんです。「トモさん」と回りからは呼ばれています。同級生の男の子からの質問に答えてください。回答は200字以内でお願いします。',
            top_p= 0.5,
            temperature= 0.5,
            response_mime_type='text/plain'
        ),
    )
    return response.text

def generate_response_with_name(prompt, user_name):
    """
    ユーザー名を含めてパーソナライズされた応答を生成する
    """
    # ユーザー名を含めたシステム指示を作成
    personalized_instruction = f'あなたは物知りな昭和レトロな世話焼きおばあちゃんです。「トモさん」と回りからは呼ばれています。今回は「{user_name}」という名前の近所の子どもからの質問に答えてください。相手の名前を適度に呼びかけながら、親しみやすく答えてください。回答は200字以内でお願いします。'
    
    response = client.models.generate_content(
        model='gemini-2.5-flash-preview-05-20',
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=personalized_instruction,
            top_p= 0.5,
            temperature= 0.5,
            response_mime_type='text/plain'
        ),
    )
    return response.text

def generate_response_with_history(prompt, user_name, user_id):
    """
    会話履歴を考慮してパーソナライズされた応答を生成する
    """
    # 過去の会話履歴を読み込み
    history = load_conversation_history(user_id)
    context = format_conversation_context(history)
    
    # ユーザー名と会話履歴を含めたシステム指示を作成
    personalized_instruction = f'''あなたは物知りな昭和レトロな世話焼きおばあちゃんです。「トモさん」と回りからは呼ばれています。
今回は「{user_name}」という名前の近所の子どもからの質問に答えてください。
相手の名前を適度に呼びかけながら、親しみやすく答えてください。
過去の会話があれば、それを参考にして一貫性のある応答をしてください。
回答は200字以内でお願いします。

{context}'''
    
    response = client.models.generate_content(
        model='gemini-2.5-flash-preview-05-20',
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=personalized_instruction,
            top_p= 0.5,
            temperature= 0.5,
            response_mime_type='text/plain'
        ),
    )
    
    bot_response = response.text
    
    # 会話履歴を保存
    save_conversation_to_file(user_id, prompt, bot_response)
    
    return bot_response

# 会話履歴を保存するためのディクショナリ（メモリ上での保存）
conversation_history = {}

def save_conversation_to_file(user_id, user_message, bot_response):
    """
    会話履歴をファイルに保存する
    """
    history_file = f"conversations/{user_id}.json"
    
    # conversationsディレクトリが存在しない場合は作成
    os.makedirs("conversations", exist_ok=True)
    
    # 会話データ
    conversation_entry = {
        "timestamp": datetime.now().isoformat(),
        "user_message": user_message,
        "bot_response": bot_response
    }
    
    # 既存の履歴を読み込み
    if os.path.exists(history_file):
        with open(history_file, 'r', encoding='utf-8') as f:
            history = json.load(f)
    else:
        history = []
    
    # 新しい会話を追加
    history.append(conversation_entry)
    
    # 履歴が10件を超えたら古いものから削除
    if len(history) > 10:
        history = history[-10:]
    
    # ファイルに保存
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def load_conversation_history(user_id):
    """
    ユーザーの会話履歴をファイルから読み込む
    """
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
    
    # 1回目の会話
    print("1回目の会話:")
    response1 = generate_response_with_history("こんにちは、トモさん！", test_user_name, test_user_id)
    print(f"太郎くん: こんにちは、トモさん！")
    print(f"トモさん: {response1}")
    
    # 2回目の会話
    print("\n2回目の会話:")
    response2 = generate_response_with_history("今日は学校で数学のテストがあったんだ", test_user_name, test_user_id)
    print(f"太郎くん: 今日は学校で数学のテストがあったんだ")
    print(f"トモさん: {response2}")
    
    # 3回目の会話（前の会話を覚えているかテスト）
    print("\n3回目の会話:")
    response3 = generate_response_with_history("あのテストの結果、気になるなあ", test_user_name, test_user_id)
    print(f"太郎くん: あのテストの結果、気になるなあ")
    print(f"トモさん: {response3}")
    
    # 保存された会話履歴を確認
    print("\n=== 保存された会話履歴 ===")
    history = load_conversation_history(test_user_id)
    for i, entry in enumerate(history, 1):
        print(f"{i}. {entry['timestamp']}")
        print(f"   ユーザー: {entry['user_message']}")
        print(f"   トモさん: {entry['bot_response']}")
        print()

    # 新しい機能（会話履歴を考慮した応答生成）のテスト
    print("\n=== 会話履歴を考慮した応答生成のテスト ===")
    user_id = "user_123"
    user_name = "タロウ"
    user_prompt_5 = "そういえば、前に教えてもらったレシピ、試してみたよ！"
    response_text_5 = generate_response_with_history(user_prompt_5, user_name, user_id)
    print("トモさん:")
    print(response_text_5)

    user_prompt_6 = "やっぱり、トモさんのアドバイス通りにしてよかった！"
    response_text_6 = generate_response_with_history(user_prompt_6, user_name, user_id)
    print("トモさん:")
    print(response_text_6)
