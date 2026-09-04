#!/usr/bin/env python3
"""6-2 ZIP 제출물만 읽어 최신 제출 기준 report.html을 갱신한다."""
import importlib.util
import json
import re
import shutil
import tempfile
from datetime import datetime, timezone
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
    """일반 ISO 문자열과 Mongo Extended JSON의 $date를 UTC 시각으로 비교한다."""
    if isinstance(value, dict):
        value = value.get("$date", "")
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except ValueError:
        return str(value)


def inferred_submitter(archive_name):
    """파일명에서 회차/수정 표기를 제외한 제출자명을 복구한다."""
    stem = Path(archive_name).stem
    return re.sub(r"(?:[. ]?2)?(?:[-_ ]?수정)?$", "", stem)


def main():
    latest = {}
    skipped = []
    incomplete = {}
    # Zone.Identifier 같은 메타데이터 파일은 ZIP이 아니므로 정확한 확장자만 읽는다.
    for archive in sorted(DIR.glob("*.zip")):
        try:
            record = submission_from_archive(archive)
        except Exception as exc:
            skipped.append(f"{archive.name} ({exc})")
            continue
        if not record:
            # 답안이 아닌 활동 로그만 제출된 경우에도 제출자 행은 리포트에 남긴다.
            incomplete[inferred_submitter(archive.name)] = archive.name
            continue
        # ISO-8601 문자열은 시간순 정렬 가능. 동시간이면 중복 표기 없는 파일을 우선한다.
        prior = latest.get(record["name"])
        rank = (
            timestamp_value(record["submitted_at"]),
            "수정" in archive.name,
            "(" not in archive.name,
            archive.name,
        )
        if prior is None or rank > prior[0]:
            latest[record["name"]] = (rank, archive.name, record)

    stage = Path(tempfile.mkdtemp(prefix="6-2-report-", dir="/tmp"))
    try:
        for _, archive_name, record in latest.values():
            safe_name = re.sub(r"[^0-9A-Za-z가-힣._-]+", "_", archive_name)
            (stage / f"{safe_name}.json").write_text(
                json.dumps(record, ensure_ascii=False), encoding="utf-8"
            )
        for name, archive_name in incomplete.items():
            # analyze_report.py가 채점 불가 제출로 렌더링하는 내부 표식.
            record = {
                "name": name,
                "region": "-",
                "answers": [],
                "submitted_at": "",
                "_report_status": "답안 30문항이 없는 활동 로그 제출",
                "source_archive": archive_name,
            }
            (stage / f"{re.sub(r'[^0-9A-Za-z가-힣._-]+', '_', archive_name)}.json").write_text(
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
    print(f"[refresh] 최신 제출 {len(latest)}명 + 채점 불가 {len(incomplete)}명 반영 완료")


if __name__ == "__main__":
    main()
