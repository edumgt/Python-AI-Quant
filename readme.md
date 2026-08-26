# Qunat 관련 과정

## WSL, VSCode, Git, GitHub, Docker 기본 사용 

## 투자분석 기초 방법론	
- 매크로 분석: 경제지표 분석(금리, 물가, 유가 등 주요 지표 보는 법 ), 거시경제상황 분석 실습 
- 산업 분석: 산업 경쟁력 분석(산업경쟁력 개념/분석모형, 산업별 분석방법), 산업 분석 실습 
- 기본적 분석: 재무제표분석 (손익계산서/대차대조표/현금흐름표), 기업가치분석(상대가치평가 밸류에이션(멀티플), 절대가치평가 밸류에이션 (DCF, EVA, FCF 등)), 분석기업선정 및 밸류에이션 실습 
- 기술적 분석: 추세 분석(지지선과 저항선, 이동평균선, 갭 반전, 되돌림 분석 등), 패턴 분석, 캔들 차트 분석, 지표 분석, 앨리어트파동이론, 분석기업선정 및 기술적 분석 실습	
> 80 시간

## 퀀트를 위한 금융 필수 지식	
- 금융상품 이해: 주식/ETF 상품(주식/ETF 개요 및 운용 전략), 채권 상품(채권 개요 및 운용 전략), 파생상품(파생상품 개요 및 운용 전략) 
- 자산배분방법론: 포트폴리오 이론(개요 및 성과분석, 리스크 지표), 자산배분 모델(평균분산, 블랙리터만, Risk-Parity 모델 설명), 사례 분석 실습
> 40 시간

## 데이터 활용 퀀트 모델링	
- 백테스트로 나오는 성과 지표 분석(MDD, Sharp ratio 등) 및 개선방향 논의 
- 주식 시장의 계절성 분석(연말 랠리, 월별 효과, 요일 효과) 
- 알고리즘 트레이딩 &amp; 자동매매 기초(트레이딩뷰 PineScript)	
> 40 시간

## 나만의 로보 어드바이저 개발 및 성과 검증 프로젝트	
- AI 기반의 자동화 로보 어드바이저 모델 개발 
- 패턴 인식 기법을 활용한 주식 시장 예측 프로젝트 
- 자산배분모델을 활용한 포트폴리오 최적화, 주식 스크리닝을 통한 종목 선정 등 직접 수행 
- 구축한 퀀트 모델의 결과를 해석해보고 자체적으로 모의 투자 의사결정 진행	
> 100 시간

## 나만의 투자 인디케이터 개발 및 성과 검증 프로젝트	
- 기본적인 인디케이터(MA, RSI등)로 전략 설계 
- 커스텀 인디케이터 개발 
- 트레이딩뷰 플랫폼으로 성과 확인 및 코딩 실습(PineScript) 
- 파이썬 프로그래밍을 통한 성과 검증 
- 증권사 연동(API 활용)을 통한 자동화 모델 구현	
> 120 시간


---


# 주식 투자 기초 학습 웹앱

로컬 PC에서 실행하는 학습용 웹앱입니다. 가장 간단한 방법은 Docker Compose를 사용하는 것입니다.

## 기술 스택

| 구분 | 기술 |
| --- | --- |
| 백엔드 | Python 3.12, FastAPI, Uvicorn, ORJSON |
| 프론트엔드 | HTML, CSS, JavaScript, Mermaid |
| 데이터·분석 | Pandas, NumPy, scikit-learn, PyTorch, yfinance, PyKrx, OpenDART |
| 데이터 저장·검색 | MongoDB, Qdrant |
| AI·RAG | Ollama (`embeddinggemma`, `qwen3:8b`), Diffusers, Amazon Lex V2 |
| 인프라·배포 | Docker, Docker Compose, AWS |
| 백테스트 | QuantConnect LEAN, Yahoo Finance Custom Data |

## NotebookLM - https://notebook.google.com/notebook/42560d11-3e03-4b66-890d-67d52d52ccca

## 1. Docker로 실행하기 (권장)

### 준비물

- Docker Desktop(Windows·macOS) 또는 Docker Engine + Docker Compose 플러그인(Linux)
- 사용 가능한 포트: `8000`, `27017`, `6333`, `6334`

저장소 최상위 폴더에서 실행합니다.

```bash
# 최초 실행: 앱·MongoDB·Qdrant·Ollama를 시작하고 퀴즈 데이터를 적재합니다.
docker compose --profile init up --build -d

# 최초 한 번: 로컬 답변 모델과 임베딩 모델을 받습니다.
docker compose --profile ollama-init run --rm ollama-init

# 모델을 받은 뒤 문서를 Ollama 임베딩으로 색인합니다.
docker compose --profile tools run --rm docs-index

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

### QuantConnect LEAN 소개

[QuantConnect LEAN](https://github.com/QuantConnect/Lean)은 QuantConnect가 공개한
오픈소스 알고리즘 트레이딩 엔진입니다. 데이터 구독, 주문 처리, 포트폴리오 관리와
성과 지표 계산을 하나의 엔진에서 제공하며, Python과 C# 전략을 실행할 수 있습니다.
이 저장소에서는 LEAN 공식 Docker 이미지(`quantconnect/lean`)를 사용해 국내 주식
일봉 데이터를 Custom Data로 불러오고, 전략의 매매 신호와 누적 수익률·낙폭·Sharpe
Ratio 등의 백테스트 결과를 재현 가능한 컨테이너 환경에서 확인합니다.

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

문서 검색은 Markdown의 제목 계층을 보존해 청크를 만들고, Ollama의 `embeddinggemma`로
문서와 질문을 같은 벡터 공간에 임베딩합니다. 질의 시에는 넓게 찾은 벡터 후보를 문서 제목·핵심어
일치로 한 번 더 정렬하며, 선택 시 로컬 Ollama 채팅 모델이 검색 원문만 근거로 답변을 생성합니다. 기본 모델은
`embeddinggemma`(임베딩)와 `qwen3:8b`(답변)이며, 저장소 루트 `.env`에서
`RAG_EMBEDDING_MODEL`, `RAG_LLM_MODEL`로 바꿀 수 있습니다. 모델을 바꿨다면 반드시
문서 색인을 다시 만드세요.

`docker-compose.prod.yml`은 AWS용 구성으로 Ollama를 포함하지 않습니다. 이 구성에서는
`RAG_EMBEDDING_PROVIDER=hash`로 동작하므로, AWS에서 Ollama 이미지·모델·포트를 설치하거나
노출하지 않습니다. AWS용 문서 색인은 `RAG_EMBEDDING_PROVIDER=hash`로 다시 만들어야 하며,
화면의 로컬 AI 답변 생성 선택지는 비활성화됩니다.

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

# 로컬 Ollama 기반 전체 RAG. 색인과 질의에 같은 임베딩 모델을 사용합니다.
RAG_EMBEDDING_PROVIDER=ollama
RAG_EMBEDDING_URL=http://localhost:11434/api/embed
RAG_EMBEDDING_MODEL=embeddinggemma
RAG_LLM_BASE_URL=http://localhost:11434/v1
RAG_LLM_API_KEY=ollama
RAG_LLM_MODEL=qwen3:8b
RAG_LLM_TIMEOUT_SECONDS=180

# 선택 사항: 우측 AI 투자 도우미를 Amazon Lex V2에 연결합니다.
# 장기 자격 증명 대신 EC2/ECS 등의 IAM 역할 사용을 권장합니다.
# AWS_REGION=ap-northeast-2
# LEX_BOT_ID=
# LEX_BOT_ALIAS_ID=
# LEX_LOCALE_ID=ko_KR

# OpenDART 기업 검색·재무 분석 기능을 사용할 때만 발급받은 인증키를 입력합니다.
# 비워 두면 DART 관련 API는 503 응답을 반환합니다.
DART_API_KEY=

# 선택 사항: GPU 환경에서 텍스트-이미지 생성에 다른 Diffusers 모델을 쓸 때만 설정합니다.
# DIFFUSERS_MODEL_ID=runwayml/stable-diffusion-v1-5
```

Lex 봇은 배포한 버전의 별칭을 사용하세요. 애플리케이션을 실행하는 EC2/ECS 역할에는 해당 별칭 ARN(`arn:aws:lex:<리전>:<계정>:bot-alias/<봇ID>/<별칭ID>`)에 대한 `lex:RecognizeText` 권한만 부여하면 됩니다. 브라우저나 저장소에 AWS 액세스 키를 넣지 마세요.

설정 항목은 다음과 같습니다.

| 변수 | 필요한 기능 | 설명 |
| --- | --- | --- |
| `MONGODB_URL` | 퀴즈 | MongoDB 접속 주소입니다. MongoDB를 쓰지 않는 화면은 이 값 없이도 열 수 있지만, 퀴즈 조회·저장은 동작하지 않습니다. |
| `MONGODB_DB` | 퀴즈 | 사용할 데이터베이스 이름입니다. 로컬 기본값은 `investment_db`입니다. |
| `QDRANT_URL` | 문서 검색 | Qdrant HTTP 주소입니다. Qdrant가 실행되지 않으면 RAG 검색 API는 `503`을 반환합니다. |
| `QDRANT_COLLECTION` | 문서 검색 | 색인할 Qdrant 컬렉션 이름입니다. 색인 명령과 같은 값으로 유지하세요. |
| `RAG_EMBEDDING_PROVIDER` | 문서 검색 | 로컬은 `ollama`, Ollama를 설치하지 않는 AWS 구성은 `hash`를 사용합니다. 두 방식의 색인은 서로 호환되지 않습니다. |
| `RAG_EMBEDDING_URL` | 문서 검색 | Ollama의 `/api/embed` 주소입니다. 색인과 질의가 같은 주소·모델을 사용해야 합니다. |
| `RAG_EMBEDDING_MODEL` | 문서 검색 | 문서·질문을 벡터화할 Ollama 임베딩 모델입니다. 모델을 바꾸면 색인을 다시 만듭니다. |
| `RAG_DENSE_CANDIDATES` | 문서 검색 | 하이브리드 재정렬 전 벡터 후보 수입니다. 기본값은 `40`이며, 큰 값은 검색 품질 후보를 넓히는 대신 응답 처리량이 조금 늘어납니다. |
| `RAG_LLM_BASE_URL` | 문서 검색 답변 생성 | Ollama OpenAI 호환 API의 기본 주소입니다. 기본값은 `http://localhost:11434/v1`입니다. |
| `RAG_LLM_API_KEY` | 문서 검색 답변 생성 | Ollama 로컬 API에서는 무시되지만, 앱의 OpenAI 호환 호출을 위해 비어 있지 않은 값을 사용합니다. |
| `RAG_LLM_MODEL` | 문서 검색 답변 생성 | 검색 원문만 바탕으로 답변을 만들 Ollama 채팅 모델입니다. |
| `RAG_LLM_TIMEOUT_SECONDS` | 문서 검색 답변 생성 | 로컬 모델 응답을 기다리는 최대 시간(초)입니다. CPU 환경에서는 첫 요청이 느릴 수 있습니다. |
| `AWS_REGION` | AI 투자 도우미 | Amazon Lex V2 봇이 배포된 AWS 리전입니다. |
| `LEX_BOT_ID` | AI 투자 도우미 | Amazon Lex V2 봇 ID입니다. |
| `LEX_BOT_ALIAS_ID` | AI 투자 도우미 | 배포한 Amazon Lex V2 별칭 ID입니다. |
| `LEX_LOCALE_ID` | AI 투자 도우미 | Lex 로캘입니다. 기본값은 `ko_KR`입니다. |
| `DART_API_KEY` | 기업·공시 분석 | OpenDART 인증키입니다. 키를 공개 저장소나 화면 캡처에 포함하지 마세요. |
| `DIFFUSERS_MODEL_ID` | 텍스트-이미지 생성 | 선택 설정입니다. 기본 모델을 바꾸려는 GPU 환경에서만 사용합니다. |

MongoDB·Qdrant·Ollama를 모두 로컬에 설치하지 않았다면, Docker Compose로 세 서비스를 실행한 뒤
Python 백엔드를 직접 실행할 수도 있습니다.

```bash
docker compose up -d mongo qdrant ollama
docker compose --profile ollama-init run --rm ollama-init
```

문서 검색을 처음 사용하거나 `docs/`의 Markdown을 변경한 뒤에는 Qdrant에 문서를 색인합니다.

```bash
QDRANT_URL=http://localhost:6333 \
QDRANT_COLLECTION=investment_docs \
RAG_EMBEDDING_PROVIDER=ollama \
RAG_EMBEDDING_URL=http://localhost:11434/api/embed \
RAG_EMBEDDING_MODEL=embeddinggemma \
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


## 본 7차 과정의 시험 방식 - 실습 50% 반영
### 다음의 실습을 https://st.edumgt.co.kr/analysis.html 사이트를 통해 진행 합니다.(국비과정에 명기된 내용)
- 매크로 분석: 경제지표 분석(금리, 물가, 유가 등 주요 지표 보는 법 ), 거시경제상황 분석 실습 
- 산업 분석: 산업 경쟁력 분석(산업경쟁력 개념/분석모형, 산업별 분석방법), 산업 분석 실습 
- 기본적 분석: 재무제표분석 (손익계산서/대차대조표/현금흐름표), 기업가치분석(상대가치평가 밸류에이션(멀티플), 절대가치평가 밸류에이션 (DCF, EVA, FCF 등)), 분석기업선정 및 밸류에이션 실습 
- 기술적 분석: 추세 분석(지지선과 저항선, 이동평균선, 갭 반전, 되돌림 분석 등), 패턴 분석, 캔들 차트 분석, 지표 분석, 앨리어트파동이론, 분석기업선정 및 기술적 분석 실습

### 결과물은 모두에게 공유되어 공정하게 확인 되도록 각자 작업 내용을 json 포맷으로 남겨 디스코드에 공유 합니다.
![alt text](image.png)

### 위와 같이 전체적으로 클릭, 입력 이벤트의 작업에 대해 Applicaion - localstorage 에 데이타가 생성되며 80%가 넘은
### 해당 데이타 셋을 copy object 로 메모장에 복사. 압축하여 디스코드에 성명1.zip 으로 업로드 합니다.

## 개발환경 구축 테스트 - 50% 반영
### https://github.com/edumgt/investment-analysis repo 에 대해 각 수강생별 본인 PC 환경의 Docker 에서
### 실행 퀴즈 - 단어장 30문제에 대해 퀴즈 본 후 해당 결과를 mongodb 에서 데이타 추출( 이 모든 과정은 AI 의 도움을 받아 처리합니다.) 후 위와 같은 방법으로 성명2.zip 으로 업로드 합니다.
