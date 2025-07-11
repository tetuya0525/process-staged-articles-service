# main.py (Hello World Test for Pub/Sub Trigger)
# ==============================================================================
# このサービスが正しく起動し、Pub/Subからのトリガーを受け取れるかを
# 確認するための、最もシンプルなテスト用プログラムです。
# ==============================================================================
import functions_framework
import base64
import json

@functions_framework.cloud_event
def process_staged_articles(cloud_event):
    """
    Pub/Subメッセージを受け取ったら、その内容をログに出力するだけの、
    非常にシンプルな関数。
    """
    try:
        # Pub/Subメッセージをデコード
        message_data = base64.b64decode(cloud_event.data["message"]["data"]).decode("utf-8")
        message_json = json.loads(message_data)
        
        print("--- process-staged-articles-service (Hello World) ---")
        print(f"SUCCESS: Service was triggered successfully!")
        print(f"Received message: {message_json}")
        print("----------------------------------------------------")

    except Exception as e:
        print(f"ERROR: Failed to process Pub/Sub message. Error: {e}")
