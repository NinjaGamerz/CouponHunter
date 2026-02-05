#!/usr/bin/env python3
# hunter.py - Hybrid Ultra Scraper (Requests + Playwright)
# Save as hunter.py and run: python hunter.py
import os
import re
import time
import json
import html
import base64
from datetime import datetime
from urllib.parse import urlparse, urljoin, unquote, parse_qs

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ----------------- CONFIG -----------------
HISTORY_FILE = "memory.json"
SENT_FILE = "sent_courses.txt"
LOG_FILE = "hunter.log"

# Telegram env
TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Source map: set use_playwright=True for JS heavy sites
PREMIUM_SOURCES = {
    "CouponScorpion_100": {"url": "https://couponscorpion.com/category/100-off-coupons/", "use_playwright": True},
    "RealDiscount_Udemy": {"url": "https://www.real.discount/udemy", "use_playwright": False},
    "UdemyFreebies": {"url": "https://www.udemyfreebies.com/", "use_playwright": False},
    "CourseCouponClub": {"url": "https://coursecouponclub.com/", "use_playwright": True},
    "InfoGnu": {"url": "https://infognu.com/", "use_playwright": False},
}

# Hacking/security keywords (lowercase)
KEYWORDS = [
    "hacking","hack","ethical hacking","penetration","pentesting","bug bounty","cybersecurity",
    "security","reverse engineering","web hacking","network hacking","social engineering","ctf",
    "kali","nmap","metasploit","sqlmap","burp"
]
KEYWORDS_SET = set(k.lower() for k in KEYWORDS)

# Regex patterns
UDEMY_REGEX = re.compile(r'(https?://(?:www\.)?udemy\.com/course/[A-Za-z0-9\-\_]+(?:[/?#&][^\s"\'<>]*)?)', re.I)
UDEMY_ESCAPED_REGEX = re.compile(r'(https?:\\\\/\\\\/[^\'"]*udemy\.com\\/course\\/[A-Za-z0-9\-\_]+)', re.I)
BASE64_TOKEN = re.compile(r'["\']([A-Za-z0-9+/=]{48,})["\']')

# --------- Helpers & Logging ----------
def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def setup_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36")
    })
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

# --------- Telegram ----------
def send_telegram(title, link, source=""):
    if not TOKEN or not CHAT_ID:
        log("⚠️ Telegram not configured (TOKEN/CHAT_ID missing)")
        return False
    try:
        safe_title = html.escape(title)
        safe_link = html.escape(link)
        safe_source = html.escape(source)
        text = (
            f"<b>🔥 100% FREE UDEMY COURSE FOUND!</b>\n\n"
            f"<b>{safe_title}</b>\n"
            f"Source: {safe_source}\n"
            f"<a href=\"{safe_link}\">Get it on Udemy — Click here</a>\n"
            f"Found: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": False}
        resp = requests.post(url, json=payload, timeout=12)
        if resp.status_code == 200:
            log(f"✅ Telegram sent: {title[:80]}")
            return True
        else:
            log(f"❌ Telegram error ({resp.status_code}): {resp.text[:200]}")
            return False
    except Exception as e:
        log(f"❌ Telegram exception: {e}")
        return False

# --------- Extraction utilities (requests) ----------
def safe_get(session, url, timeout=12):
    try:
        r = session.get(url, timeout=timeout, allow_redirects=True)
        r.encoding = r.apparent_encoding or 'utf-8'
        log(f"   GET {url} -> {r.status_code} ({len(r.content)} bytes) final_url={getattr(r,'url',url)}")
        return r
    except Exception as e:
        log(f"   ⚠️ GET error {url}: {e}")
        return None

def extract_udemy_from_text(text):
    found = set()
    if not text:
        return found
    for m in UDEMY_REGEX.finditer(text):
        u = m.group(1).rstrip('"\').,; ')
        found.add(u)
    for m in UDEMY_ESCAPED_REGEX.finditer(text):
        esc = m.group(1)
        dec = esc.replace('\\\\/','/').replace('\\/','/').replace('http:\\/\\/','http://').replace('https:\\/\\/','https://')
        found.add(dec)
    # try to decode base64 tokens inside text
    for t in BASE64_TOKEN.findall(text):
        try:
            dec = base64.b64decode(t + '===').decode('utf-8', errors='ignore')
            if 'udemy.com/course' in dec:
                found.add(dec)
        except Exception:
            pass
    cleaned = set(unquote(html.unescape(u)) for u in found)
    return cleaned

def decode_targets_from_query(url):
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

def resolve_and_extract_udemy(session, candidate_url):
    found = set()
    found |= decode_targets_from_query(candidate_url)
    r = safe_get(session, candidate_url)
    if not r:
        return found
    # check redirect chain & final url
    try:
        chain = [h.url for h in (r.history or [])] + [r.url]
        for u in chain:
            if 'udemy.com/course' in u.lower():
                found.add(u)
        found |= extract_udemy_from_text(r.text)
    except Exception as e:
        log(f"   ⚠️ resolve error: {e}")
    return found

# --------- Requests-based scraper for "fast" sources ----------
def scrape_requests_source(session, source_name, source_url):
    results = []
    log(f"🔍 (requests) Scanning: {source_name} -> {source_url}")
    r = safe_get(session, source_url)
    if not r:
        return results
    soup = BeautifulSoup(r.text, "html.parser")
    page_title = (soup.title.string or "").strip() if soup.title else ""
    meta_desc = ''
    md = soup.find('meta', attrs={'name':'description'})
    if md and md.get('content'):
        meta_desc = md['content']

    # quick page-level scan for plain udemy links
    page_found = extract_udemy_from_text(r.text)
    for u in page_found:
        results.append({"title": page_title or u, "link": u, "source": source_name, "post_link": source_url})
    if page_found:
        log(f"   ✓ Page-level found: {len(page_found)}")

    anchors = soup.find_all(['a','button','input'], href=True) + soup.find_all(['a','button','input'])
    processed = set()
    for tag in anchors:
        try:
            # gather candidate URLs
            cands = set()
            if tag.get('href'):
                cands.add(urljoin(source_url, tag.get('href').strip()))
            for attr in ('data-href','data-url','data-clipboard-text','data-link','data-redirect'):
                v = tag.get(attr)
                if v:
                    cands.add(urljoin(source_url, v.strip()))
            onclick = tag.get('onclick') or ''
            if onclick:
                for m in re.findall(r"(https?:\/\/[^\)'\"]+)", onclick):
                    cands.add(m.strip())
            text = (tag.get_text(" ",strip=True) or '')
            if 'http' in text:
                cands |= extract_udemy_from_text(text)
            for cand in list(cands):
                if not cand or cand in processed:
                    continue
                processed.add(cand)
                if 'udemy.com/course' in cand.lower():
                    rr = safe_get(session, cand)
                    final = rr.url if rr else cand
                    title = (tag.get_text(" ",strip=True) or page_title or final)[:150]
                    # accept if seems free
                    if is_probably_free(title, meta_desc):
                        results.append({"title": title, "link": final, "source": source_name, "post_link": source_url})
                        log(f"    ✓ Direct udemy href: {title[:80]}")
                    continue
                # otherwise resolve candidate
                resolved = resolve_and_extract_udemy(session, cand)
                for u in resolved:
                    if is_probably_free((tag.get_text(" ",strip=True) or page_title), r.text[:1000]):
                        results.append({"title": (tag.get_text(" ",strip=True) or page_title)[:150], "link": u, "source": source_name, "post_link": cand})
                        log(f"    ✓ Resolved -> Udemy: {u}")
                time.sleep(0.08)
        except Exception as e:
            log(f"   ⚠️ requests tag error: {e}")
            continue
    # dedupe
    uniq = {}
    for r in results:
        if r['link'] not in uniq:
            uniq[r['link']] = r
    final = list(uniq.values())
    log(f"  ✅ {len(final)} courses found (requests) on {source_name}")
    return final

def is_probably_free(title, context_text=''):
    t = (title or '') + ' ' + (context_text or '')
    txt = t.lower()
    positives = ["100% off","100% free","100 percent","free coupon","free course","$0","gratis","100%"]
    if any(p in txt for p in positives):
        return True
    if "free" in txt and any(k in txt for k in KEYWORDS_SET):
        return True
    return False

# --------- Playwright-based scraper for JS-heavy sites ----------
def scrape_playwright_source(source_name, source_url, max_articles=200, headless=True):
    results = []
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        log("⚠️ Playwright not installed; skipping Playwright sources. (Install playwright to enable)")
        return results

    log(f"🔍 (playwright) Scanning: {source_name} -> {source_url}")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto(source_url, timeout=30000, wait_until="networkidle")
        except Exception as e:
            log(f"   ⚠️ play load fail: {e}")
            try:
                page.close()
            except:
                pass
            browser.close()
            return results

        # gather candidate article links heuristics
        candidates = set()
        try:
            anchors = page.query_selector_all("a[href]")
            for a in anchors:
                try:
                    href = a.get_attribute("href") or ""
                    txt = (a.inner_text() or "").lower()
                    full = urljoin(source_url, href)
                    if any(x in full.lower() for x in ['/free','coupon','udemy','course','deal','/free-']):
                        candidates.add(full)
                    if '100%' in txt or 'free' in txt:
                        candidates.add(full)
                except Exception:
                    continue
            # also page-level regex
            page_html = page.content()
            for u in UDEMY_REGEX.findall(page_html):
                candidates.add(u)
        except Exception as e:
            log(f"   ⚠️ gather candidates error: {e}")

        candidates = list(candidates)[:max_articles]
        log(f"   Candidates to open: {len(candidates)}")

        for art in candidates:
            try:
                art_page = context.new_page()
                try:
                    art_page.goto(art, timeout=30000, wait_until="networkidle")
                except Exception:
                    # some articles require interaction; continue anyway
                    pass
                # try extracting udemy from final DOM + scripts
                html_content = art_page.content()
                found = extract_udemy_from_text(html_content)
                # also inspect anchors
                try:
                    anchors = art_page.query_selector_all("a")
                    for a in anchors:
                        try:
                            href = a.get_attribute("href") or ""
                            if href and "udemy.com/course" in href.lower():
                                found.add(urljoin(art_page.url, href))
                        except:
                            pass
                except:
                    pass
                # click typical "get coupon"/"get it" buttons to open popups
                if not found:
                    try:
                        btns = art_page.query_selector_all("a,button,input")
                        for b in btns:
                            try:
                                label = (b.inner_text() or "").lower() + " " + (b.get_attribute("value") or "")
                                if any(k in label for k in ('coupon','get coupon','claim','get it','grab','claim coupon')):
                                    try:
                                        with context.expect_page(timeout=3000) as new_page_info:
                                            b.click(timeout=2000)
                                        new_p = new_page_info.value
                                        found |= extract_udemy_from_text(new_p.content())
                                        try:
                                            new_p.close()
                                        except:
                                            pass
                                    except Exception:
                                        href = b.get_attribute("href") or ""
                                        if href and "udemy" in href.lower():
                                            found |= extract_udemy_from_text(href)
                            except Exception:
                                continue
                    except Exception:
                        pass

                # accept found
                for u in found:
                    results.append({"title": art_page.title() or art, "link": u, "source": source_name, "post_link": art})
                try:
                    art_page.close()
                except:
                    pass
                time.sleep(0.12)
            except Exception as e:
                log(f"   ⚠️ playwright article error: {e}")
                continue

        try:
            page.close()
        except:
            pass
        browser.close()
    # dedupe
    uniq = {}
    for r in results:
        if r['link'] not in uniq:
            uniq[r['link']] = r
    final = list(uniq.values())
    log(f"  ✅ {len(final)} courses found (playwright) on {source_name}")
    return final

# ---------------- Main scanning flow ----------------
def start_scan():
    log("=" * 60)
    log("🚀 Starting Hybrid CouponHunter (Ultra)")
    log("=" * 60)

    session = setup_session()
    history = load_history()
    sent_links = set(history.get("sent_links", []))
    sent_courses = set(history.get("sent_courses", []))
    all_courses = []
    new_finds = 0

    # iterate sources
    for name, meta in PREMIUM_SOURCES.items():
        url = meta.get("url")
        use_playwright = bool(meta.get("use_playwright", False))
        try:
            if use_playwright:
                courses = scrape_playwright_source(name, url)
            else:
                courses = scrape_requests_source(session, name, url)
            all_courses.extend(courses)
        except Exception as e:
            log(f"❌ Error scanning {name}: {e}")
        time.sleep(0.8)

    # dedupe & send
    sent_this_run = set()
    for c in all_courses:
        try:
            cid_match = re.search(r'/course/([A-Za-z0-9\-\_]+)', c['link'], re.I)
            cid = cid_match.group(1).lower() if cid_match else c['link']
            if c['link'] in sent_links or cid in sent_courses or cid in sent_this_run:
                log(f"⏭️ Duplicate: {c['title'][:50]}")
                continue
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

    log("=" * 60)
    log(f"🏁 Scan complete! New finds: {new_finds}. Total tracked: {len(sent_courses)}")
    log("=" * 60)

if __name__ == "__main__":
    start_scan()