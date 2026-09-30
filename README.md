# Gemini Enterprise ハンズオン応用編

このリポジトリは、Gemini Enterprise ハンズオン応用編（BigQuery Conversational Analytics エージェント作成、ADK 2.0 ワークフローエージェントの Cloud Run デプロイ、および Agent Designer × Google Workspace 連携）の資材一式です。

## 1. Cloud Shell でチュートリアルを起動する

以下のボタンを押すか、Cloud Shell ターミナルでコマンドを実行すると、画面右側にハンズオン手順（`tutorial.md`）が開きます。

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://console.cloud.google.com/cloudshell/open?cloudshell_git_repo=https://github.com/rikaando/ge-hands-on&cloudshell_tutorial=tutorial.md)

すでに Cloud Shell を開いている場合は、以下の1行を実行してください。

```bash
git clone https://github.com/rikaando/ge-hands-on.git && cd ge-hands-on && cloudshell launch-tutorial tutorial.md
```

## 2. リポジトリ構成

* `tutorial.md` - Cloud Shell 右側ペインに表示されるハンズオン手順書（Step 1〜Step 8）
* `claims_sample.csv` - テーマ1で BigQuery に登録する保険金請求・お客さまの声サンプルデータ（100件）
* `claims_schema.json` - テーマ1で BigQuery テーブルに設定する全12カラムの日本語説明（Description）定義
* `insurance_agent/` - テーマ2で Cloud Run にデプロイする ADK 2.0 審査・試算ワークフローエージェント（`SequentialAgent`）
  * `agent.py` - ツール関数（2つ）と専門エージェント（`policy_checker` / `payout_calculator`）の直列ワークフロー定義
  * `requirements.txt` - Python 依存パッケージ定義（`google-adk[a2a]>=2.0.0`）
* `main.py` / `Dockerfile` - A2A プロトコル公開用エントリーポイントおよびコンテナ定義
