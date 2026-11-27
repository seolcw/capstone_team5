"""입력 검사 연결부 — 팀원 범위 관문(scope_guard.guard)을 v1+ · v3 가 쓰는 check_input 약속에 맞춤

  check_input(query, session) -> None(통과) | {"answer": 응답, "reason": 사유}

- 범위 밖(block) · 인사(greeting) → 여기서 끝냄 (LLM 상담·도구 호출 없음 → 토큰 절약)
- 긴급(urgent) · 혼합(mixed) · 범위 안(pass) → None 으로 통과시켜 v3 가 처리
  (v3 에 안전사고 E02 처리기가 있어 상담원 연결·콜백 판정까지 일관되게 처리)
- 관문 자체 오류는 통과 (상담을 막는 것보다 v3 의 범위외 처리에 맡기는 편이 안전)
"""
from .common import Trace
from .scope_guard import guard

STOP = {"block": "out_of_scope", "greeting": "greeting"}


def check_input(query, session):
    tr = Trace("guard")
    try:
        g = guard(query, tr)
    except Exception:  # 임베딩 모델 로드 실패 등
        return None
    if g["route"] in STOP:
        return {"answer": g["answer"], "reason": STOP[g["route"]], "layer": g.get("layer"),
                "tokens": tr.prompt_tokens + tr.completion_tokens}
    return None
