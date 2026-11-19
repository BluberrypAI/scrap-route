# Re:Source AI

> **현재 SCRAP 처리경로 서비스:** 공정·업체 데이터와 인계 기록은 `scrap-server` PostgreSQL에서 관리합니다. 이 서비스는 후보 전체의 AI 근거 검토와 공개 업체 조사를 담당합니다. 2026-11-15 공개 검색을 PP에서 전체 지원 소재 13종(11개 수지군·알루미늄·철스크랩)으로 확장했습니다. 서버의 공정명·재질·형태·단계를 사용하며, 검색 도구가 반환한 출처 URL이 일치한 단서만 반환합니다. 현재 허가·반입 승인은 추정하지 않습니다. 아래의 기존 연구 아키텍처와 구분합니다.

중소 제조기업의 폐자원 처리 의사결정을 지원하는 **AI·지식 기반 서비스 레포**입니다.
공정·시설 후보 탐색, 근거 문서 검색, 법규·시설 검증 지원, 비용·탄소 계산을 담당합니다.

- 전체 실행 흐름: [docs/pipeline-baseline.md](docs/pipeline-baseline.md)
- 코드와 데이터 구조: [docs/architecture.md](docs/architecture.md)
- SCRAP 처리경로 API: [docs/scrap-next-step.md](docs/scrap-next-step.md)
- 상태·사진 업체 검토: [사진만 먼저 관찰 → 설명·업체 자료 대조](docs/lot-vision-review.md). 업체 최종 수락과 구분합니다.
- 업체별 질문 답변: [추가 답변을 AI 검토에 반영](docs/intake-answers.md). 답변은 자기신고이며 공개 근거·반입 승인으로 취급하지 않습니다.
- 플라스틱 업체 확장: [11개 수지군의 소재·형태 근거 검토와 Azure 실호출 결과](docs/plastic-evidence-review.md). 공정·사업장 데이터는 서버 DB에 있으며 이 레포는 AI 검토를 담당합니다.
- 수도권 후속 검증: [신규 업체 검토·알루미늄캔 표현 수정](docs/capital-region-review-20261116.md). 원문에 있는 “알루미늄캔”을 놓치던 형태 검증을 수정했으며 실제 업체 인수는 자동 승인하지 않습니다.
- 의사결정 연구 검토: [docs/scrap-decision-research.md](docs/scrap-decision-research.md)
- 팀 공통 규칙: [resource-ai-team/.github CONTRIBUTING](https://github.com/resource-ai-team/.github/blob/main/CONTRIBUTING.md)
- 예전 KG를 보는 독립 개발 도구: [scripts/kg_explorer](scripts/kg_explorer/README.md). 현재 업체 검토 런타임에서는 사용하지 않습니다.

## 조직 레포 구성

| 레포 | 역할 |
| --- | --- |
| `Re_ai` (이 레포) | AI Agent, RAG, Knowledge Graph, 비용·탄소 계산 |
| `Re_server` | API Gateway, 인증·회원, 기업 정보, 업무 데이터 |
| `Re_client` | 사용자 화면 |
| `Re_infra` | 전체 통합 실행, 컨테이너 구성, 클라우드 인프라 |
| `.github` | 공통 규칙과 Issue·PR 템플릿 |

## 빠른 시작

### A. macOS·Linux

필수 환경은 Python 3.11 이상과 Docker Desktop입니다.

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,embeddings]'
```

`.env`에서 아래 값을 설정합니다.

```dotenv
NEO4J_PASSWORD=로컬에서_사용할_비밀번호
LAW_API_OC=국가법령정보_공동활용_API_OC
```

PostgreSQL·pgvector와 Neo4j를 실행합니다.

```bash
docker compose -f docker-compose.yml -f docker-compose.neo4j.yml up -d
```

DB 스키마와 지식그래프를 준비합니다.

```bash
resource-rag init-db
resource-kg import
resource-kg audit
```

공식 법령·판례 데이터를 수집하고 인덱싱합니다.

```bash
legal-rag collect
legal-rag index
resource-rag build-public-evidence
resource-rag index data/official/public_evidence_summaries.jsonl
```

API를 실행합니다.

```bash
uvicorn resource_ai.main:app --reload
```

실행 후 확인:

- Swagger UI: http://127.0.0.1:8000/docs
- 상태 확인: http://127.0.0.1:8000/health
- Neo4j Browser: http://127.0.0.1:7474

```bash
curl http://127.0.0.1:8000/health
```

정상 응답:

```json
{"status":"ok"}
```

### B. Windows PowerShell

```powershell
Copy-Item .env.example .env
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev,embeddings]"
docker compose -f docker-compose.yml -f docker-compose.neo4j.yml up -d
.\.venv\Scripts\resource-rag.exe init-db
.\.venv\Scripts\resource-kg.exe import
.\.venv\Scripts\resource-kg.exe audit
.\.venv\Scripts\legal-rag.exe collect
.\.venv\Scripts\legal-rag.exe index
.\.venv\Scripts\uvicorn.exe resource_ai.main:app --reload
```

### C. 전체 서비스 통합 실행

이 레포의 Docker Compose는 AI 로컬 개발용 PostgreSQL·Neo4j만 실행합니다.
`Re_client → Re_server → Re_ai` 전체 서비스 실행과 배포는 `Re_infra`의 Compose·운영 절차를 따릅니다.


## 기술스택

| 영역 | 선택 |
| --- | --- |
| 언어·API | Python 3.11+ / FastAPI |
| RAG 저장소 | PostgreSQL 16 / pgvector |
| 지식그래프 | Neo4j 5 |
| 검색 | Vector Search + Keyword Search + RRF + Reranking |
| 임베딩 | `intfloat/multilingual-e5-small` |
| DB 클라이언트 | psycopg / Neo4j Python Driver |
| 품질 | pytest / ruff |
| 로컬 인프라 | Docker Compose |

`EMBEDDING_PROVIDER=hash`는 테스트용이며 실제 의미 검색에는 사용하지 않습니다.

## 현재 구조

```text
Re_ai/
├── src/resource_ai/
│   ├── agents/            후보 조사 실행과 RAG·KG 호출
│   ├── api/               FastAPI 라우터와 입출력 스키마
│   ├── calculators/       비용·탄소·시나리오 비교
│   ├── core/              설정과 의존성 구성
│   ├── evidence/          공통 근거 문서·검색 결과 모델
│   ├── integrations/      국가법령정보 공동활용 API 연동
│   ├── knowledge_graph/   Neo4j 적재·공정 경로·시설 후보 조회
│   ├── rag/               수집·검증·청킹·임베딩·검색
│   └── rules/             검수된 판정 규칙 골격
├── migrations/            PostgreSQL·pgvector 마이그레이션
├── data/                  설정·샘플·평가 데이터
├── docs/                  아키텍처·실행·검증 문서
├── tests/                 단위·통합 테스트
├── docker-compose.yml     PostgreSQL·pgvector
└── docker-compose.neo4j.yml
```

## 주요 API

| 메서드 | 경로 | 설명 |
| --- | --- | --- |
| `GET` | `/health` | API 프로세스 상태 확인 |
| `GET` | `/rag/search` | RAG 근거 검색 |
| `GET` | `/kg/ontology` | 지식그래프 온톨로지 조회 |
| `GET` | `/kg/planning-coverage` | 공정·시설 연결 범위 진단 |
| `POST` | `/kg/candidates` | 소재 기반 공정 후보 조회 |
| `POST` | `/kg/candidate-pool` | 전체 후보 조사 묶음 조회 |
| `POST` | `/kg/process-plans` | 공정·시설 경로 후보 생성 |
| `POST` | `/kg/facility-candidates` | 시설 후보 조회 |
| `POST` | `/kg/facility-assessment` | 시설 공개 조건 대조 |
| `POST` | `/kg/assessed-plans` | 경로 생성과 시설 조건 대조 |
| `POST` | `/analysis/research` | KG 후보와 법률 근거 연결 |
| `POST` | `/analysis/compare-scenarios` | 비용·탄소·Pareto 비교 |

API별 입력·출력과 현재 한계는 [docs/api.md](docs/api.md)와 실행 중인 Swagger UI에서 확인합니다.

## 테스트

```bash
ruff check .
ruff format --check .
pytest -q
```

실제 PostgreSQL 통합 테스트:

```bash
docker compose up -d postgres
RUN_POSTGRES_INTEGRATION=true pytest -q tests/integration/test_multi_corpus_postgres.py
```

실제 Neo4j 통합 테스트는 `RUN_NEO4J_INTEGRATION=true`를 지정해 실행합니다.

Legal·Technical RAG 검색 품질은 적재가 완료된 PostgreSQL에서 다음과 같이 확인합니다.

```bash
resource-rag evaluate --cases data/config/retrieval_eval.json
```

## 문서

| 문서 | 내용 |
| --- | --- |
| [docs/pipeline-baseline.md](docs/pipeline-baseline.md) | 전체 서비스 파이프라인과 역할 경계 |
| [docs/architecture.md](docs/architecture.md) | 코드·DB·서비스 구조 |
| [docs/api.md](docs/api.md) | API 목록과 오류 처리 |
| [docs/rag-multi-corpus.md](docs/rag-multi-corpus.md) | RAG 문서 계약과 코퍼스별 정책 |
| [docs/knowledge-graph.md](docs/knowledge-graph.md) | KG 적재·조회·검증 |
| [docs/candidate-analysis.md](docs/candidate-analysis.md) | 후보 조사와 비용·탄소 비교 |
| [data/README.md](data/README.md) | 데이터 위치·출처·권리 관리 |
| [docs/README.md](docs/README.md) | 전체 문서 안내 |

## 기여 방법

1. Jira 티켓과 GitHub Issue를 생성합니다.
2. `develop`에서 `feat/깃허브이슈번호-작업명` 브랜치를 만듭니다.
3. 커밋은 `feat:`, `fix:`, `refactor:`, `docs:` 머리말을 사용합니다.
4. 모든 PR은 `develop`을 대상으로 생성하고 CI와 리뷰를 통과합니다.
5. PR이 병합되면 Jira 티켓을 `Done`으로 변경합니다.

`develop → main` 배포 PR은 인프라 담당자만 병합합니다.

## SCRAP 반입 근거 검토

SCRAP의 공정·업체 후보는 scrap-server의 PostgreSQL에서 조회합니다. AI 서비스는 서버가 보낸 후보별 공개 근거를 검토하고, 요청이 있을 때 서버가 선택한 재질·현재 형태·공정의 공개 웹 조사 단서를 반환합니다.

| scrap-server API | scrap-route 내부 API | 역할 |
| --- | --- | --- |
| `POST /api/treatment/intake-review` | `POST /treatment/intake-reviews` | 선택한 한 업체의 반입 근거 검토 |
| `POST /api/treatment/intake-reviews` | `POST /treatment/intake-reviews` | 현재 단계의 모든 업체 후보 검토 |
| `POST /api/treatment/facility-web-search` | `POST /treatment/facility-web-search` | 지원 소재의 현재 공정에 대한 추가 공개 웹 조사 |

서버와 AI에 같은 `SCRAP_INTAKE_SERVICE_TOKEN`을 설정하고 AI에 Azure Responses 배포를 설정합니다. 검토 결과와 조사 단서는 후보 판단에 사용하며 실제 인계 확인은 서버에서 따로 진행합니다.

## 2026-11-15 세부 재질 연결 재검사

server PR #47 / web PR #46에서 문진의 포장재·PA6 어망·기타 수지·알루미늄 스크랩을 연결했습니다. 이 엔진은 서버에서 보낸 후보 전부를 기존 API로 검토합니다. 실제 Azure 49조합/290건은 공개 근거 확인 38건, 추가 근거 필요 252건이었으며 인수 자동 승인은 하지 않았습니다. 첫 병렬 실행의 74건 미완료는 순차 재실행 후 결과를 받았습니다. 이는 가용성 문제가 해결됐다는 의미가 아닙니다.

장애 분석을 위해 후보 검토 실패를 `intake_review_failed reason=...`으로 기록합니다. 허용된 유형만 출력하고 기업 정보·사진·문서·모델 원문·URL·키·예외 원문은 남기지 않습니다. 유형은 provider_rate_limit / provider_auth / provider_timeout / output_budget / provider_filter / incomplete_response / provider_unavailable / invalid_model_json / invalid_result_shape / missing_or_duplicate_result입니다. 상태 계약은 그대로 `model_unavailable`이고 근거 부족과 구분합니다.

## 2026-11-16: 근거 부족 사유와 호출 안정성

후보별 `evidence_gaps` 배열을 추가했습니다. 이전 응답은 빈 배열로 호환됩니다.

| 값 | 의미 |
| --- | --- |
| `input_form_unproven` / `material_unproven` | 투입 형태 / 재질 근거 부족 |
| `output_only` / `process_unproven` | 생산품 소개만 있음 / 수행 공정 불명 |
| `site_scope_unverified` | 실제 수행 사업장 불명 |
| `source_missing` | 공개 자료 없음 |
| `source_context_conflict` / `citation_invalid` | 인용 문맥 상충 / 인용 대조 실패 |
| `unspecified` | 세부 원인 구분 불가 |

모델의 부족 사유와 코드의 인용·형태·사업장 검사 결과를 보존합니다. 이것은 검토 이유의 범주이며 법적 적합성 판정이나 모델 내부 추론 기록이 아닙니다. 과거 252회에는 이 필드가 없었으므로 새 검토 사유와 구분해야 합니다.

Azure 요청 대기는 80초입니다. HTTP 429에 한해 `Retry-After`가 0~30초이고 남은 시간 예산에 여유가 있으면 한 번 재시도합니다. 응답 여부가 불명확한 시간 초과·인증 오류는 자동 재호출하지 않습니다. 추론 설정은 high이며, 실패를 근거 확인이나 인수 승인으로 바꾸지 않습니다. 전체 테스트 540개 통과, 환경 의존 72개 제외, subtest 24개 통과.

## 사진 관찰 재사용과 거리순 검토 연결

인증된 server는 `GET /treatment/review-config`로 모델·지침 버전을 확인하고 `POST /treatment/photo-observations`로 사진만 한 번 관찰합니다. 이후 `intake-reviews`에는 이미지 대신 사진 ID와 관찰 결과를 전달할 수 있습니다. 사진 ID·관찰 버전을 검증하며 비폐기물 사진은 업체 비교 전에 차단합니다. 기존 사진 포함 API는 호환 유지합니다.

근거 대조·인용 검증·업체별 실패 격리와 추론 high를 유지합니다. 실제 AI 호출은 프로세스 전체 최대 3개로 제한합니다. 새 server의 DB 작업 선점과 함께 사용하며, 여러 독립 route 배포에 걸친 분산 할당량 제어를 보장하지 않습니다. 원문·이미지·키를 로그에 남기지 않습니다.

## 공개 근거와 현재 물량 검토 분리

현재 배치 검토는 **공정 관련 업체 탐색**입니다. `process_match`(matched/unverified/mismatch), `process_source`, `process_quote`를 추가했습니다. 실제 사업장의 재질·공정 또는 제조공장 생산품이 관련되면, 구체 투입 형태의 반입 증빙이 없어도 문의 후보가 됩니다. 판매 목록만 있거나 다른 재질·사업장인 경우는 구분합니다. 출처 인용은 서버가 보낸 수집 자료와 다시 대조합니다.

새 방식에서 모델은 허가증·시험성적서·순도 증빙 질문을 생성하지 않습니다. 사진과 설명의 명백한 모순, 눈에 보이는 선별·세척 등의 확인점만 남깁니다. 반입조건과 수락은 B의 대화에서 결정합니다. 기존 `kind`와 단건 API 계약은 보존하며 `process_match=matched`가 반입 승인을 뜻하지 않습니다.

`/treatment/intake-reviews`는 기존 호출을 유지하면서 `public_findings`와 `public_signature`를 선택적으로 받습니다. server가 공용 캐시에 저장한 공개 결과를 보낼 때도 출처 인용·재질·형태를 다시 검사합니다. 서명이 바뀌면409로 거절합니다. 검증된 공개 근거가 있으면 AI는 이번 물량의 관찰·확인사항만 검토합니다. 사진·상태 설명과 업체별 답변은 공용 캐시 대상이 아니며 최종 수락은 수신 업체가 합니다.
