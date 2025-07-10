# main.py
# ==============================================================================
# Memory Library - Process Staged Articles Service
# Role:         Listens for a trigger, processes one article from the staging
#               area, and passes it to the next service in the pipeline.
# Version:      1.0 (Simple, Non-AI version)
# Author:       心理 (Thinking Partner)
# ==============================================================================
import functions_framework
import os
import firebase_admin
from firebase_admin import firestore
from google.cloud import pubsub_v1
from datetime import datetime, timezone

# --- 定数 (Constants) ---
SERVICE_NAME = "process-staged-articles-service"
# 憲章2.6に基づき、設定は環境変数から取得します。
PROJECT_ID = os.environ.get('GCP_PROJECT')
NEXT_TOPIC_ID = os.environ.get('INTEGRATE_BOOKS_TOPIC_ID') # 次の「図書編纂係」を呼び出すトピック

# --- 初期化 (Initialization) ---
db = None
publisher = None
next_topic_path = None

try:
    firebase_admin.initialize_app()
    db = firestore.client()
    if PROJECT_ID and NEXT_TOPIC_ID:
        publisher = pubsub_v1.PublisherClient()
        next_topic_path = publisher.topic_path(PROJECT_ID, NEXT_TOPIC_ID)
    else:
        print(f"CRITICAL in {SERVICE_NAME}: GCP_PROJECT or INTEGRATE_BOOKS_TOPIC_ID env vars not set.")
except Exception as e:
    print(f"CRITICAL in {SERVICE_NAME}: Initialization failed. Error: {e}")


@functions_framework.cloud_event
def process_staged_articles(cloud_event):
    """
    Pub/Subメッセージをトリガーとして、staging_articlesから記事を1件処理する。
    """
    print(f"INFO in {SERVICE_NAME}: Service triggered by message ID: {cloud_event['id']}")

    if not db or not publisher or not next_topic_path:
        print(f"ERROR in {SERVICE_NAME}: Service is not properly configured. Aborting.")
        return

    try:
        # 憲章3.3に基づき、ステータスが'received'のものを1件だけ取得
        docs_query = db.collection('staging_articles').where('status', '==', 'received').limit(1)
        docs = list(docs_query.stream())

        if not docs:
            print(f"INFO in {SERVICE_NAME}: No articles with status 'received' found. Nothing to do.")
            return

        target_doc = docs[0]
        doc_ref = target_doc.reference
        doc_id = target_doc.id

        print(f"INFO in {SERVICE_NAME}: Processing article: {doc_id}")

        # ステータスを更新し、次の工程へ進んだことを記録
        update_data = {
            'status': 'processed_for_integration', # 次は統合(integration)の工程
            'updatedAt': datetime.now(timezone.utc)
        }
        doc_ref.update(update_data)

        # 次のAI司書（図書編纂係）に、仕事を依頼するメッセージを送信
        message_data = str(doc_id).encode('utf-8')
        future = publisher.publish(next_topic_path, message_data)
        future.result() # 送信完了を待つ

        print(f"SUCCESS in {SERVICE_NAME}: Article {doc_id} processed and message sent to topic '{NEXT_TOPIC_ID}'.")

    except Exception as e:
        print(f"ERROR in {SERVICE_NAME}: An error occurred during processing. Error: {e}")
        # TODO: エラーハンドリングを強化（例：失敗ステータスに更新、エラーログサービスへの報告）
