#!/usr/bin/env python3
"""
투자분석 실습 로그(JSON) 일괄 분석 스크립트.

이 폴더(4-1-rst)에 있는 학생 제출 JSON 파일을 모두 읽어서
  1) 클릭 타임스탬프를 추출해 평균 클릭 간격을 계산하고 랭킹을 매기고
  2) 답안 필드(슬라이더/조건/서술형)를 비교해 파일 간 유사도를 계산한 뒤
  3) 결과를 report.html 로 저장한다.

브라우저 콘솔에서 그대로 복사해 저장된 파일(따옴표 없는 key, "…" 로 잘린 배열 등)도
최대한 복구해서 분석하며, 복구가 안 되는 부분은 report.html에 경고로 표시한다.

단독 실행:  python3 analyze_report.py
"""
import json
import re
import os
import sys
import html
import math
import itertools
import difflib
from datetime import datetime, timezone
from glob import glob

DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_PATH = os.path.join(DIR, "report.html")
EXCLUDE_NAMES = {"report.html", "report_prev.html"}

# JSON의 lessons 속성을 커리큘럼 구조에 따라 6개 카테고리로 분류 (방사형 차트 축)
CATEGORY_MAP = [
    ("거시경제", ["macro-indicator", "macro-practice"]),
    ("산업분석", ["industry-competitiveness", "industry-practice"]),
    ("재무제표", ["fundamental-financials"]),
    ("밸류에이션", ["fundamental-valuation"]),
    ("기업실습", ["fundamental-practice"]),
    ("기술적분석", ["technical-trend", "technical-pattern", "technical-practice", "technical-indicators"]),
]

TS_PATTERN = re.compile(r'"?at"?\s*:\s*"(\d{4}-\d{2}-\d{2}T[\d:.]+Z)"')
FIELDS_BLOCK_PATTERN = re.compile(
    r'(macro-indicator|macro-practice|industry-competitiveness|industry-practice|'
    r'fundamental-financials|fundamental-valuation|fundamental-practice|'
    r'technical-trend|technical-pattern|technical-indicators|technical-practice|'
    r'json-consistency)\s*:?\s*\n?\s*\{fields:\s*\{([^}]*)\}'
)


def _try_raw_decode(text):
    """앞에 잡텍스트가 붙어 있어도 첫 '{' 부터 유효한 JSON 객체를 최대한 복구."""
    first_brace = text.find("{")
    if first_brace == -1:
        return None
    candidate = text[first_brace:]
    try:
        obj, _ = json.JSONDecoder().raw_decode(candidate)
        return obj
    except Exception:
        return None


def _try_unwrap_localstorage(text):
    """'{edumgt-...-v1 : \\n\\n{...}' 같은 localStorage 키:값 복사 포맷 복구."""
    m = re.search(r"\{[^{}]*?:\s*\n*\s*(\{.*)", text, re.DOTALL)
    if not m:
        return None
    try:
        obj, _ = json.JSONDecoder().raw_decode(m.group(1))
        return obj
    except Exception:
        return None


def _regex_fields_fallback(text):
    """DevTools 콘솔 펼침 텍스트({fields: {strength:0: "3", ...}})에서 필드만 정규식으로 복구."""
    fields = {}
    for m in FIELDS_BLOCK_PATTERN.finditer(text):
        lesson_name, fields_str = m.group(1), m.group(2)
        for kv in re.finditer(r'([\w:]+):\s*"?([^",}]+)"?', fields_str):
            fields[f"{lesson_name}::{kv.group(1)}"] = kv.group(2)
    return fields


def parse_file(fp):
    name = os.path.basename(fp)
    raw = open(fp, encoding="utf-8", errors="replace").read()

    all_ts = sorted(set(TS_PATTERN.findall(raw)))
    times_dt = [datetime.fromisoformat(t.replace("Z", "+00:00")) for t in all_ts]
    diffs = [(times_dt[i + 1] - times_dt[i]).total_seconds() for i in range(len(times_dt) - 1)]
    avg_interval = sum(diffs) / len(diffs) if diffs else None
    total_span = (times_dt[-1] - times_dt[0]).total_seconds() if len(times_dt) > 1 else 0

    # 엄격 검증: 파일 전체가 군더더기 없이 그 자체로 유효한 JSON 이어야 통과.
    # (브라우저 콘솔 복사, 이름 접두어, 뒤에 남은 텍스트 등은 전부 실패로 간주)
    strict_valid = False
    strict_error = None
    REQUIRED_KEYS = {"lessons", "clicks", "activeLesson"}
    try:
        strict_obj = json.loads(raw)
        if isinstance(strict_obj, dict) and REQUIRED_KEYS.issubset(strict_obj.keys()):
            strict_valid = True
        else:
            strict_error = "필수 키 누락(lessons/clicks/activeLesson)"
    except json.JSONDecodeError as e:
        strict_error = f"{e.msg} (line {e.lineno}, col {e.colno})"

    obj = strict_obj if strict_valid else (_try_raw_decode(raw) or _try_unwrap_localstorage(raw))
    parsed_ok = obj is not None

    fields = {}
    if parsed_ok:
        for lesson_name, ldata in (obj.get("lessons") or {}).items():
            for k, v in (ldata.get("fields") or {}).items():
                fields[f"{lesson_name}::{k}"] = v
    else:
        fields = _regex_fields_fallback(raw)

    # 절단(truncation) 의심: 콘솔 생략기호(…) 존재, 혹은 파싱 실패+타임스탬프 극소, 혹은
    # 파일 끝이 완전한 JSON 구조로 안 닫혀 있는 경우
    looks_truncated = ("…" in raw) or (not parsed_ok and len(times_dt) < 50)
    if not looks_truncated:
        stripped = raw.rstrip()
        if stripped and stripped[-1] not in "}]" and '"at"' in raw:
            looks_truncated = True

    return {
        "name": name,
        "path": fp,
        "size": os.path.getsize(fp),
        "mtime": os.path.getmtime(fp),
        "parsed_ok": parsed_ok,
        "strict_valid": strict_valid,
        "strict_error": strict_error,
        "num_timestamps": len(times_dt),
        "avg_interval": avg_interval,
        "total_span_sec": total_span,
        "looks_truncated": looks_truncated,
        "fields": fields,
        "first_ts": all_ts[0] if all_ts else None,
        "last_ts": all_ts[-1] if all_ts else None,
    }


# 드롭다운/단일선택형 필드(예: sector)는 값 종류가 몇 개 안 되어 우연히 겹쳐도
# 표절과 무관하므로 서술형 비교에서 제외한다.
CATEGORICAL_KEY_SUFFIXES = ("::sector",)


def _is_freetext(key, v):
    if not isinstance(v, str):
        return False
    if v in ("true", "false"):
        return False
    if re.fullmatch(r"-?\d+(\.\d+)?", v):
        return False
    if key.endswith(CATEGORICAL_KEY_SUFFIXES):
        return False
    # 서술형 문장으로 볼 수 있는 최소 길이(짧은 단답은 우연 일치가 흔해 제외)
    return len(v) >= 15


def compute_similarity(results):
    names = list(results.keys())
    numeric_pairs = []
    text_pairs = []

    for a, b in itertools.combinations(names, 2):
        fa, fb = results[a]["fields"], results[b]["fields"]
        if not fa or not fb:
            continue
        common = set(fa.keys()) & set(fb.keys())
        union = set(fa.keys()) | set(fb.keys())
        if not union:
            continue
        same = sum(1 for k in common if str(fa[k]) == str(fb[k]))
        jaccard = same / len(union)
        match_rate = same / len(common) if common else 0
        numeric_pairs.append({
            "a": a, "b": b, "jaccard": jaccard, "match_rate": match_rate,
            "same": same, "common": len(common), "union": len(union),
        })

        # 서술형 답변 근접 일치 검사 (동일 key 를 가진 자유서술 필드끼리 비교)
        text_keys_a = {k: v for k, v in fa.items() if _is_freetext(k, v)}
        text_keys_b = {k: v for k, v in fb.items() if _is_freetext(k, v)}
        shared_text_keys = set(text_keys_a) & set(text_keys_b)
        for k in shared_text_keys:
            va, vb = text_keys_a[k], text_keys_b[k]
            ratio = difflib.SequenceMatcher(None, va, vb).ratio()
            if ratio >= 0.6:
                text_pairs.append({
                    "a": a, "b": b, "field": k, "ratio": ratio,
                    "va": va, "vb": vb,
                })

    numeric_pairs.sort(key=lambda x: -x["jaccard"])
    text_pairs.sort(key=lambda x: -x["ratio"])
    return numeric_pairs, text_pairs


def compute_category_scores(results):
    """학생별 6개 카테고리 참여도(해당 카테고리 레슨에서 답한 필드 수)를 계산하고
    카테고리별 최댓값 대비 백분율로 정규화한다. 반 평균도 함께 반환."""
    names = list(results.keys())
    raw = {n: {} for n in names}
    for n, r in results.items():
        for cat, lessons in CATEGORY_MAP:
            count = sum(
                1 for k in r["fields"]
                if k.split("::", 1)[0] in lessons
            )
            raw[n][cat] = count

    cat_max = {
        cat: max((raw[n][cat] for n in names), default=0) or 1
        for cat, _ in CATEGORY_MAP
    }

    pct = {
        n: {cat: round(raw[n][cat] / cat_max[cat] * 100) for cat, _ in CATEGORY_MAP}
        for n in names
    }
    avg_pct = {
        cat: round(sum(pct[n][cat] for n in names) / len(names)) if names else 0
        for cat, _ in CATEGORY_MAP
    }
    return raw, pct, avg_pct


def radar_svg(values, avg, categories, size=280):
    """values, avg: {카테고리: 0~100} / categories: 순서가 있는 카테고리명 리스트."""
    n = len(categories)
    cx = cy = size / 2
    R = size * 0.36
    label_r = size * 0.46

    def point(i, val):
        angle = -90 + i * (360 / n)
        rad = math.radians(angle)
        r = R * max(0, min(100, val)) / 100
        return cx + r * math.cos(rad), cy + r * math.sin(rad)

    def axis_point(i, r):
        angle = -90 + i * (360 / n)
        rad = math.radians(angle)
        return cx + r * math.cos(rad), cy + r * math.sin(rad)

    grid = []
    for ring in (20, 40, 60, 80, 100):
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (axis_point(i, R * ring / 100) for i in range(n)))
        grid.append(f'<polygon points="{pts}" fill="none" stroke="#e0e0e0" stroke-width="1"/>')

    axes = []
    labels = []
    for i, cat in enumerate(categories):
        x2, y2 = axis_point(i, R)
        axes.append(f'<line x1="{cx}" y1="{cy}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#ccc" stroke-width="1"/>')
        lx, ly = axis_point(i, label_r)
        anchor = "middle"
        if lx < cx - 5:
            anchor = "end"
        elif lx > cx + 5:
            anchor = "start"
        labels.append(f'<text x="{lx:.1f}" y="{ly:.1f}" font-size="11" text-anchor="{anchor}" '
                       f'dominant-baseline="middle" fill="#444">{html.escape(cat)}</text>')

    avg_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, avg[categories[i]]) for i in range(n)))
    val_pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in (point(i, values[categories[i]]) for i in range(n)))

    return f"""<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
      {''.join(grid)}
      {''.join(axes)}
      <polygon points="{avg_pts}" fill="none" stroke="#999" stroke-width="1.5" stroke-dasharray="4,3"/>
      <polygon points="{val_pts}" fill="#2e7d32" fill-opacity="0.28" stroke="#2e7d32" stroke-width="2"/>
      {''.join(labels)}
    </svg>"""


def fmt_sec(s):
    if s is None:
        return "-"
    return f"{s:.2f}초"


def fmt_min(s):
    return f"{s / 60:.1f}분"


def _has_content(fields, prefix):
    return any(
        k.split("::", 1)[0] == prefix and str(v).strip()
        for k, v in fields.items()
    )


def render_html(results, numeric_pairs, text_pairs, generated_at):
    # 기업선정(fundamental-practice) + 기술적 분석 실습(technical-practice) 둘 다
    # 실제로 작성한 경우 "기업선정함" 뱃지 표기
    for n, r in results.items():
        r["company_selected"] = (
            _has_content(r["fields"], "fundamental-practice")
            and _has_content(r["fields"], "technical-practice")
        )

    def company_badge(r):
        return ' <span class="badge-company">🏢 기업선정함</span>' if r["company_selected"] else ""

    ranked = sorted(
        [(n, r) for n, r in results.items() if r["avg_interval"] is not None and r["num_timestamps"] >= 2],
        key=lambda x: x[1]["avg_interval"],
    )
    # 타임스탬프 2개 미만이면 평균 간격 계산이 불가해 랭킹에는 못 넣지만,
    # 엄격 JSON 검증을 통과한(정상) 파일은 "데이터 부족" 경고 대상에서 제외한다.
    # (예: 김인조1.json 처럼 클릭 1건뿐이라도 파일 자체는 정상 제출인 경우)
    excluded = [n for n, r in results.items() if r["num_timestamps"] < 2 and not r["strict_valid"]]

    resubmit_needed = sorted(n for n, r in results.items() if not r["strict_valid"])

    def strict_cell(r):
        if r["strict_valid"]:
            return '<span class="ok">✅ 정상</span>'
        err = html.escape(r["strict_error"] or "형식 오류")
        return f'<span class="resubmit">❌ 다시제출 ({err})</span>'

    rows_status = "\n".join(
        f"<tr class=\"{'row-bad' if not r['strict_valid'] else ''}\"><td>{html.escape(n)}{company_badge(r)}</td>"
        f"<td>{strict_cell(r)}</td>"
        f"<td>{'복구됨(참고용)' if r['parsed_ok'] and not r['strict_valid'] else ('-' if not r['parsed_ok'] else '')}</td>"
        f"<td>{r['num_timestamps']}</td>"
        f"<td>{'<span class=\"warn\">⚠ 의심</span>' if r['looks_truncated'] else '-'}</td>"
        f"<td>{len(r['fields'])}</td></tr>"
        for n, r in sorted(results.items())
    )

    rows_rank = "\n".join(
        f"<tr><td>{i}</td><td>{html.escape(n)}</td>"
        f"<td>{fmt_sec(r['avg_interval'])}</td>"
        f"<td>{r['num_timestamps']}</td>"
        f"<td>{fmt_min(r['total_span_sec'])}</td>"
        f"<td>{'<span class=\"warn\">⚠ 절단 의심 데이터</span>' if r['looks_truncated'] else ''}</td></tr>"
        for i, (n, r) in enumerate(ranked, 1)
    )

    rows_excluded = "".join(f"<li>{html.escape(n)}</li>" for n in sorted(excluded))

    rows_numeric = "\n".join(
        f"<tr><td>{html.escape(p['a'])}</td><td>{html.escape(p['b'])}</td>"
        f"<td>{p['jaccard']:.2f}</td><td>{p['match_rate']:.2f}</td>"
        f"<td>{p['same']}/{p['common']} (전체 {p['union']})</td></tr>"
        for p in numeric_pairs[:20]
    )

    def order_info(a, b):
        """last_ts(마지막 클릭=제출 완료 시각) 기준 어느 파일이 먼저 작성됐는지 판단."""
        la, lb = results[a].get("last_ts"), results[b].get("last_ts")
        if not la or not lb or la == lb:
            return None
        return (a, la, b, lb) if la < lb else (b, lb, a, la)

    if text_pairs:
        row_htmls = []
        for p in text_pairs[:30]:
            order = order_info(p["a"], p["b"])
            if order:
                earlier, earlier_ts, later, later_ts = order
                if p["ratio"] >= 0.85:
                    order_cell = (
                        f'<span class="copy-strong">⛔ {html.escape(later)}가 {html.escape(earlier)} '
                        f'제출({earlier_ts[11:19]}) 이후({later_ts[11:19]})에 거의 동일 문구 작성 '
                        f'→ 표절 의심 강함</span>'
                    )
                else:
                    order_cell = (
                        f'<span class="copy-weak">△ {html.escape(later)}가 {html.escape(earlier)}보다 '
                        f'나중에 작성({earlier_ts[11:19]} → {later_ts[11:19]})</span>'
                    )
            else:
                order_cell = '<span class="meta">작성 시각 비교 불가</span>'

            row_htmls.append(
                f"<tr><td>{html.escape(p['a'])}</td><td>{html.escape(p['b'])}</td>"
                f"<td>{html.escape(p['field'])}</td><td>{p['ratio']:.2f}</td>"
                f"<td>{html.escape(p['va'][:80])}</td><td>{html.escape(p['vb'][:80])}</td>"
                f"<td>{order_cell}</td></tr>"
            )
        rows_text = "\n".join(row_htmls)
        strong_count = sum(1 for p in text_pairs if p["ratio"] >= 0.85)
        banner = (
            f'<p class="alert">⛔ 유사도 0.85 이상 + 작성 시각상 뒤에 제출된 표절 의심 사례 {strong_count}건 포함. '
            f'"표절 의심 강함" 항목을 우선 검토하세요.</p>'
            if strong_count
            else '<p class="alert">서술형 답변에서 유사도 0.6 이상인 쌍이 발견되었습니다. 표절/복사 가능성을 검토하세요.</p>'
        )
        text_section = f"""
        {banner}
        <table>
          <tr><th>파일 A</th><th>파일 B</th><th>필드</th><th>유사도</th><th>답변 A</th><th>답변 B</th><th>작성 선후관계</th></tr>
          {rows_text}
        </table>
        <p class="meta">※ 작성 선후관계는 각 파일의 마지막 클릭 타임스탬프(제출 완료 시각)를 기준으로 추정한 것으로, 참고용 정황 증거입니다.</p>
        """
    else:
        text_section = '<p class="ok">서술형 답변 기준으로 유의미한 유사(표절 의심) 사례는 발견되지 않았습니다.</p>'

    n_files = len(results)

    # 5. 개인별 6대 역량 방사형 차트 (모달 팝업)
    categories = [cat for cat, _ in CATEGORY_MAP]
    _, pct_by_name, avg_pct = compute_category_scores(results)

    radar_buttons = []
    radar_modals = []
    for idx, (n, r) in enumerate(sorted(results.items())):
        modal_id = f"radar-modal-{idx}"
        radar_buttons.append(
            f'<button class="radar-btn" onclick="document.getElementById(\'{modal_id}\').style.display=\'flex\'">'
            f'📊 {html.escape(n)}{company_badge(r)}</button>'
        )
        svg = radar_svg(pct_by_name[n], avg_pct, categories)
        radar_modals.append(f"""
        <div id="{modal_id}" class="modal-overlay" onclick="if(event.target===this)this.style.display='none'">
          <div class="modal-box">
            <h3>{html.escape(n)}{company_badge(r)}</h3>
            {svg}
            <p class="meta">실선(초록)=본인, 점선(회색)=반 평균. 각 축은 카테고리 내 최다 참여 학생 대비 %.</p>
            <button class="close-btn" onclick="document.getElementById('{modal_id}').style.display='none'">닫기</button>
          </div>
        </div>""")

    radar_section = f"""
    <div class="radar-grid">{''.join(radar_buttons)}</div>
    {''.join(radar_modals)}
    """

    return f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<title>4-1-rst 실습 로그 분석 리포트</title>
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
  .alert {{ color: #c0392b; font-weight: bold; }}
  .ok {{ color: #2e7d32; }}
  .meta {{ color: #666; font-size: .85rem; }}
  ul {{ font-size: .88rem; }}
  .resubmit {{ color: #ffffff; background:#c0392b; font-weight: bold; padding: 2px 8px; border-radius: 4px; }}
  .resubmit-banner {{ color: #ffffff; background:#c0392b; font-weight: bold; padding: 10px 14px; border-radius: 6px; }}
  tr.row-bad td {{ background: #fdecea; }}
  .copy-strong {{ color: #ffffff; background:#c0392b; font-weight: bold; padding: 1px 6px; border-radius: 4px; }}
  .copy-weak {{ color: #b8860b; font-weight: bold; }}
  .badge-company {{ display:inline-block; color:#fff; background:#2e7d32; font-size:.75rem; font-weight:bold; padding:1px 7px; border-radius: 10px; }}
  .radar-grid {{ display:flex; flex-wrap:wrap; gap:.6rem; margin: .8rem 0 1.5rem; }}
  .radar-btn {{ cursor:pointer; border:1px solid #ccc; background:#fff; border-radius:6px; padding:8px 14px; font-size:.88rem; }}
  .radar-btn:hover {{ background:#f0f7f0; border-color:#2e7d32; }}
  .modal-overlay {{ display:none; position:fixed; inset:0; background:rgba(0,0,0,.55); align-items:center; justify-content:center; z-index:1000; }}
  .modal-box {{ background:#fff; padding:1.4rem 1.6rem; border-radius:10px; text-align:center; max-width:92vw; }}
  .modal-box h3 {{ margin:.2rem 0 .6rem; }}
  .close-btn {{ margin-top:.6rem; padding:6px 18px; border:none; background:#2e7d32; color:#fff; border-radius:5px; cursor:pointer; font-size:.85rem; }}
  .close-btn:hover {{ background:#245c26; }}
</style></head>
<body>
<h1>4-1-rst 실습 로그 분석 리포트</h1>
<p class="meta">생성 시각: {generated_at} &nbsp;|&nbsp; 대상 파일: {n_files}개</p>

<h2>1. JSON 정합성 검사 (엄격 검증)</h2>
{f'<p class="resubmit-banner">⛔ 형식 오류로 다시제출이 필요한 파일: {", ".join(html.escape(n) for n in resubmit_needed)}</p>' if resubmit_needed else '<p class="ok">모든 파일이 엄격 JSON 검증을 통과했습니다.</p>'}
<table>
<tr><th>파일</th><th>엄격 JSON 검증</th><th>비고</th><th>타임스탬프 수</th><th>절단 의심</th><th>추출된 답안 필드 수</th></tr>
{rows_status}
</table>

<h2>2. 평균 클릭 간격 랭킹 (짧은 순)</h2>
<table>
<tr><th>순위</th><th>파일</th><th>평균 간격</th><th>클릭 수</th><th>총 소요시간</th><th>비고</th></tr>
{rows_rank}
</table>
{f'<p class="meta">랭킹 제외(타임스탬프 부족): {rows_excluded}</p>' if excluded else ''}

<h2>3. 답안 유사도 - 숫자형 필드 (참고용, 5점 척도라 우연 일치 가능성 높음)</h2>
<table>
<tr><th>파일 A</th><th>파일 B</th><th>Jaccard</th><th>공통필드 일치율</th><th>일치/공통(전체)</th></tr>
{rows_numeric}
</table>

<h2>4. 답안 유사도 - 서술형 필드 (표절 의심 판단 기준)</h2>
{text_section}

<h2>5. 개인별 6대 역량 방사형 차트</h2>
<p class="meta">카테고리: {' / '.join(categories)} — 이름을 클릭하면 모달로 방사형 차트가 열립니다.</p>
{radar_section}

</body></html>"""


def main():
    files = sorted(
        fp for fp in glob(os.path.join(DIR, "*.json"))
        if os.path.basename(fp) not in EXCLUDE_NAMES
    )
    results = {}
    for fp in files:
        r = parse_file(fp)
        results[r["name"]] = r

    numeric_pairs, text_pairs = compute_similarity(results)
    generated_at = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    html_out = render_html(results, numeric_pairs, text_pairs, generated_at)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(html_out)

    print(f"[analyze_report] {len(results)}개 파일 분석 완료 -> {REPORT_PATH}")
    return results


if __name__ == "__main__":
    main()
