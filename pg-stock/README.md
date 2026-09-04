# pg-stock: 공개 PostgreSQL + 비공개 데이터 시드

## 기술 스택

| 구성 | 역할 | 배포 범위 |
| --- | --- | --- |
| Docker Engine / Docker Compose v2 | 컨테이너와 named volume 오케스트레이션 | 로컬·서버 |
| `postgres:18.6` | PostgreSQL 서버 런타임 (원본 백업과 같은 메이저/마이너 버전) | Docker Hub 공개 Official Image |
| `edumgt/pg-stock-data-seed:2026-09-04` | `pg_stock_data` 백업 아카이브만 포함하는 초기화 이미지 | Docker Hub Private |
| `pg_stock_data` | PostgreSQL 물리 데이터 디렉터리 | Docker named volume |
| `.env` | 포트와 접속 환경 변수 | 서버 로컬 전용 |

## 동작 순서

1. `seed`가 private data-seed 이미지를 받아 빈 `pg_stock_data` 볼륨에 데이터를 푼다.
2. `db`가 공개 `postgres:18.6` 이미지로 시작하고, 같은 named volume을 `/var/lib/postgresql`에 마운트한다.
3. 이미 `PG_VERSION` 파일이 있으면 seed는 데이터를 덮어쓰지 않는다.

물리 PostgreSQL 데이터 디렉터리를 사용하므로 PostgreSQL **18.6**을 유지해야 한다.

## 최초 준비

Docker Hub private 이미지를 받을 수 있도록 로그인한다.

```bash
docker login
cp .env.example .env
# .env의 POSTGRES_PASSWORD를 안전한 값으로 변경
```

`POSTGRES_PASSWORD`는 빈 볼륨을 새로 초기화할 때만 PostgreSQL 계정을 생성한다.
현재 구성처럼 복원된 물리 데이터가 있을 때 실제 계정/비밀번호는 백업 안의 데이터베이스 설정을 따른다.

## data-seed 이미지 빌드 및 게시

저장소 루트에서 실행한다. 데이터가 들어 있으므로 `edumgt/pg-stock-data-seed`는 반드시 Private으로 유지한다.

```bash
docker build \
  -f pg-stock/Dockerfile.seed \
  -t edumgt/pg-stock-data-seed:2026-09-04 \
  .

docker push edumgt/pg-stock-data-seed:2026-09-04
```

## 실행

```bash
cd pg-stock
docker compose up -d
docker compose ps
```

로컬 접속:

```bash
psql "postgresql://admin@localhost:5432/admin"
```

## 재초기화

`down`만으로 named volume은 삭제되지 않는다. seed 데이터를 다시 풀고 싶을 때만 다음을 사용한다. 이 명령은 현재 데이터베이스를 삭제한다.

```bash
docker compose down
docker volume rm pg_stock_data
docker compose up -d
```
