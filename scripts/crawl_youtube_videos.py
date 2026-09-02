#!/usr/bin/env python3
"""주식 투자 학습 주제별 YouTube 검색 결과를 수집하고, 임베드 재생이 가능한 영상만 골라
app/frontend/js/data/youtubeVideos.json 으로 저장한다.

런타임(배포된 앱)에서는 크롤링을 하지 않는다 — 이 스크립트는 개발 중 수동으로
실행해 정적 데이터 파일을 갱신하는 용도다. YouTube가 공식 지원하는 API가 아니라
검색결과 페이지에 내장된 ytInitialData / 시청페이지의 ytInitialPlayerResponse를
파싱하는 방식이라, YouTube 페이지 구조가 바뀌면 깨질 수 있다.

사용법: .venv/bin/python3 scripts/crawl_youtube_videos.py
"""
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "app" / "frontend" / "js" / "data" / "youtubeVideos.json"

VIDEOS_PER_TOPIC = 3
CANDIDATES_TO_CHECK = 12
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# 페이지에는 총 30개(10개 주제 × 3개)만 노출한다. 개별 종목 추천·단기 시황 대신
# 투자 판단에 재사용 가능한 기초, 기업 분석, 가치·기술 분석, ETF·리스크 관리 중심이다.
STOCK_TOPICS = [
    {"category": "주식 투자 기초", "label": "주식 투자 입문", "query": "주식 투자 기초 초보 강의"},
    {"category": "기업 분석", "label": "재무제표로 기업 분석", "query": "주식 투자 재무제표 기업분석"},
    {"category": "기업 분석", "label": "산업·경쟁력 분석", "query": "주식 투자 산업분석 기업 경쟁력"},
    {"category": "가치 평가", "label": "PER·PBR·ROE 가치평가", "query": "주식 투자 PER PBR ROE 가치평가"},
    {"category": "가치 평가", "label": "현금흐름·기업가치", "query": "주식 투자 현금흐름 DCF 기업가치"},
    {"category": "기술적 분석", "label": "이동평균·추세 분석", "query": "주식 차트 이동평균 추세분석 강의"},
    {"category": "기술적 분석", "label": "RSI·MACD 보조지표", "query": "주식 차트 RSI MACD 보조지표 강의"},
    {"category": "ETF·배당", "label": "ETF 투자 기초", "query": "ETF 투자 기초 주식 강의"},
    {"category": "ETF·배당", "label": "배당주·배당 ETF", "query": "주식 배당주 배당 ETF 투자 기초"},
    {"category": "포트폴리오·리스크", "label": "분산투자와 리스크 관리", "query": "주식 투자 분산투자 리스크 관리 강의"},
]
EXCLUDED_TITLE_TERMS = ("비트코인", "코인", "가상자산", "부동산", "아파트")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def search_candidates(query: str) -> list[dict]:
    url = "https://www.youtube.com/results?" + urllib.parse.urlencode({"search_query": query})
    html = fetch(url)
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", html)
    if not m:
        return []
    data = json.loads(m.group(1))

    out: list[dict] = []

    def walk(obj):
        if isinstance(obj, dict):
            if "videoRenderer" in obj:
                out.append(obj["videoRenderer"])
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)

    walk(data)
    return out[:CANDIDATES_TO_CHECK]


def check_embeddable(video_id: str) -> bool:
    try:
        html = fetch(f"https://www.youtube.com/watch?v={video_id}")
        m = re.search(r"var ytInitialPlayerResponse = (\{.*?\});", html)
        if not m:
            return False
        data = json.loads(m.group(1))
        status = data.get("playabilityStatus", {})
        return bool(status.get("playableInEmbed")) and status.get("status") == "OK"
    except Exception as exc:  # noqa: BLE001
        print(f"    embeddable check failed for {video_id}: {exc}")
        return False


def main() -> None:
    topics = STOCK_TOPICS
    print(f"{len(topics)}개 주제에 대해 크롤링을 시작합니다.")

    result: dict[str, list[dict]] = {}
    used_video_ids: set[str] = set()
    for t in topics:
        print(f"- {t['category']} / {t['label']} ({t['query']})")
        candidates = search_candidates(t["query"])
        picked = []
        for c in candidates:
            if len(picked) >= VIDEOS_PER_TOPIC:
                break
            vid = c.get("videoId")
            title = "".join(r.get("text", "") for r in c.get("title", {}).get("runs", []))
            if not vid or vid in used_video_ids or any(term in title for term in EXCLUDED_TITLE_TERMS):
                continue
            time.sleep(0.3)
            if not check_embeddable(vid):
                print(f"    skip (임베드 불가): {vid}")
                continue
            channel = "".join(r.get("text", "") for r in c.get("ownerText", {}).get("runs", []))
            length = c.get("lengthText", {}).get("simpleText", "")
            thumbs = c.get("thumbnail", {}).get("thumbnails", [])
            thumb = thumbs[-1]["url"] if thumbs else f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
            picked.append({
                "videoId": vid,
                "title": title,
                "channel": channel,
                "length": length,
                "thumbnail": thumb,
            })
            used_video_ids.add(vid)
            print(f"    OK: {vid} - {title}")
        result[t["label"]] = {
            "category": t["category"],
            "query": t["query"],
            "videos": picked,
        }
        time.sleep(0.5)

    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(len(v["videos"]) for v in result.values())
    print(f"\n완료: {OUT_JSON.relative_to(ROOT)} ({total}개 영상)")


if __name__ == "__main__":
    main()
