"""공공 금융기관 사이트의 공개 페이지를 깊이 2까지 텍스트로 저장하는 Scrapy 스파이더."""
from __future__ import annotations

import argparse
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import scrapy
from scrapy.crawler import CrawlerProcess
from scrapy.exceptions import CloseSpider

SOURCES = {
    "fsc": "https://www.fsc.go.kr/",
    "fss": "https://www.fss.or.kr/",
    "dart": "https://dart.fss.or.kr/",
    "krx": "https://www.krx.co.kr/",
    "ksd": "https://www.ksd.or.kr/",
    "nts": "https://www.nts.go.kr/",
}


def clean_text(values: list[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(value.strip() for value in values if value.strip())).strip()


class FinancialSiteSpider(scrapy.Spider):
    name = "financial_site_text"
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 1.0,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "CONCURRENT_REQUESTS": 1,
        "DEPTH_LIMIT": 2,
        "DEPTH_PRIORITY": 1,
        "USER_AGENT": "investment-analysis-public-text-crawler/1.0 (educational research)",
        "LOG_LEVEL": "INFO",
        "RETRY_TIMES": 1,
        "DOWNLOAD_TIMEOUT": 30,
    }

    def __init__(self, output: str, max_files: str = "20", source_names: str = "", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.max_files = max(int(max_files), 1)
        self.saved_total = 0
        requested_sources = [name.strip() for name in source_names.split(",") if name.strip()] or list(SOURCES)
        unknown = set(requested_sources) - set(SOURCES)
        if unknown:
            raise ValueError(f"Unknown source names: {', '.join(sorted(unknown))}")
        self.sources = {name: SOURCES[name] for name in requested_sources}
        self.allowed_domains = [urlparse(url).netloc for url in self.sources.values()]
        self.start_urls = list(self.sources.values())
        self.counts = {key: 0 for key in SOURCES}

    def parse(self, response: scrapy.http.Response):
        host = urlparse(response.url).netloc
        source = next((key for key, url in self.sources.items() if urlparse(url).netloc == host), "other")
        self.counts[source] = self.counts.get(source, 0) + 1
        number = self.counts[source]
        text = clean_text(response.css("main *::text, article *::text, body *::text").getall())
        if text and self.saved_total < self.max_files:
            directory = self.output / source / "pages"
            directory.mkdir(parents=True, exist_ok=True)
            target = directory / f"{number:04d}.txt"
            target.write_text(f"URL: {response.url}\n수집시각(UTC): {datetime.now(timezone.utc).isoformat()}\n\n{text}\n", encoding="utf-8")
            self.saved_total += 1
            if self.saved_total >= self.max_files:
                raise CloseSpider(f"Requested text-file limit reached: {self.max_files}")
        yield {"source": source, "url": response.url, "saved": bool(text)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-files", default="20")
    parser.add_argument("--source-names", default="", help="Comma-separated source names, e.g. krx,ksd")
    args = parser.parse_args()
    process = CrawlerProcess()
    process.crawl(FinancialSiteSpider, output=args.output, max_files=args.max_files, source_names=args.source_names)
    process.start()


if __name__ == "__main__":
    main()
