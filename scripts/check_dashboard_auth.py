"""Check browser login recovery against a running app and an existing test account.

Install Playwright separately; this check never resets a database or writes to Meko.
Pass --credentials-file with a private JSON file containing email and password,
or set OPENHUMAN_TEST_EMAIL and OPENHUMAN_TEST_PASSWORD.
"""

import argparse
import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from playwright.async_api import async_playwright, expect


async def main(args):
    credentials = json.loads(args.credentials_file.read_text()) if args.credentials_file else {
        "email": os.getenv("OPENHUMAN_TEST_EMAIL"),
        "password": os.getenv("OPENHUMAN_TEST_PASSWORD"),
    }
    if not credentials.get("email") or not credentials.get("password"):
        raise SystemExit("Provide an existing test account with --credentials-file or OPENHUMAN_TEST_EMAIL/PASSWORD.")
    async with async_playwright() as p:
        request = await p.request.new_context(base_url=args.api)
        response = await request.post("/api/auth/login", data={k: credentials[k] for k in ("email", "password")})
        assert response.ok, f"Test account login failed ({response.status})."
        token = (await response.json())["access_token"]
        await request.dispose()
        browser = await p.chromium.launch(**({"executable_path": args.chromium} if args.chromium else {}))

        async def session(stored_token=None, cookie_token=None):
            state = {"cookies": [], "origins": []}
            if stored_token:
                state["origins"] = [{"origin": args.web, "localStorage": [{"name": "oh_token", "value": stored_token}]}]
            if cookie_token:
                state["cookies"] = [{"name": "oh_token", "value": cookie_token, "domain": urlsplit(args.web).hostname, "path": "/", "expires": -1, "httpOnly": False, "secure": args.web.startswith("https://"), "sameSite": "Lax"}]
            context = await browser.new_context(storage_state=state)
            page = await context.new_page()
            page.set_default_timeout(20000)
            return context, page

        try:
            context, page = await session(stored_token=token)
            try:
                await page.goto(args.web + "/dashboard")
                await page.get_by_role("link", name="Go to dashboard", exact=True).click()
                await expect(page).to_have_url(args.web + "/dashboard")
                await expect(page.get_by_role("heading", name="Team", exact=True)).to_be_visible()
                assert any(c["name"] == "oh_token" for c in await context.cookies())
                await page.reload()
                await expect(page.get_by_role("heading", name="Team", exact=True)).to_be_visible()
                print("Missing cookie: stored login recovers; dashboard and reload work.", flush=True)
            finally:
                await context.close()

            context, page = await session(stored_token="invalid-test-session")
            try:
                await page.goto(args.web + "/dashboard")
                await page.get_by_role("link", name="Go to dashboard", exact=True).click()
                await expect(page.get_by_label("Email address")).to_be_visible()
                assert await page.evaluate("localStorage.getItem('oh_token')") is None
                assert not any(c["name"] == "oh_token" for c in await context.cookies())
                print("Invalid stored login: rejected by the API and cleared; sign-in form works.", flush=True)
            finally:
                await context.close()

            context, page = await session(cookie_token=token)
            try:
                await page.goto(args.web + "/dashboard")
                await expect(page.get_by_label("Email address")).to_be_visible()
                assert not any(c["name"] == "oh_token" for c in await context.cookies())
                print("Cookie without stored login: returns to sign-in instead of spinning.", flush=True)
            finally:
                await context.close()

            context, page = await session()
            try:
                await page.goto(args.web + "/dashboard")
                await page.get_by_label("Email address").fill(credentials["email"])
                await page.locator("#password").fill(credentials["password"])
                await page.get_by_role("button", name="Sign in", exact=True).click()
                await expect(page).to_have_url(args.web + "/dashboard")
                await expect(page.get_by_role("heading", name="Team", exact=True)).to_be_visible()
                print("Fresh sign-in: real form submission opens the dashboard.", flush=True)
            finally:
                await context.close()
        finally:
            await browser.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--web", default="http://localhost:3000")
    parser.add_argument("--api", default="http://localhost:8000")
    parser.add_argument("--credentials-file", type=Path)
    parser.add_argument("--chromium", help="Optional path to an installed Chromium executable.")
    asyncio.run(main(parser.parse_args()))
