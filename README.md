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

---

# 데이터셋 — A사 이커머스 고객 상담 목업 데이터

> 배포된 데이터 설명(README)을 옮긴 것입니다. 이 레포에는 `data/` 아래에 풀려 있으며,
> 공개 평가셋은 `data/eval_public.jsonl` 에 있습니다 (`eval/` 폴더 아님). `eval_private`·`eval_security` 는 배포되지 않았습니다.

- **운영 시간대**: `2026-11-28(토) 10:00 ~ 17:00 KST`
- 이 시간대 안에서는 **언제 조회해도 데이터 상태가 바뀌지 않도록** 설계했습니다. 서버는 실제 현재 시각을 그대로 LLM에 넣으면 됩니다.
  - 10:00 / 13:30 / 17:00 기준으로 각각 생성해 주문·배송·쿠폰 상태와 평가 정답이 모두 같음을 확인
  - 11/28은 토요일이라 출고·배송·상품준비중 전환·환불 승인·보상 지급이 일어나지 않습니다 (모두 영업일에만 발생)
  - 새벽배송은 토요일 04~07시에 완료되고 다음 출고는 23:30이라 시간대 밖, 구매확정은 자정 배치, 쿠폰 만료는 23:59
- 모든 고객·주문 정보는 가상 데이터. 재생성: `python3 generate.py <출력경로> [기준시각ISO]` (seed 고정)

### 토요일이라서 생기는 정답 차이
- 상담원 연결이 필요한 경우(E03~E07, E09~E11) → "주말이라 상담 예약(콜백) 접수, **11월 30일(월)** 오전 중 연락"이 정답에 포함
- 긴급(E01 법적 분쟁, E02 안전사고, E08 계정 도용) → 주말에도 **당직 상담원** 즉시 연결
- 배송중인 주문 대부분의 도착 예정일은 **11월 30일(월)** 이후 (주말 배송 없음)
- 그래서 LLM에 **요일까지** 넘겨야 판단할 수 있습니다 (예: `2026-11-28(토) 13:05`)

## 파일 구성

| 구분 | 파일 | 건수 | 용도 |
| --- | --- | --- | --- |
| 지식 | `knowledge/shipping_policy.md` | 10 문서 | 배송 정책 (RAG) |
| 지식 | `knowledge/refund_exchange_policy.md` | 20 문서 | 교환·환불 정책 |
| 지식 | `knowledge/terms_of_service.md` | 10 문서 | 이용약관 |
| 지식 | `knowledge/coupon_compensation_policy.md` | 10 문서 | 쿠폰·보상 정책 |
| 지식 | `knowledge/agent_escalation_manual.md` | 5 문서 | 상담원 연결·대응 매뉴얼 |
| 지식 | `knowledge/faq.json` | 100 | FAQ (outdated 4건 포함) |
| 지식 | `knowledge/consultation_history.json` | 200 | 베이스라인 봇의 과거 상담 로그 (오답 라벨 포함) |
| 시스템 | `system/products.json` | 100 | 상품 |
| 시스템 | `system/customers.json` | 50 | 고객 |
| 시스템 | `system/orders.json` | 200 | 주문 |
| 시스템 | `system/shipments.json` | 200 | 배송 (주문 1:1) |
| 시스템 | `system/coupons.json` | 50 | 고객 보유 쿠폰 |
| 시스템 | `system/product_return_conditions.json` | 100 | 상품별 교환·환불 조건 |
| 평가 | `eval/eval_public.jsonl` | 30 | 공개 평가셋 (C0001~C0025 시나리오) |
| 평가 | `eval/eval_private.jsonl` | 30 | 비공개 평가셋 (C0026~C0045 시나리오) |
| 평가 | `eval/eval_security.jsonl` | 20 | 보안·예외 상황 테스트 |

## 정책 문서(.md) 포맷

`## [DOC_ID] 제목` 단위로 청킹하고, 바로 아래 ```yaml 블록을 메타데이터로 파싱합니다.

| 필드 | 값 |
| --- | --- |
| `status` | `approved` / `deprecated` / `draft` / `rejected` / `expired` / `unverified` |
| `effective_from`, `effective_to` | 시행 기간 (null = 미정/현행) |
| `supersedes`, `superseded_by` | 버전 연결 |
| `visibility` | `internal` 이면 고객에게 내용 공개 금지 (CPN-007, MAN-001/003/005) |

**고객 안내 근거로 쓸 수 있는 문서 = `status: approved` 이면서 NOW가 시행 기간 안에 있는 문서**뿐입니다.

## 전제한 도구(Tool) 인터페이스

평가셋의 `expected.tool_calls`는 아래 이름을 기준으로 작성했습니다. 실제 구현에 맞게 이름을 바꿔 써도 됩니다.

| 도구 | 인자 | 비고 |
| --- | --- | --- |
| `get_customer_profile` | `customer_id` | 등급, 적립금 |
| `list_orders` | `customer_id`, `status?`, `date_from?` | 세션 customer_id만 허용 |
| `get_order` | `order_id` | **소유자 검증 필수** — 타인 주문이면 `FORBIDDEN` |
| `get_shipment` | `order_id` | 택배사 연동 실시간 정보 (orders보다 우선) |
| `get_product` | `product_id` | 재고·판매상태 |
| `get_return_conditions` | `product_id` | 상품별 조건 (카테고리 정책보다 우선) |
| `list_coupons` | `customer_id`, `status?` | |
| `search_knowledge` | `query`, `filters?` | 권장 필터: `status=approved`, 시행기간 |
| `cancel_order` | `order_id` | 고객의 명시적 확인 후에만 실행 |
| `create_claim` | `order_id`, `type`, `line_ids`, `reason` | 반품/교환 접수 |
| `escalate_to_agent` | `reason_code`(E01~E11), `summary` | MAN-001 기준 |


## v4 — B 방식 에이전트 (멘토 피드백 반영)

LLM 이 도구를 고르고, 결과를 보고 다음 행동을 정하는 Baseline B 구조를 유지한 채, 실패 원인을 먼저 분석해 **도구 · 검색(RAG) · 행동 수단**을 고친 버전입니다.
원인 분석과 단계별 측정: `docs/b_failure_analysis.md` · 구조도: `docs/architecture_v4.png`

| 파일 | 내용 |
|---|---|
| `cs_agent/v4_agent.py` | Agent loop + 도구 9개(list_orders, get_order, get_shipment, get_return_conditions, list_coupons, get_customer_profile, search_knowledge, escalate_to_agent, ask_customer) + 답변 자기 점검 |
| `eval_b.py` | `eval_run.py` 와 같은 채점으로 v4 평가 |

```powershell
# 평가 (공개 30문항)
py -m uv run --with sentence-transformers python eval_b.py --versions v1p v4 --runs 1 --cases all
# 다른 평가 파일
py -m uv run --with sentence-transformers python eval_b.py --versions v4 --runs 1 --cases all --data holdout_team.jsonl
# 직접 대화
py -m uv run --with sentence-transformers python chat_v3.py C0001 --v4
```

에이전트 함수: `from cs_agent.v4_agent import run` → `run(query, {"customer_id": "C0001", "authenticated": True})` → `{"answer", "action", "escalation", "tool_calls", ...}`
