"""관문만 따로 시험 — v1 을 부르지 않고 guard() 판단만 봄 (빠르고 토큰 적음)

  uv run --with sentence-transformers python guard_only.py data/eval_public.jsonl
  uv run --with sentence-transformers python guard_only.py 다른질문파일.jsonl

- 질문 파일은 한 줄에 {"id": ..., "query": ...} 형식. "label"(block/pass/urgent)이 있으면 맞았는지도 셈
- label 이 없으면 전부 '범위 안'으로 보고 막힌 질문(오차단)을 찾음 (공개 평가셋은 원래 전부 범위 안)
결과: 화면 출력 + guard_only_<파일이름>.jsonl
"""
import json
import pathlib
import sys
from collections import Counter

from cs_agent.common import Trace
from cs_agent.scope_guard import guard

OK = {"block": {"block"}, "pass": {"pass"}, "urgent": {"urgent"}, None: {"pass", "urgent"}}


def main():
    path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "data/eval_public.jsonl")
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    out, wrong = [], []
    for r in rows:
        tr = Trace("guard", r.get("id"))
        g = guard(r["query"], tr)
        label = r.get("label")
        ok = g["route"] in OK[label]
        rec = {"id": r.get("id"), "query": r["query"], "label": label or "pass(범위 안)", "route": g["route"],
               "layer": g.get("layer"), "score": g.get("score"), "reason": g.get("reason"), "ok": ok,
               "llm_calls": tr.llm_calls, "tokens": tr.prompt_tokens + tr.completion_tokens}
        out.append(rec)
        if not ok:
            wrong.append(rec)
        mark = "O" if ok else "X"
        print(f"{mark} {rec['id']} [{rec['label']}] {rec['layer']}→{rec['route']} (유사도 {rec['score']}) {r['query'][:50]}")

    print("\n[요약]")
    print(f"  전체 {len(out)}개 중 맞음 {len(out) - len(wrong)}개")
    print(f"  판단 경로: {dict(Counter(r['layer'] for r in out))}")
    print(f"  LLM 분류 호출 {sum(r['llm_calls'] for r in out)}회")
    if wrong:
        print("  틀린 것:")
        for w in wrong:
            print(f"    - {w['id']} 기대 {w['label']} / 실제 {w['route']} ({w['layer']}, {w['reason']}) {w['query']}")

    save = pathlib.Path(f"guard_only_{path.stem}.jsonl")
    save.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in out) + "\n", encoding="utf-8")
    print(f"\n저장: {save}")


if __name__ == "__main__":
    main()
