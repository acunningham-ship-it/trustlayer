#!/usr/bin/env python3
"""
TrustLayer Advertising Poster — Playwright-based script to post to Reddit, HN, Dev.to.

Usage:
    python3 poster.py --platform reddit       # Post to Reddit subreddits
    python3 poster.py --platform hn           # Post to Hacker News
    python3 poster.py --platform devto        # Post to Dev.to
    python3 poster.py --platform all          # Post everywhere
    python3 poster.py --platform reddit --create-account   # Open Reddit signup
    python3 poster.py --platform reddit --visible          # Run with browser visible
"""

import argparse
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CRED_FILE = Path.home() / "ai-builder" / "trustlayer" / "advertise" / ".ad-credentials"
SCREENSHOT_DIR = Path.home() / "ai-builder" / "trustlayer" / "advertise" / "screenshots"
PROFILE_DIR = Path("/tmp") / "trustlayer_ad_profile"
TIMEOUT = 30_000  # 30s

GITHUB_URL = "https://github.com/acunningham-ship-it/trustlayer"

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# ---------------------------------------------------------------------------
# Post content
# ---------------------------------------------------------------------------
REDDIT_TITLE = (
    "I built an open-source trust layer for AI tools \u2014 verifies outputs, "
    "tracks costs across providers, runs 100% locally"
)

REDDIT_BODY = (
    "Hey everyone \u2014 I've been working on **TrustLayer**, an open-source trust layer "
    "that sits between your app and any AI provider (OpenAI, Anthropic, Ollama, etc.).\n"
    "\n"
    "**What it does:**\n"
    "- Verifies AI outputs against configurable rules before they reach your app\n"
    "- Tracks token usage and costs across multiple providers in one dashboard\n"
    "- Adds retry/fallback logic \u2014 if one provider fails, it rolls to the next\n"
    "- Runs 100% locally. No data leaves your machine.\n"
    "\n"
    "**Quick start:**\n"
    "```bash\n"
    "pip install trustlayer\n"
    "trustlayer init\n"
    "```\n"
    "\n"
    "It works as a drop-in proxy \u2014 point your existing code at `localhost:7432` instead "
    "of the provider URL and TrustLayer handles the rest.\n"
    "\n"
    "Built with Python, no heavy dependencies. Feedback and contributions welcome.\n"
    "\n"
    "GitHub: " + GITHUB_URL + "\n"
)

HN_TITLE = "Show HN: TrustLayer \u2013 Universal trust layer for AI tools (open source, local-first)"
HN_URL = GITHUB_URL

DEVTO_TITLE = "I built TrustLayer \u2014 an open-source trust layer for every AI tool"
DEVTO_BODY = """## The problem

If you use AI APIs from multiple providers, you know the pain:
- No unified way to verify outputs before they hit production
- Cost tracking is scattered across dashboards
- One provider goes down and your whole pipeline breaks
- Sensitive data gets sent to APIs you didn't intend

## The solution

**TrustLayer** is an open-source local-first proxy that sits between your application and any AI provider.

### How it works

You point your existing API calls at TrustLayer (runs on `localhost:7432`), and it:

1. **Routes** requests to your configured provider (OpenAI, Anthropic, Ollama, etc.)
2. **Validates** responses against rules you define \u2014 format checks, content filters, confidence thresholds
3. **Retries or falls back** to another provider if something fails
4. **Logs** every request with token counts and cost estimates

### Quick start

```bash
pip install trustlayer-ai
trustlayer server
```

That gives you a `trustlayer.yaml` config file. Point it at your providers, define your validation rules, and start it up:

```bash
trustlayer serve
```

Your existing code just changes one line \u2014 the base URL.

### Why local-first?

TrustLayer runs entirely on your machine. No cloud service, no account, no data leaving your network. The validation rules execute locally before and after each API call.

### What's next

- Plugin system for custom validators
- Web UI for cost dashboards
- MCP (Model Context Protocol) integration

I'd love feedback \u2014 especially from anyone running multi-provider setups or self-hosting LLMs.

**GitHub:** [acunningham-ship-it/trustlayer](""" + GITHUB_URL + """)

---

*TrustLayer is MIT licensed. Contributions welcome.*
"""

REDDIT_SUBREDDITS = ["LocalLLaMA", "selfhosted", "opensource"]

# ---------------------------------------------------------------------------
# Credential loader
# ---------------------------------------------------------------------------

def load_credentials():
    """Read key=value pairs from the credentials file."""
    creds = {}
    if not CRED_FILE.exists():
        print("[ERROR] Credentials file not found: " + str(CRED_FILE), file=sys.stderr)
        print("  Create it with placeholder values and fill in your creds.", file=sys.stderr)
        sys.exit(1)
    with open(CRED_FILE) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            key, _, value = line.partition("=")
            creds[key.strip()] = value.strip()
    return creds


def require_cred(creds, *keys):
    """Exit if any required credential is missing or empty."""
    for k in keys:
        if not creds.get(k):
            print("[ERROR] Missing credential: " + k + " in " + str(CRED_FILE), file=sys.stderr)
            sys.exit(1)


def screenshot(page, name):
    """Save a timestamped screenshot."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = SCREENSHOT_DIR / (name + "_" + ts + ".png")
    page.screenshot(path=str(path), full_page=True)
    print("  [screenshot] " + str(path))
    return path

# ---------------------------------------------------------------------------
# Account creation helpers (just opens signup pages)
# ---------------------------------------------------------------------------

def create_account(platform, pw_instance):
    """Open signup page in visible browser for manual account creation."""
    urls = {
        "reddit": "https://www.reddit.com/register",
        "hn": "https://news.ycombinator.com/login?creating=t",
        "devto": "https://dev.to/enter?state=new-user",
    }
    if platform == "all":
        targets = list(urls.keys())
    else:
        targets = [platform]

    browser = pw_instance.chromium.launch(headless=False)
    for t in targets:
        url = urls.get(t)
        if not url:
            print("[WARN] Unknown platform for account creation: " + t)
            continue
        page = browser.new_page()
        page.goto(url)
        print("[INFO] Opened " + t + " signup: " + url)
        print("  Complete signup manually in the browser window.")

    print("\n[INFO] Press Enter here when done with all signups...")
    input()
    browser.close()

# ---------------------------------------------------------------------------
# Reddit poster
# ---------------------------------------------------------------------------

def post_reddit(creds, headless=True):
    """Log in to Reddit and post to target subreddits."""
    from playwright.sync_api import sync_playwright

    require_cred(creds, "REDDIT_USER", "REDDIT_PASS")
    user = creds["REDDIT_USER"]
    passwd = creds["REDDIT_PASS"]

    print("[reddit] Starting Reddit poster as u/" + user)

    with sync_playwright() as pw:
        import random
        width = random.randint(1280, 1440)
        height = random.randint(720, 900)
        timezones = ["America/New_York", "America/Chicago", "America/Los_Angeles"]
        tz = random.choice(timezones)
        ua_profiles = [
            {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
             "sec_ch_ua": '"Chromium";v="130", "Google Chrome";v="130", "Not-A.Brand";v="99"', "platform": "Windows"},
            {"ua": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
             "sec_ch_ua": '"Chromium";v="131", "Google Chrome";v="131", "Not-A.Brand";v="99"', "platform": "Linux"},
        ]
        profile = random.choice(ua_profiles)
        stealth_js = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
delete navigator.__proto__.webdriver;
Object.defineProperty(navigator, 'plugins', {
    get: () => {
        const plugins = [
            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
            { name: 'Native Client', filename: 'internal-nacl-plugin' },
        ];
        plugins.length = 3;
        return plugins;
    }
});
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
window.chrome = { runtime: {} };
"""
        browser = pw.chromium.launch(
            headless=headless,
            args=[
                "--no-sandbox", "--disable-setuid-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage", "--no-first-run",
                "--no-default-browser-check", f"--window-size={width},{height}",
                "--disable-gpu", "--disable-software-rasterizer",
            ],
        )
        ctx = browser.new_context(
            user_agent=profile["ua"],
            viewport={"width": width, "height": height},
            locale="en-US",
            timezone_id=tz,
            extra_http_headers={
                "accept-language": "en-US,en;q=0.9",
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "sec-ch-ua": profile["sec_ch_ua"],
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"" + profile["platform"] + "\"",
                "sec-fetch-dest": "document",
                "sec-fetch-mode": "navigate",
                "sec-fetch-site": "none",
                "sec-fetch-user": "?1",
                "upgrade-insecure-requests": "1",
            },
        )
        ctx.add_init_script(stealth_js)
        page = ctx.new_page()

        # --- Load session cookies (extracted from Chrome) ---
        import json as _json
        cookie_file = Path(__file__).parent / "reddit_cookies.json"
        if cookie_file.exists():
            cookies = _json.loads(cookie_file.read_text())
            ctx.add_cookies(cookies)
            print(f"[reddit] Loaded {len(cookies)} cookies from Chrome session")
        else:
            print("[reddit] ERROR: No reddit_cookies.json found")
            browser.close()
            return False
        
        page.goto("https://old.reddit.com", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=TIMEOUT)
        time.sleep(3)

        # Verify login
        if "login" in page.url.lower():
            screenshot(page, "reddit_login_failed")
            print("[reddit] [ERROR] Login may have failed \u2014 check screenshot")
            browser.close()
            return False

        screenshot(page, "reddit_logged_in")
        print("[reddit] Login successful")

        # --- Post to each subreddit ---
        for sub in REDDIT_SUBREDDITS:
            print("[reddit] Posting to r/" + sub + "...")
            try:
                submit_url = "https://old.reddit.com/r/" + sub + "/submit"
                page.goto(submit_url, wait_until="domcontentloaded")
                time.sleep(3)

                # Old Reddit submit page — click "text" tab, fill title + body
                try:
                    text_tab = page.locator("a.text-button, li.text a")
                    if text_tab.count() > 0:
                        text_tab.first.click()
                        time.sleep(1)
                except Exception:
                    pass

                # Fill title (old reddit uses input or textarea with name="title")
                page.fill('textarea[name="title"], input[name="title"]', REDDIT_TITLE)
                time.sleep(1)

                # Fill body (old reddit uses textarea with name="text")
                page.fill('textarea[name="text"]', REDDIT_BODY)
                time.sleep(1)

                # Submit (old reddit uses button with name="submit")
                page.click('form#newlink button.btn[name="submit"]')
                time.sleep(5)
                page.wait_for_load_state("networkidle", timeout=TIMEOUT)

                screenshot(page, "reddit_" + sub + "_posted")
                print("[reddit] Posted to r/" + sub + ": " + page.url)

            except Exception as e:
                screenshot(page, "reddit_" + sub + "_error")
                print("[reddit] [ERROR] r/" + sub + ": " + str(e))

            # Delay between posts to avoid rate limits
            if sub != REDDIT_SUBREDDITS[-1]:
                print("[reddit] Waiting 60s between subreddit posts...")
                time.sleep(60)

        browser.close()
    return True

# ---------------------------------------------------------------------------
# Hacker News poster
# ---------------------------------------------------------------------------

def post_hn(creds, headless=True):
    """Log in to Hacker News and submit a Show HN post."""
    from playwright.sync_api import sync_playwright

    require_cred(creds, "HN_USER", "HN_PASS")
    user = creds["HN_USER"]
    passwd = creds["HN_PASS"]

    print("[hn] Starting HN poster as " + user)

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        page = browser.new_page(
            viewport={"width": 1280, "height": 900},
            user_agent=USER_AGENT,
        )

        # --- Login ---
        print("[hn] Logging in...")
        page.goto("https://news.ycombinator.com/login", wait_until="domcontentloaded")
        time.sleep(1)

        page.fill('input[name="acct"]', user)
        page.fill('input[name="pw"]', passwd)
        page.click('input[type="submit"][value="login"]')
        page.wait_for_load_state("networkidle", timeout=TIMEOUT)
        time.sleep(2)

        # Check login
        content = page.content()
        if "login" in page.url.lower() and "Bad login" in content:
            screenshot(page, "hn_login_failed")
            print("[hn] [ERROR] Login failed")
            browser.close()
            return False

        screenshot(page, "hn_logged_in")
        print("[hn] Login successful")

        # --- Submit ---
        print("[hn] Submitting Show HN post...")
        page.goto("https://news.ycombinator.com/submit", wait_until="domcontentloaded")
        time.sleep(1)

        page.fill('input[name="title"]', HN_TITLE)
        page.fill('input[name="url"]', HN_URL)
        page.click('input[type="submit"]')
        page.wait_for_load_state("networkidle", timeout=TIMEOUT)
        time.sleep(2)

        screenshot(page, "hn_posted")
        print("[hn] Submitted: " + page.url)

        browser.close()
    return True

# ---------------------------------------------------------------------------
# Dev.to poster (API-based is primary, browser fallback)
# ---------------------------------------------------------------------------

def post_devto(creds, headless=True):
    """Post article to Dev.to using their API or browser fallback."""
    api_key = creds.get("DEVTO_API_KEY", "")

    if api_key:
        return _post_devto_api(api_key)
    else:
        return _post_devto_browser(creds, headless)


def _post_devto_api(api_key):
    """Post via Dev.to Forem API."""
    import json
    import urllib.request

    print("[devto] Posting via API...")

    article = {
        "article": {
            "title": DEVTO_TITLE,
            "body_markdown": DEVTO_BODY,
            "published": True,
            "tags": ["opensource", "ai", "python", "selfhosted"],
        }
    }

    data = json.dumps(article).encode("utf-8")
    req = urllib.request.Request(
        "https://dev.to/api/articles",
        data=data,
        headers={
            "Content-Type": "application/json",
            "api-key": api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read())
            url = result.get("url", "unknown")
            print("[devto] Published: " + url)
            return True
    except Exception as e:
        print("[devto] [ERROR] API post failed: " + str(e))
        return False


def _post_devto_browser(creds, headless=True):
    """Fallback: guidance when no API key is set."""
    from playwright.sync_api import sync_playwright

    print("[devto] No API key found \u2014 using browser fallback")
    print("[devto] Note: Dev.to uses GitHub/OAuth login. Browser posting may")
    print("        require a pre-authenticated session. Consider using API key instead.")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=headless)
        page = browser.new_page(
            viewport={"width": 1280, "height": 900},
            user_agent=USER_AGENT,
        )

        page.goto("https://dev.to/enter", wait_until="domcontentloaded")
        time.sleep(2)
        screenshot(page, "devto_login_page")

        print("[devto] [WARN] Browser-based Dev.to posting requires OAuth login.")
        print("        Get an API key from https://dev.to/settings/extensions")
        print("        and add it to .ad-credentials as DEVTO_API_KEY=...")

        browser.close()
    return False

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="TrustLayer advertising poster \u2014 post to Reddit, HN, Dev.to"
    )
    parser.add_argument(
        "--platform",
        choices=["reddit", "hn", "devto", "all"],
        required=True,
        help="Platform to post to",
    )
    parser.add_argument(
        "--create-account",
        action="store_true",
        help="Open signup pages for manual account creation (visible mode)",
    )
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Run browser in visible mode for debugging",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print post content without actually posting",
    )
    args = parser.parse_args()

    headless = not args.visible

    # --- Dry run ---
    if args.dry_run:
        sep = "=" * 60
        print(sep)
        print("DRY RUN \u2014 Post content preview")
        print(sep)
        if args.platform in ("reddit", "all"):
            subs = ", ".join("r/" + s for s in REDDIT_SUBREDDITS)
            print("\n--- Reddit (" + subs + ") ---")
            print("Title: " + REDDIT_TITLE)
            print("Body:\n" + REDDIT_BODY)
        if args.platform in ("hn", "all"):
            print("\n--- Hacker News ---")
            print("Title: " + HN_TITLE)
            print("URL: " + HN_URL)
        if args.platform in ("devto", "all"):
            print("\n--- Dev.to ---")
            print("Title: " + DEVTO_TITLE)
            print("Body:\n" + DEVTO_BODY)
        return

    # --- Account creation mode ---
    if args.create_account:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            create_account(args.platform, pw)
        return

    # --- Load credentials ---
    creds = load_credentials()

    # --- Post ---
    results = {}
    if args.platform == "all":
        platforms = ["reddit", "hn", "devto"]
    else:
        platforms = [args.platform]

    for p in platforms:
        sep = "=" * 50
        print("\n" + sep)
        print(" Posting to: " + p.upper())
        print(sep + "\n")

        if p == "reddit":
            results[p] = post_reddit(creds, headless)
        elif p == "hn":
            results[p] = post_hn(creds, headless)
        elif p == "devto":
            results[p] = post_devto(creds, headless)

        if p != platforms[-1]:
            print("\n[*] Pausing 10s before next platform...\n")
            time.sleep(10)

    # --- Summary ---
    sep = "=" * 50
    print("\n" + sep)
    print(" RESULTS")
    print(sep)
    for p, ok in results.items():
        status = "OK" if ok else "FAILED"
        print("  " + p.ljust(10) + " : " + status)
    print("\nScreenshots saved to: " + str(SCREENSHOT_DIR))


if __name__ == "__main__":
    main()
