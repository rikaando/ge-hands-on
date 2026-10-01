"""Cloud Run 上で ADK エージェントを A2A プロトコルとして公開するエントリポイント."""

import os
import uvicorn
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from insurance_agent.agent import root_agent

os.environ.setdefault("ADK_SUPPRESS_A2A_EXPERIMENTAL_FEATURE_WARNINGS", "TRUE")

# ADK の root_agent を A2A 準拠の ASGI アプリに変換
app = to_a2a(root_agent)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
