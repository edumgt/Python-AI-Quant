#!/usr/bin/env python3
"""
4-2-rst 단어장 30문제 시험 채점 스크립트.

이 폴더의 응시자 제출 JSON을 모두 읽어 report.html로 정리한다. 리포트는 3개
파트로만 구성한다.
  1) 성적 레포트   - 응시자별 점수/오답 요약
  2) 문항 컬렉션   - 30문항과 정답
  3) 예외 컬렉션   - 단어장 제출 스키마(name/region/answers/submitted_at)와
                    겹치지 않는 파일(다른 컬렉션을 잘못 export한 경우 등).
                    extract_archives.py가 남긴 .archive_provenance.json으로
                    원본 압축파일/제출자를 함께 표시한다.

단독 실행: python3 analyze_report.py
"""
import json
import re
import os
import html
from datetime import datetime, timezone
from glob import glob

DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.join(DIR, "report.html")
EXCLUDE_NAMES = {"report.html", "report_prev.html"}

# 정답 소스오브트루스: app/backend/routers/vocabulary_exam.py의 ANSWER_KEY.
# 이 스크립트는 백엔드 의존성 없이 단독 실행돼야 하므로 값만 복제해 둔다.
VOCAB_EXAM_MD_PATH = os.path.join(os.path.dirname(DIR), "docs", "voca-exam.md")
VOCAB_ANSWER_KEY = [1, 0, 0, 2, 1, 1, 1, 0, 0, 0, 1, 1, 0, 1, 1, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 1, 0, 1, 1, 2]
VOCAB_QUESTION_PATTERN = re.compile(r"^(\d+)\. (.+?)\n((?: {3,4}\d\. .+\n){4})", re.MULTILINE)
VOCAB_REQUIRED_KEYS = {"name", "region", "answers", "submitted_at"}
OTHER_COLLECTION_ITEM_KEYS = {"question", "choices", "answer"}

# extract_archives.py가 해제 시점에 남기는 "해제된 파일명 -> 원본 압축파일/제출자
# 추정치" 매핑. 예외 컬렉션 파일은 자체 데이터에 이름이 없을 수 있어 이 매핑으로
# 작업자명을 표시한다.
PROVENANCE_PATH = os.path.join(DIR, ".archive_provenance.json")


def load_vocab_questions():
    """docs/voca-exam.md 를 파싱해 30문항(번호/질문/보기)을 반환. 실패 시 None."""
    if not os.path.exists(VOCAB_EXAM_MD_PATH):
        return None
    text = open(VOCAB_EXAM_MD_PATH, encoding="utf-8").read()
    questions = []
    for number, question, block in VOCAB_QUESTION_PATTERN.findall(text):
        choices = re.findall(r"^ {3,4}\d\. (.+)$", block, re.MULTILINE)
        questions.append({"id": int(number), "question": question, "choices": choices})
    if len(questions) != len(VOCAB_ANSWER_KEY) or any(len(q["choices"]) != 4 for q in questions):
        return None
    return questions


def _as_single_record(parsed):
    if isinstance(parsed, list) and len(parsed) == 1 and isinstance(parsed[0], dict):
        return parsed[0]
    if isinstance(parsed, dict):
        return parsed
    return None


def classify_vocab_related(fp):
    """단어장 시험 제출 스키마(name/region/answers/submitted_at)인지, 그와 겹치지
    않는 다른 컬렉션(문항은행 등) 스키마인지 판별한다.
    ("vocab", record) / ("other", [item, ...]) / None(어느 쪽도 아님) 반환."""
    try:
        with open(fp, encoding="utf-8") as f:
            parsed = json.load(f)
    except Exception:
        return None

    record = _as_single_record(parsed)
    if (
        record
        and VOCAB_REQUIRED_KEYS <= record.keys()
        and isinstance(record.get("answers"), list)
        and len(record["answers"]) == len(VOCAB_ANSWER_KEY)
    ):
        return ("vocab", record)

    items = parsed if isinstance(parsed, list) else ([record] if record else None)
    if items and all(isinstance(x, dict) and OTHER_COLLECTION_ITEM_KEYS <= x.keys() for x in items):
        return ("other", items)

    return None


def load_provenance():
    if not os.path.exists(PROVENANCE_PATH):
        return {}
    try:
        with open(PROVENANCE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def render_grading_section(vocab_records, questions):
    """1. 성적 레포트: 응시자별 점수와 오답 상세(선택/정답)."""
    if not vocab_records:
        return '<p class="meta">단어장 시험 제출 형식(name/region/answers/submitted_at)의 파일이 없습니다.</p>'
    if not questions:
        return '<p class="warn">⚠ docs/voca-exam.md 문제지를 찾을 수 없거나 형식이 달라 채점할 수 없습니다.</p>'

    rows = []
    for fn, rec in sorted(vocab_records.items(), key=lambda kv: kv[1].get("name") or kv[0]):
        answers = rec.get("answers") or []
        wrong = [
            (q["id"], answers[i], VOCAB_ANSWER_KEY[i])
            for i, q in enumerate(questions)
            if i < len(answers) and answers[i] != VOCAB_ANSWER_KEY[i]
        ]
        score = len(questions) - len(wrong)
        name = html.escape(str(rec.get("name", fn)))
        region = html.escape(str(rec.get("region", "-")))
        detail = (
            "<br>".join(f"{qid}번: 선택 {sel + 1}번 (정답 {cor + 1}번)" for qid, sel, cor in wrong)
            if wrong else "-"
        )
        rows.append(
            f"<tr><td>{name}</td><td>{region}</td>"
            f"<td>{score}/{len(questions)}</td><td>{detail}</td></tr>"
        )

    return f"""
    <table>
    <tr><th>이름</th><th>지역</th><th>점수</th><th>오답 상세</th></tr>
    {''.join(rows)}
    </table>
    """


def render_question_collection_section(questions):
    """2. 문항 컬렉션: 30문항과 정답(굵게 표시)."""
    if not questions:
        return '<p class="warn">⚠ docs/voca-exam.md 문제지를 찾을 수 없어 문항 목록을 표시할 수 없습니다.</p>'

    rows = []
    for idx, q in enumerate(questions):
        correct = VOCAB_ANSWER_KEY[idx]
        choices_html = "<br>".join(
            (f"<b>{i + 1}. {html.escape(c)} ✅</b>" if i == correct else f"{i + 1}. {html.escape(c)}")
            for i, c in enumerate(q["choices"])
        )
        rows.append(
            f"<tr><td>{q['id']}</td><td>{html.escape(q['question'])}</td><td>{choices_html}</td></tr>"
        )

    return f"""
    <table>
    <tr><th>번호</th><th>문제</th><th>보기 (✅ 정답)</th></tr>
    {''.join(rows)}
    </table>
    """


def render_exception_collection_section(other_items, provenance):
    """3. 예외 컬렉션: 단어장 제출 스키마와 겹치지 않는 파일(다른 컬렉션 오export 등).
    provenance에 기록이 있으면 원본 압축파일과 제출자 추정치를 함께 표시한다."""
    if not other_items:
        return '<p class="ok">단어장 제출 스키마와 겹치지 않는 예외 데이터는 발견되지 않았습니다.</p>'

    blocks = []
    for fn, items in other_items.items():
        info = provenance.get(fn)
        if info:
            who = (
                f"작업자 추정: <b>{html.escape(info['submitter'])}</b> "
                f"(원본 압축파일: {html.escape(info['archive'])} → {html.escape(fn)})"
            )
        else:
            who = f"파일: {html.escape(fn)} (작업자 정보 없음)"

        rows = []
        for it in items:
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(it.get('day', it.get('question_no', '-'))))}</td>"
                f"<td>{html.escape(str(it.get('topic', '-')))}</td>"
                f"<td>{html.escape(str(it.get('question', '-')))}</td>"
                f"<td>{html.escape(' / '.join(str(c) for c in it.get('choices', [])))}</td>"
                f"<td>{html.escape(str(it.get('answer', '-')))}</td>"
                "</tr>"
            )
        blocks.append(f"""
        <p class="warn">⚠ {who} — 단어장 제출 스키마(name/region/answers/submitted_at)가 아니라
        다른 컬렉션(문항은행 등)의 데이터로 보입니다. 응시자 개인 제출이 아니므로 위 성적 레포트에는 포함하지 않았습니다.</p>
        <table>
        <tr><th>Day/번호</th><th>주제</th><th>문항</th><th>보기</th><th>정답(0-based)</th></tr>
        {''.join(rows)}
        </table>
        """)
    return "\n".join(blocks)


def render_html(vocab_records, other_items, questions, provenance, generated_at):
    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<title>4-2-rst 단어장 시험 채점 리포트</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", "Malgun Gothic", sans-serif; margin: 2rem; color:#1a1a1a; background:#fafafa; }}
  h1 {{ font-size: 1.4rem; }}
  h2 {{ font-size: 1.1rem; margin-top: 2rem; border-bottom: 2px solid #ddd; padding-bottom: .3rem; }}
  table {{ border-collapse: collapse; width: 100%; margin: .8rem 0 1.5rem; background:#fff; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 10px; font-size: .88rem; text-align: left; }}
  th {{ background: #f0f0f0; }}
  tr:nth-child(even) {{ background: #f9f9f9; }}
  .bad {{ color: #c0392b; font-weight: bold; }}
  .warn {{ color: #b8860b; }}
  .ok {{ color: #2e7d32; }}
  .meta {{ color: #666; font-size: .85rem; }}
</style></head>
<body>
<h1>4-2-rst 단어장 시험 채점 리포트</h1>
<p class="meta">생성 시각: {generated_at} &nbsp;|&nbsp; 응시자 {len(vocab_records)}명 &nbsp;|&nbsp; 예외 파일 {len(other_items)}개</p>

<h2>1. 성적 레포트</h2>
{render_grading_section(vocab_records, questions)}

<h2>2. 문항 컬렉션</h2>
{render_question_collection_section(questions)}

<h2>3. 예외 컬렉션</h2>
{render_exception_collection_section(other_items, provenance)}

</body></html>"""


def main():
    files = sorted(
        fp for fp in glob(os.path.join(DIR, "*.json"))
        if os.path.basename(fp) not in EXCLUDE_NAMES
    )

    vocab_records = {}
    other_items = {}
    unclassified = []
    for fp in files:
        classified = classify_vocab_related(fp)
        if classified is None:
            unclassified.append(os.path.basename(fp))
            continue
        kind, data = classified
        (vocab_records if kind == "vocab" else other_items)[os.path.basename(fp)] = data

    questions = load_vocab_questions()
    provenance = load_provenance()
    generated_at = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    html_out = render_html(vocab_records, other_items, questions, provenance, generated_at)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(html_out)

    msg = f"[analyze_report] 성적 레포트 {len(vocab_records)}명 / 예외 컬렉션 {len(other_items)}개 -> {REPORT_PATH}"
    if unclassified:
        msg += f" (인식 불가로 제외: {', '.join(unclassified)})"
    print(msg)
    return vocab_records


if __name__ == "__main__":
    main()
