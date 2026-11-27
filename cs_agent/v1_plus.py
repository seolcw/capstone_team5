"""v1+ — v1(Baseline B) 에이전트에 범위 관문(scope_guard.py)을 붙인 버전. v1_naive_agent.py 없이 동작

  from cs_agent import v1_plus
  v1_plus.run(질문, 세션)

흐름: ① 긴급 규칙 → ② 유사도 1차 판정 → ③ LLM 분류 (여기까지 scope_guard.guard) → 에이전트 → ④ 출력 검사 (scope_guard.check_output)
- 긴급·범위 밖·인사는 에이전트를 거치지 않고 끝남
- 범위 안만 에이전트에 넘기고, 답변은 출력 검사를 거침. 문제가 있으면 1회 재실행 → 그래도 문제면 안내 문구
- 에이전트 부분은 v1_naive_agent.py 를 그대로 옮겨 온 것. 앞으로 에이전트 수정은 이 파일에서, 관문 수정은 scope_guard.py 에서
설계·결과: SCOPE_GUARD_DESIGN.md · SCOPE_GUARD_RESULT.md
"""
import json

from llm_client import client, MODEL

from .common import (NOW, Trace, kdatetime, search_docs, tool_escalate_to_agent, tool_get_order,
                     tool_get_return_conditions, tool_get_shipment, tool_list_orders)
from .scope_guard import TEMPLATES, check_output, guard


# ================================================================ 에이전트 (v1 에서 옮겨 온 부분)
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


def agent_run(query, session, case_id=None):
    """v1 에이전트 (v1_naive_agent.run 과 같은 동작). 관문을 통과한 질문만 여기로 옴"""
    tr = Trace("v1+:agent", case_id)
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


# ================================================================ v1+ 실행
RETRY_SUFFIX = "\n\n(답변은 반드시 한국어로만, 고객에게 보여 줄 문장만 작성해 주세요)"


def _merge(tr, outs, answer, **extra):
    """관문 기록 + v1 실행 기록을 하나로 합침 (토큰·호출 수를 정확히 비교하기 위해)"""
    s = tr.summary(answer, **extra)
    for o in outs:
        s["llm_calls"] += o.get("llm_calls", 0)
        s["prompt_tokens"] += o.get("prompt_tokens", 0)
        s["completion_tokens"] += o.get("completion_tokens", 0)
        s["tool_calls"] += o.get("tool_calls", [])
        s["events"] += o.get("events", [])
    return s


def run(query, session, case_id=None):
    tr = Trace("v1+", case_id)
    g = guard(query, tr)
    tr.log("guard", **{k: v for k, v in g.items() if k != "answer"})
    info = {k: g.get(k) for k in ("route", "layer", "score", "reason", "code")}

    if g["route"] == "urgent":
        res = tool_escalate_to_agent(session, g["code"], query)
        tr.tool("escalate_to_agent", {"reason_code": g["code"]}, res)
        return _merge(tr, [], g["answer"], action="escalate", escalation=g["code"], guard=info)

    if g["route"] in ("block", "greeting"):
        return _merge(tr, [], g["answer"], action="answer", escalation=None, guard=info)

    out = agent_run(g["query"], session, case_id)
    problem = check_output(out["answer"])
    if not problem:
        return _merge(tr, [out], out["answer"], action=out.get("action"), escalation=out.get("escalation"), guard=info)

    tr.log("output_check", problem=problem, retry=True)
    out2 = agent_run(g["query"] + RETRY_SUFFIX, session, case_id)
    problem2 = check_output(out2["answer"])
    info["output_check"] = f"{problem} → 재실행 " + ("통과" if not problem2 else f"실패({problem2}) → 안내 문구")
    if not problem2:
        return _merge(tr, [out, out2], out2["answer"], action=out2.get("action"), escalation=out2.get("escalation"), guard=info)
    return _merge(tr, [out, out2], TEMPLATES["fallback"], action="answer",
                  escalation=out2.get("escalation") or out.get("escalation"), guard=info)
