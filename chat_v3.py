"""직접 써 보기 — 고객이 되어 최종 상담봇(관문 + v3)과 대화

  py -m uv run --with sentence-transformers python chat_v3.py            # 기본 고객 C0001
  py -m uv run --with sentence-transformers python chat_v3.py C0007      # 고객 번호 지정
  py -m uv run --with sentence-transformers python chat_v3.py C0001 --v4 # B 방식 에이전트(v4)로 대화

명령: /고객 C0013  → 고객 바꾸기 · /나가기 → 종료
답변 아래에 [처리 경로 · 상담원 이관 코드 · 토큰 · 시간] 이 같이 나옵니다.
"""
import sys

from cs_agent import v3_hybrid, v4_agent

args = [a for a in sys.argv[1:] if not a.startswith("--")]
cid = args[0] if args else "C0001"
agent = v4_agent if "--v4" in sys.argv else v3_hybrid
print(f"[{agent.__name__.split('.')[-1]}] 고객 {cid} 로 로그인했어요. 질문을 입력하세요. (/고객 C0007 · /나가기)\n")
n = 0
while True:
    try:
        q = input(f"[{cid}] 나> ").strip()
    except (EOFError, KeyboardInterrupt):
        break
    if not q:
        continue
    if q == "/나가기":
        break
    if q.startswith("/고객"):
        cid = q.split()[-1]
        print(f"→ 고객 {cid} 로 바꿨어요.\n")
        continue
    n += 1
    out = agent.run(q, {"customer_id": cid, "authenticated": True}, f"CHAT-{n:03d}")
    print(f"\n상담봇> {out['answer']}")
    print(f"   [경로 {out.get('route')} · 이관 {out.get('escalation') or '-'} · "
          f"토큰 {out['prompt_tokens'] + out['completion_tokens']:,} · {out['latency_s']:.1f}초]\n")
