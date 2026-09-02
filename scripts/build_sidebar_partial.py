#!/usr/bin/env python3
"""index.html의 <nav class="sidebar-nav"> 블록을 읽어
app/frontend/pages/partials/sidebar-nav.html 을 재생성한다.

index.html 사이드바(SPA용, data-view 클릭 라우팅)에 메뉴를 추가/수정했다면
이 스크립트를 다시 실행해서 정적 MPA 페이지(pages/*.html)용 partial도 함께 갱신한다.

사용법: python3 scripts/build_sidebar_partial.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX_HTML = ROOT / "app" / "frontend" / "index.html"
PARTIAL_OUT = ROOT / "app" / "frontend" / "pages" / "partials" / "sidebar-nav.html"

# 외부 자료 메뉴는 학습 문서 안의 링크로 통합했다.
EXTERNAL_PAGES: dict[str, str] = {}


def add_href(match: re.Match) -> str:
    tag = match.group(0)
    view = match.group(1)
    if "href=" in tag:
        return tag
    return tag.replace('<a class="nav-item', f'<a href="../index.html?view={view}" class="nav-item', 1)


def main() -> None:
    html = INDEX_HTML.read_text(encoding="utf-8")
    match = re.search(r'<nav class="sidebar-nav">.*?</nav>', html, re.S)
    if not match:
        raise SystemExit("index.html에서 <nav class=\"sidebar-nav\"> 블록을 찾지 못했습니다.")

    nav = match.group(0)
    # SPA 라우트(data-view)가 있는 항목엔 정적 페이지에서도 동작하도록 href 보강
    nav = re.sub(r'<a class="nav-item[^>]*data-view="([^"]+)"[^>]*>', add_href, nav)

    # index.html의 "pages/xxx.html" 링크는 partial 관점(pages/ 내부)에서는 상대경로가 되어야 함
    for file_name, page_id in EXTERNAL_PAGES.items():
        nav = nav.replace(
            f'href="pages/{file_name}"',
            f'href="{file_name}" data-page="{page_id}"',
        )

    PARTIAL_OUT.parent.mkdir(parents=True, exist_ok=True)
    PARTIAL_OUT.write_text(nav + "\n", encoding="utf-8")
    print(f"생성 완료: {PARTIAL_OUT.relative_to(ROOT)} ({len(nav)} bytes)")


if __name__ == "__main__":
    main()
