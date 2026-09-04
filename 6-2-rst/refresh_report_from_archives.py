#!/usr/bin/env python3
"""6-2 ZIP 제출물만 읽어 최신 제출 기준 report.html을 갱신한다."""
import importlib.util
import json
import re
import shutil
import tempfile
from pathlib import Path
from zipfile import ZipFile

DIR = Path(__file__).resolve().parent
REQUIRED = {"name", "region", "answers", "submitted_at"}


def submission_from_archive(path):
    """JSON 또는 Mongo shell pretty() 출력에서 한 건의 시험 제출을 복구한다."""
    with ZipFile(path) as archive:
        for info in archive.infolist():
            if info.is_dir() or info.filename.startswith("__MACOSX/"):
                continue
            raw = archive.read(info).decode("utf-8", "replace")
            try:
                value = json.loads(raw)
                record = value[0] if isinstance(value, list) and len(value) == 1 else value
                if isinstance(record, dict) and REQUIRED <= record.keys() and len(record["answers"]) == 30:
                    return record
            except (json.JSONDecodeError, TypeError):
                pass

            name = re.search(r"name:\s*['\"]([^'\"]+)", raw)
            region = re.search(r"region:\s*['\"]([^'\"]+)", raw)
            answers = re.search(r"answers:\s*\[([^]]+)\]", raw, re.DOTALL)
            submitted_at = re.search(r"ISODate\(['\"]([^'\"]+)", raw)
            if name and region and answers and submitted_at:
                choices = [int(v) for v in re.findall(r"\d+", answers.group(1))]
                if len(choices) == 30:
                    return {"name": name.group(1), "region": region.group(1),
                            "answers": choices, "submitted_at": submitted_at.group(1)}
    return None


def timestamp_value(value):
    """일반 ISO 문자열과 Mongo Extended JSON의 $date를 같은 기준으로 비교한다."""
    if isinstance(value, dict):
        return str(value.get("$date", ""))
    return str(value)


def main():
    latest = {}
    skipped = []
    for archive in sorted(DIR.glob("*.zip*")):
        record = submission_from_archive(archive)
        if not record:
            skipped.append(archive.name)
            continue
        # ISO-8601 문자열은 시간순 정렬 가능. 동시간이면 중복 표기 없는 파일을 우선한다.
        prior = latest.get(record["name"])
        rank = (timestamp_value(record["submitted_at"]), "(" not in archive.name, archive.name)
        if prior is None or rank > prior[0]:
            latest[record["name"]] = (rank, archive.name, record)

    stage = Path(tempfile.mkdtemp(prefix="6-2-report-", dir="/tmp"))
    try:
        for _, archive_name, record in latest.values():
            safe_name = re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", archive_name)
            (stage / f"{safe_name}.json").write_text(
                json.dumps(record, ensure_ascii=False), encoding="utf-8"
            )
        spec = importlib.util.spec_from_file_location("six_two_analysis", DIR / "analyze_report.py")
        analyzer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(analyzer)
        analyzer.DIR = str(stage)
        analyzer.REPORT_PATH = str(DIR / "report.html")
        analyzer.main()
    finally:
        shutil.rmtree(stage, ignore_errors=True)
    if skipped:
        print("[refresh] 인식 불가 ZIP:", ", ".join(skipped))
    print(f"[refresh] 최신 제출 {len(latest)}명 반영 완료")


if __name__ == "__main__":
    main()
