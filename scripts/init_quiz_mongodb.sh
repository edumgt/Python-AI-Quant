#!/usr/bin/env bash
# MongoDB에 퀴즈 데이터를 적재합니다.
# 이미 존재하는 문항은 건너뜁니다(upsert).
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SQL_FILE="${QUIZ_SQL_FILE:-$ROOT_DIR/app/backend/quiz_seed.sql}"
MONGODB_URL="${MONGODB_URL:-mongodb://localhost:27017}"
MONGODB_DB="${MONGODB_DB:-investment_db}"
MONGODB_COLLECTION="${MONGODB_COLLECTION:-quiz_questions}"

usage() {
  cat <<EOF
Usage: $(basename "$0") [--sql-file <path>] [--replace]

Options:
  --sql-file <path>   사용할 SQL 파일 경로 (기본: app/backend/quiz_seed.sql)
  --replace           기존 퀴즈 문항을 모두 삭제한 뒤 시드 데이터로 교체
  -h, --help          도움말 출력

환경 변수:
  MONGODB_URL         MongoDB 연결 URL (기본: mongodb://localhost:27017)
  MONGODB_DB          데이터베이스 이름 (기본: investment_db)
  MONGODB_COLLECTION  컬렉션 이름 (기본: quiz_questions)
EOF
}

REPLACE=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --sql-file)
      if [[ $# -lt 2 ]]; then
        echo "[ERROR] --sql-file 옵션에는 경로가 필요합니다."
        usage; exit 1
      fi
      SQL_FILE="$2"; shift 2 ;;
    --replace)
      REPLACE=true; shift ;;
    -h|--help)
      usage; exit 0 ;;
    *)
      echo "[ERROR] 알 수 없는 옵션: $1"
      usage; exit 1 ;;
  esac
done

for cmd in mongosh python3; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[ERROR] $cmd 이(가) 설치되어 있지 않습니다."; exit 1
  fi
done

if [[ ! -f "$SQL_FILE" ]]; then
  echo "[ERROR] SQL 파일이 없습니다: $SQL_FILE"; exit 1
fi

TMP_JSON="$(mktemp)"
trap 'rm -f "$TMP_JSON"' EXIT

python3 - "$SQL_FILE" "$TMP_JSON" <<'PY'
import json, sqlite3, sys
from pathlib import Path

sql_file, out_file = Path(sys.argv[1]), Path(sys.argv[2])
conn = sqlite3.connect(":memory:")
try:
    conn.executescript(sql_file.read_text(encoding="utf-8"))
    rows = conn.execute(
        "SELECT day, question_no, source_doc, topic, question,"
        " choice_1, choice_2, choice_3, choice_4, answer, explanation"
        " FROM quiz_questions ORDER BY day, question_no"
    ).fetchall()
finally:
    conn.close()

docs = [
    {
        "day": int(r[0]), "question_no": int(r[1]),
        "source_doc": r[2], "topic": r[3], "question": r[4],
        "choices": [r[5], r[6], r[7], r[8]],
        "answer": int(r[9]), "explanation": r[10],
    }
    for r in rows
]
out_file.write_text(json.dumps(docs, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"prepared_docs={len(docs)}")
PY

mongosh "$MONGODB_URL/$MONGODB_DB" --quiet \
  --eval "db.createCollection('$MONGODB_COLLECTION');" >/dev/null 2>&1 || true
mongosh "$MONGODB_URL/$MONGODB_DB" --quiet \
  --eval "db.getCollection('$MONGODB_COLLECTION').createIndex({day:1,question_no:1},{unique:true});" >/dev/null

if [[ "$REPLACE" == true ]]; then
  mongosh "$MONGODB_URL/$MONGODB_DB" --quiet --eval "
const fs = require('fs');
const docs = JSON.parse(fs.readFileSync('$TMP_JSON', 'utf8'));
const coll = db.getCollection('$MONGODB_COLLECTION');
const removed = coll.deleteMany({}).deletedCount;
if (docs.length) coll.insertMany(docs);
printjson({ replaced: true, removed, total: coll.countDocuments({}) });
"
else
  mongosh "$MONGODB_URL/$MONGODB_DB" --quiet --eval "
const fs = require('fs');
const docs = JSON.parse(fs.readFileSync('$TMP_JSON', 'utf8'));
const coll = db.getCollection('$MONGODB_COLLECTION');
let inserted = 0;
for (const doc of docs) {
  const r = coll.updateOne(
    { day: doc.day, question_no: doc.question_no },
    { \$setOnInsert: doc },
    { upsert: true }
  );
  if (r.upsertedCount > 0) inserted++;
}
printjson({ inserted, total: coll.countDocuments({}) });
"
fi

echo "[OK] MongoDB 초기화/데이터 적재 완료"
