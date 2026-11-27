"""v0 / v1 / v2 를 같은 테스트셋으로 실행하고 수정 전후를 비교

  py -m uv run python eval_run.py                 # 전체 (버전 3개 × 케이스 10개 × 3회)
  py -m uv run python eval_run.py --versions v1 v2 --runs 1 --cases PUB-006 PUB-019

결과: results/<시각>/runs.jsonl (실행별 trace 포함), results/<시각>/summary.md
"""
import argparse
import json
import pathlib
import statistics
import time
from collections import defaultdict

from cs_agent import v0_naive_rag, v1_naive_agent, v1_plus, v2_hybrid, v3_hybrid

# 집중 영역: 시스템 실행 — 비즈니스 로직 위반 (취소·반품 가능 여부 판정)
TARGET_CASES = ["PUB-005", "PUB-006", "PUB-007", "PUB-008", "PUB-009",
                "PUB-010", "PUB-011", "PUB-017", "PUB-019", "PUB-025"]
# v1+ 영역: 지식 검색 정보 충돌 · 데이터 정합성 (배송조회·정책문의)  →  --cases info
INFO_CASES = ["PUB-001", "PUB-002", "PUB-003", "PUB-004", "PUB-012", "PUB-013",
              "PUB-014", "PUB-022", "PUB-023", "PUB-024", "PUB-028", "PUB-029"]
VERSIONS = {"v0": v0_naive_rag.run, "v1": v1_naive_agent.run, "v1p": v1_plus.run, "v2": v2_hybrid.run, "v3": v3_hybrid.run}
ALL_CASES = [f"PUB-{n:03d}" for n in range(1, 31)]  # --cases all
ROOT = pathlib.Path(__file__).parent


def load_cases(ids, data="eval_public.jsonl"):
    rows = [json.loads(l) for l in (ROOT / "data" / data).read_text(encoding="utf-8").splitlines() if l.strip()]
    by_id = {r["id"]: r for r in rows}
    return list(by_id.values()) if ids == ["all"] else [by_id[i] for i in ids]


def score(case, out):
    exp, ans = case["expected"], out["answer"] or ""
    inc = [s for s in exp["must_include"] if s in ans]
    bad = [s for s in exp["must_not_include"] if s in ans]
    return {
        "include_hit": len(inc), "include_total": len(exp["must_include"]),
        "missing": [s for s in exp["must_include"] if s not in ans], "forbidden_hit": bad,
        "pass": len(inc) == len(exp["must_include"]) and not bad,
        "action_ok": out.get("action") == exp["action"],
        "escalation_ok": out.get("escalation") == exp["escalation_code"],
    }


def run_one(fn, case, version):
    try:
        out = fn(case["query"], case["session"], case["id"])
    except Exception as e:  # 실행 오류도 결과로 기록 (도구 장애·파싱 오류 분석용)
        out = {"version": version, "case_id": case["id"], "answer": f"(ERROR {type(e).__name__}: {e})",
               "tool_calls": [], "llm_calls": 0, "prompt_tokens": 0, "completion_tokens": 0,
               "latency_s": 0, "events": [], "action": None, "escalation": None}
    out["score"] = score(case, out)
    return out


def summarize(results, cases, versions, runs):
    lines = [f"# 평가 결과 — 케이스 {len(cases)}개 × {runs}회\n"]
    head = "| 지표 | " + " | ".join(versions) + " |\n|---|" + "---|" * len(versions)
    rows = defaultdict(list)
    for v in versions:
        rs = [r for r in results if r["version"] == v]
        n = len(rs)
        per_case = defaultdict(list)
        for r in rs:
            per_case[r["case_id"]].append(r)
        consistent = sum(1 for c in per_case.values()
                         if len({json.dumps([t["tool"] for t in r["tool_calls"]]) for r in c}) == 1
                         and len({r["score"]["pass"] for r in c}) == 1)
        same_answer = sum(1 for c in per_case.values() if len({r["answer"] for r in c}) == 1)
        rows["통과율 (must_include 전부 + must_not 없음)"].append(f"{sum(r['score']['pass'] for r in rs)}/{n}")
        rows["must_include 충족률"].append(
            f"{sum(r['score']['include_hit'] for r in rs) / max(1, sum(r['score']['include_total'] for r in rs)):.0%}")
        rows["금지 표현 등장 (잘못된 판정 안내)"].append(f"{sum(bool(r['score']['forbidden_hit']) for r in rs)}건")
        rows["action 일치 (answer/confirm/clarify/escalate)"].append(f"{sum(r['score']['action_ok'] for r in rs)}/{n}")
        rows["일관성: 반복 실행 시 도구순서·결과 동일"].append(f"{consistent}/{len(per_case)} 케이스")
        rows["일관성: 반복 실행 시 답변 문장 동일"].append(f"{same_answer}/{len(per_case)} 케이스")
        rows["평균 도구 호출 수"].append(f"{statistics.mean(len(r['tool_calls']) for r in rs):.1f}")
        rows["평균 LLM 호출 수"].append(f"{statistics.mean(r['llm_calls'] for r in rs):.1f}")
        rows["평균 토큰 (입력+출력)"].append(f"{statistics.mean(r['prompt_tokens'] + r['completion_tokens'] for r in rs):,.0f}")
        rows["latency 중앙값 (초)"].append(f"{statistics.median(r['latency_s'] for r in rs):.1f}")
        rows["출력검증 → draft 대체 횟수 (v2·v3)"].append(f"{sum(bool(r.get('fallback')) for r in rs)}건" if v in ("v2", "v3") else "")
        rows["경로 (v3: 코드/정책/agent)"].append(" · ".join(f"{k} {n}" for k, n in sorted(
            __import__("collections").Counter(r.get("route", "-") for r in rs).items())) if v == "v3" else "")
    lines.append(head)
    for k, vals in rows.items():
        vals = vals + [""] * (len(versions) - len(vals))
        lines.append(f"| {k} | " + " | ".join(vals) + " |")

    lines.append("\n## 케이스별 통과 (통과 횟수/실행 횟수)\n")
    lines.append("| 케이스 | 질문 | " + " | ".join(versions) + " |\n|---|---|" + "---|" * len(versions))
    for c in cases:
        cells = []
        for v in versions:
            rs = [r for r in results if r["version"] == v and r["case_id"] == c["id"]]
            cells.append(f"{sum(r['score']['pass'] for r in rs)}/{len(rs)}")
        lines.append(f"| {c['id']} | {c['query']} | " + " | ".join(cells) + " |")

    lines.append("\n## 실패 상세 (첫 번째 실행 기준)\n")
    for c in cases:
        for v in versions:
            r = next((r for r in results if r["version"] == v and r["case_id"] == c["id"]), None)
            if r and not r["score"]["pass"]:
                lines.append(f"- **{c['id']} {v}** — 누락 {r['score']['missing']} · 금지 {r['score']['forbidden_hit']} · "
                             f"도구 {[t['tool'] for t in r['tool_calls']]}\n  - 답변: {(r['answer'] or '').replace(chr(10), ' ')[:300]}")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--versions", nargs="+", default=list(VERSIONS))
    ap.add_argument("--cases", nargs="+", default=TARGET_CASES)
    ap.add_argument("--runs", type=int, default=3)
    ap.add_argument("--data", default="eval_public.jsonl", help="평가 데이터 파일 (data/ 아래), 예: holdout_team.jsonl")
    args = ap.parse_args()

    ids = {"info": INFO_CASES}.get(args.cases[0], args.cases) if len(args.cases) == 1 else args.cases
    cases = load_cases(ids, args.data)
    outdir = ROOT / "results" / time.strftime("%Y%m%d-%H%M%S")
    outdir.mkdir(parents=True, exist_ok=True)
    results = []
    with (outdir / "runs.jsonl").open("w", encoding="utf-8") as f:
        for v in args.versions:
            for case in cases:
                for k in range(args.runs):
                    r = run_one(VERSIONS[v], case, v)
                    r["run"] = k
                    results.append(r)
                    f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
                    f.flush()
                    print(f"{v} {case['id']} run{k}: {'PASS' if r['score']['pass'] else 'FAIL'} "
                          f"tools={len(r['tool_calls'])} llm={r['llm_calls']} {r['latency_s']}s", flush=True)
    summary = summarize(results, cases, args.versions, args.runs)
    (outdir / "summary.md").write_text(summary, encoding="utf-8")
    print(f"\n결과 저장: {outdir}")


if __name__ == "__main__":
    main()
