# char_linebot

LINE Messaging API 連携のチャットボット実装です。Google の Generative AI（Gemini）を用いた応答生成、JMA（気象庁）API との連携による天気情報の提供、カリキュラム/会話フロー定義に基づくガイド付き対話をサポートします。

- 言語: Python 100%
- 主要機能:
  - LINE Webhook 受信・返信
  - Gemini を用いた自然言語応答（`gemini.py`）
  - 気象庁 API による天気情報取得（`jma_weather_api.py`）
  - カリキュラム/会話フローの外部定義（`curriculum.json`, `conversations/`）
  - システムプロンプトの外部管理（`systempro.txt`）
  - 設定の一元管理（`config.py`）

## リポジトリ構成

```
.
├─ app.py                 # アプリケーションのエントリポイント（Webhook サーバ）
├─ config.py              # 環境変数/設定の読み込み
├─ gemini.py              # Gemini（Generative AI）との連携ロジック
├─ jma_weather_api.py     # 気象庁 API からの天気情報取得
├─ curriculum.json        # 学習/ガイド用カリキュラム定義
├─ systempro.txt          # システムプロンプト定義
├─ conversations/         # 会話フロー/プロンプトの追加定義
├─ check.py               # 簡易チェック/ヘルスチェック用スクリプト（任意）
└─ README.md
```

## 動作要件

- Python 3.10 以上を推奨
- LINE Developers にて Messaging API チャネルを作成済みであること
- 外部アクセス可能な Webhook URL（開発時は ngrok 等でトンネリング）

依存パッケージ（例）:
- line-bot-sdk
- requests
- google-generativeai（Gemini 連携）
- Flask（または同等の WSGI/ASGI フレームワーク）
- python-dotenv（任意、ローカルでの環境変数管理向け）

> 実装に合わせて必要なパッケージを追加してください。`requirements.txt` が未整備の場合は、以下のように手動でインストールできます。

```bash
pip install line-bot-sdk requests google-generativeai flask python-dotenv
```

## 環境変数

以下の環境変数を設定してください（.env の利用可）:

- LINE_CHANNEL_SECRET: LINE チャネルシークレット
- LINE_CHANNEL_ACCESS_TOKEN: LINE チャネルアクセストークン（長期）
- GOOGLE_API_KEY: Google Generative AI（Gemini）用 API キー
- PORT: 起動ポート（ホスティング環境により自動で渡される場合あり）

（任意）
- 各種気象情報取得に関する地域コード等（必要に応じて `jma_weather_api.py` 実装に合わせて設定）

`.env` 例:

```
LINE_CHANNEL_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LINE_CHANNEL_ACCESS_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
PORT=8080
```

## セットアップ・起動

1) 依存パッケージのインストール
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U pip
# requirements.txt がある場合
# pip install -r requirements.txt
# 無い場合（例）
pip install line-bot-sdk requests google-generativeai flask python-dotenv
```

2) 環境変数の設定（`.env` またはシェルでエクスポート）

3) ローカル起動
```bash
python app.py
# または実装に応じて
# flask run
```

4) Webhook 公開（ローカル開発時）
```bash
ngrok http 8080
# 生成された https URL を LINE Developers の Webhook URL に設定
```

5) LINE Developers で以下を設定
- チャネル基本設定 > Webhook URL に ngrok（または本番 URL）を登録
- Messaging API > Webhook を有効化
- 応答メッセージ/リッチメニュー等は必要に応じて設定

## 機能詳細

- Gemini 応答（`gemini.py`）
  - システムプロンプト（`systempro.txt`）とユーザ入力をもとに、Google Generative AI へ問い合わせて応答を生成
- 天気情報（`jma_weather_api.py`）
  - 気象庁の公開 API から天気/警報等のデータを取得し、ユーザに提供
- カリキュラム/会話フロー（`curriculum.json`, `conversations/`）
  - 対話の進行や学習支援のためのステップ/トピックを外部定義
  - 追加・編集によりボットの振る舞いを拡張可能
- 設定管理（`config.py`）
  - 環境変数の読み込み、キー管理など

## 拡張・開発ガイド

- システムプロンプトの調整: `systempro.txt` を編集
- 会話シナリオの追加: `conversations/` 配下に新規ファイルを追加、`curriculum.json` に参照を追加
- 外部 API の追加: 新規 `xxx_api.py` を作成し、`app.py` 内のハンドラから呼び出す
- 依存パッケージの固定化: プロジェクトに合わせて `requirements.txt` を作成し、`pip freeze > requirements.txt` などで管理

## デプロイ

- 任意の Python ホスティング（Render, Railway, Fly.io, Google Cloud Run, Heroku 互換など）へデプロイ可能
- 必要事項
  - 環境変数の登録（LINE/Google API キー等）
  - Web サーバの起動コマンド設定（`python app.py` または `gunicorn app:app` など実装に合わせる）
  - 外部から到達可能な Webhook URL を LINE Developers に設定

## セキュリティ注意

- アクセストークン/シークレットはリポジトリにコミットしない
- キーのローテーションを定期的に実施
- Webhook 署名検証（`X-Line-Signature`）を有効にする（実装済みであることを確認）

## ライセンス

- 現時点でライセンスファイルは未設定です。プロジェクト方針に従い `LICENSE` を追加してください（例: MIT License）。

## 謝辞

- [LINE Messaging API](https://developers.line.biz/ja/services/messaging-api/)
- [Google Generative AI (Gemini)](https://ai.google.dev/)
- [気象庁防災情報](https://www.jma.go.jp/bosai/)

## 作者

- GitHub: [otofu1024](https://github.com/otofu1024)

不明点や改善提案があれば Issue/PR を歓迎します。
