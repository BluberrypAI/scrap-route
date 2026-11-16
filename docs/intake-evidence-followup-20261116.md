# 반입 근거 후속 검증과 공급자 오류 구분

2026-11-16. 업체 데이터는 server PR #47의 PostgreSQL 참조에 둔다.
이번 서버 변경은 화성 LDPE 필름의 자체 압출 공정을 추가하고, 기존 보류 연결의 원문을 다시 대조한다.
AI가 공장 목록을 만들어내거나 부족한 근거를 강제로 통과시키지는 않는다.

문진 번호·R유형·현재 형태 → 모든 후보별 근거 검토 순서와 `dispatch_approved=false`는 유지한다.
한국철강의 철스크랩 구매·전기로 투입 반기보고서를 추가한 후, 가공 철스크랩 후속 공정은 실제 Azure에서
공개 근거 확인 응답을 받았다. 이는 개별 로트의 절단 치수·등급·오염 한도나 반입 승인이 확인됐다는 뜻은 아니다.

병렬 검증 중 Azure 호출 한도에 걸렸다. 근거 부족과 호출 장애를 구분해 순차 재검사했다.
HTTP 400·404·408·500·502·503·504도 원문 예외 대신 고정된 오류 사유로만 로그에 남긴다.
숫자 외 비공개 문자열이 섞인 예외는 일반 사유로 처리한다. 모델 텍스트·기업 정보·키는 기록하지 않는다.

검증: 558개 및 24개 하위 검사 통과, 환경 의존 72개 생략. 오류 로그 회귀 8개 추가, Ruff 검사 통과.

[문진·웹·PostgreSQL·Azure 통합 검사와 남은 범위](https://github.com/BluberrypAI/scrap-server/blob/feat/T-142-plastic-facility-evidence/docs/intake-evidence-followup-validation-20261116.md)
 · [12개 연결·PE/PS 베일 원문 대조](https://github.com/BluberrypAI/scrap-server/blob/feat/T-142-plastic-facility-evidence/docs/registry-screen/intake-evidence-followup-20261116.md)
