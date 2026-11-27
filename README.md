# 캡스톤 5팀 — E-commerce 상담 에이전트

집중 영역: **시스템 실행 — 비즈니스 로직 위반** (취소·반품 가능 여부를 LLM 이 잘못 판단하는 문제)

## 버전별 구성 (같은 데이터·같은 도구, 판단 주체만 다름)

| 버전 | 파일 | 구성 | 판단 주체 |
|---|---|---|---|
| v0 Naive RAG | `cs_agent/v0_naive_rag.py` | 질문 → 문서 검색(필터 없음) → LLM 답변 | LLM (주문 데이터 없음) |
| v1 Naive Agent | `cs_agent/v1_naive_agent.py` | LLM 이 도구·순서 자율 결정, 정책 읽고 가능 여부 판단 | LLM |
| v2 Hybrid | `cs_agent/v2_hybrid.py` | LLM 의도 분류 → 코드 판정(`rules.py`) → LLM 문장화 → 코드 출력 검증 | 코드 |

공통: `cs_agent/common.py` (데이터·기준 시각 2026-11-28(토) 14:00·날짜 유틸·세션 범위 도구·trace)

## 처음 세팅 (팀원)

```powershell
git clone https://github.com/seolcw/capstone_team5.git
cd capstone_team5
copy .env.example .env               # 값 확인 후 저장 (.env 는 커밋 금지)
py -m uv sync                        # Python 3.14 + 의존성 설치
py -m uv run python 01_chat.py       # LLM 연결 확인 (SSH 터널 필요)
```

## 협업 규칙

- `main` 에 직접 push 하지 말고 브랜치(`feat/...`, `fix/...`)를 만들어 PR 로 합칩니다.
- 작업 시작 전 `git pull` 로 최신 `main` 을 받습니다.
- `results/` 는 각자 로컬에만 남습니다. 보고서에 쓸 결과만 `git add -f` 로 올립니다.

## 실행

```powershell
py -m uv run python test_rules.py          # LLM 없이 판정 로직 점검
py -m uv run python eval_run.py            # v0/v1/v2 × 케이스 10개 × 3회
py -m uv run python eval_run.py --versions v2 --runs 1 --cases PUB-006
```

결과는 `results/<시각>/summary.md`(비교표·실패 상세)와 `runs.jsonl`(실행별 trace)에 저장됩니다.
SSH 터널(`ssh -N -L 8000:localhost:8000 tunnel@117.16.244.167`)이 켜져 있어야 합니다.

## 테스트 케이스 (eval_public 중 판정 관련 10건)

PUB-005(결제완료 취소 → 확인 질문), 006(배송중 취소 → 불가·반품 안내), 007(반품 기한 12/1),
008(기한 경과), 009(신선식품), 010(상품별 30일 무료 우선), 011(Final Sale), 017(설치 TV·고액 E06),
019(주문제작 취소 불가), 025(대상 모호 → 되묻기)
