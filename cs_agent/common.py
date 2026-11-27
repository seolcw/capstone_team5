"""공통 모듈 — 데이터 로드, 기준 시각, 날짜 유틸, 세션 범위 조회 도구, 실행 기록(trace)

v0 / v1 / v2 가 모두 같은 데이터와 같은 도구를 쓰도록 한 곳에 모았습니다.
버전 사이의 차이는 '누가 판단하느냐'(LLM vs 코드)뿐이어야 비교가 공정합니다.
"""
import json
import pathlib
import re
import time
from datetime import date, datetime, timedelta, timezone

import yaml

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
KST = timezone(timedelta(hours=9))

# 평가 세션은 전부 2026-11-28(토) 10:00~17:00 사이 → 기준 시각을 코드에서 주입
NOW = datetime(2026, 11, 28, 14, 0, tzinfo=KST)

WEEKDAY = "월화수목금토일"


def _load(name):
    return json.loads((DATA / "system" / name).read_text(encoding="utf-8"))


ORDERS = {o["order_id"]: o for o in _load("orders.json")}
SHIPMENTS = {s["order_id"]: s for s in _load("shipments.json")}
PRODUCTS = {p["product_id"]: p for p in _load("products.json")}
CONDITIONS = {c["product_id"]: c for c in _load("product_return_conditions.json")}
CUSTOMERS = {c["customer_id"]: c for c in _load("customers.json")}


# ---------------------------------------------------------------- 정책 문서
def _load_policy_docs(path):
    text = path.read_text(encoding="utf-8")
    docs = []
    for chunk in re.split(r"\n(?=## \[)", text)[1:]:
        meta = yaml.safe_load(re.search(r"```yaml\n(.*?)```", chunk, re.S).group(1))
        body = re.sub(r"```yaml\n.*?```", "", chunk, flags=re.S).strip()
        docs.append({"meta": meta, "text": body})
    return docs


DOCS = [d for f in sorted((DATA / "knowledge").glob("*.md")) for d in _load_policy_docs(f)]
DOC_BY_ID = {d["meta"]["doc_id"]: d for d in DOCS}


def _bigrams(s):
    s = re.sub(r"\s+", "", s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def search_docs(query, k=3, approved_only=False, now=NOW):
    """글자 2개 겹침 검색. approved_only=True 이면 승인·유효기간 필터를 먼저 적용"""
    pool = DOCS
    if approved_only:
        pool = [d for d in DOCS if is_doc_valid(d["meta"], now)]
    q = _bigrams(query)
    return sorted(pool, key=lambda d: len(q & _bigrams(d["text"])), reverse=True)[:k]


def is_doc_valid(meta, now=NOW):
    if meta.get("status") != "approved":
        return False
    start, end = meta.get("effective_from"), meta.get("effective_to")
    today = now.date()
    if start and _as_date(start) > today:
        return False
    if end and _as_date(end) < today:
        return False
    return True


# ---------------------------------------------------------------- 날짜 유틸
def _as_date(v):
    if isinstance(v, date) and not isinstance(v, datetime):
        return v
    if isinstance(v, datetime):
        return v.date()
    return datetime.fromisoformat(str(v)).date() if "T" in str(v) else date.fromisoformat(str(v))


def parse_dt(s):
    return datetime.fromisoformat(s) if s else None


def kdate(d):
    """2026-12-01 → '12월 1일(화)'"""
    d = _as_date(d)
    return f"{d.month}월 {d.day}일({WEEKDAY[d.weekday()]})"


def kdatetime(dt):
    """'11월 28일(토) 05:54'"""
    return f"{kdate(dt)} {dt.strftime('%H:%M')}"


def won(n):
    return f"{int(n):,}원"


def next_business_day(d):
    d = _as_date(d) + timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def is_business_hours(now=NOW):
    """MAN-002: 평일 09~18시, 12~13시 제외"""
    if now.weekday() >= 5:
        return False
    return 9 <= now.hour < 18 and now.hour != 12


# ---------------------------------------------------------------- 실행 기록
class Trace:
    """한 요청의 실행 과정을 남김 — 원인 분석과 수정 전후 비교의 근거"""

    def __init__(self, version, case_id=None):
        self.version, self.case_id = version, case_id
        self.events, self.tool_calls = [], []
        self.llm_calls = self.prompt_tokens = self.completion_tokens = 0
        self.t0 = time.time()

    def log(self, kind, **data):
        self.events.append({"t": round(time.time() - self.t0, 3), "kind": kind, **data})

    def tool(self, name, args, result):
        self.tool_calls.append({"tool": name, "args": args})
        self.log("tool", tool=name, args=args, result=_short(result))

    def llm(self, resp, purpose):
        self.llm_calls += 1
        if resp.usage:
            self.prompt_tokens += resp.usage.prompt_tokens
            self.completion_tokens += resp.usage.completion_tokens
        self.log("llm", purpose=purpose,
                 tokens=(resp.usage.prompt_tokens, resp.usage.completion_tokens) if resp.usage else None)

    def summary(self, answer, **extra):
        return {
            "version": self.version, "case_id": self.case_id, "answer": answer,
            "tool_calls": self.tool_calls, "llm_calls": self.llm_calls,
            "prompt_tokens": self.prompt_tokens, "completion_tokens": self.completion_tokens,
            "latency_s": round(time.time() - self.t0, 2), "events": self.events, **extra,
        }


def _short(obj, limit=600):
    s = json.dumps(obj, ensure_ascii=False, default=str)
    return s if len(s) <= limit else s[:limit] + "…"


# ---------------------------------------------------------------- 세션 범위 조회 도구
# customer_id 는 항상 세션 값 — 모델이 인자로 바꿀 수 없음 (접근 권한은 코드에서)
HIDDEN_ORDER_FIELDS = {"shipping_address"}


def tool_list_orders(session):
    cid = session["customer_id"]
    rows = []
    for o in sorted(ORDERS.values(), key=lambda o: o["ordered_at"], reverse=True):
        if o["customer_id"] != cid:
            continue
        sh = SHIPMENTS.get(o["order_id"], {})
        rows.append({
            "order_id": o["order_id"], "ordered_at": o["ordered_at"], "order_status": o["status"],
            "shipment_status": sh.get("status"), "delivered_at": sh.get("delivered_at"),
            "items": [{"line_id": i["line_id"], "product_id": i["product_id"],
                       "product_name": i["product_name"], "line_amount": i["line_amount"]}
                      for i in o["items"]],
        })
    return rows


def tool_get_order(session, order_id):
    o = ORDERS.get(order_id)
    if o is None or o["customer_id"] != session["customer_id"]:
        return {"error": "NOT_FOUND"}  # 존재 여부도 숨김 (MAN-003)
    return {k: v for k, v in o.items() if k not in HIDDEN_ORDER_FIELDS}


def tool_get_shipment(session, order_id):
    sh = SHIPMENTS.get(order_id)
    if sh is None or sh["customer_id"] != session["customer_id"]:
        return {"error": "NOT_FOUND"}
    return sh


def tool_get_return_conditions(session, product_id):
    c = CONDITIONS.get(product_id)
    if c is None:
        return {"error": "NOT_FOUND"}
    p = PRODUCTS[product_id]
    return {**c, "is_final_sale": p["is_final_sale"], "is_custom_made": p["is_custom_made"],
            "product_category": p["category"], "delivery_type": p["delivery_type"]}


def escalation_notice(code, now=NOW):
    """MAN-001/002: E01·E02·E08 은 24시간 긴급, 그 외는 운영시간 외면 다음 영업일 콜백"""
    if code in ("E01", "E02", "E08") or is_business_hours(now):
        return {"code": code, "mode": "즉시 연결", "callback_date": None}
    return {"code": code, "mode": "콜백 예약", "callback_date": next_business_day(now).isoformat()}


def tool_escalate_to_agent(session, reason_code, summary=""):
    return {"ticket": f"ESC-{session['customer_id']}-{reason_code}", **escalation_notice(reason_code)}
