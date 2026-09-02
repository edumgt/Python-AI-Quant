"""
repo 의 docs/*.md + readme.md 를 하나의 텍스트로 합쳐서 NotebookLM 노트북에
'붙여넣은 텍스트' 소스로 업로드하는 스크립트.

사용법:
    python3 scripts/upload_docs_to_notebooklm.py

동작 방식:
    1. headed(화면 표시) 크롬을 persistent context 로 띄운다 (로그인 세션은
       scripts/playwright_chrome_profile 폴더에 저장되어 다음 실행부터는
       재로그인이 필요 없다).
    2. notebooklm.google.com 으로 이동한다.
    3. 아직 로그인/노트북 생성이 안 되어 있으면, 사용자가 화면에 뜬 크롬 창에서
       직접 로그인하고 새 노트북을 만들 때까지 기다린다 (URL 에 /notebook/ 이
       포함될 때까지 최대 5분 대기).
    4. 노트북 페이지가 열리면 '소스 추가' -> '복사한 텍스트' 를 선택해 repo
       문서를 합친 텍스트를 붙여넣고 제출한다.
"""

import asyncio
import re
from pathlib import Path

from playwright.async_api import async_playwright

REPO_ROOT = Path(__file__).resolve().parent.parent
USER_DATA_DIR = str(Path(__file__).resolve().parent / "playwright_chrome_profile")

# 합칠 문서 목록: readme.md 먼저, 그 다음 docs/ 안의 나머지 파일들을 이름순으로.
DOC_FILES = [REPO_ROOT / "readme.md"] + sorted((REPO_ROOT / "docs").glob("*.md"))


def build_combined_text() -> str:
    parts = []
    for path in DOC_FILES:
        rel = path.relative_to(REPO_ROOT)
        parts.append(f"# {rel}\n\n{path.read_text(encoding='utf-8')}")
    return "\n\n---\n\n".join(parts)


async def upload_docs_to_notebooklm():
    combined_text = build_combined_text()
    print(f"{len(DOC_FILES)}개 문서, 총 {len(combined_text):,}자를 합쳤습니다.")

    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=False,
            args=["--disable-blink-features=AutomationControlled"],
        )

        page = context.pages[0] if context.pages else await context.new_page()
        print("NotebookLM 으로 이동 중...")
        await page.goto("https://notebooklm.google.com/")

        notebook_url_re = re.compile(r".*/notebook/(?!creating\b)[^/?#]+")
        if not notebook_url_re.match(page.url):
            print(
                "\n로그인이 필요하거나 아직 노트북이 없습니다.\n"
                "브라우저 창에서 Google 로그인 후 새 노트북을 만들어 주세요.\n"
                "(노트북 페이지가 열릴 때까지 최대 5분 대기합니다...)\n"
            )
            await page.wait_for_url(notebook_url_re, timeout=300_000)

        print(f"노트북 페이지 확인: {page.url}")

        # 빈 노트북이면 '소스 추가' 대화상자가 자동으로 열려 있는 경우가 있다.
        pasted_text_tile = page.locator(
            "button:has-text('복사된 텍스트'), button:has-text('Pasted text')"
        ).first
        if not await pasted_text_tile.is_visible():
            print("소스 추가 버튼 클릭...")
            add_source_button = page.locator(
                "button:has-text('소스 추가'), button:has-text('Add source'), "
                "button[aria-label='출처 추가'], button[aria-label='Add source']"
            ).first
            await add_source_button.wait_for(state="visible", timeout=60_000)
            await add_source_button.click()
            await page.wait_for_timeout(1000)
            pasted_text_tile = page.locator(
                "button:has-text('복사된 텍스트'), button:has-text('Pasted text')"
            ).first

        print("텍스트 붙여넣기 옵션 선택...")
        await pasted_text_tile.wait_for(state="visible", timeout=30_000)
        await pasted_text_tile.click()
        await page.wait_for_timeout(1000)

        print("내용 입력 중...")
        textarea = page.locator(
            "textarea[formcontrolname='copiedText'], textarea[aria-label='붙여넣은 텍스트']"
        ).first
        await textarea.wait_for(state="visible", timeout=30_000)
        await textarea.fill(combined_text)
        await page.wait_for_timeout(500)

        print("소스 제출...")
        insert_button = page.locator(
            "button:has-text('삽입'), button:has-text('Insert')"
        ).first
        await insert_button.wait_for(state="visible", timeout=10_000)
        await insert_button.click()

        await page.wait_for_timeout(5000)
        print(f"업로드 완료! 노트북: {page.url}")

        await context.close()


if __name__ == "__main__":
    asyncio.run(upload_docs_to_notebooklm())
