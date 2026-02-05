#!/usr/bin/env python3
"""
Hybrid Ultra Scraper (requests + Playwright fallback)
- Fast requests/BS4 scanning for simple aggregator pages
- Playwright rendering for JS-heavy/obfuscated pages (popups, onclick redirects)
- Robust extraction: href, data-attrs, onclick, script-embedded and encoded targets
- Redirect resolution and query/base64 decoding
- Deduplication and Telegram notifications
- Save history in memory.json and per-run sent list in sent_courses.txt
"""

import os
import re
import time
import json
import html
import base64
import logging
from datetime import datetime
from urllib.parse import urljoin, urlparse, unquote, parse_qs

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Optionally load .env for local testing
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ---------- CONFIG ----------
HISTORY_FILE = "memory.json"
SENT_FILE = "sent_courses.txt"
LOG_FILE = "hunter.log"

# Telegram (fill with env var or secrets in GitHub Actions)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Sources: set use_playwright=True for sites that need JS rendering
PREMIUM_SOURCES = {
    "CouponScorpion_100": {"url": "https://couponscorpion.com/category/100-off-coupons/", "use_playwright": True},
    "RealDiscount_Udemy": {"url": "https://www.real.discount/udemy", "use_playwright": False},
    "UdemyFreebies": {"url": "https://www.udemyfreebies.com/", "use_playwright": False},
    "CourseCouponClub": {"url": "https://coursecouponclub.com/", "use_playwright": True},
    "InfoGnu": {"url": "https://infognu.com/", "use_playwright": False},
}

# Hacking/security keywords (used for heuristic "free" detection)
KEYWORDS = [
    "hacking","hack","ethical hacking","penetration","pentesting","bug bounty",
    "cybersecurity","security","reverse engineering","web hacking","network hacking",
    "social engineering","ctf","kali","nmap","metasploit","sqlmap","burp"
]
KEYWORDS_SET = set(k.lower() for k in KEYWORDS)

# HTTP headers for requests (helps avoid 403)
DEFAULT_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Regex patterns
UDEMY_REGEX = re.compile(r'(https?://(?:www\.)?udemy\.com/course/[A-Za-z0-9\-\_]+(?:[/?#&][^\s"\'<>]*)?)', re.I)
UDEMY_ESCAPED = re.compile(r'(https?:\\\\/\\\\/[^\'"]*udemy\.com\\/course\\/[A-Za-z0-9\-\_]+)', re.I)
BASE64_TOKEN = re.compile(r'["\']([A-Za-z0-9+/=]{48,})["\']')

# Playwright settings
PLAYWRIGHT_NAV_TIMEOUT = 30_000  # ms
PLAYWRIGHT_MAX_ARTICLES = 200

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
    ],
)
log = logging.getLogger("coupon_hunter").info

# ---------- Utilities ----------
def now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def setup_requests_session():
    s = requests.Session()
    s.headers.update(DEFAULT_HEADERS)
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[429,500,502,503,504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.mount("http://", HTTPAdapter(max_retries=retries))
    return s

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"sent_links": [], "sent_courses": []}
    return {"sent_links": [], "sent_courses": []}

def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        log(f"❌ Error saving history: {e}")

# ---------- Telegram ----------
def send_telegram(title: str, link: str, source: str = "") -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        log("⚠️ Telegram not configured (TOKEN/CHAT_ID missing)")
        return False
    try:
        text = (
            f"<b>🔥 100% FREE UDEMY COURSE FOUND!</b>\n\n"
            f"<b>{html.escape(title)}</b>\n"
            f"Source: {html.escape(source)}\n"
            f"<a href=\"{html.escape(link)}\">Get it on Udemy — Click here</a>\n"
            f"Found: {now()}"
        )
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        resp = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }, timeout=12)
        if resp.status_code == 200:
            log(f"✅ Telegram sent: {title[:80]}")
            return True
        else:
            log(f"❌ Telegram error ({resp.status_code}): {resp.text[:200]}")
            return False
    except Exception as e:
        log(f"❌ Telegram exception: {e}")
        return False

# ---------- Extraction utilities ----------
def extract_udemy_from_text(text: str):
    """Find direct and escaped Udemy links inside arbitrary text."""
    found = set()
    if not text:
        return found
    # direct
    for m in UDEMY_REGEX.finditer(text):
        u = m.group(1).rstrip('"\').,; ')
        found.add(u)
    # escaped JS forms (https:\/\/www.udemy.com\/course\/...)
    for m in UDEMY_ESCAPED.finditer(text):
        esc = m.group(1)
        dec = esc.replace('\\\\/','/').replace('\\/','/').replace('http:\\/\\/','http://').replace('https:\\/\\/','https://')
        found.add(dec)
    # base64 tokens embedded
    for token in BASE64_TOKEN.findall(text):
        try:
            dec = base64.b64decode(token + '===').decode('utf-8', errors='ignore')
            if 'udemy.com/course' in dec:
                found.add(dec)
        except Exception:
            pass
    # unescape & unquote
    cleaned = set()
    for u in found:
        try:
            cleaned.add(unquote(html.unescape(u)))
        except Exception:
            cleaned.add(u)
    return cleaned

def decode_targets_from_query(url: str):
    """Search for encoded target URLs in query parameters and attempt to decode/base64."""
    found = set()
    try:
        parsed = urlparse(url)
        qs = parse_qs(parsed.query)
        for k, vals in qs.items():
            if any(x in k.lower() for x in ('url','to','target','redirect','link','u')):
                for v in vals:
                    v2 = unquote(v)
                    if 'udemy.com/course' in v2:
                        found.add(v2)
                    # base64 attempt
                    if len(v2) > 40 and re.match(r'^[A-Za-z0-9+/=]+$', v2):
                        try:
                            dec = base64.b64decode(v2 + '===').decode('utf-8', errors='ignore')
                            if 'udemy.com/course' in dec:
                                found.add(dec)
                        except Exception:
                            pass
    except Exception:
        pass
    return found

def resolve_and_extract(session: requests.Session, candidate_url: str):
    """Follow redirects; inspect body and chain for Udemy links and encoded targets."""
    found = set()
    try:
        found |= decode_targets_from_query(candidate_url)
        r = session.get(candidate_url, timeout=15, allow_redirects=True)
        r.encoding = r.apparent_encoding or 'utf-8'
        # check redirect chain and final url
        try:
            chain_urls = [h.url for h in (r.history or [])] + [r.url]
        except Exception:
            chain_urls = [r.url]
        for u in chain_urls:
            if 'udemy.com/course' in u.lower():
                found.add(u)
        found |= extract_udemy_from_text(r.text)
        # investigate base64-like tokens in body
        for token in BASE64_TOKEN.findall(r.text):
            try:
                dec = base64.b64decode(token + '===').decode('utf-8', errors='ignore')
                if 'udemy.com/course' in dec:
                    found.add(dec)
            except Exception:
                pass
    except Exception as e:
        log(f"   ⚠️ resolve_and_extract error for {candidate_url[:120]}: {e}")
    return found

# ---------- Heuristic: is this offering 100% free? ----------
def is_probably_free(title: str, context: str = ""):
    """Large heuristic to decide whether a page likely advertises 100% off / free coupon."""
    txt = (title or "") + " " + (context or "")
    txt = txt.lower()
    positives = ["100% off", "100% free", "100 percent", "free coupon", "free course", "$0", "gratis", "100%"]
    if any(p in txt for p in positives):
        return True
    # 'free' + presence of hacking/security keywords
    if "free" in txt and any(k in txt for k in KEYWORDS_SET):
        return True
    return False

# ---------- Requests-based scraper (fast, for plain sites) ----------
def scrape_requests_source(session: requests.Session, source_name: str, source_url: str):
    results = []
    log(f"🔍 (requests) Scanning: {source_name} -> {source_url}")
    try:
        r = session.get(source_url, timeout=15)
    except Exception as e:
        log(f"   ⚠️ GET error for {source_url}: {e}")
        return results

    r.encoding = r.apparent_encoding or 'utf-8'
    soup = BeautifulSoup(r.text, "html.parser")
    page_title = (soup.title.string or "").strip() if soup.title else source_name
    meta_desc = ""
    md = soup.find('meta', attrs={'name':'description'})
    if md and md.get('content'):
        meta_desc = md['content']

    # 1) page-level search for direct udemy links
    page_found = extract_udemy_from_text(r.text)
    if page_found:
        for u in page_found:
            results.append({"title": page_title, "link": u, "source": source_name, "post_link": source_url})
        log(f"   ✓ Page-level found: {len(page_found)}")

    # 2) inspect anchors/buttons for candidate links and follow
    processed = set()
    tags = soup.find_all(['a','button','input'])
    for tag in tags:
        try:
            cands = set()
            # common attributes
            href = tag.get('href') or tag.get('data-href') or tag.get('data-url') or ""
            if href:
                cands.add(urljoin(source_url, href.strip()))
            for attr in ('data-href','data-url','data-clipboard-text','data-link','data-redirect','value'):
                v = tag.get(attr)
                if v:
                    cands.add(urljoin(source_url, str(v).strip()))
            onclick = tag.get('onclick') or ''
            if onclick:
                for m in re.findall(r'(https?://[^\)\'"]+)', onclick):
                    cands.add(m.strip())
            # inline text that might contain URL
            text = (tag.get_text(" ", strip=True) or "")
            if 'http' in text:
                cands |= extract_udemy_from_text(text)

            for cand in list(cands):
                if not cand or cand in processed:
                    continue
                processed.add(cand)
                # direct candidate includes udemy
                if 'udemy.com/course' in cand.lower():
                    try:
                        rr = session.get(cand, timeout=12, allow_redirects=True)
                        final = getattr(rr, 'url', cand)
                    except Exception:
                        final = cand
                    title = (tag.get_text(" ", strip=True) or page_title)[:150]
                    if is_probably_free(title, meta_desc):
                        results.append({"title": title, "link": final, "source": source_name, "post_link": source_url})
                        log(f"    ✓ Direct udemy href: {title[:80]}")
                    continue

                # else resolve candidate (follow redirects, inspect body and params)
                resolved = resolve_and_extract(session, cand)
                if resolved:
                    inner_title = (tag.get_text(" ", strip=True) or page_title)[:150]
                    for u in resolved:
                        if is_probably_free(inner_title, r.text[:1000]):
                            results.append({"title": inner_title, "link": u, "source": source_name, "post_link": cand})
                            log(f"    ✓ Resolved -> Udemy: {u}")
                time.sleep(0.06)  # politeness
        except Exception as e:
            log(f"   ⚠️ requests tag processing error: {e}")
            continue

    # dedupe by link
    uniq = {}
    for item in results:
        if item['link'] not in uniq:
            uniq[item['link']] = item
    final = list(uniq.values())
    log(f"  ✅ {len(final)} courses found (requests) on {source_name}")
    return final

# ---------- Playwright-based scraper (for JS-heavy sites) ----------
def scrape_playwright_source(source_name: str, source_url: str, max_articles=PLAYWRIGHT_MAX_ARTICLES, headless=True):
    results = []
    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except Exception:
        log("⚠️ Playwright not installed - skipping Playwright sources. Install 'playwright' and run 'playwright install --with-deps chromium'")
        return results

    log(f"🔍 (playwright) Scanning: {source_name} -> {source_url}")
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=headless)
            context = browser.new_context()
            page = context.new_page()
            try:
                # use domcontentloaded - networkidle sometimes blocks on persistent analytics
                page.goto(source_url, timeout=PLAYWRIGHT_NAV_TIMEOUT, wait_until="domcontentloaded")
            except PWTimeout:
                log(f"   ⚠️ play load timeout for {source_url}")
            except Exception as e:
                log(f"   ⚠️ play load error for {source_url}: {e}")

            # gather candidate article links (flexible selectors)
            candidates = set()
            try:
                anchors = page.query_selector_all("a[href]")
                for a in anchors:
                    try:
                        href = a.get_attribute("href") or ""
                        href_full = urljoin(source_url, href)
                        txt = (a.inner_text() or "").lower()
                        # heuristic: article or coupon pages, or direct udemy link
                        if any(x in href_full.lower() for x in ('coupon','free','udemy','course','deal','/free-')) or '100%' in txt or 'free' in txt:
                            candidates.add(href_full)
                    except Exception:
                        continue

                # also check page HTML for direct udemy urls
                page_html = page.content()
                for u in UDEMY_REGEX.findall(page_html):
                    candidates.add(u)
            except Exception as e:
                log(f"   ⚠️ playwright candidate gather error: {e}")

            candidates = list(candidates)[:max_articles]
            log(f"   Candidates to open: {len(candidates)}")

            for art in candidates:
                try:
                    art_page = context.new_page()
                    try:
                        art_page.goto(art, timeout=PLAYWRIGHT_NAV_TIMEOUT, wait_until="domcontentloaded")
                    except PWTimeout:
                        log(f"     ⚠️ Article load timeout: {art}")
                    except Exception:
                        pass

                    # extract from final DOM + scripts
                    html_content = art_page.content()
                    found = extract_udemy_from_text(html_content)

                    # anchors on article page
                    try:
                        anchors = art_page.query_selector_all("a")
                        for a in anchors:
                            try:
                                href = a.get_attribute("href") or ""
                                if href and "udemy.com/course" in href.lower():
                                    found.add(urljoin(art_page.url, href))
                            except Exception:
                                pass
                    except Exception:
                        pass

                    # try clicking coupon buttons / typical labels
                    if not found:
                        try:
                            btns = art_page.query_selector_all("a,button,input")
                            for b in btns:
                                try:
                                    label = ((b.inner_text() or "") + " " + (b.get_attribute("value") or "")).lower()
                                    if any(k in label for k in ('coupon','get coupon','get it','claim','grab','claim coupon','free')):
                                        # try expect new page (popup)
                                        try:
                                            with context.expect_page(timeout=3000) as new_page_info:
                                                b.click(timeout=2000)
                                            newp = new_page_info.value
                                            found |= extract_udemy_from_text(newp.content())
                                            try:
                                                newp.close()
                                            except:
                                                pass
                                        except Exception:
                                            # fallback: check href attr
                                            href = b.get_attribute("href") or ""
                                            if href and 'udemy' in href.lower():
                                                found |= extract_udemy_from_text(href)
                                except Exception:
                                    continue
                        except Exception:
                            pass

                    # use resolve extraction on any relative non-udemy candidates found in the article DOM
                    # find common redirect patterns
                    try:
                        for tag in art_page.query_selector_all("[href], [data-href], [data-url], [data-redirect], [onclick]"):
                            try:
                                H = (tag.get_attribute("href") or tag.get_attribute("data-href") or tag.get_attribute("data-url") or "")
                                if H and 'udemy' not in H.lower():
                                    resolved = resolve_and_extract(requests.Session(), urljoin(art_page.url, H))
                                    found |= resolved
                            except Exception:
                                pass
                    except Exception:
                        pass

                    # collect final results
                    for u in found:
                        results.append({"title": art_page.title() or art, "link": u, "source": source_name, "post_link": art})
                    try:
                        art_page.close()
                    except:
                        pass
                    time.sleep(0.12)
                except Exception as e:
                    log(f"     ⚠️ playwright article processing error: {e}")
                    continue

            try:
                page.close()
            except:
                pass
            browser.close()
    except Exception as e:
        log(f"   ⚠️ Playwright overall error: {e}")

    # dedupe
    uniq = {}
    for r in results:
        if r['link'] not in uniq:
            uniq[r['link']] = r
    final = list(uniq.values())
    log(f"  ✅ {len(final)} courses found (playwright) on {source_name}")
    return final

# ---------- Hybrid scanning driver ----------
def start_scan():
    log("="*60)
    log("🚀 Starting Hybrid CouponHunter (Ultra)")
    log("="*60)

    session = setup_requests_session()
    history = load_history()
    sent_links = set(history.get("sent_links", []))
    sent_courses = set(history.get("sent_courses", []))
    all_courses = []
    new_finds = 0

    for name, meta in PREMIUM_SOURCES.items():
        url = meta.get("url")
        use_play = bool(meta.get("use_playwright", False))
        if not url:
            log(f"⏭️ Skipping invalid source: {name}")
            continue
        try:
            if use_play:
                courses = scrape_playwright_source(name, url)
            else:
                courses = scrape_requests_source(session, name, url)
            all_courses.extend(courses)
        except Exception as e:
            log(f"❌ Error scanning {name}: {e}")
        time.sleep(0.8)

    # Deduplicate by course id, send to Telegram
    sent_this_run = set()
    for c in all_courses:
        try:
            m = re.search(r'/course/([A-Za-z0-9\-\_]+)', c['link'], re.I)
            cid = m.group(1).lower() if m else c['link']
            if c['link'] in sent_links or cid in sent_courses or cid in sent_this_run:
                log(f"⏭️ Duplicate: {c['title'][:50]}")
                continue
            # send
            if send_telegram(c['title'], c['link'], c.get('source','')):
                sent_links.add(c['link'])
                sent_courses.add(cid)
                sent_this_run.add(cid)
                new_finds += 1
                try:
                    with open(SENT_FILE, "a", encoding="utf-8") as f:
                        f.write(f"{c['link']} | {c['title']} | {c.get('source','')}\n")
                except Exception:
                    pass
        except Exception as e:
            log(f"❌ Error sending course: {e}")

    history["sent_links"] = list(sent_links)
    history["sent_courses"] = list(sent_courses)
    save_history(history)

    log("="*60)
    log(f"🏁 Scan complete! New finds: {new_finds}. Total tracked: {len(sent_courses)}")
    log("="*60)

# ---------- ENTRY ----------
if __name__ == "__main__":
    start_scan()
