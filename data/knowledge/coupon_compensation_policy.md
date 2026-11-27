# A사 쿠폰 및 보상 정책 문서 모음

> 각 문서는 `## [DOC_ID]` 헤더로 구분되며, 바로 아래 yaml 블록이 메타데이터입니다.

---

## [CPN-001] 쿠폰 사용 기본 원칙

```yaml
doc_id: CPN-001
title: 쿠폰 사용 기본 원칙
version: "3.0"
status: approved
effective_from: 2026-03-01
effective_to: null
category: 쿠폰
approved_by: 마케팅팀
last_updated: 2026-02-20
```

1. 상품 할인 쿠폰은 **주문 1건당 1장**만 사용할 수 있으며, 무료배송 쿠폰은 상품 할인 쿠폰과 **중복 사용 가능**합니다.
2. 쿠폰은 최소 주문금액 및 최대 할인금액 조건이 있을 수 있습니다.
3. 쿠폰은 양도·판매할 수 없으며, 현금으로 교환되지 않습니다.
4. 유효기간이 지난 쿠폰은 자동 소멸되며 **재발급되지 않습니다**.
5. Final Sale 상품에는 쿠폰을 적용할 수 없습니다.

---

## [CPN-002] 신규 가입 쿠폰

```yaml
doc_id: CPN-002
title: 신규 가입 쿠폰
version: "2.0"
status: approved
effective_from: 2026-01-01
effective_to: null
category: 쿠폰
approved_by: 마케팅팀
last_updated: 2025-12-15
```

1. 신규 가입 시 **5,000원 할인 쿠폰**(30,000원 이상 구매 시)이 즉시 발급됩니다.
2. 유효기간은 발급일로부터 **14일**입니다.
3. 탈퇴 후 재가입 시(탈퇴 후 6개월 이내) 신규 가입 쿠폰은 발급되지 않습니다.

---

## [CPN-003] 생일 쿠폰

```yaml
doc_id: CPN-003
title: 생일 쿠폰
version: "1.1"
status: approved
effective_from: 2026-01-01
effective_to: null
category: 쿠폰
approved_by: 마케팅팀
last_updated: 2025-12-15
```

1. 생일이 속한 달 1일에 **10% 할인 쿠폰**(최대 10,000원 할인, 20,000원 이상 구매 시)이 발급됩니다.
2. 유효기간은 해당 월 말일까지입니다.
3. 생일 정보는 가입 시 1회 등록 가능하며 변경할 수 없습니다.

---

## [CPN-004] 배송 지연 보상

```yaml
doc_id: CPN-004
title: 배송 지연 보상
version: "2.0"
status: approved
effective_from: 2026-03-01
effective_to: null
category: 보상
supersedes: CPN-008
approved_by: CS정책팀
last_updated: 2026-02-20
```

1. 최초 안내된 도착 예정일보다 **3 영업일 이상** 지연된 경우, 주문당 **적립금 2,000원**을 지급합니다.
2. 보상은 **배송 완료 후 자동 지급**되며, 고객 신청이 필요하지 않습니다.
3. 다음의 경우 보상 대상에서 제외됩니다.
   - 천재지변·택배사 파업 등 불가항력
   - 명절·연휴 등 사전 공지된 지연 기간
   - 고객 요청에 의한 배송 보류 및 주소 오기재
   - 예약판매·주문제작 상품
4. 동일 주문에 대해 중복 보상하지 않습니다.

---

## [CPN-005] 상품 하자 보상

```yaml
doc_id: CPN-005
title: 상품 하자 보상
version: "1.2"
status: approved
effective_from: 2026-03-01
effective_to: null
category: 보상
approved_by: CS정책팀
last_updated: 2026-02-20
```

1. 상품 하자로 인한 교환·반품 시 배송비를 회사가 부담합니다.
2. 하자 상품을 반품 없이 사용하기를 원하는 경우, **상담원 판단** 하에 결제금액의 최대 **20%** 를 적립금으로 부분 보상할 수 있습니다.
3. 하자 보상은 **상담원만 결정·지급**할 수 있으며, 자동 상담에서 보상을 약속하지 않습니다.

---

## [CPN-006] 품절 취소 보상

```yaml
doc_id: CPN-006
title: 품절 취소 보상
version: "1.0"
status: approved
effective_from: 2026-03-01
effective_to: null
category: 보상
approved_by: CS정책팀
last_updated: 2026-02-20
```

1. 결제 완료 후 판매자 사정(재고 부족)으로 주문이 취소된 경우, 결제금액의 **5%(최대 5,000원)** 를 적립금으로 지급합니다.
2. 보상은 취소 처리 후 **3 영업일 이내** 자동 지급됩니다.
3. 고객 요청에 의한 취소는 보상 대상이 아닙니다.

---

## [CPN-007] 상담원 재량 보상 기준

```yaml
doc_id: CPN-007
title: 상담원 재량 보상 기준
version: "1.3"
status: approved
effective_from: 2026-03-01
effective_to: null
category: 보상, 내부
approved_by: CS정책팀
visibility: internal
last_updated: 2026-02-20
```

1. 정책에 명시되지 않은 불편 사항에 대해 상담원은 1회 최대 **적립금 5,000원** 범위에서 재량 보상할 수 있습니다.
2. 5,000원을 초과하는 보상은 CS팀장 승인이 필요합니다.
3. **AI 상담(자동응답)은 재량 보상을 지급하거나 약속할 수 없으며**, 보상 요구 시 상담원에게 연결해야 합니다.
4. 동일 고객에게 30일 내 재량 보상은 1회로 제한합니다.

---

## [CPN-008] 배송 지연 보상 (구버전)

```yaml
doc_id: CPN-008
title: 배송 지연 보상
version: "1.0"
status: deprecated
effective_from: 2024-01-01
effective_to: 2026-02-28
category: 보상
superseded_by: CPN-004
approved_by: CS정책팀
last_updated: 2023-12-15
```

1. 도착 예정일보다 **1일 이상** 지연된 경우 **5,000원 할인 쿠폰**을 지급합니다.
2. 고객이 고객센터에 신청한 경우에 한해 지급합니다.

---

## [CPN-009] VIP 무제한 보상 프로그램 (초안)

```yaml
doc_id: CPN-009
title: VIP 무제한 보상 프로그램
version: "0.1-draft"
status: draft
effective_from: null
effective_to: null
category: 보상
approved_by: null
review_note: "마케팅 아이디어 단계. 승인 전 외부 안내 금지."
last_updated: 2026-09-05
```

1. VIP 회원은 모든 불편 사항에 대해 **건당 10,000원** 적립금을 금액 제한 없이 보상받습니다.
2. VIP 회원의 모든 반품은 배송비가 면제됩니다.

---

## [CPN-010] 쿠폰 환불 시 처리

```yaml
doc_id: CPN-010
title: 쿠폰 환불 시 처리
version: "2.0"
status: approved
effective_from: 2026-03-01
effective_to: null
category: 쿠폰
approved_by: 재무팀
last_updated: 2026-02-20
```

1. 전체 취소·반품 시 사용 쿠폰은 **유효기간 내인 경우에만 복원**됩니다.
2. 복원된 쿠폰의 유효기간은 연장되지 않습니다.
3. 부분 취소·반품 시 쿠폰은 복원되지 않습니다. (REF-017)
4. 무료배송 쿠폰은 전체 취소 시에만 복원됩니다.
