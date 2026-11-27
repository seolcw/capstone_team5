"""v0 — Naive RAG (주제 PDF 11p Baseline A)

질문 → 글자 겹침 검색 상위 3개(필터 없음) → 프롬프트 → 답변.
주문·배송 데이터에 접근할 수 없으므로 '내 주문' 질문은 원리적으로 풀 수 없습니다.
"""
from llm_client import client, MODEL

from .common import Trace, search_docs


def run(query, session, case_id=None):
    tr = Trace("v0", case_id)
    docs = search_docs(query, k=3, approved_only=False)
    tr.log("retrieve", docs=[(d["meta"]["doc_id"], d["meta"]["status"]) for d in docs])
    context = "\n\n".join(d["text"] for d in docs)
    prompt = f"다음 문서를 참고하여 고객 질문에 답변하세요.\n\n참고 문서:\n{context}\n\n고객 질문:\n{query}\n"
    resp = client.chat.completions.create(model=MODEL, messages=[{"role": "user", "content": prompt}], temperature=0)
    tr.llm(resp, "answer")
    return tr.summary(resp.choices[0].message.content,
                      retrieved=[d["meta"]["doc_id"] for d in docs], action="answer")
