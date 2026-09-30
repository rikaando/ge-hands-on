"""Cloud Run 上で ADK エージェントを A2A プロトコルとして公開するエントリポイント."""

import os
from urllib.parse import urlparse

os.environ.setdefault("ADK_SUPPRESS_A2A_EXPERIMENTAL_FEATURE_WARNINGS", "TRUE")

import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from insurance_agent.agent import root_agent

# Cloud Run の公開 URL（環境変数 AGENT_URL）からホスト・プロトコル・ポートを取得
agent_url = os.environ.get("AGENT_URL", "http://localhost:8080")
parsed = urlparse(agent_url)
protocol = parsed.scheme or "http"
host = parsed.hostname or "localhost"
port = parsed.port or (443 if protocol == "https" else int(os.environ.get("PORT", 8080)))

# ADK の root_agent を Gemini Enterprise 連携用の A2A サーバーに変換
app = to_a2a(root_agent, host=host, protocol=protocol, port=port)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
