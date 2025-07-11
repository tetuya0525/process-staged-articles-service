# main.py
# ==============================================================================
# 図書分類係の魂 (再検証・確定版)
# functions-frameworkへの依存をなくし、標準的なWebフレームワークであるFlaskで
# 直接アプリケーションを起動するように、構造を完全に刷新しました。
# これにより、特定のフレームワークが原因で起動に失敗する、という問題を根絶します。
# ==============================================================================
import os
import firebase_admin
from firebase_admin import firestore
from google.cloud import pubsub_v1
from datetime import datetime, timezone
from flask import Flask, request, jsonify
import base64
import json

# --- Flaskアプリケーションの初期化 ---
# これが、gunicornが起動する本体です。
app = Flask(__name__)

# --- 定数 (Constants) ---
SERVICE_NAME = "process-staged-articles-service"
PROJECT_ID = os.environ.get('GCP_PROJECT')
NEXT_TOPIC_ID = os.environ.get('INTEGRATE_BOOKS_TOPIC_ID')

# --- 初期化 (Initialization) ---
db = None
publisher = None
next_topic_path = None
is_configured = False

try:
    firebase_admin.initialize_app()
    db = firestore.client()
    if PROJECT_ID and NEXT_TOPIC_ID:
        publisher = pubsub_v1.PublisherClient()
        next_topic_path = publisher.topic_path(PROJECT_ID, NEXT_TOPIC_ID)
        is_configured = True
    else:
        print(f"CRITICAL in {SERVICE_NAME}: GCP_PROJECT or INTEGRATE_BOOKS_TOPIC_ID env vars not set.")
except Exception as e:
    print(f"CRITICAL in {SERVICE_NAME}: Initialization failed. Error: {e}")

# ★★★【最重要・再検証】リクエスト処理の入り口 ★★★
# Pub/SubからのPOSTリクエストを、ルートパス("/")で受け付けます。
@app.route("/", methods=["POST"])
def process_staged_articles():
    """
    Pub/Subメッセージをトリガーとして、staging_articlesから記事を1件処理する。
    """
    # Pub/Subからのリクエストボディは、特定の形式になっています。
    envelope = request.get_json()
    if not envelope or "message" not in envelope:
        print(f"ERROR: Invalid Pub/Sub message format: {envelope}")
        return "Bad Request: invalid Pub/Sub message format", 400

    # 実際のメッセージは、base64でエンコードされています。
    pubsub_message = base64.b64decode(envelope["message"]["data"]).decode("utf-8")
    print(f"INFO in {SERVICE_NAME}: Service triggered by message: {pubsub_message}")

    if not is_configured:
        print(f"ERROR in {SERVICE_NAME}: Service is not properly configured. Aborting.")
        return "Server Error: not configured", 500

    try:
        docs_query = db.collection('staging_articles').where('status', '==', 'received').limit(1)
        docs = list(docs_query.stream())

        if not docs:
            print(f"INFO in {SERVICE_NAME}: No articles with status 'received' found.")
            return "OK", 200 # 処理対象がなくても正常終了

        target_doc = docs[0]
        doc_ref = target_doc.reference
        doc_id = target_doc.id

        print(f"INFO in {SERVICE_NAME}: Processing article: {doc_id}")

        update_data = {'status': 'processed_for_integration', 'updatedAt': datetime.now(timezone.utc)}
        doc_ref.update(update_data)

        message_data = str(doc_id).encode('utf-8')
        future = publisher.publish(next_topic_path, message_data)
        future.result()

        print(f"SUCCESS in {SERVICE_NAME}: Article {doc_id} processed and message sent to topic '{NEXT_TOPIC_ID}'.")
        return "OK", 200

    except Exception as e:
        print(f"ERROR in {SERVICE_NAME}: An error occurred during processing. Error: {e}")
        return "Server Error", 500

# ローカルテスト用の起動設定
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
