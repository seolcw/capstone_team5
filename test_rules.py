"""LLM 없이 판정 로직(rules.py)만 점검 — 사람이 정한 정답 대상에 대해 draft 가 평가 기준을 만족하는지

  py -m uv run python test_rules.py
"""
import json
import pathlib

from cs_agent.common import ORDERS
from cs_agent.rules import check_cancellation, check_return, return_candidates
from cs_agent.common import tool_list_orders

ROOT = pathlib.Path(__file__).parent
CASES = {r["id"]: r for r in map(json.loads, (ROOT / "data" / "eval_public.jsonl").read_text(encoding="utf-8").splitlines())}

# (케이스, 판정 종류, 주문, line 순번, 사유)
TARGETS = [
    ("PUB-005", "cancel", "ORD-20261128-0001", 0, None),
    ("PUB-006", "cancel", "ORD-20261126-0003", 0, None),
    ("PUB-007", "return", "ORD-20261123-0001", 0, "단순변심"),
    ("PUB-008", "return", "ORD-20261106-0001", 0, "단순변심"),
    ("PUB-009", "return", "ORD-20261127-0002", 0, "단순변심"),
    ("PUB-010", "return", "ORD-20261110-0001", 0, "단순변심"),
    ("PUB-011", "return", "ORD-20261120-0002", 0, "단순변심"),
    ("PUB-017", "return", "ORD-20261110-0002", 0, "단순변심"),
    ("PUB-019", "cancel", "ORD-20261125-0001", 0, None),
]

ok_all = True
for cid, kind, oid, li, reason in TARGETS:
    order = ORDERS[oid]
    d = check_cancellation(order) if kind == "cancel" else check_return(order, order["items"][li], reason)
    exp = CASES[cid]["expected"]
    miss = [s for s in exp["must_include"] if s not in d["draft"]]
    bad = [s for s in exp["must_not_include"] if s in d["draft"]]
    act = d["action"] == exp["action"]
    ok = not miss and not bad and act
    ok_all &= ok
    print(f"{'OK ' if ok else 'NG '} {cid} action={d['action']} esc={d['escalation']} miss={miss} bad={bad}")
    if not ok:
        print("     ", d["draft"])

# PUB-025: 대상이 모호 → 후보 2건이어야 함
cands = [o["order_id"] for o in return_candidates(tool_list_orders({"customer_id": "C0024"}))]
ok = cands == ["ORD-20261124-0002", "ORD-20261123-0003"]
ok_all &= ok
print(f"{'OK ' if ok else 'NG '} PUB-025 후보={cands}")
print("\n전체:", "통과" if ok_all else "실패 있음")
