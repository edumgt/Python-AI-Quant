# 주식 투자 기초 학습 웹앱

로컬 PC에서 실행하는 학습용 웹앱입니다. 가장 간단한 방법은 Docker Compose를 사용하는 것입니다.

## NotebookLM - https://notebook.google.com/notebook/42560d11-3e03-4b66-890d-67d52d52ccca

## 1. Docker로 실행하기 (권장)

### 준비물

- Docker Desktop(Windows·macOS) 또는 Docker Engine + Docker Compose 플러그인(Linux)
- 사용 가능한 포트: `8000`, `27017`, `6333`, `6334`

저장소 최상위 폴더에서 실행합니다.

```bash
# 최초 실행: 앱·MongoDB·Qdrant를 시작하고 퀴즈 데이터를 적재합니다.
docker compose --profile init up --build -d

# 이후 실행
docker compose up -d
```

브라우저에서 <http://localhost:8000>을 엽니다.

정상 실행 여부는 다음 주소에서 확인합니다.

```text
http://localhost:8000/api/health
```

## 삼성전자 LEAN 백테스트 (별도 Compose 구성)

웹앱과 독립적으로 QuantConnect LEAN 기반 삼성전자(`005930.KS`) 일봉 예제를
실행할 수 있습니다. 실행 이미지에는 전략 모듈이 포함되며, 컨테이너가 시작할 때
공개 가격 데이터를 받은 뒤 한 번의 백테스트를 수행합니다.

```bash
docker compose -f docker-compose.lean.yml run --rm samsung-backtest
```

결과 파일과 `orders.csv`는 `lean-results/`에 생성됩니다. 기본 기간은 2024년이며,
다른 기간을 지정하려면 다음처럼 실행합니다.

```bash
SAMSUNG_START_DATE=2023-01-01 SAMSUNG_END_DATE=2024-01-01 \
  docker compose -f docker-compose.lean.yml run --rm samsung-backtest
```

전략과 Dockerfile은 [lean-samsung/](lean-samsung/)에 있습니다. 이 구성은 Custom
Data 기반의 동작 예제이므로 KRX 수수료·배당·거래일·환율 모델을 포함하지 않습니다.

## 현대자동차 LEAN 추세 신호 검증 (별도 Compose 구성)

현대자동차 보통주(`005380.KS`)의 Yahoo Finance 일봉 Custom Data로 2026년 상반기
추세 신호를 검증할 수 있습니다. 2022~2025년 데이터로 이동평균을 준비한 뒤,
`SMA20 > SMA60`일 때 롱 신호를 내고 그 외에는 현금 보유하는 전략입니다.

```bash
docker compose -f docker-compose.hd.yaml run --build --rm hyundai-backtest
```

기본 데이터 기간은 2022-01-01부터 2026-06-30까지이며, 검증 기간은 2026년
상반기입니다. 다른 기간을 지정하려면 다음 환경 변수를 설정합니다.

```bash
HYUNDAI_DATA_START_DATE=2022-01-01 HYUNDAI_DATA_END_DATE=2026-07-01 \
HYUNDAI_TEST_START_DATE=2026-01-01 HYUNDAI_TEST_END_DATE=2026-07-01 \
  docker compose -f docker-compose.hd.yaml run --build --rm hyundai-backtest
```

실행 결과는 `hyundai-results/`에 저장되며,
`hyundai-2026-h1-report.html`에서 월별 다음 거래일 방향 적중률, 신호 전략과
단순 보유의 누적 수익률, 주문 수·순수익·낙폭·Sharpe Ratio를 확인할 수 있습니다.
전략과 상세 사용법은 [lean-hyundai/](lean-hyundai/)에서 확인하세요. 이 검증은
과거 가격 기반 신호 예제이며 KRX 수수료·세금·배당·액면분할·환율은 반영하지 않습니다.

### 포트 또는 API 키 설정

이미 같은 포트를 사용 중이면 저장소 루트에 `.env` 파일을 만들고 값을 바꿉니다.

```dotenv
APP_PORT=8080
MONGO_PORT=27018
QDRANT_PORT=6335
QDRANT_GRPC_PORT=6336

# 선택 사항: 공시·통계 API 기능
DART_API_KEY=
```

`APP_PORT`를 바꿨다면 접속 주소도 예를 들어 <http://localhost:8080>으로 바뀝니다.

### 문서 검색 색인 만들기

`docs/`의 Markdown 문서를 바꾼 뒤에는 아래 명령으로 Qdrant 검색 색인을 다시 만듭니다.

```bash
docker compose --profile tools run --rm docs-index
```

문서 검색은 외부 생성형 AI 없이 해시 임베딩을 사용합니다.

### 상태 확인·종료

```bash
# 컨테이너 상태
docker compose ps

# 앱 로그
docker compose logs -f backend

# 컨테이너 종료 (데이터는 유지)
docker compose down
```

아래 명령은 MongoDB 퀴즈 데이터와 Qdrant 검색 색인까지 삭제합니다.

```bash
docker compose down -v
```

## 2. Python으로 직접 실행하기

Docker를 쓰지 않는 경우에는 Python과 MongoDB를 직접 준비합니다.

### 준비물

- Python 3.12 이상
- MongoDB (퀴즈 기능 사용 시)
- `mongosh` (아래 퀴즈 초기화 스크립트 사용 시)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 로컬 환경변수 설정

백엔드는 실행할 때 `app/backend/.env`를 읽습니다. 먼저 저장소에 포함된 예시 파일을
복사해 개인별 설정 파일을 만드세요. `.env`는 API 키처럼 민감한 값을 담을 수 있으므로
Git에 추가하지 않습니다.

macOS·Linux에서는 다음을 실행합니다.

```bash
cp app/backend/.env.example app/backend/.env
```

Windows PowerShell에서는 다음 명령을 사용합니다.

```powershell
Copy-Item app/backend/.env.example app/backend/.env
```

복사한 `app/backend/.env`를 열어 필요한 값만 수정합니다.

```dotenv
# 퀴즈 기능용 MongoDB. 로컬 기본 설치를 사용하면 그대로 둡니다.
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=investment_db

# 문서 검색(RAG)용 Qdrant. 검색 기능을 쓰지 않으면 Qdrant가 없어도 앱의 다른 기능은 실행됩니다.
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=investment_docs

# 선택 사항: 문서 검색 결과만 외부 AI로 문장 정리할 때 사용합니다.
# 세 값이 모두 있어야 문서 검색 채팅의 외부 AI 선택 항목이 활성화됩니다.
# RAG_LLM_BASE_URL=https://api.openai.com/v1
# RAG_LLM_API_KEY=
# RAG_LLM_MODEL=

# OpenDART 기업 검색·재무 분석 기능을 사용할 때만 발급받은 인증키를 입력합니다.
# 비워 두면 DART 관련 API는 503 응답을 반환합니다.
DART_API_KEY=

# 선택 사항: GPU 환경에서 텍스트-이미지 생성에 다른 Diffusers 모델을 쓸 때만 설정합니다.
# DIFFUSERS_MODEL_ID=runwayml/stable-diffusion-v1-5
```

설정 항목은 다음과 같습니다.

| 변수 | 필요한 기능 | 설명 |
| --- | --- | --- |
| `MONGODB_URL` | 퀴즈 | MongoDB 접속 주소입니다. MongoDB를 쓰지 않는 화면은 이 값 없이도 열 수 있지만, 퀴즈 조회·저장은 동작하지 않습니다. |
| `MONGODB_DB` | 퀴즈 | 사용할 데이터베이스 이름입니다. 로컬 기본값은 `investment_db`입니다. |
| `QDRANT_URL` | 문서 검색 | Qdrant HTTP 주소입니다. Qdrant가 실행되지 않으면 RAG 검색 API는 `503`을 반환합니다. |
| `QDRANT_COLLECTION` | 문서 검색 | 색인할 Qdrant 컬렉션 이름입니다. 색인 명령과 같은 값으로 유지하세요. |
| `RAG_LLM_BASE_URL` | 문서 검색 답변 다듬기 | 선택 설정입니다. OpenAI Chat Completions 호환 API의 기본 주소입니다. |
| `RAG_LLM_API_KEY` | 문서 검색 답변 다듬기 | 선택 설정입니다. 외부 AI 인증키이며 공개 저장소나 화면 캡처에 포함하지 마세요. |
| `RAG_LLM_MODEL` | 문서 검색 답변 다듬기 | 선택 설정입니다. 사용할 외부 AI 모델 이름입니다. 세 값이 모두 설정될 때만 선택 UI가 활성화됩니다. |
| `DART_API_KEY` | 기업·공시 분석 | OpenDART 인증키입니다. 키를 공개 저장소나 화면 캡처에 포함하지 마세요. |
| `DIFFUSERS_MODEL_ID` | 텍스트-이미지 생성 | 선택 설정입니다. 기본 모델을 바꾸려는 GPU 환경에서만 사용합니다. |

MongoDB와 Qdrant를 모두 로컬에 설치하지 않았다면, Docker Compose로 두 서비스만 실행한 뒤
Python 백엔드를 직접 실행할 수도 있습니다.

```bash
docker compose up -d mongo qdrant
```

문서 검색을 처음 사용하거나 `docs/`의 Markdown을 변경한 뒤에는 Qdrant에 문서를 색인합니다.

```bash
QDRANT_URL=http://localhost:6333 \
QDRANT_COLLECTION=investment_docs \
./scripts/upload_docs_to_qdrant.sh
```

앱을 시작합니다.

```bash
uvicorn app.backend.main:app --host 0.0.0.0 --port 8000
```

브라우저에서 <http://localhost:8000>을 열고, API 명세와 요청 예시는
<http://localhost:8000/docs>에서 확인할 수 있습니다. 다음 명령으로도 서버 상태를 확인합니다.

```bash
curl http://localhost:8000/api/health
```

퀴즈 데이터를 MongoDB에 넣으려면 별도 터미널에서 실행합니다.

```bash
./scripts/init_quiz_mongodb.sh --replace
```

`--replace`는 기존 퀴즈 문항을 삭제하고 현재 시드 문항으로 교체합니다.

## 문서 메뉴 갱신

학습 문서의 제목이나 파일을 수정했다면 다음 명령을 실행합니다.

```bash
python3 scripts/sync_learning_menu.py
```

## 문제 해결

- 페이지에 접속할 수 없으면 `docker compose ps` 또는 터미널의 Uvicorn 로그를 확인하세요.
- 퀴즈가 저장되지 않으면 MongoDB가 실행 중인지와 `MONGODB_URL`을 확인하세요.
- 문서 검색이 비어 있으면 Qdrant가 실행 중인지 확인한 뒤 `docs-index`를 다시 실행하세요.
- `DART_API_KEY` 등 선택 API 키가 비어 있으면 해당 외부 데이터 기능이 제한될 수 있습니다.
