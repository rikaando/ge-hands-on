"""社内従業員向け：保険金審査・照会サポートワークフロー（ADK 2.0）."""

from google.adk.agents import Agent, SequentialAgent

# プラン別の補償ルール（補償割合・通院/入院の1日上限・手術の1回上限）
PLAN_RULES = {
    "あんしんプラン 70%": {"rate": 0.7, "daily_limit": 12000, "surgery_limit": 150000},
    "あんしんプラン 50%": {"rate": 0.5, "daily_limit": 10000, "surgery_limit": 100000},
    "あんしんプラン キュート": {"rate": 0.7, "daily_limit": 10000, "surgery_limit": 100000},
}


# --- 1. ツール定義（エージェントが呼び出す Python 関数） ---
def check_coverage_rules(treatment_summary: str, treatment_type: str) -> dict:
    """診療内容から、約款上の補償対象外項目と審査に必要な書類を判定します.

    Args:
        treatment_summary: 傷病名や診療・処置の内訳（例: 外耳炎の治療15000円、混合ワクチン3000円）
        treatment_type: 診療区分（「通院」「入院」「手術」）
    """
    excluded_keywords = ["ワクチン", "予防接種", "健康診断", "フィラリア", "ノミ", "ダニ", "爪切り", "去勢", "避妊"]
    found_exclusions = [kw for kw in excluded_keywords if kw in treatment_summary]

    required_docs = ["動物病院発行の診療明細書（原本または写真）"]
    if treatment_type == "手術":
        required_docs.append("手術名・実施日が確認できる診断書または手術同意書")

    return {
        "treatment_type": treatment_type,
        "detected_excluded_items": found_exclusions if found_exclusions else ["該当なし（すべて補償対象）"],
        "exclusion_policy_note": "ワクチン接種・健康診断・予防薬等の予防処置は、約款上すべて補償対象外（全額自己負担）となります。",
        "required_documents": required_docs,
    }


def calculate_payout(
    plan_name: str,
    eligible_fee_yen: int,
    excluded_fee_yen: int,
    treatment_type: str,
    claim_method: str,
) -> dict:
    """補償対象の診療費とプランから、支払保険金と自己負担額を計算します.

    Args:
        plan_name: プラン名（「あんしんプラン 70%」「あんしんプラン 50%」「あんしんプラン ライト」「あんしんプラン キュート」）
        eligible_fee_yen: 補償対象となる診療費（円）※ワクチン等の対象外費用を除いた金額
        excluded_fee_yen: 補償対象外の費用（円）※ワクチンや健康診断など（なければ 0）
        treatment_type: 診療区分（「通院」「入院」「手術」）
        claim_method: 請求方法（「窓口精算」「WEB請求」「郵送請求」）
    """
    if "ライト" in plan_name:
        payout = min(max(0, int((eligible_fee_yen - 30000) * 0.9)), 500000) if treatment_type == "手術" else 0
        note = "手術特化プラン（免責30,000円控除後の90%・上限500,000円、通院/入院は対象外）"
    else:
        rule = PLAN_RULES.get(plan_name, PLAN_RULES["あんしんプラン 70%"])
        limit = rule["surgery_limit"] if treatment_type == "手術" else rule["daily_limit"]
        payout = min(int(eligible_fee_yen * rule["rate"]), limit)
        note = f"補償割合{int(rule['rate'] * 100)}%（上限 {limit:,} 円）で試算"

    total_fee = eligible_fee_yen + excluded_fee_yen
    self_burden = total_fee - payout

    guides = {
        "窓口精算": "提携病院の窓口で保険証を提示（自己負担額のみ病院窓口でお支払い、後日の請求手続は不要）",
        "郵送請求": "病院で全額お支払い後、保険金請求書と診療明細書を郵送提出",
        "WEB請求": "病院で全額お支払い後、マイページから診療明細書の画像をアップロードして申請",
    }

    return {
        "plan_name": plan_name,
        "total_medical_fee_yen": f"{total_fee:,}円（うち補償対象: {eligible_fee_yen:,}円 / 対象外: {excluded_fee_yen:,}円）",
        "estimated_payout_yen": f"{payout:,}円",
        "total_self_burden_yen": f"{self_burden:,}円",
        "calculation_rule": note,
        "procedure_guide": guides.get(claim_method, guides["WEB請求"]),
    }


# --- 2. 専門エージェント定義 ---
# Step 1: 約款・審査ルール確認エージェント
policy_checker = Agent(
    name="policy_checker",
    model="gemini-3.8-flash",
    description="診療内容から約款上の補償可否・対象外項目・必要書類を判定するエージェント",
    instruction=(
        "あなたは保険金サービス部の一次審査チェッカーです。\n"
        "照会内容から `check_coverage_rules` ツールを呼び出し、補償対象となる診療費・対象外費用・必要書類の3点のみを簡潔に整理して出力してください（支払額の計算や案内文の作成は次のエージェントが行うため不要です）。"
    ),
    tools=[check_coverage_rules],
    output_key="policy_check_result",
)

# Step 2: 支払額試算＆社内回答作成エージェント
payout_calculator = Agent(
    name="payout_calculator",
    model="gemini-2.5-flash",
    description="審査結果に基づき支払保険金を試算し、社内審査メモとお客さま案内文を作成するエージェント",
    instruction=(
        "あなたは保険金サービス部・お客さまサポート部向けの照会回答作成アシスタントです。\n"
        "前段の約款チェック結果（{policy_check_result}）を踏まえ、`calculate_payout` ツールで支払保険金と自己負担額を計算してください。\n"
        "回答は社内担当者が見やすいよう、以下の3項目に整理して日本語で出力してください。\n"
        "1. 審査判定・必要書類（対象外項目の有無と根拠）\n"
        "2. 支払保険金・自己負担額の試算内訳\n"
        "3. お客さまへの案内トーク例（そのまま読み上げ・送付できる丁寧な文案）"
    ),
    tools=[calculate_payout],
)


# --- 3. ワークフロー定義（Step 1 → Step 2 を順番に自動実行） ---
root_agent = SequentialAgent(
    name="concierge_agent",
    description="社内担当者向けに「①約款・対象外チェック → ②支払保険金試算＆案内文作成」を自動実行する審査サポートエージェント",
    sub_agents=[policy_checker, payout_calculator],
)
