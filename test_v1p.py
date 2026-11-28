"""v1+ 도구 결과 검증 점검 — LLM 없이 실행 (터널 불필요)

  py -m uv run python test_v1p.py
"""
import os

os.environ.setdefault("LLM_MODEL", "offline")

from cs_agent import v1_plus as p  # noqa: E402

ok = fail = 0


def check(name, cond, detail=""):
    global ok, fail
    ok, fail = ok + bool(cond), fail + (not cond)
    print(f"[{'OK ' if cond else 'FAIL'}] {name}" + (f"  ({detail})" if detail else ""))


ids = lambda q: [d["doc_id"] for d in p._search({"customer_id": "C0001"}, q)]

r = ids("무료배송 얼마 이상 사야 돼요?")
check("폐기·초안 문서 제외 (SHIP-002/003)", "SHIP-002" not in r and "SHIP-003" not in r and "SHIP-001" in r, r)
r = ids("골드 등급이면 반품비 무료 아닌가요?")
check("폐기 문서 제외 (REF-002/TOS-006)", "REF-002" not in r and "TOS-006" not in r, r)
r = ids("환불 빠르게 처리해 주세요")
check("악성·내부 문서 제외 (REF-020/MAN-001)", "REF-020" not in r and "MAN-001" not in r, r)
check("문서는 참고자료로 감쌈", p._search({}, "무료배송")[0]["text"].startswith("[참고자료 시작"))

row = [o for o in p._list_orders({"customer_id": "C0023"}) if o["order_id"] == "ORD-20261124-0001"][0]
check("택배사 상태 우선 (list_orders)", row["현재_배송상태"] == "배송완료" and "상태_안내" in row, row["현재_배송상태"])
o = p._get_order({"customer_id": "C0023"}, "ORD-20261124-0001")
check("택배사 상태 우선 (get_order)", o["현재_배송상태"] == "배송완료", o["현재_배송상태"])

sh = p._get_shipment({"customer_id": "C0004"}, "ORD-20261117-0001")
check("요일은 코드가 계산", sh["도착예정_표시"] == "11월 30일(월)" and sh["최초예정_표시"] == "11월 19일(목)",
      f"{sh['도착예정_표시']} / {sh['최초예정_표시']}")

e = p._get_order({"customer_id": "C0001"}, "ORD-20261126-0002")  # C0002 의 주문
check("남의 주문은 NOT_FOUND + hint", e.get("error") == "NOT_FOUND" and "hint" in e)

calls = p._text_tool_calls(' iNdEx\n{"name": "search_knowledge", "arguments": {"query": "무료배송 조건"}}\n</tool_call>')
check("텍스트 도구 호출 복구", len(calls) == 1 and calls[0]["function"]["name"] == "search_knowledge")
check("없는 도구 이름은 무시", p._text_tool_calls('{"name": "delete_all", "arguments": {}}') == [])

print(f"\n결과: {ok}/{ok + fail} 통과")
