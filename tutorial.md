# Gemini Enterprise ハンズオン応用編

このチュートリアルでは、社内業務で活用する性質の異なる2つのエージェントを作成し、Gemini Enterpriseにパブリッシュして活用する流れを体験します。

1. テーマ1では、保険金請求・お客さまの声データを BigQuery に登録し、対話型分析エージェント（`claims_analyzer`）を作成して連携します。
2. テーマ2では、社内担当者向けの保険金審査・照会サポートワークフロー（ADK 2.0 エージェント `concierge_agent`）を Cloud Run にデプロイし、A2A 登録して呼び出します。

右下の **「開始（Start）」** をクリックして Step 1 に進んでください。

## Step 1: 事前準備（API有効化と権限設定）

エージェントの作成・デプロイに必要な API を有効化し、Gemini Enterprise が Cloud Run 上のエージェントを安全に呼び出せるよう実行権限（`roles/run.invoker`）とモデル利用権限（`roles/aiplatform.user`）を付与します。

コードブロック右上の **「Cloud Shell にコピー」** ボタンをクリックし、ターミナルで **Enter キー** を押してください（初回に「Cloud Shell の承認 / Authorize」が表示された場合は **承認** をクリックします）。

```bash
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
export PROJECT_NUMBER=$(gcloud projects describe ${GOOGLE_CLOUD_PROJECT} --format="value(projectNumber)")
export GOOGLE_CLOUD_LOCATION="us-central1"

gcloud services enable bigquery.googleapis.com run.googleapis.com \
  cloudbuild.googleapis.com artifactregistry.googleapis.com \
  aiplatform.googleapis.com discoveryengine.googleapis.com \
  geminidataanalytics.googleapis.com cloudaicompanion.googleapis.com \
  dataplex.googleapis.com agentregistry.googleapis.com

gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT} \
  --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --condition=None --no-user-output-enabled --quiet

gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT} \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user" \
  --condition=None --no-user-output-enabled --quiet

echo "Step 1 setup complete."
```

（※補足：もし Gemini Enterprise App が別プロジェクトにある場合のみ、以下の `GEMINI_ENTERPRISE_PROJECT_ID` を実際のプロジェクト ID に書き換えて実行してください。同一プロジェクトの場合は不要です）

```bash
export GE_PROJECT_NUMBER=$(gcloud projects describe GEMINI_ENTERPRISE_PROJECT_ID --format="value(projectNumber)")
gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT} \
  --member="serviceAccount:service-${GE_PROJECT_NUMBER}@gcp-sa-discoveryengine.iam.gserviceaccount.com" \
  --role="roles/run.invoker" \
  --condition=None --no-user-output-enabled --quiet
```

実行が完了したら **「次へ（Next）」** をクリックしてください。

## Step 2: テーマ1（1/3）BigQuery へのサンプルデータとスキーマ説明の登録

エージェントが分析時に参照する元データとして、保険金請求・お客さまの声データ（`claims_sample.csv`・全100件）と各カラムの日本語説明（`claims_schema.json`）を BigQuery の `insurance_demo.claims` テーブルへ一括ロードします（テーブルとカラムに Description を設定することで、次のステップで作成する Conversational Analytics エージェントの SQL 生成精度が向上します）。

コードブロック右上の **「Cloud Shell にコピー」** ボタンをクリックし、ターミナルで **Enter キー** を押して実行してください。

```bash
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
bq --location=US mk -d -f ${GOOGLE_CLOUD_PROJECT}:insurance_demo
bq load --replace --source_format=CSV --skip_leading_rows=1 \
  ${GOOGLE_CLOUD_PROJECT}:insurance_demo.claims \
  ./claims_sample.csv ./claims_schema.json
bq update --description="保険金請求およびお客さまの声（VOC）の明細データ（全100件）" \
  ${GOOGLE_CLOUD_PROJECT}:insurance_demo.claims
echo "CSV upload complete."
```

`Upload complete.` と表示されたら **「次へ（Next）」** をクリックしてください。

## Step 3: テーマ1（2/3）BigQuery で分析エージェント（Conversational Analytics）を作成

BigQuery の Conversational Analytics（Data Agent）機能を使い、Step 2 で登録したテーブル（カラム説明付き）と自然言語の指示（Instructions）を紐づけて、質問に応じて自動的に SQL を生成・集計するエージェントを作成します。

1. [BigQuery コンソール](https://console.cloud.google.com/bigquery) を開き（画面左上のプロジェクトがハンズオン用プロジェクトになっていることを確認）、左メニューの **「Agents（エージェント）」** → **「Agent catalog（エージェント カタログ）」**（または「新しいチャット」画面右端）の **「+ New agent（+ 新しいエージェント）」** をクリックします。
2. **Agent name（エージェント名）** 欄に `claims_analyzer`、**Agent description（説明）** 欄に `保険金請求・お客さまの声データを集計・分析するエージェント` と入力します（Region は `US` または `Global` を選択します）。
3. **Knowledge sources（ナレッジソース）** 欄の **「+ Add source（ソースを追加）」** から **`insurance_demo` -> `claims`** テーブルにチェックを入れて **「Add（追加）」** をクリックします（Step 2 で設定したテーブル・全12カラムの日本語 Description が自動的に読み込まれます）。
4. **Agent instructions（エージェントへの指示）** 欄に以下をコピペします。
   ```text
   あなたは保険金請求・お客さまの声（VOC）データを分析するアシスタントです。
   - 傷病カテゴリ（disease_category）の件数ランキングを出す際は、同率順位も省略せず表示してください。
   - 金額の集計時は、診療費（medical_fee_yen）と支払保険金（payout_yen）を円単位で分かりやすく表示してください。
   - お客さまの声（customer_voice）の分析時は、精算方法（claim_method）ごとの傾向や改善要望を要約してください。
   ```
5. 画面右上の **「Publish（公開）」** ボタンをクリックし、開いたダイアログの **Additional channels** で **「Integrate via A2A (Agent2Agent)」の「Copy JSON」** をクリックして JSON をコピー（または Agent Gateway 設定済みの場合は **「Register this agent」** にチェック）し、ダイアログ右下の **「Publish（公開）」** をクリックします。

公開が完了したら **「次へ（Next）」** をクリックしてください。

## Step 4: テーマ1（3/3）Gemini Enterprise App に登録して分析

公開した BigQuery エージェントを既存の Gemini Enterprise App に接続し、チャット画面から `@メンション` でデータを集計できることを確認します。

1. [Gemini Enterprise 管理コンソール](https://console.cloud.google.com/gemini-enterprise) で対象の App を選び、左メニュー **「Agents」** → **「+ Add Agents（または Add agent）」** をクリックします。
2. **「Custom agent via A2A」** の **「Add」** をクリックし、Step 3 でコピーした JSON を貼り付けて **「Preview agent details」** → **「Next」** をクリックします（Agent Gateway 設定済みの場合は **「Agents from Agent Registry」** から `claims_analyzer` を選択しても登録できます）。
3. 認証設定は **「Default Google-managed credentials」** を選択して **「Finish」** をクリックします。
4. Gemini Enterprise の Web App（チャット画面）を開き、**ブラウザの再読み込み（リロード）** を行ってから、チャット欄で `@claims_analyzer` を選択して以下の質問を送信してみましょう。

```text
@claims_analyzer 犬と猫それぞれで請求件数が多い傷病トップ3（同率含む）と、プラン別（あんしんプラン 70%・50%・ライト・キュート）の平均診療費・平均支払保険金を教えて
```

```text
@claims_analyzer 窓口精算・WEB請求・郵送請求それぞれの利用率と、お客さまの声（customer_voice）にある改善要望の傾向をまとめて
```

確認できたら **「次へ（Next）」** をクリックしてください。

## Step 5: テーマ2（1/3）ADK 2.0 ワークフローエージェントのコード確認

ここからはテーマ2として、社内担当者（査定・サポート部門）向けに **「①約款・対象外チェック → ②支払保険金試算＆案内文作成」を2段階のパイプラインで自動実行する ADK 2.0 ワークフローエージェント** のコードを確認します。

以下のボタンをクリックすると、Cloud Shell エディタで `insurance_agent/agent.py` と `main.py` が開きます。

<walkthrough-editor-open-file filePath="insurance_agent/agent.py">insurance_agent/agent.py をエディタで開く</walkthrough-editor-open-file>

<walkthrough-editor-open-file filePath="main.py">main.py をエディタで開く</walkthrough-editor-open-file>

* 1つ目のブロックでは、2つのツール（Python 関数）を定義しています。`check_coverage_rules` は診療内容からワクチン等の予防処置（補償対象外）の有無と審査に必要な書類を判定し、`calculate_payout` は補償対象額とプラン（70%・50%・ライト・キュート）から支払保険金と自己負担額を計算します。
* 2つ目のブロックでは、2つの専門エージェント（`Agent`）を定義しています。1段目の `policy_checker` が約款・対象外チェックを行って結果を `output_key="policy_check_result"` に渡し、2段目の `payout_calculator` が `{policy_check_result}` を受け取って支払額試算と「社内審査メモ＋お客さま案内トーク例」を作成します。
* 3つ目のブロックでは、`root_agent = SequentialAgent(..., sub_agents=[policy_checker, payout_calculator])` で2つのエージェントを直列につなぎ、`main.py` の `to_a2a(root_agent)` で A2A サーバーとして公開しています。

コードの編集は不要です。確認したら **「次へ（Next）」** をクリックしてください。

## Step 6: テーマ2（2/3）Cloud Run へのデプロイと JSON 出力

ADK 2.0 ワークフローエージェントを Cloud Run にデプロイし、Gemini Enterprise に登録するための名刺ファイル（`agent_card.json`）を生成します（完了まで約2〜3分かかります）。

コードブロック右上の **「Cloud Shell にコピー」** ボタンをクリックし、ターミナルで **Enter キー** を押して実行してください。

```bash
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
export PROJECT_NUMBER=$(gcloud projects describe ${GOOGLE_CLOUD_PROJECT} --format="value(projectNumber)")
export GOOGLE_CLOUD_LOCATION="us-central1"
export AGENT_URL="https://insurance-concierge-agent-${PROJECT_NUMBER}.${GOOGLE_CLOUD_LOCATION}.run.app"

gcloud run deploy insurance-concierge-agent \
  --source . \
  --region=${GOOGLE_CLOUD_LOCATION} \
  --project=${GOOGLE_CLOUD_PROJECT} \
  --memory=1Gi \
  --no-allow-unauthenticated \
  --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},GOOGLE_CLOUD_LOCATION=global,AGENT_URL=${AGENT_URL}" \
  --quiet

export AGENT_URL=$(gcloud run services describe insurance-concierge-agent --region=${GOOGLE_CLOUD_LOCATION} --project=${GOOGLE_CLOUD_PROJECT} --format="value(status.url)")

cat <<EOF > agent_card.json
{
  "protocolVersion": "0.3.0",
  "name": "concierge_agent",
  "description": "社内担当者向けに「①約款・対象外チェック → ②支払保険金試算＆案内文作成」を自動実行する審査サポートエージェント",
  "url": "${AGENT_URL}",
  "version": "1.0.0",
  "capabilities": {
    "streaming": false
  },
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/plain"],
  "skills": [
    {
      "id": "claims_review_workflow",
      "name": "保険金審査・支払額試算ワークフロー",
      "description": "診療内容から約款上の対象外項目・必要書類を判定し、プラン別の支払保険金・自己負担額の試算とお客さま案内トーク例を作成します。",
      "tags": ["insurance", "workflow", "claims-review"],
      "examples": [
        "あんしんプラン 70%で、通院（外耳炎15,000円、ワクチン3,000円）を窓口精算するといくら出る？",
        "あんしんプラン ライトで、椎間板ヘルニアの手術28万円をWEB請求するといくら出る？"
      ]
    }
  ]
}
EOF
echo "=== 以下の JSON をコピーして Gemini Enterprise の Custom agent via A2A に貼り付けてください ==="
cat agent_card.json
```

デプロイ完了後、ターミナルに出力された **`{` から `}` までの JSON 部分のみ** をコピーして **「次へ（Next）」** をクリックしてください（以下のボタンで `agent_card.json` をエディタで開いて全選択コピーすると確実です）。

<walkthrough-editor-open-file filePath="agent_card.json">生成された agent_card.json をエディタで開く</walkthrough-editor-open-file>

## Step 7: テーマ2（3/3）Gemini Enterprise App に登録して業務照会テスト

出力された `agent_card.json` を既存の Gemini Enterprise App に A2A 登録し、短い1行の質問だけで「①約款・対象外チェック → ②支払額試算 → ③お客さま案内トーク例」が自動出力されることを確認します。

1. [Gemini Enterprise 管理コンソール](https://console.cloud.google.com/gemini-enterprise) で対象の App を選び、左メニュー **「Agents」** → **「+ Add Agents（または Add agent）」** をクリックします。
2. **「Custom agent via A2A」** の **「Add」** をクリックし、**「Agent card JSON」** 欄に Step 6 でコピーした JSON をそのまま貼り付けます。
3. **「Preview agent details」** → **「Next」** をクリックし、続く認証設定画面では何も変更せず **「Skip & Finish」** をクリックして登録を完了します（Step 1 で Cloud Run 側の IAM 呼び出し権限を付与済みのため追加設定は不要です）。
4. Gemini Enterprise の Web App（チャット画面）を開き、**ブラウザの再読み込み（リロード）** を行ってから、チャット欄で `@concierge_agent` を選択して以下のプロンプトを送信してみましょう。

```text
@concierge_agent あんしんプラン 70%で、通院（外耳炎15,000円、ワクチン3,000円）を窓口精算するといくら出る？
```

```text
@concierge_agent あんしんプラン ライトで、椎間板ヘルニアの手術28万円をWEB請求するといくら出る？
```

確認できたら **「次へ（Next）」** をクリックしてください。

## Step 8: 応用編まとめ（Agent Designer で ADK エージェントと Google Workspace を連携）

最後に、Step 7 で登録した ADK エージェント（`concierge_agent`）をワークフローの1ステップとして呼び出し、試算結果と案内トーク例を Google Workspace（Gmail 等）へ自動連携するノーコード・ワークフローを Agent Designer（Workflow Builder）で作成します。

1. Gemini Enterprise の Web App（チャット画面）左メニューの **「Agents」** から **「+ New agent（または + Create agent）」** → **「Workflow」** → **「Build manually」** をクリックしてキャンバスを開きます。
2. 最初の **Manual trigger** ノードをクリックし、**Input fields** に `inquiry`（照会内容）を追加します。
3. キャンバスの **「+ Add step」** をクリックし、**「Existing agents」** セクションを展開して **`concierge_agent`** を選択します。追加された `concierge_agent` ステップの **Prompt** 欄で **`+`** を押し、前のステップの入力チップ（`${inquiry}`）を挿入します。
4. 続けて **「+ Add step」** をクリックし、**「Apps」**（`View all`）から **「Gmail」** → **「Send message」** を選択します。
   * **To** 欄に自分のメールアドレスを入力します。
   * **Subject** 欄に半角英数字で `Claims Review Result` と入力します（プレビュー版の制限により件名は英数字を推奨）。
   * **Message** 欄で **`+`** をクリックし、前段の `concierge_agent` の出力チップ（`${concierge_agent.output}`）を挿入します。
5. 画面上部の **「Test（または Preview）」** タブを開き、`inquiry` に以下を入力して実行すると、ADK エージェントの審査・試算結果が自動的に Gmail へ送信されることを確認できます。

```text
あんしんプラン 70%で、通院（外耳炎15,000円、ワクチン3,000円）を窓口精算するといくら出る？
```

## 完了

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>

お疲れさまでした！これで **Gemini Enterprise App** の中に、以下の3つの仕組みが統合されました。
* BigQuery 上の100件のデータを分析する Conversational Analytics エージェント（`claims_analyzer`）
* Cloud Run 上で動く ADK 2.0 保険金審査・試算ワークフローエージェント（`concierge_agent`）
* ADK エージェントと Google Workspace（Gmail 等）をノーコードでつなぐ Agent Designer ワークフロー

