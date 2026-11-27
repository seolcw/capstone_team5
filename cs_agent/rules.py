"""결정론적 비즈니스 로직 — 취소·반품 가능 여부 판정 (v2 에서 LLM 대신 판단)

각 판정 함수는 Decision 을 돌려줍니다.
  - ok / action / escalation : 판정 결과 (answer · confirm · clarify · escalate)
  - draft      : 사실만으로 만든 기본 답변 (LLM 문장화가 실패하면 그대로 사용)
  - required   : 답변에 반드시 들어가야 하는 사실 (출력 검증에 사용)
  - forbidden  : 이 판정과 모순되는 표현 (출력 검증에 사용)
  - refs       : 근거 정책 doc_id
근거 정책: REF-001(일반원칙 7일·6,000원), REF-003(취소), REF-010(신선식품), REF-011(가전 설치),
           REF-015(주문제작), REF-016(Final Sale), REF-018(상품별 조건 우선), MAN-001(E06 고액)
"""
from datetime import timedelta

from .common import (CONDITIONS, NOW, PRODUCTS, SHIPMENTS, escalation_notice, kdate, kdatetime,
                     parse_dt, won)

HIGH_AMOUNT = 500_000  # MAN-001 E06: 환불 예정액 50만원 이상은 상담원 이관
ACTIVE = {"결제완료", "상품준비중", "배송중"}


def decision(ok, draft, *, action="answer", required=(), forbidden=(), refs=(), escalation=None, facts=None):
    return {"ok": ok, "action": action, "draft": draft, "required": list(required),
            "forbidden": list(forbidden), "refs": list(refs), "escalation": escalation, "facts": facts or {}}


def _caution(cond):
    cases = [c for c in cond["non_returnable_cases"] if "단순변심" not in c and "Final Sale" not in c]
    return f" 단, {', '.join(cases)} 시에는 반품이 불가하니 주의해 주세요." if cases else ""


def _escalate_text(code):
    n = escalation_notice(code)
    if n["callback_date"]:
        return (f"상담원이 직접 확인해 드리도록 연결하겠습니다. 지금은 상담원 운영 시간(평일 09:00~18:00)이 아니어서 "
                f"상담 예약(콜백)으로 접수되며, {kdate(n['callback_date'])} 오전 중 연락드립니다."), n
    return "상담원에게 바로 연결해 드리겠습니다.", n


# ---------------------------------------------------------------- 반품 판정
def check_return(order, line, reason="단순변심", now=NOW):
    pid = line["product_id"]
    cond, prod = CONDITIONS[pid], PRODUCTS[pid]
    sh = SHIPMENTS.get(order["order_id"], {})
    name, oid = line["product_name"], order["order_id"]
    delivered = parse_dt(sh.get("delivered_at"))
    refs = list(cond.get("policy_refs") or []) + ["REF-018"]
    fee = cond["return_shipping_fee"]
    window = cond["simple_change_window_days"]
    head = f"{oid} {name}"

    esc = None
    if line["line_amount"] >= HIGH_AMOUNT:
        esc = "E06"

    def finish(ok, draft, required, forbidden, extra_refs=(), facts=None):
        if esc:
            txt, n = _escalate_text(esc)
            draft = f"{draft} 다만 환불 요청 금액이 {won(line['line_amount'])}으로 고액 건이라 {txt}"
            required = list(required) + ["상담원"] + ([kdate(n["callback_date"])] if n["callback_date"] else [])
            return decision(ok, draft, action="escalate", escalation=esc, required=required,
                            forbidden=list(forbidden) + ["환불해 드리겠습니다", "반품 접수되었습니다"],
                            refs=refs + list(extra_refs) + ["MAN-001"], facts=facts)
        return decision(ok, draft, required=required, forbidden=forbidden, refs=refs + list(extra_refs), facts=facts)

    if delivered is None:
        draft = (f"{head}은(는) 아직 수령 전입니다. 상품을 받으신 후 {window}일 이내 반품 신청하실 수 있습니다."
                 if cond["simple_change_returnable"] else f"{head}은(는) 아직 수령 전입니다.")
        return finish(None, draft, [], ["반품 접수되었습니다"])

    if reason == "하자":
        if cond["defect_window_days"] == 1:
            deadline = delivered + timedelta(hours=24)
            ok = now <= deadline
            draft = (f"{head}은(는) 신선식품으로 품질 이상은 수령 후 24시간 이내({kdatetime(deadline)}까지) 사진과 함께 접수해 주셔야 합니다."
                     + ("" if ok else " 접수 가능 시간이 지나 하자 반품 접수가 어렵습니다."))
            return finish(ok, draft, ["24시간"], [], ["REF-010"])
        deadline = delivered.date() + timedelta(days=cond["defect_window_days"])
        ok = now.date() <= deadline
        draft = (f"{head}은(는) 상품 하자의 경우 수령 후 {cond['defect_window_days']}일 이내({kdate(deadline)}까지) 반품 배송비 없이 반품이 가능합니다."
                 if ok else f"{head}은(는) 하자 반품 기간(수령 후 {cond['defect_window_days']}일)이 지났습니다. A/S 센터를 이용해 주세요.")
        return finish(ok, draft, [kdate(deadline)], [], ["REF-005"])

    # ---- 단순변심 (상품별 조건 우선, REF-018)
    nonret = " ".join(cond["non_returnable_cases"])
    if prod["is_final_sale"]:
        return finish(False, f"{head}은(는) Final Sale 상품으로 단순변심 반품·교환이 불가합니다. 상품 하자나 오배송인 경우에는 처리 가능하니 사진과 함께 알려주세요. 모니터 화면에 따른 색상 차이는 하자로 보지 않습니다.",
                      ["Final Sale", "불가"], ["반품 가능합니다", "교환 가능합니다"], ["REF-016"])
    if prod["is_custom_made"]:
        return finish(False, f"{head}은(는) 주문제작 상품으로 단순변심 반품이 불가합니다.",
                      ["주문제작", "불가"], ["반품 가능합니다"], ["REF-015"])
    if prod["category"] == "신선식품":
        return finish(False, f"{head}은(는) 신선식품으로 단순변심 반품이 불가합니다. 다만 변질·이물 등 품질 이상이 있다면 수령 후 24시간 이내({kdatetime(delivered + timedelta(hours=24))}까지) 사진과 함께 접수해 주세요.",
                      ["신선식품", "단순변심 반품이 불가", "24시간"], ["반품 가능합니다", "7일 이내 반품 가능"], ["REF-010"])
    installed = bool(sh.get("installation")) and "설치 완료 후 단순변심" in nonret
    if installed:
        return finish(False, f"{head}은(는) 설치 완료된 가전으로 단순변심 반품이 불가합니다.",
                      ["설치 완료", "불가"], ["반품 가능합니다"], ["REF-011"])
    if not cond["simple_change_returnable"]:
        return finish(False, f"{head}은(는) 단순변심 반품이 불가한 상품입니다({', '.join(cond['non_returnable_cases'])}). 상품 하자는 수령 후 {cond['defect_window_days']}일 이내 접수 가능합니다.",
                      ["불가"], ["반품 가능합니다"])

    deadline = delivered.date() + timedelta(days=window)
    if now.date() > deadline:
        return finish(False, f"{head}은(는) {kdate(delivered)} 수령으로 단순변심 반품 기간(수령 후 {window}일, {kdate(deadline)}까지)이 지나 단순변심 반품은 어렵습니다. 제품 불량이라면 수령 후 {cond['defect_window_days']}일 이내 하자 반품이 가능하니 증상을 알려주세요.",
                      [f"{window}일", "지나", "불량", f"{cond['defect_window_days']}일"], ["반품 가능합니다"],
                      facts={"deadline": str(deadline)})

    promo = f" 상품별 프로모션 조건({cond['special_note']})이 적용됩니다." if cond.get("special_note") else ""
    fee_txt = "반품 배송비는 무료입니다." if fee == 0 else f"단순변심 반품 시 왕복 배송비 {won(fee)}이 부과됩니다."
    required = ["반품이 가능", kdate(deadline), f"{window}일"] + (["무료"] if fee == 0 else [won(fee)])
    forbidden = ["7일이 지나"] if window > 7 else []
    if fee == 0:
        forbidden.append("6,000원")
    return finish(True, f"{head}은(는) {kdate(delivered)}에 수령하셔서 수령 후 {window}일인 {kdate(deadline)}까지 단순변심 반품이 가능합니다.{promo} {fee_txt}{_caution(cond)}",
                  required, forbidden, facts={"deadline": str(deadline), "fee": fee})


# ---------------------------------------------------------------- 취소 판정
def check_cancellation(order, now=NOW):
    oid, status = order["order_id"], order["status"]
    sh = SHIPMENTS.get(oid, {})
    names = ", ".join(i["product_name"] for i in order["items"])
    paid = order["amounts"]["paid_amount"]
    custom = any(PRODUCTS[i["product_id"]]["is_custom_made"] for i in order["items"])
    deny = ["취소되었습니다", "취소 완료"]

    if status in ("취소완료", "환불완료"):
        return decision(False, f"{oid}({names}) 주문은 이미 {status} 상태입니다.", required=[status], refs=["REF-003"])
    if status == "결제완료":
        return decision(True, f"{oid}({names}, {won(paid)}) 주문은 결제완료 상태로 즉시 취소 가능합니다. 취소를 진행할까요? 확인해 주시면 취소 후 결제 수단으로 3~5 영업일 내 환불됩니다.",
                        action="confirm", required=[oid, "취소", "진행할까요"], forbidden=deny, refs=["REF-003", "REF-004"])
    if status == "상품준비중":
        if custom:
            return decision(False, f"{oid}({names})은(는) 주문제작 상품으로, 제작이 시작된 상품준비중 상태부터는 취소가 불가합니다. 각인·제작 내용이 주문과 다르게 제작된 경우에는 재제작 또는 환불이 가능합니다.",
                            required=["주문제작", "취소가 불가"], forbidden=deny + ["취소 가능합니다"], refs=["REF-015", "REF-003"])
        return decision(True, f"{oid}({names}) 주문은 상품준비중 상태로 취소 요청이 가능합니다(출고 여부 확인 후 최대 1영업일 내 처리). 취소 요청을 진행할까요?",
                        action="confirm", required=[oid, "진행할까요"], forbidden=deny, refs=["REF-003"])

    # 배송중 · 배송완료 · 구매확정 → 취소 불가, 반품으로 안내 (REF-003)
    ship_status = sh.get("status") or status
    line = order["items"][0]
    cond = CONDITIONS[line["product_id"]]
    if ship_status == "배송중" or status == "배송중":
        fee = cond["return_shipping_fee"]
        draft = (f"{oid}({names}) 주문은 이미 배송중이라 취소가 불가합니다. 상품을 받으신 후 {cond['simple_change_window_days']}일 이내 반품 신청하실 수 있으며, "
                 f"단순변심 반품 시 왕복 배송비 {won(fee)}이 부과됩니다.{_caution(cond)}")
        return decision(False, draft, required=["배송중", "취소가 불가", "반품"], forbidden=deny,
                        refs=["REF-003", "REF-001"] + list(cond.get("policy_refs") or []))
    ret = check_return(order, line, "단순변심", now)
    ret["draft"] = f"{oid} 주문은 이미 배송이 완료되어 취소는 불가하고 반품으로 진행해야 합니다. " + ret["draft"]
    ret["required"] = ["취소는 불가"] + ret["required"]
    ret["forbidden"] += deny
    ret["refs"] = ["REF-003"] + ret["refs"]
    return ret


# ---------------------------------------------------------------- 대상 주문 후보
def cancel_candidates(orders):
    return [o for o in orders if o["order_status"] in ACTIVE]


def return_candidates(orders, now=NOW):
    """수령 후 단순변심 기간이 남은 주문 (대상이 모호할 때 되묻기용)"""
    out = []
    for o in orders:
        if not o["delivered_at"] or o["order_status"] in ("취소완료", "환불완료", "반품요청", "교환요청"):
            continue
        d = parse_dt(o["delivered_at"]).date()
        if any(CONDITIONS[i["product_id"]]["simple_change_returnable"]
               and now.date() <= d + timedelta(days=CONDITIONS[i["product_id"]]["simple_change_window_days"])
               for i in o["items"]):
            out.append(o)
    return out
