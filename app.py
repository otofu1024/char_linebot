# 必要なライブラリをインポートします
from flask import Flask, request, abort
# from google import genai # gemini.py でインポートしているのでここでは不要かも
import config
import os
import gemini
import json
import requests
import datetime
import jma_weather_api


# LINE Messaging API SDK v3 をインポートします
from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent # TextMessage ではなく TextMessageContent
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage as V3TextMessage # 送信用のTextMessage
)

# config.py からLINE Botの認証情報、Gemini APIキーを取得します
GEMINI_API_KEY = config.GEMINI_API_KEY
LINE_CHANNEL_ACCESS_TOKEN = config.LINE_CHANNEL_ACCESS_TOKEN
LINE_CHANNEL_SECRET = config.LINE_CHANNEL_SECRET

# Flaskアプリケーションのインスタンスを作成します
app = Flask(__name__)

# LINE Bot API v3 の設定
if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    print("エラー: LINE_CHANNEL_ACCESS_TOKEN または LINE_CHANNEL_SECRET が設定されていません。")
    print("config.py の変数を確認してください。")
    messaging_api = None
    handler = None
else:
    configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
    # ApiClient のインスタンス化
    api_client_instance = ApiClient(configuration)
    # MessagingApi のインスタンス化
    messaging_api = MessagingApi(api_client_instance)
    handler = WebhookHandler(LINE_CHANNEL_SECRET)


# '/webhook' というURLパスにPOSTリクエストが来たときの処理を定義します
@app.route("/webhook", methods=['POST'])
def callback():
    if not handler:
        app.logger.error("エラー: WebhookHandlerが初期化されていません。")
        abort(500)
        return 'Internal Server Error'

    # リクエストヘッダーから署名を取得します
    signature = request.headers['X-Line-Signature']

    # リクエストボディ（本文）をテキストとして取得します
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body) # ログにリクエストボディを出力します（デバッグ用）

    # 署名を検証し、問題なければイベントを処理します
    try:
        # ★★★ handle_message に body も渡すように変更 ★★★
        events = handler.parser.parse(body, signature)
        for event in events:
            if isinstance(event, MessageEvent) and isinstance(event.message, TextMessageContent):
                handle_message(event, body) # body を渡す
            # 他のイベントタイプも必要に応じて処理
            # elif isinstance(event, FollowEvent):
            #     handle_follow(event)
            # elif ...

    except InvalidSignatureError:
        app.logger.error("無効な署名です。リクエストがLINEプラットフォームから来たものか確認してください。")
        abort(400) # 不正なリクエスト
    except Exception as e:
        app.logger.error(f"イベント処理のディスパッチ中にエラーが発生しました: {e}", exc_info=True)
        abort(500) # サーバー内部エラー

    return 'OK' # LINEプラットフォームに処理が正常に完了したことを伝えます


# テキストメッセージイベントを処理するハンドラを定義します
# ★★★ handle_message の引数に body を追加 ★★★
def handle_message(event: MessageEvent, request_body_str: str):
    if not messaging_api:
        app.logger.error("エラー: MessagingApiが初期化されていません。")
        return

    user_id = event.source.user_id if event.source else None
    if not user_id:
        app.logger.error("ユーザーIDが取得できませんでした。")
        return

    user_message = event.message.text
    message_id = event.message.id
    print(f"message_id: {message_id}")
    group_id = event.source.group_id if event.source and event.source.type == 'group' else None

    quoted_id = None
    try:
        # Webhookで受け取った生のJSON文字列(request_body_str)をパースして直接参照する
        webhook_data = json.loads(request_body_str)
        # 現在処理しているイベントに対応するデータを特定する
        # (複数のイベントが一度に来る可能性があるため、replyTokenで照合するのが確実)
        current_event_data = None
        for ev_data in webhook_data.get('events', []):
            if ev_data.get('replyToken') == event.reply_token:
                current_event_data = ev_data
                break
        
        if current_event_data and 'message' in current_event_data and 'quotedMessageId' in current_event_data['message']:
            quoted_id = current_event_data['message']['quotedMessageId']
        else:
            app.logger.info("リクエストボディのイベントデータに quotedMessageId が見つかりませんでした。")
            # SDKのオブジェクトからも試みる (フォールバックまたはデバッグ用)
            if hasattr(event.message, 'quote_token') and event.message.quote_token: # v3では quote_token がある
                app.logger.info(f"event.message.quote_token が存在します: {event.message.quote_token}")
                # quote_token から quotedMessageId を取得する直接的なAPIはSDKにはない
                # もしSDKの将来のバージョンで event.message.quoted_message_id のような属性が追加されたらそれを使う

    except json.JSONDecodeError:
        app.logger.error("リクエストボディのJSONパースに失敗しました（quoted_id取得時）。")
    except Exception as e:
        app.logger.error(f"quoted_id の取得中に予期せぬエラー: {e}", exc_info=True)

    app.logger.info(f"最終的に取得した quoted_id: {quoted_id}")

    user_name = "カミーユ" # デフォルト名
    try:
        # v3 SDK でのプロフィール取得
        profile_response = messaging_api.get_profile(user_id)
        user_name = profile_response.display_name
        app.logger.info(f"ユーザー名: {user_name}, メッセージ: {user_message}")
    except Exception as e:
        app.logger.error(f"プロフィール取得エラー: {e}", exc_info=True)

    if "天気" in user_message:
        # 天気情報を取得
        city_number = "140010" # 神奈川のシティコード
        if "明日" in user_message:
            reply_text = gemini.generate_weather_response(1, city_number)  # 明日の天気
        elif "明後日" in user_message:
            reply_text = gemini.generate_weather_response(2, city_number)  # 明後日の天気
        else:
            reply_text = gemini.generate_weather_response(0, city_number)
        try:
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[V3TextMessage(text=reply_text)]
                )
            )
        except Exception as e:
            app.logger.error(f"天気情報の返信中にエラー: {e}", exc_info=True)
    elif "授業" in user_message or "時間割" in user_message or "シラバス" in user_message:
        # カリキュラム情報を取得
        reply_text = gemini.generate_curriculum_response()
        try:
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[V3TextMessage(text=reply_text)]
                )
            )
        except Exception as e:
            app.logger.error(f"カリキュラム情報の返信中にエラー: {e}", exc_info=True)
    else:
        # ユーザーにテキストメッセージを返信します (v3 SDK)
        try:
            reply_text = gemini.generate_response_with_history(user_message, user_name, user_id, message_id, group_id, quoted_id)
            messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[V3TextMessage(text=reply_text)]
                )
            )
        except Exception as e:
            app.logger.error(f"メッセージの返信中にエラー: {e}", exc_info=True)


# このスクリプトが直接実行された場合にサーバーを起動します
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
