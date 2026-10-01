# Gemini Enterprise ハンズオン応用編

このリポジトリは、Gemini Enterprise ハンズオン応用編（BigQuery Conversational Analytics エージェント作成、ADK 2.0 ワークフローエージェントの Cloud Run デプロイ、および Agent Designer × Google Workspace 連携）の資材一式です。

## 1. Cloud Shell でチュートリアルを起動する

以下のボタンを押すか、Cloud Shell ターミナルでコマンドを実行すると、画面右側にハンズオン手順（`tutorial.md`）が開きます。

[![Open in Cloud Shell](https://gstatic.com/cloudssh/images/open-btn.svg)](https://console.cloud.google.com/cloudshell/open?cloudshell_git_repo=https://github.com/rikaando/ge-hands-on&cloudshell_tutorial=tutorial.md)

すでに Cloud Shell を開いている場合は、以下の1行を実行してください。

```bash
git clone https://github.com/rikaando/ge-hands-on.git && cd ge-hands-on && cloudshell launch-tutorial tutorial.md
```

## 2. 作成するエージェントの概要

### テーマ1：保険金請求・お客さまの声分析エージェント（`claims_analyzer`）
企画部門や品質管理の担当者が、SQL を書かずにチャット上で
「犬・猫別の傷病ランキング」「プラン別の平均診療費」「お客さまの声」を
集計・グラフ化するためのエージェントです。
BigQuery に登録した請求データをもとにノーコードで作成し、
Gemini Enterprise から質問するだけで SQL の自動生成・集計・可視化までを実行します。

### テーマ2：保険金審査・照会サポートエージェント（`concierge_agent`）
保険金サービス部門などの担当者が、診療明細をもとに支払額の試算や
案内文作成を迅速に行うための業務支援エージェントです。
たとえば、診療明細の中に「外耳炎の治療（15,000円）」と「混合ワクチン（3,000円）」が
あわせて記載されている場合でも、約款ルールに沿って対象外のワクチン代を自動で除外し、
加入プランに応じた支払保険金・自己負担額の計算とお客さまへの案内トーク例を
一括で作成します。Google Cloud の ADK で作成した審査エージェントをデプロイし、
後半では Agent Designer を使って Gmail などと組み合わせた業務フローへ拡張します。

## 3. リポジトリ構成

* `tutorial.md` - Cloud Shell 右側ペインに表示されるハンズオン手順書（Step 1〜Step 9）
* `claims_sample.csv` - テーマ1で BigQuery に登録する保険金請求・お客さまの声サンプルデータ（100件）
* `claims_schema.json` - テーマ1で BigQuery テーブルに設定する全12カラムの日本語説明（Description）定義
* `insurance_agent/` - テーマ2で Cloud Run にデプロイする ADK 2.0 審査・試算ワークフローエージェント（`SequentialAgent`）
  * `agent.py` - ツール関数（2つ）と専門エージェント（`policy_checker` / `payout_calculator`）の直列ワークフロー定義
* `requirements.txt` - Python 依存パッケージ定義（`google-adk[a2a]>=2.0.0`）
* `main.py` / `Dockerfile` - A2A プロトコル公開用エントリーポイントおよびコンテナ定義
