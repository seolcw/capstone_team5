# v1+ 작업 분담 — 팀원용 AI 프롬프트

v1+ = Baseline B(v1, `cs_agent/v1_naive_agent.py`) 구조는 그대로 두고, LLM 앞뒤를 코드로 지키는 개선판입니다.

```
사용자 질문
   ↓
[작업 1. 입력 검사]  ── 범위 외 / 인젝션 / 타인 정보 → 거절      ← 팀원 A  (cs_agent/guard.py)
   ↓ 정상 질문
 LLM Agent ⇄ [작업 2. 도구 결과 검증] ⇄ 정책 검색 / 주문 / 배송 도구   ← 팀원 B  (cs_agent/v1_plus.py)
   ↓
 최종 답변
```

| 작업 | 담당 | 만드는 파일 | 프롬프트 |
|---|---|---|---|
| 1. 입력 검사 | 팀원 A | `cs_agent/guard.py`, `test_guard.py` | [task_1_input_guard.md](task_1_input_guard.md) |
| 2. 도구 결과 검증 | 팀원 B | `cs_agent/v1_plus.py`, `eval_run.py` 수정 | [task_2_tool_verify.md](task_2_tool_verify.md) |

## 사용법
1. 자기 작업 파일(`task_1_...md` 또는 `task_2_...md`)을 **통째로 복사**해서 자기 AI(Claude Code, ChatGPT 등)에 붙여 넣습니다.
2. AI가 설명 → 코드 작성 → 실행 확인 순서로 도와줍니다. 모르는 건 AI에게 "더 쉽게 설명해줘"라고 물어보면 됩니다.

## 두 사람이 겹치지 않게 하는 약속
- 팀원 A는 `cs_agent/guard.py`, `test_guard.py` **만** 만들고 고칩니다.
- 팀원 B는 `cs_agent/v1_plus.py`, `eval_run.py` **만** 만들고 고칩니다.
- 둘을 잇는 약속(인터페이스)은 함수 하나입니다:
  ```python
  # cs_agent/guard.py
  def check_input(query: str, session: dict) -> dict | None:
      """정상 질문이면 None, 거절해야 하면 {"answer": 거절 문장, "reason": 사유코드} 반환"""
  ```
  사유코드: `"out_of_scope"`(범위 외), `"injection"`(인젝션), `"other_customer"`(타인 정보)
- 팀원 B는 guard.py 가 아직 없어도 돌아가게 만들어 둡니다(아래 task_2 참고). A가 끝나면 자동으로 연결됩니다.
- 작업 전 `git pull`, 올릴 때는 **자기 파일만** `git add` 합니다. `.env` 는 절대 올리지 않습니다.
