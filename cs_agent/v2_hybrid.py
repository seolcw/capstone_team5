"""v2 — Hybrid (LLM 은 이해와 표현, 판단은 코드)

  [코드]  세션 고객의 주문 목록 조회 (list_orders)
  [LLM]   의도·사유·대상 상품 추출 — JSON(Structured Output)
  [코드]  추출 결과 검증 → 대상 주문 확정(모호하면 되묻기) → 결정론적 판정(rules.py) → 필요 시 이관
  [LLM]   판정 결과(draft)를 자연스러운 문장으로 다듬기 — 사실 추가·변경 금지
  [코드]  출력 검증: 필수 사실 포함 · 모순 표현 없음 → 실패하면 draft 로 대체
"""
import json
import re

from llm_client import client, MODEL

from .common import (NOW, ORDERS, Trace, search_docs, tool_escalate_to_agent, tool_get_order,
                     tool_get_return_conditions, tool_list_orders)
from .rules import cancel_candidates, check_cancellation, check_return, decision, return_candidates

INTENTS = {"주문취소", "반품문의", "교환문의", "기타"}
REASONS = {"단순변심", "하자"}

CLASSIFY = """너는 이커머스 상담 요청을 분석하는 분류기야. 판단이나 답변은 하지 말고 JSON 하나만 출력해.
형식: {{"intents": [...], "reason": "단순변심"|"하자"|null, "target_line_ids": [...]}}
- intents: "주문취소", "반품문의", "교환문의", "기타" 중 해당하는 것 모두 (여러 개 가능)
  · "안 받을래요", "취소할게요"처럼 주문을 없던 일로 하려는 요청은 "주문취소"
  · 이미 받은 상품을 돌려보내거나 환불을 원하면 "반품문의"
- reason: 고객 사정(마음에 안 듦, 사이즈·색상·크기 불만, 써봤는데 별로)이면 "단순변심", 불량·파손·오배송이면 "하자", 알 수 없으면 null
- target_line_ids: 고객이 말한 상품에 해당하는 line_id (아래 목록에서만 고르기, 상품을 특정하지 않았으면 빈 리스트)

고객의 주문 상품 목록:
{items}

고객 요청: {query}"""

POLISH = """다음은 고객 문의에 대해 시스템이 확정한 안내문이야. 고객에게 보낼 답변으로 자연스럽게 다듬어 줘.
규칙: 숫자·날짜·주문번호·가능/불가 판단·조건은 절대 바꾸거나 빼지 말 것. 안내문에 없는 약속이나 보상, 정책은 추가하지 말 것.
'불가', '가능' 같은 판정 표현은 원문 그대로 유지할 것. 답변만 출력할 것.
다음 표현은 띄어쓰기·괄호까지 글자 그대로 답변에 포함할 것: {required}

고객 문의: {query}
안내문: {draft}"""


def _parse_json(text):
    m = re.search(r"\{.*\}", text or "", re.S)
    try:
        return json.loads(m.group(0)) if m else {}
    except json.JSONDecodeError:
        return {}


def classify(query, orders, tr):
    items = "\n".join(f"- line_id={i['line_id']} | {i['product_name']} | 주문 {o['order_id']} ({o['order_status']})"
                      for o in orders for i in o["items"])
    resp = client.chat.completions.create(
        model=MODEL, temperature=0,
        messages=[{"role": "user", "content": CLASSIFY.format(items=items, query=query)}])
    tr.llm(resp, "classify")
    raw = _parse_json(resp.choices[0].message.content)
    # LLM 출력은 그대로 믿지 않고 코드로 검증 (허용값·세션 고객 소유 line 만 남김)
    valid_lines = {i["line_id"] for o in orders for i in o["items"]}
    intents = [x for x in raw.get("intents") or [] if x in INTENTS] or ["기타"]
    reason = raw.get("reason") if raw.get("reason") in REASONS else None
    lines = [x for x in raw.get("target_line_ids") or [] if x in valid_lines]
    out = {"intents": intents, "reason": reason, "target_line_ids": lines}
    tr.log("classify", raw=raw, validated=out)
    return out


def _clarify(cands, what):
    listing = " ".join(f"{n}. {o['order_id']} {', '.join(i['product_name'] for i in o['items'])}"
                       for n, o in enumerate(cands, 1))
    return decision(None, f"{what} 가능한 최근 주문이 {len(cands)}건 있습니다. {listing}. 어떤 주문(상품)을 말씀하시는지, 사유(단순변심/상품 하자)와 함께 알려주세요.",
                    action="clarify", required=[o["order_id"] for o in cands] + ["어떤"],
                    forbidden=["접수되었습니다"], refs=["REF-001"])


def route(intent_info, orders, session, tr):
    intents = intent_info["intents"]
    by_line = {i["line_id"]: (o, i) for o in orders for i in o["items"]}
    # 같은 상품이 여러 주문에 있으면 가장 최근 주문을 우선 (orders 는 최신순)
    rank = {o["order_id"]: n for n, o in enumerate(orders)}
    picked = sorted((by_line[l] for l in intent_info["target_line_ids"]), key=lambda p: rank[p[0]["order_id"]])

    if "주문취소" in intents:
        if picked:
            oid = picked[0][0]["order_id"]
        else:
            cands = cancel_candidates(orders)
            if len(cands) != 1:
                return _clarify(cands, "취소") if cands else decision(None, "현재 취소할 수 있는 진행 중 주문이 없습니다.", required=["없습니다"])
            oid = cands[0]["order_id"]
        order = tool_get_order(session, oid)
        tr.tool("get_order", {"order_id": oid}, order)
        line = order["items"][0]
        tr.tool("get_return_conditions", {"product_id": line["product_id"]},
                tool_get_return_conditions(session, line["product_id"]))
        return check_cancellation(order)

    if {"반품문의", "교환문의"} & set(intents):
        if picked:
            o_row, line = picked[0]
        else:
            cands = return_candidates(orders)
            if len(cands) != 1:
                return _clarify(cands, "반품") if cands else decision(None, "단순변심 반품 기간이 남은 주문이 없습니다. 상품 하자라면 주문번호와 증상을 알려주세요.", required=["없습니다"])
            o_row, line = cands[0], cands[0]["items"][0]
        tr.tool("get_return_conditions", {"product_id": line["product_id"]},
                tool_get_return_conditions(session, line["product_id"]))
        return check_return(ORDERS[o_row["order_id"]], line, intent_info["reason"] or "단순변심")

    # 판정 대상이 아닌 일반 문의 → 승인·유효 문서만 검색해 근거로 사용
    docs = search_docs(" ".join(intents), k=3, approved_only=True)
    tr.tool("search_knowledge", {"approved_only": True}, [d["meta"]["doc_id"] for d in docs])
    return decision(None, "문의하신 내용은 상담원이 확인해 드리겠습니다.", refs=[d["meta"]["doc_id"] for d in docs])


def validate(answer, dec):
    missing = [r for r in dec["required"] if r not in answer]
    contradict = [f for f in dec["forbidden"] if f in answer]
    return missing, contradict


def run(query, session, case_id=None):
    tr = Trace("v2", case_id)
    orders = tool_list_orders(session)
    tr.tool("list_orders", {"customer_id": session["customer_id"]}, [o["order_id"] for o in orders])

    info = classify(query, orders, tr)
    dec = route(info, orders, session, tr)
    tr.log("decision", ok=dec["ok"], action=dec["action"], escalation=dec["escalation"], refs=dec["refs"])

    if dec["escalation"]:
        tr.tool("escalate_to_agent", {"reason_code": dec["escalation"]},
                tool_escalate_to_agent(session, dec["escalation"], query))

    resp = client.chat.completions.create(
        model=MODEL, temperature=0,
        messages=[{"role": "user", "content": POLISH.format(query=query, draft=dec["draft"],
                                                                 required=", ".join(f"'{r}'" for r in dec["required"]) or "(없음)")}])
    tr.llm(resp, "polish")
    answer = (resp.choices[0].message.content or "").strip()

    missing, contradict = validate(answer, dec)
    fallback = bool(missing or contradict)
    tr.log("validate", missing=missing, contradict=contradict, fallback=fallback)
    if fallback:
        answer = dec["draft"]  # 검증 실패 → 사실만으로 만든 안내문 사용
    return tr.summary(answer, action=dec["action"], escalation=dec["escalation"], intents=info["intents"],
                      decision_ok=dec["ok"], refs=dec["refs"], fallback=fallback)
