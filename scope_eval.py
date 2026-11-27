"""범위 판단 시험 — scope_testset.jsonl 질문을 버전별로 돌려 답변을 모음

  uv run --with sentence-transformers python scope_eval.py              # v1+ 만
  uv run --with sentence-transformers python scope_eval.py --versions v1 v1+ --runs 3   # v1 과 비교할 때

결과: scope_results_<시각>.jsonl (답변 원문 + 관문 판단) + scope_judge_<시각>.md (판정 칸이 빈 표)
"""
import argparse
import json
import time

from cs_agent import v1_naive_agent, v1_plus

VERSIONS = {"v1": v1_naive_agent.run, "v1+": v1_plus.run}
SESSION = {"customer_id": "C0001", "authenticated": True, "now": None, "channel": "앱 채팅"}
EXPECT = {"block": "막기", "pass": "통과", "urgent": "긴급 이관"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--versions", nargs="+", default=["v1+"])
    ap.add_argument("--runs", type=int, default=1)
    ap.add_argument("--testset", default="scope_testset.jsonl")
    args = ap.parse_args()

    cases = [json.loads(l) for l in open(args.testset, encoding="utf-8") if l.strip()]
    stamp = time.strftime("%m%d-%H%M")
    rows = []
    for r_i in range(args.runs):
        for c in cases:
            for v in args.versions:
                try:
                    out = VERSIONS[v](c["query"], SESSION, c["id"])
                except Exception as e:
                    out = {"answer": f"(ERROR {type(e).__name__}: {e})", "tool_calls": [], "llm_calls": 0,
                           "prompt_tokens": 0, "completion_tokens": 0, "latency_s": 0}
                g = out.get("guard") or {}
                row = {**c, "version": v, "run": r_i + 1, "answer": out.get("answer"),
                       "tools": [t["tool"] for t in out.get("tool_calls", [])],
                       "llm_calls": out.get("llm_calls"),
                       "tokens": (out.get("prompt_tokens") or 0) + (out.get("completion_tokens") or 0),
                       "latency_s": out.get("latency_s"), "escalation": out.get("escalation"),
                       "guard_route": g.get("route"), "guard_layer": g.get("layer"),
                       "guard_score": g.get("score"), "guard_reason": g.get("reason"),
                       "output_check": g.get("output_check")}
                rows.append(row)
                gtxt = f" [{row['guard_layer']}→{row['guard_route']}]" if g else ""
                print(f"[{c['id']} {v} #{r_i+1}] ({EXPECT[c['label']]}){gtxt} {c['query']}\n"
                      f"   → {(row['answer'] or '').strip()[:140]}")

    res_path, judge_path = f"scope_results_{stamp}.jsonl", f"scope_judge_{stamp}.md"
    with open(res_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    with open(judge_path, "w", encoding="utf-8") as f:
        f.write("# 범위 판단 판정표\n\n판정: 막음 / 답함 / 이관. 맞음: 기대와 같으면 O\n\n")
        f.write("| ID | 버전 | 회차 | 분류 | 질문 | 기대 | 관문 | 답변(앞부분) | 이관 | 판정 | 맞음 |\n"
                "|---|---|---|---|---|---|---|---|---|---|---|\n")
        for r in rows:
            ans = (r["answer"] or "").replace("\n", " ").replace("|", "/")[:80]
            gate = f"{r['guard_layer']}→{r['guard_route']}" if r["guard_route"] else ""
            f.write(f"| {r['id']} | {r['version']} | {r['run']} | {r['category']} | {r['query']} | "
                    f"{EXPECT[r['label']]} | {gate} | {ans} | {r['escalation'] or ''} |  |  |\n")
    print(f"\n저장: {res_path}, {judge_path}")


if __name__ == "__main__":
    main()
