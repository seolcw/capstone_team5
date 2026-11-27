"""v1 — Naive Agent (주제 PDF 12p Baseline B)

LLM 이 도구와 호출 순서를 스스로 정하고, 취소·반품 가능 여부도 LLM 이 정책 문서와 조회 결과를 읽고 판단합니다.
도구 자체와 세션 권한 처리는 cs_agent/common.py 에 있어 개선 버전과 같은 조건으로 비교할 수 있습니다.
"""
import json

from llm_client import client, MODEL

from .common import (NOW, Trace, kdatetime, search_docs, tool_escalate_to_agent, tool_get_order,
                     tool_get_return_conditions, tool_get_shipment, tool_list_orders)

MAX_TURNS = 6

SYSTEM = f"""너는 이커머스 고객 상담원이야. 한국어로 친절하고 정확하게 답해.
현재 시각은 {kdatetime(NOW)}이야.
고객 주문·배송·반품 조건은 반드시 도구로 조회하고, 정책은 search_knowledge 로 찾아서
취소·반품·환불 가능 여부를 판단해 안내해. 필요하면 escalate_to_agent 로 상담원에게 넘겨."""

TOOLS = [
    {"type": "function", "function": {"name": "list_orders", "description": "로그인한 고객의 주문 목록 조회",
                                      "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "get_order", "description": "주문 상세 조회",
                                      "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}},
                                                     "required": ["order_id"]}}},
    {"type": "function", "function": {"name": "get_shipment", "description": "배송 상태 조회",
                                      "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}},
                                                     "required": ["order_id"]}}},
    {"type": "function", "function": {"name": "get_return_conditions", "description": "상품별 교환·반품 조건 조회",
                                      "parameters": {"type": "object", "properties": {"product_id": {"type": "string"}},
                                                     "required": ["product_id"]}}},
    {"type": "function", "function": {"name": "search_knowledge", "description": "상담 정책 문서 검색",
                                      "parameters": {"type": "object", "properties": {"query": {"type": "string"}},
                                                     "required": ["query"]}}},
    {"type": "function", "function": {"name": "escalate_to_agent", "description": "상담원 연결 (E01~E11 코드)",
                                      "parameters": {"type": "object",
                                                     "properties": {"reason_code": {"type": "string"},
                                                                    "summary": {"type": "string"}},
                                                     "required": ["reason_code"]}}},
]


def _search(session, query):
    return [{"doc_id": d["meta"]["doc_id"], "title": d["meta"]["title"], "text": d["text"]}
            for d in search_docs(query, k=3, approved_only=False)]


FUNCS = {
    "list_orders": lambda s, **a: tool_list_orders(s),
    "get_order": tool_get_order,
    "get_shipment": tool_get_shipment,
    "get_return_conditions": tool_get_return_conditions,
    "search_knowledge": _search,
    "escalate_to_agent": tool_escalate_to_agent,
}


def run(query, session, case_id=None):
    tr = Trace("v1", case_id)
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": query}]
    answer, escalation = None, None
    for _ in range(MAX_TURNS):
        resp = client.chat.completions.create(model=MODEL, messages=messages, tools=TOOLS, temperature=0)
        tr.llm(resp, "agent_step")
        msg = resp.choices[0].message
        if not msg.tool_calls:
            answer = msg.content
            break
        messages.append(msg)
        for call in msg.tool_calls:
            try:
                args = json.loads(call.function.arguments or "{}")
                result = FUNCS[call.function.name](session, **args)
            except Exception as e:  # 모델이 없는 도구·잘못된 인자를 만든 경우
                args, result = call.function.arguments, {"error": f"{type(e).__name__}: {e}"}
            if call.function.name == "escalate_to_agent" and isinstance(args, dict):
                escalation = args.get("reason_code")
            tr.tool(call.function.name, args, result)
            messages.append({"role": "tool", "tool_call_id": call.id,
                             "content": json.dumps(result, ensure_ascii=False, default=str)})
    if answer is None:
        answer = "(최대 반복 횟수 초과 — 답변 생성 실패)"
        tr.log("max_turns")
    return tr.summary(answer, action="escalate" if escalation else "answer", escalation=escalation)
