#!/usr/bin/env python3
"""
4-1-rst 폴더 변경 감지 배치 트리거. 매 실행마다 아래 순서로 처리한다.

  0순위: 파일 확장자를 .json 으로 정규화 (확장자가 달라 분석 대상에서
         누락되는 파일이 없도록, 정합성 검사보다 먼저 수행)
  1순위: JSON 정합성 검사 + 클릭간격/유사도 분석 (analyze_report.py, report.html 1번 섹션)
  2순위: 변경분(추가/삭제/수정) 감지 시에만 위 분석을 재실행

cron 등으로 주기적으로(예: 1분마다) 호출하도록 설계됨:
  * * * * * /usr/bin/python3 /home/ubuntu/investment-analysis/4-1-rst/watch_and_report.py >> /home/ubuntu/investment-analysis/4-1-rst/batch.log 2>&1
"""
import json
import os
import sys
from datetime import datetime
from glob import glob

DIR = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(DIR, ".report_state.json")
EXCLUDE_NAMES = {"report.html", "report_prev.html"}

# 분석 대상이 아닌 스크립트/산출물 확장자 (extension normalization에서 건드리지 않음)
SKIP_EXT = {".py", ".html", ".log", ".json"}

sys.path.insert(0, DIR)
import analyze_report  # noqa: E402


def normalize_extensions():
    """0순위: .json이 아닌 데이터 파일을 .json으로 확장자만 변경.

    이름 충돌(이미 같은 이름의 .json이 존재)이면 덮어쓰지 않고 건너뛴다.
    """
    renamed = []
    for fp in glob(os.path.join(DIR, "*")):
        if os.path.isdir(fp):
            continue
        name = os.path.basename(fp)
        if name.startswith("."):
            continue
        base, ext = os.path.splitext(name)
        if ext.lower() in SKIP_EXT:
            continue
        target = os.path.join(DIR, base + ".json")
        if os.path.exists(target):
            print(f"[extension] 건너뜀(이미 존재): {name} -> {base}.json")
            continue
        os.rename(fp, target)
        renamed.append((name, base + ".json"))
    return renamed


def current_state():
    state = {}
    for fp in glob(os.path.join(DIR, "*.json")):
        name = os.path.basename(fp)
        if name in EXCLUDE_NAMES or name == os.path.basename(STATE_PATH):
            continue
        st = os.stat(fp)
        state[name] = {"size": st.st_size, "mtime": st.st_mtime}
    return state


def load_prev_state():
    if not os.path.exists(STATE_PATH):
        return {}
    try:
        with open(STATE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def diff_state(prev, cur):
    added = sorted(set(cur) - set(prev))
    removed = sorted(set(prev) - set(cur))
    modified = sorted(
        n for n in (set(cur) & set(prev))
        if cur[n] != prev[n]
    )
    return added, removed, modified


def main():
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 0순위: 확장자 정규화 (정합성 검사보다 먼저)
    renamed = normalize_extensions()
    if renamed:
        print(f"[{ts}] 확장자 정규화: {renamed}")

    prev = load_prev_state()
    cur = current_state()
    added, removed, modified = diff_state(prev, cur)

    if not (added or removed or modified):
        return  # 변경 없음 -> 조용히 종료 (로그 스팸 방지)

    print(f"[{ts}] 변경 감지: 추가={added} 삭제={removed} 수정={modified}")

    # 1순위: JSON 정합성 검사 + 클릭간격/유사도 분석
    analyze_report.main()
    save_state(cur)
    print(f"[{ts}] report.html 갱신 완료")


if __name__ == "__main__":
    main()
