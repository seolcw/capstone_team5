"""3단계 — 기준점 흔들림 보기: 유사도 기준점을 바꿔도 결과가 유지되는지 확인

  uv run --with sentence-transformers python threshold_sweep.py

방식: 질문마다 유사도 점수와 LLM 분류 결과를 '한 번만' 구해 두고,
      낮은 기준점 0.40/0.45/0.50 × 높은 기준점 0.60/0.65/0.70 = 9개 조합으로 처리 결과를 계산
시험 질문: scope_testset.jsonl 30문항 + 공개 평가셋 30개(전부 범위 안 → 오차단 확인용)
주의: 기준점을 '고르는' 용도가 아니라 '흔들리는지 확인'하는 용도. 여기 결과로 기준점을 다시 맞추면 과적합
결과: 화면 출력 + threshold_sweep_result.md
"""
import json
import pathlib

from cs_agent.common import Trace
from cs_agent.scope_guard import OTHER_SHOPS, SIM_HIGH, SIM_LOW, check_urgent, classify, similarity

LOWS = [0.40, 0.45, 0.50]
HIGHS = [0.60, 0.65, 0.70]


def load():
    rows = []
    for l in pathlib.Path("scope_testset.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            rows.append({"id": r["id"], "query": r["query"], "label": r["label"]})
    for l in pathlib.Path("data/eval_public.jsonl").read_text(encoding="utf-8").splitlines():
        if l.strip():
            r = json.loads(l)
            rows.append({"id": r["id"], "query": r["query"], "label": "pass"})
    return rows


def route(q, low, high):
    """scope_guard.guard 와 같은 순서로, 미리 구한 점수·분류로 처리 결과만 계산"""
    if q["urgent"]:
        return "urgent", False
    if not q["shop"]:
        if q["score"] >= high:
            return "pass", False
        if q["score"] <= low:
            return "block", False
    cat = q["category"]
    if cat in ("out_of_scope", "greeting"):
        return "block", True          # greeting 도 v1 으로 안 넘어감
    return "pass", True               # in_scope · mixed


def main():
    qs = load()
    print(f"질문 {len(qs)}개 — 유사도·분류를 한 번씩 계산합니다")
    for q in qs:
        tr = Trace("sweep", q["id"])
        q["urgent"] = check_urgent(q["query"])
        q["score"], _ = similarity(q["query"])
        q["shop"] = any(s in q["query"] for s in OTHER_SHOPS)
        q["category"] = classify(q["query"], tr)["category"]   # 기준점과 상관없이 한 번만
        print(f"  {q['id']:<8} [{q['label']}] 유사도 {q['score']} · 분류 {q['category']}{' · 타사' if q['shop'] else ''}"
              f"{' · 긴급 ' + q['urgent'] if q['urgent'] else ''}  {q['query'][:40]}")

    n_block = sum(q["label"] == "block" for q in qs)
    n_pass = sum(q["label"] == "pass" for q in qs)
    n_urgent = sum(q["label"] == "urgent" for q in qs)

    lines = ["| 낮은 기준점 | 높은 기준점 | 범위 밖 차단 | 오차단 | 긴급 연결 | LLM 분류 호출 | 틀린 질문 |",
             "|---|---|---|---|---|---|---|"]
    for low in LOWS:
        for high in HIGHS:
            blocked = false_block = urgent_ok = llm = 0
            wrong = []
            for q in qs:
                r, used_llm = route(q, low, high)
                llm += used_llm
                if q["label"] == "block":
                    blocked += r == "block"
                    if r != "block":
                        wrong.append(q["id"])
                elif q["label"] == "pass":
                    if r != "pass":
                        false_block += 1
                        wrong.append(q["id"])
                else:
                    urgent_ok += r == "urgent"
                    if r != "urgent":
                        wrong.append(q["id"])
            cur = " ← 지금" if (low, high) == (SIM_LOW, SIM_HIGH) else ""
            lines.append(f"| {low:.2f} | {high:.2f}{cur} | {blocked}/{n_block} | {false_block}/{n_pass} | "
                         f"{urgent_ok}/{n_urgent} | {llm}/{len(qs)} | {', '.join(wrong) or '-'} |")

    table = "\n".join(lines)
    print("\n" + table)
    detail = "\n".join(f"| {q['id']} | {q['label']} | {q['score']} | {q['category']} | {'O' if q['shop'] else ''} | {q['query']} |"
                       for q in sorted(qs, key=lambda x: -(x['score'] or 0)))
    pathlib.Path("threshold_sweep_result.md").write_text(
        "# 기준점 흔들림 결과\n\n" + table +
        "\n\n## 질문별 점수·분류 (유사도 높은 순)\n\n| ID | 기대 | 유사도 | LLM 분류 | 타사 | 질문 |\n|---|---|---|---|---|---|\n" + detail + "\n",
        encoding="utf-8")
    print("\n저장: threshold_sweep_result.md")


if __name__ == "__main__":
    main()
