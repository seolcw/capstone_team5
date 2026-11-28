"""B 방식(v4) 평가 — eval_run.py 와 같은 채점·요약을 쓰고 v4 만 추가로 등록

  py -m uv run --with sentence-transformers python eval_b.py --versions v1p v4 --runs 1 --cases all
"""
import os

import llm_client

if os.getenv("LLM_MAX_RETRIES"):  # 외부 무료 API 의 분당 호출 제한(429) 대비 — 재시도 횟수만 늘림
    llm_client.client = llm_client.client.with_options(max_retries=int(os.environ["LLM_MAX_RETRIES"]))

import eval_run  # noqa: E402 (위에서 client 를 바꾼 뒤 불러와야 적용됨)
from cs_agent import v4_agent  # noqa: E402

eval_run.VERSIONS["v4"] = v4_agent.run

if __name__ == "__main__":
    eval_run.main()
