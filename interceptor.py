#!/usr/bin/env python3
"""
MVR API Traffic Interceptor
Captures network requests to identify the actual API endpoints used by the MVR e-services portal
"""

import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

# Test data - replace with your own values
EGN = "<YOUR_EGN>"
LAST_NAME = "<YOUR_LAST_NAME>"
# Direct link to the service information page
TARGET_URL = "https://www.mvr.bg/%D0%B5%D0%BB%D0%B5%D0%BA%D1%82%D1%80%D0%BE%D0%BD%D0%B8%D0%B7%D0%B8%D1%80%D0%B0%D0%BD%D0%B8-%D1%83%D1%81%D0%BB%D1%83%D0%B3%D0%B8/%D1%81%D0%BF%D1%80%D0%B0%D0%B2%D0%BA%D0%B0-%D0%B7%D0%B0-%D0%B8%D0%B7%D0%B4%D0%B0%D0%B4%D0%B5%D0%BD%D0%B8-%D0%B8-%D0%BD%D0%B5%D0%BF%D0%BE%D0%BB%D1%83%D1%87%D0%B5%D0%BD%D0%B8-%D0%B1%D1%8A%D0%BB%D0%B3%D0%B0%D1%80%D1%81%D0%BA%D0%B8-%D0%BB%D0%B8%D1%87%D0%BD%D0%B8-%D0%B4%D0%BE%D0%BA%D1%83%D0%BC%D0%B5%D0%BD%D1%82%D0%B8"

# Output directory
OUTPUT_DIR = Path(__file__).parent / "captured_data"
OUTPUT_DIR.mkdir(exist_ok=True)

async def intercept_traffic():
    """Launch browser and intercept all network traffic"""

    captured_requests = []
    captured_responses = []

    async with async_playwright() as p:
        # Launch browser in headed mode so we can see what's happening
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # Set up request interceptor
        async def handle_request(request):
            # Capture API calls (filter out static resources)
            if any(ext in request.url for ext in ['.js', '.css', '.png', '.jpg', '.woff', '.svg', '.woff2', '.ttf']):
                return

            req_data = {
                'url': request.url,
                'method': request.method,
                'headers': dict(request.headers),
                'post_data': request.post_data if request.method == 'POST' else None
            }
            captured_requests.append(req_data)
            print(f"\n📤 REQUEST: {request.method} {request.url}")
            if request.post_data:
                print(f"   Data: {request.post_data[:200]}...")

        # Set up response interceptor
        async def handle_response(response):
            if any(ext in response.url for ext in ['.js', '.css', '.png', '.jpg', '.woff', '.svg', '.woff2', '.ttf']):
                return

            try:
                body = await response.text()
                resp_data = {
                    'url': response.url,
                    'status': response.status,
                    'headers': dict(response.headers),
                    'body': body[:2000] if len(body) > 2000 else body
                }
                captured_responses.append(resp_data)
                print(f"📥 RESPONSE: {response.status} {response.url}")
                if body and len(body) < 1000:
                    print(f"   Body: {body[:300]}...")
            except Exception as e:
                print(f"   Could not read body: {e}")

        page.on("request", handle_request)
        page.on("response", handle_response)

        print(f"\n🌐 Navigating to: {TARGET_URL}")
        await page.goto(TARGET_URL, wait_until="networkidle")

        print("\n⏳ Waiting for page to fully load (5 seconds)...")
        await asyncio.sleep(5)

        print("\n🔍 Looking for the e-services portal link...")

        # Look for link to e-uslugi.mvr.bg
        try:
            print("\n📋 Searching for 'Start Service' button or link to e-uslugi.mvr.bg...")
            print("   Please click on the button/link that says:")
            print("   - 'Заявяване' (Apply)")
            print("   - 'Стартирай услугата' (Start Service)")
            print("   - Or any link to e-uslugi.mvr.bg")
            print("   This will take you to the actual form.")

        except Exception as e:
            print(f"   Error: {e}")

        print("\n⏳ Waiting 20 seconds for you to navigate to the form...")
        await asyncio.sleep(20)

        print("\n🔍 Looking for form fields...")

        # Try to find the form fields
        try:
            # Wait for form to appear
            await page.wait_for_selector("input", timeout=5000)

            # Get all input fields to understand the form structure
            inputs = await page.query_selector_all("input")
            print(f"\n📋 Found {len(inputs)} input fields:")
            for i, inp in enumerate(inputs):
                name = await inp.get_attribute("name")
                placeholder = await inp.get_attribute("placeholder")
                input_type = await inp.get_attribute("type")
                input_id = await inp.get_attribute("id")
                print(f"  {i+1}. Type: {input_type}, Name: {name}, ID: {input_id}, Placeholder: {placeholder}")

            # Look for CAPTCHA
            captcha_frames = await page.query_selector_all("iframe[src*='recaptcha'], iframe[src*='hcaptcha']")
            if captcha_frames:
                print(f"\n🤖 Found {len(captcha_frames)} CAPTCHA iframe(s)")
                for frame in captcha_frames:
                    src = await frame.get_attribute("src")
                    print(f"   {src}")
            else:
                print("\n✅ No CAPTCHA iframes found (reCAPTCHA/hCaptcha)")

            # Look for buttons
            buttons = await page.query_selector_all("button")
            print(f"\n🔘 Found {len(buttons)} buttons:")
            for i, btn in enumerate(buttons):
                text = await btn.inner_text()
                btn_type = await btn.get_attribute("type")
                print(f"  {i+1}. Type: {btn_type}, Text: {text.strip()}")

            print("\n" + "="*80)
            print("⏸️  MANUAL INTERACTION REQUIRED")
            print("="*80)
            print(f"\n   Test Data:")
            print(f"   - ЕГН: {EGN}")
            print(f"   - Last Name: {LAST_NAME}")
            print(f"\n   Please:")
            print(f"   1. Fill in the form with the test data above")
            print(f"   2. Solve any CAPTCHA if present")
            print(f"   3. Submit the form")
            print(f"   4. Wait for results to load")
            print(f"\n   This script will capture all API calls and save them.")
            print(f"   Waiting for 60 seconds...\n")
            print("="*80)

            await asyncio.sleep(60)

        except Exception as e:
            print(f"\n⚠️  Error analyzing form: {e}")
            print("   Taking screenshot for debugging...")
            await page.screenshot(path=str(OUTPUT_DIR / "page_screenshot.png"))

        print("\n📸 Taking final screenshot...")
        await page.screenshot(path=str(OUTPUT_DIR / "final_screenshot.png"))

        await browser.close()

    # Save captured traffic
    print("\n💾 Saving captured traffic...")
    with open(OUTPUT_DIR / "captured_requests.json", "w", encoding="utf-8") as f:
        json.dump(captured_requests, f, indent=2, ensure_ascii=False)

    with open(OUTPUT_DIR / "captured_responses.json", "w", encoding="utf-8") as f:
        json.dump(captured_responses, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Captured {len(captured_requests)} requests and {len(captured_responses)} responses")
    print(f"\n📁 Files saved in: {OUTPUT_DIR}")
    print(f"   - captured_requests.json")
    print(f"   - captured_responses.json")
    print(f"   - page_screenshot.png")
    print(f"   - final_screenshot.png")

if __name__ == "__main__":
    asyncio.run(intercept_traffic())
