# 必要なライブラリをインポートします
from flask import Flask, request, abort
from google import genai
import config
import os
import gemini

# LINE Messaging API SDKをインポートします
# もしインストールしていない場合は、ターミナルで pip install line-bot-sdk と実行してください
from linebot import LineBotApi, WebhookHandler # line_bot_sdk ではなく linebot
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
)

# config.py からLINE Botの認証情報、Gemini APIキーを取得します
GEMINI_API_KEY = config.GEMINI_API_KEY
LINE_CHANNEL_ACCESS_TOKEN = config.LINE_CHANNEL_ACCESS_TOKEN
LINE_CHANNEL_SECRET = config.LINE_CHANNEL_SECRET

# Flaskアプリケーションのインスタンスを作成します
app = Flask(__name__)

# 環境変数からチャネルアクセストークンとチャネルシークレットを取得します
# これらはLINE Developersコンソールで確認できます
# セキュリティのため、直接コードに書き込むのではなく、環境変数に設定することを推奨します
# ローカルでテストする際は、これらの値を直接文字列として代入しても動作しますが、
# 公開するサーバーでは必ず環境変数を使用してください。

# LINE Bot APIとWebhookHandlerのインスタンスを作成します
# LINE_CHANNEL_ACCESS_TOKEN や LINE_CHANNEL_SECRET が None の場合、エラーになります。
# 実行前に環境変数が正しく設定されているか確認してください。
if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    print("エラー: LINE_CHANNEL_ACCESS_TOKEN または LINE_CHANNEL_SECRET が設定されていません。")
    print("変数を確認してください。")
    # ここでプログラムを終了させるか、デフォルト値を設定するなどの処理が必要です。
    # このサンプルでは、簡単のためこのまま進めますが、実際にはエラー処理をしっかり行いましょう。
    line_bot_api = None
    handler = None
else:
    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
    handler = WebhookHandler(LINE_CHANNEL_SECRET)


# '/webhook' というURLパスにPOSTリクエストが来たときの処理を定義します
# このURLはLINE DevelopersコンソールのWebhook URLに設定します
@app.route("/webhook", methods=['POST'])
def callback():
    if not handler:
        print("エラー: WebhookHandlerが初期化されていません。")
        abort(500) # サーバー内部エラー
        return 'Internal Server Error'

    # リクエストヘッダーから署名を取得します
    signature = request.headers['X-Line-Signature']

    # リクエストボディ（本文）をテキストとして取得します
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body) # ログにリクエストボディを出力します（デバッグ用）

    # 署名を検証し、問題なければイベントを処理します
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("無効な署名です。リクエストがLINEプラットフォームから来たものか確認してください。")
        abort(400) # 不正なリクエスト
    except Exception as e:
        print(f"イベント処理中にエラーが発生しました: {e}")
        abort(500) # サーバー内部エラー

    return 'OK' # LINEプラットフォームに処理が正常に完了したことを伝えます


# テキストメッセージイベントを処理するハンドラを定義します
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    if not line_bot_api:
        print("エラー: LineBotApiが初期化されていません。")
        return

    # ユーザーIDを取得
    user_id = event.source.user_id
    user_message = event.message.text # ユーザーが送信したメッセージ内容
    
    # ユーザーのプロフィール情報を取得
    try:
        profile = line_bot_api.get_profile(user_id)
        user_name = profile.display_name
        print(f"ユーザー名: {user_name}, メッセージ: {user_message}")
    except Exception as e:
        print(f"プロフィール取得エラー: {e}")
        user_name = "お友達"  # デフォルト名
    
    # ユーザー名を含めたプロンプトでGeminiに応答を生成させる（会話履歴付き）
    reply_text = gemini.generate_response_with_history(user_message, user_name, user_id)

    # ユーザーにテキストメッセージを返信します
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text))


# このスクリプトが直接実行された場合にサーバーを起動します
if __name__ == "__main__":
    
    # ポート番号は環境変数 PORT があればそれを使用し、なければデフォルトで5000番を使用します
    # HerokuなどのPaaS環境では、PORT環境変数が自動的に設定されることが多いです
    port = int(os.environ.get("PORT", 5000))
    # 開発中は debug=True にすると、コード変更時に自動でリロードされたり、エラー表示が詳細になったりして便利です。
    # 本番環境では debug=False にしてください。
    app.run(host="0.0.0.0", port=port, debug=True)
