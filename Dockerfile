# Dockerfile
# ==============================================================================
# 建築手順書 (シンプルテスト版)
# ==============================================================================

# ベースイメージとして、公式のPython 3.12安定版を使用します。
FROM python:3.12-slim

# コンテナ内の作業ディレクトリを設定します。
WORKDIR /app

# まず、依存関係ファイル(部品リスト)をコピーします。
COPY requirements.txt .

# 部品リストに基づいて、必要なライブラリをインストールします。
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションの本体であるソースコードをコピーします。
COPY main.py .

# functions-frameworkを使って、Pub/Subイベントを処理する関数を起動します。
CMD ["functions-framework", "--target=process_staged_articles", "--signature-type=event"]

