"""
crawler.py - polite same-domain crawler using BeautifulSoup with html.parser

Usage:
    python crawler.py http://localhost:3000 --depth 2 --max-pages 100 --delay 1.0

Output:
    outputs/scan_results_<safe>.json
"""

import argparse
import json
import os
import time
import urllib.parse
from collections import deque
from typing import Dict, List, Set, Tuple

import requests
from bs4 import BeautifulSoup
from urllib import robotparser

# ---------- Config / Defaults ----------
DEFAULT_USER_AGENT = "WebScanProCrawler/1.0 (+https://example.com)"
OUTPUT_DIR = "outputs"


# ---------- Utility helpers ----------
def make_safe_filename(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    safe = parsed.netloc + parsed.path
    safe = safe.strip("/").replace("/", "_").replace(":", "_")
    if not safe:
        safe = parsed.netloc
    return safe or "root"


def same_domain(base: str, other: str) -> bool:
    try:
        return urllib.parse.urlparse(base).netloc == urllib.parse.urlparse(other).netloc
    except Exception:
        return False


def normalize_url(base: str, link: str) -> str:
    return urllib.parse.urljoin(base, link.split("#")[0])  # drop fragments


# ---------- Robots helper ----------
class RobotsChecker:
    def __init__(self, base_url: str, user_agent: str = DEFAULT_USER_AGENT):
        parsed = urllib.parse.urlparse(base_url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        self.rp = robotparser.RobotFileParser()
        try:
            self.rp.set_url(robots_url)
            self.rp.read()
        except Exception:
            # If robots.txt unavailable or unreadable, allow by default (for lab)
            self.rp = None

        self.user_agent = user_agent

    def can_fetch(self, url: str) -> bool:
        if self.rp is None:
            return True
        try:
            return self.rp.can_fetch(self.user_agent, url)
        except Exception:
            return True


# ---------- Main crawler ----------
class Crawler:
    def __init__(
        self,
        start_url: str,
        *,
        max_pages: int = 200,
        max_depth: int = 2,
        delay: float = 1.0,
        user_agent: str = DEFAULT_USER_AGENT,
        allowed_external: bool = False,
    ):
        self.start_url = start_url.rstrip("/")
        self.max_pages = max_pages
        self.max_depth = max_depth
        self.delay = delay
        self.user_agent = user_agent
        self.allowed_external = allowed_external

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.user_agent})

        self.robots = RobotsChecker(self.start_url, user_agent=self.user_agent)

        # Storage
        self.visited: Set[str] = set()
        self.results: Dict[str, Dict] = {}

    def extract_links_and_forms(self, url: str, html: str) -> Tuple[List[str], List[Dict]]:
        # Use html.parser because lxml is not installed
        soup = BeautifulSoup(html, "html.parser")
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href:
                links.append(href)

        forms = []
        for form in soup.find_all("form"):
            action = form.get("action") or ""
            method = form.get("method", "get").lower()
            inputs = []
            for inp in form.find_all(["input", "textarea", "select"]):
                name = inp.get("name")
                itype = inp.get("type", inp.name)
                inputs.append({"name": name, "type": itype})
            forms.append({"action": action, "method": method, "inputs": inputs})

        return links, forms

    def fetch(self, url: str) -> Tuple[int, str, Dict]:
        try:
            resp = self.session.get(url, timeout=15, allow_redirects=True)
            status = resp.status_code
            text = resp.text
            headers = dict(resp.headers)
            return status, text, headers
        except Exception as e:
            return 0, f"__fetch_error__:{repr(e)}", {}

    def crawl(self):
        q = deque()
        q.append((self.start_url, 0))
        self.visited.add(self.start_url)

        while q and len(self.results) < self.max_pages:
            url, depth = q.popleft()
            # respect depth
            if depth > self.max_depth:
                continue

            # robots
            if not self.robots.can_fetch(url):
                self.results[url] = {"skipped": "blocked_by_robots"}
                continue

            # fetch
            status, html_or_err, headers = self.fetch(url)
            print(f"[{len(self.results)+1}] {url} (depth {depth}) status={status}")

            # store
            page_data = {
                "url": url,
                "status": status,
                "headers": headers,
                "depth": depth,
                "forms": [],
                "out_links": [],
            }

            if status == 200 and isinstance(html_or_err, str) and not html_or_err.startswith("__fetch_error__"):
                links, forms = self.extract_links_and_forms(url, html_or_err)

                # normalize links and filter
                normalized = []
                for link in links:
                    try:
                        n = normalize_url(url, link)
                    except Exception:
                        continue
                    # filter mailto, javascript:
                    if n.startswith("mailto:") or n.startswith("javascript:"):
                        continue
                    if not self.allowed_external and not same_domain(self.start_url, n):
                        continue
                    normalized.append(n)

                    # enqueue if not visited and within depth
                    if n not in self.visited and depth + 1 <= self.max_depth and len(self.results) + len(q) < self.max_pages:
                        self.visited.add(n)
                        q.append((n, depth + 1))

                # resolve forms actions to absolute urls
                resolved_forms = []
                for f in forms:
                    action = f.get("action") or ""
                    resolved_action = normalize_url(url, action) if action else url
                    f["resolved_action"] = resolved_action
                    resolved_forms.append(f)

                page_data["forms"] = resolved_forms
                page_data["out_links"] = normalized
            else:
                # store fetch error text if present
                page_data["error"] = html_or_err

            self.results[url] = page_data

            # polite delay between requests
            time.sleep(self.delay)

        return self.results

    def save_results(self, path: str = None):
        if not os.path.exists(OUTPUT_DIR):
            os.makedirs(OUTPUT_DIR, exist_ok=True)
        if path is None:
            fname = os.path.join(OUTPUT_DIR, f"scan_results_{make_safe_filename(self.start_url)}.json")
        else:
            fname = path
        with open(fname, "w", encoding="utf-8") as fh:
            json.dump(self.results, fh, indent=2, ensure_ascii=False)
        print(f"Saved results to {fname}")
        return fname


# ---------- CLI ----------
def parse_args():
    p = argparse.ArgumentParser(description="WebScanPro - simple polite crawler")
    p.add_argument("start_url", help="Start URL (include http(s)://)")
    p.add_argument("--depth", type=int, default=2, help="Max crawl depth (default 2)")
    p.add_argument("--max-pages", type=int, default=200, help="Max pages to crawl (default 200)")
    p.add_argument("--delay", type=float, default=1.0, help="Delay between requests in seconds (default 1.0)")
    p.add_argument("--user-agent", default=DEFAULT_USER_AGENT, help="User-Agent string")
    p.add_argument("--allow-external", action="store_true", help="Allow crawling external domains (not same-domain)")
    p.add_argument("--output", help="Optional output file path (JSON)")
    return p.parse_args()


def main():
    args = parse_args()
    c = Crawler(
        args.start_url,
        max_pages=args.max_pages,
        max_depth=args.depth,
        delay=args.delay,
        user_agent=args.user_agent,
        allowed_external=args.allow_external,
    )
    results = c.crawl()
    out = c.save_results(path=args.output)
    print(f"Crawled {len(results)} pages. Output: {out}")


if __name__ == "__main__":
    main()
