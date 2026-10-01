# Gemini Enterprise ハンズオン応用編

このチュートリアルでは、社内業務で活用する2つのエージェントを作成し、Gemini Enterprise に公開して連携する流れを体験します。

1. **テーマ1（データ分析）**
   BigQuery に保険金請求・お客さまの声データを登録し、対話型の分析エージェント（`claims_analyzer`）を作成します。
2. **テーマ2（審査サポート）**
   社内担当者向けの保険金審査・試算ワークフロー（ADK 2.0 エージェント `concierge_agent`）を Cloud Run にデプロイし、Gemini Enterprise や Google Workspace と連携します。

右下の **開始** をクリックして進めてください。

## Step 1: 事前準備（API有効化と権限設定）

エージェントの作成に必要な API の有効化と、サービスアカウントへの権限付与を順番に行います。
コードブロック右上の **「Cloud Shell にコピー」** をクリックし、ターミナルで **Enter キー** を押して実行してください。

**1. 必要な API の有効化**
（初回に「承認 / Authorize」が表示された場合は **承認** をクリックします）

```bash
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
echo "${GOOGLE_CLOUD_PROJECT}" > .project_id
gcloud services enable bigquery.googleapis.com run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com aiplatform.googleapis.com discoveryengine.googleapis.com geminidataanalytics.googleapis.com cloudaicompanion.googleapis.com dataplex.googleapis.com agentregistry.googleapis.com
echo "API enablement complete."
```

※もし `(unset)` エラーが表示された場合は、`gcloud config set project プロジェクトID` を実行してから再度実行してください。

**2. サービスアカウントへの権限付与**
Cloud Run 呼び出し権限（`roles/run.invoker`）と、Vertex AI のモデル利用権限（`roles/aiplatform.user`）を付与します。

```bash
export GOOGLE_CLOUD_PROJECT=$(cat .project_id)
export PROJECT_NUMBER=$(gcloud projects describe ${GOOGLE_CLOUD_PROJECT} --format="value(projectNumber)")
gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT} --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-discoveryengine.iam.gserviceaccount.com" --role="roles/run.invoker" --condition=None --no-user-output-enabled --quiet
gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT} --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" --role="roles/aiplatform.user" --condition=None --no-user-output-enabled --quiet
echo "Step 1 setup complete."
```

※Gemini Enterprise App が別プロジェクトにある場合のみ、以下の `GEMINI_ENTERPRISE_PROJECT_ID` を書き換えて実行してください（同一プロジェクトの場合は不要です）。

```bash
export GE_PROJECT_NUMBER=$(gcloud projects describe GEMINI_ENTERPRISE_PROJECT_ID --format="value(projectNumber)")
gcloud projects add-iam-policy-binding ${GOOGLE_CLOUD_PROJECT} --member="serviceAccount:service-${GE_PROJECT_NUMBER}@gcp-sa-discoveryengine.iam.gserviceaccount.com" --role="roles/run.invoker" --condition=None --no-user-output-enabled --quiet
```

実行が完了したら **次へ** をクリックしてください。

## Step 2: テーマ1（1/3）BigQuery へのサンプルデータ登録

対話型のデータ分析エージェントを作成するために、BigQuery にデータセットを作成し、保険金請求とお客様の声のサンプルデータ(claims_sample.csv)をアップロードします。

コードブロック右上の **「Cloud Shell にコピー」** をクリックし、ターミナルで **Enter キー** を押して実行してください。

```bash
gcloud config set project $(cat .project_id) --quiet
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
bq --location=US mk -d -f ${GOOGLE_CLOUD_PROJECT}:insurance_demo
bq load --replace --source_format=CSV --skip_leading_rows=1 ${GOOGLE_CLOUD_PROJECT}:insurance_demo.claims ./claims_sample.csv ./claims_schema.json
echo "CSV upload complete."
```

`CSV upload complete.` と表示されたら **次へ** をクリックしてください。

## Step 3: テーマ1（2/3）BigQuery で分析エージェントを作成

BigQuery の Conversational Analytics 機能を使い、自然言語でデータを集計・分析するエージェントを作成します。

1. [BigQuery コンソール](https://console.cloud.google.com/bigquery) を開きます。
   左メニューの **エージェント** → **+ 新しいエージェント** をクリックします。

2. 基本情報を入力します。
   * **エージェント名** に `claims_analyzer` を入力
   * **エージェントの説明** に `保険金請求・お客さまの声データを集計・分析するエージェント` を入力
   * **リージョン** は `US`（または `Global`）を選択

3. **ナレッジソース** の **ソースの追加** をクリックし、**`insurance_demo` -> `claims`** テーブルを選択して **「確認」** をクリックします。

4. **手順** に以下を貼り付けます。
   ```text
   あなたは保険金請求・お客さまの声（VOC）データを分析するアシスタントです。
   - 件数や金額のランキング・比較を行う際は、集計表とあわせて見やすいグラフ（棒グラフや円グラフ）を積極的に生成して可視化してください。
   - 1つのグラフに「件数」と「金額（円）」のような単位・桁数が大きく異なる指標を混在させないでください。
   - SQLのSELECT句では、カラム名に日本語の別名（例: 種別, 傷病名, プラン名, 請求件数, 平均診療費_円, 平均支払保険金_円）を付け、val1のような汎用名は使わないでください。
   - 1回のクエリで集計軸が異なる複数の表をUNION ALLで結合せず、1つの分かりやすい集計表として出力してください。
   - 金額の平均値は ROUND 関数で整数（1円単位）に丸めて表示してください。
   - お客さまの声（customer_voice）の分析時は、精算方法（claim_method）ごとの傾向や改善要望を要約してください。
   ```

5. 画面右上の **保存** をクリックし、右側の **公開** をクリックします。
   開いたダイアログの右下の **「Publish agent」** をクリックし、エージェントを公開します。
   ポップアップが出たら、**公開** をクリックします。
   権限の共有ページで **プリンシパルを追加** をクリックし、新しいプリンシパルに自分の email を追加し、ロールには **Gemini データ分析データ エージェント オーナー** を選択し、**保存** します。

6. 再度、**公開** をクリックし、**A2A 経由での統合** の **JSON をコピー** をクリックし、クリップボードに保存します。

公開が完了したら **次へ** をクリックしてください。

## Step 4: テーマ1（3/3）Gemini Enterprise App に登録して分析

公開した BigQuery エージェントを Gemini Enterprise App に接続し、チャット画面からデータを集計します。

1. [Gemini Enterprise 管理コンソール](https://console.cloud.google.com/gemini-enterprise) で対象の App を選び、左メニュー **エージェント** → **+ エージェントを追加** をクリックします。

2. **A2A によるカスタム エージェント** の追加をクリックし、Step 3 でコピーした JSON を貼り付けて **エージェントの詳細をプレビュー** → **次へ** をクリックします。

3. エージェントの認可では **Google が管理するデフォルトの認証情報** を選択し、**完了** をクリックします。

4. Gemini Enterprise のアプリ画面を再読み込みし、**エージェント > 自分の組織から** に追加された `@claims_analyzer` をクリックし、以下の質問を送信してみましょう。

```text
犬と猫それぞれで、請求件数が多い傷病トップ5を棒グラフで教えて
```

```text
プラン別の平均診療費と平均支払保険金を棒グラフで比較して
```

```text
窓口精算・WEB請求・郵送請求それぞれの件数（円グラフ）と、お客さまの声にある改善要望の傾向をまとめて
```

※初回利用時にアクセス承認のメッセージが表示された場合は、**承認** をクリックし、ポップアップから Google Workspace のアカウントで承認します。

これでテーマ1の BigQuery の対話型エージェントを Gemini Enterprise から利用できるようになりました。

ADK のエージェントを作成する場合には、**次へ** をクリックしてください。

## Step 5: テーマ2（1/3）ADK 2.0 エージェントの確認

テーマ2では、社内担当者向けに **「①約款・対象外チェック → ②支払保険金試算＆案内文作成」** を2段階で自動実行する ADK 2.0 ワークフローエージェントを Cloud Run にデプロイし、Gemini Enterprise に登録します。

以下のボタンをクリックして、エディタでコードを開いてみましょう。

<walkthrough-editor-open-file filePath="insurance_agent/agent.py">insurance_agent/agent.py を開く</walkthrough-editor-open-file>

<walkthrough-editor-open-file filePath="main.py">main.py を開く</walkthrough-editor-open-file>

ファイルが開かなかった場合には、エディタからge-hands-onのフォルダを開き、上記のファイルを確認します。

**コードの構成（`insurance_agent/agent.py`）**
* **1. ツール定義（Python 関数）**
  * `check_coverage_rules`: ワクチン等の予防処置（対象外）の有無と必要書類を判定
  * `calculate_payout`: 補償対象額とプランから支払保険金・自己負担額を試算
* **2. サブエージェント定義（`Agent`）**
  * `policy_checker`: 1段目の約款・対象外チェックを実行
  * `payout_calculator`: 1段目の結果を受け取り、支払額試算と案内文を作成
* **3. ワークフロー定義（`SequentialAgent`）**
  * `root_agent`: 2つのエージェントを直列につなぎ、`main.py` の `to_a2a(root_agent)` で A2A サーバーとして公開

コードの編集は不要です。確認したら **次へ** をクリックしてください。

## Step 6: テーマ2（2/3）Cloud Run へのデプロイと JSON 出力

ADK 2.0 エージェントを Cloud Run にデプロイし、Gemini Enterprise 登録用の `agent_card.json` を生成します。
コードブロック右上の **「Cloud Shell にコピー」** をクリックし、ターミナルで **Enter キー** を押して順番に実行してください。

※もし途中で Cloud Shell の接続が切れていた場合は、デプロイの前に以下を再実行してください。

```bash
export GOOGLE_CLOUD_PROJECT=$(gcloud config get-value project)
echo "${GOOGLE_CLOUD_PROJECT}" > .project_id
```

**1. Cloud Run へのデプロイ**（約2〜3分かかります）

```bash
gcloud config set project $(cat .project_id) --quiet
export GOOGLE_CLOUD_PROJECT=$(cat .project_id)
export PROJECT_NUMBER=$(gcloud projects describe ${GOOGLE_CLOUD_PROJECT} --format="value(projectNumber)")
export GOOGLE_CLOUD_LOCATION="us-central1"
export AGENT_URL="https://insurance-concierge-agent-${PROJECT_NUMBER}.${GOOGLE_CLOUD_LOCATION}.run.app"
gcloud run deploy insurance-concierge-agent --source . --region=${GOOGLE_CLOUD_LOCATION} --project=${GOOGLE_CLOUD_PROJECT} --no-allow-unauthenticated --set-env-vars="GOOGLE_GENAI_USE_VERTEXAI=TRUE,GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT},GOOGLE_CLOUD_LOCATION=global,AGENT_URL=${AGENT_URL}" --quiet
```

**2. 登録用 `agent_card.json` の生成**
デプロイが完了したら、以下のコマンドを実行して Cloud Run の URL を埋め込んだ `agent_card.json` を出力します。

```bash
export GOOGLE_CLOUD_PROJECT=$(cat .project_id)
export GOOGLE_CLOUD_LOCATION="us-central1"
export AGENT_URL=$(gcloud run services describe insurance-concierge-agent --region=${GOOGLE_CLOUD_LOCATION} --project=${GOOGLE_CLOUD_PROJECT} --format="value(status.url)")
sed "s|__AGENT_URL__|${AGENT_URL}|g" agent_card.template.json > agent_card.json
cat agent_card.json
```

ターミナルに出力された JSON（または以下のボタンで開いた `agent_card.json` の中身）をすべてコピーし、**次へ** をクリックしてください。

<walkthrough-editor-open-file filePath="agent_card.json">生成された agent_card.json を開く</walkthrough-editor-open-file>

## Step 7: テーマ2（3/3）Gemini Enterprise App に登録して照会テスト

生成した `agent_card.json` を Gemini Enterprise App に登録し、審査・試算ワークフローを呼び出します。

1. [Gemini Enterprise 管理コンソール](https://console.cloud.google.com/gemini-enterprise) で対象の App を選び、左メニュー **エージェント** → **+ エージェントを追加** をクリックします。

2. **A2A によるカスタム エージェント** の追加をクリックし、Step 6 でコピーした JSON を貼り付けて **エージェントの詳細をプレビュー** → **次へ** をクリックします。

3. エージェントの認可画面では何も変更せず **スキップして終了** をクリックします。

4. Gemini Enterprise のアプリ画面を再読み込みし、**エージェント > 自分の組織から** に追加された `concierge_agent` をクリックし、以下の質問を送信してみましょう。

```text
あんしんプラン 70%で、通院（外耳炎15,000円、ワクチン3,000円）を窓口精算するといくら出る？
```

```text
あんしんプラン ライトで、椎間板ヘルニアの手術28万円をWEB請求するといくら出る？
```

確認できたら **次へ** をクリックしてください。

## Step 8: 応用編まとめ（ワークフローで Google Workspace と連携）

最後に、Step 7 で登録した `concierge_agent` と Google Workspace（Gmail）をノーコードでつなぐワークフローを作成します。

1. Gemini Enterprise のアプリ画面でワークフロー作成画面を開き、画面右下の **手動で構築** をクリックします。

2. 最初の **手動** ノードをクリックし、**入力フィールド** に `inquiry` を追加して **保存** します。

3. **+ ステップを追加** → **既存のエージェント** から **`concierge_agent`** を選択します。
   **プロンプト** 欄で **`+`** を押し、入力チップ（`inquiry`）を挿入します。

4. 続けて **+ ステップを追加** → **アプリ**（**すべて表示**）→ **Gmail** → **メッセージを送信** を選択し、以下を設定します。
   * **To（宛先）** 欄に自分のメールアドレスを入力
   * **Subject（件名）** 欄に半角英数字で `Claims Review Result` と入力
   * **Message（メッセージ）** 欄で **`+`** を押し、`concierge_agent` の出力チップを挿入

5. 画面上部の **テスト** タブを開き、`inquiry` に以下を入力して実行すると、審査・試算結果が Gmail へ自動送信されます。

```text
あんしんプラン 70%で、通院（外耳炎15,000円、ワクチン3,000円）を窓口精算するといくら出る？
```

## 完了

<walkthrough-conclusion-trophy></walkthrough-conclusion-trophy>

お疲れさまでした！これで **Gemini Enterprise App** の中に、以下の3つの仕組みが統合されました。
* BigQuery の100件データを分析するエージェント（`claims_analyzer`）
* Cloud Run 上で動く ADK 2.0 保険金審査・試算エージェント（`concierge_agent`）
* ADK エージェントと Google Workspace をつなぐノーコード・ワークフロー
