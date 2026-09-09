from pathlib import Path
import json
import os
from playwright.sync_api import sync_playwright

BASE = os.environ.get("DEMO_BASE_URL", "http://127.0.0.1:8766").rstrip("/")
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "qa-artifacts"
OUT.mkdir(exist_ok=True)
PAGES = [
    ("mt", "/mt-studio/"),
    ("colaguo", "/colaguo-baby/"),
    ("monbebe", "/monbebe/"),
    ("superbling", "/superbling/"),
    ("dogo", "/dogohotel/"),
    ("shanlin", "/shanlin-spa/"),
    ("petfactory", "/the-pet-factory/"),
    ("mamas", "/mamas-chalet/"),
]
VIEWPORTS = {
    "desktop": {"width": 1440, "height": 950},
    "mobile": {"width": 390, "height": 844},
}

results = []
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    )
    for label, viewport in VIEWPORTS.items():
        context = browser.new_context(viewport=viewport, device_scale_factor=1)
        for slug, path in PAGES:
            page = context.new_page()
            console_errors = []
            page_errors = []
            failed_requests = []
            page.on("console", lambda msg, bucket=console_errors: bucket.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda exc, bucket=page_errors: bucket.append(str(exc)))
            page.on("requestfailed", lambda req, bucket=failed_requests: bucket.append({"url": req.url, "failure": req.failure}))
            response = page.goto(BASE + path, wait_until="networkidle")
            before = page.evaluate("""() => ({
                title: document.title,
                width: document.documentElement.clientWidth,
                scrollWidth: document.documentElement.scrollWidth,
                h1: document.querySelector('h1')?.innerText,
                services: document.querySelectorAll('.service-card').length,
                images: [...document.images].map(i => ({src:i.getAttribute('src'), complete:i.complete, naturalWidth:i.naturalWidth})),
                noindex: document.querySelector('meta[name=robots]')?.content || '',
                conceptBar: document.querySelector('.concept-bar')?.innerText || '',
            })""")
            page.screenshot(path=str(OUT / f"{slug}-{label}.png"), full_page=False)
            page.locator("[data-demo-form] button[type=submit]").click()
            result_text = page.locator(".form-result").inner_text()
            result_visible = page.locator(".form-result").is_visible()
            # Explicitly reveal every lazy image. Mobile browsers may jump
            # directly to the form and legitimately skip intermediate images.
            for lazy_image in page.locator("img[loading='lazy']").all():
                lazy_image.scroll_into_view_if_needed()
                page.wait_for_timeout(120)
            page.wait_for_function(
                "[...document.images].every(i => i.complete && i.naturalWidth > 0)",
                timeout=5000,
            )
            after_images = page.evaluate("[...document.images].map(i => ({src:i.getAttribute('src'), complete:i.complete, naturalWidth:i.naturalWidth}))")
            # Trigger the internal navigation independent of viewport visibility;
            # mobile CSS intentionally hides the header's text links.
            page.evaluate("document.querySelector('a[href=\"#services\"]').click()")
            page.wait_for_timeout(120)
            nav_hash = page.evaluate("location.hash")
            record = {
                "page": slug,
                "viewport": label,
                "http_status": response.status if response else None,
                **before,
                "overflow": before["scrollWidth"] > before["width"],
                "images_after_scroll": after_images,
                "all_images_loaded": all(x["complete"] and x["naturalWidth"] > 0 for x in after_images),
                "form_result_visible": result_visible,
                "form_result_text": result_text,
                "internal_nav_hash": nav_hash,
                "console_errors": console_errors,
                "page_errors": page_errors,
                "failed_requests": failed_requests,
            }
            results.append(record)
            page.close()
        context.close()
    browser.close()

errors = []
for r in results:
    if r["http_status"] != 200: errors.append(f"{r['page']} {r['viewport']}: HTTP {r['http_status']}")
    if r["overflow"]: errors.append(f"{r['page']} {r['viewport']}: horizontal overflow")
    if r["services"] != 6: errors.append(f"{r['page']} {r['viewport']}: service count {r['services']}")
    if not r["all_images_loaded"]: errors.append(f"{r['page']} {r['viewport']}: image load failure")
    if "noindex" not in r["noindex"]: errors.append(f"{r['page']} {r['viewport']}: noindex missing")
    form_ok = "沒有送出或保存" in r["form_result_text"] or "not sent or stored" in r["form_result_text"]
    if not r["form_result_visible"] or not form_ok: errors.append(f"{r['page']} {r['viewport']}: form demo failed")
    if r["internal_nav_hash"] != "#services": errors.append(f"{r['page']} {r['viewport']}: anchor nav failed")
    if r["console_errors"] or r["page_errors"] or r["failed_requests"]: errors.append(f"{r['page']} {r['viewport']}: browser errors")

report = {"base_url": BASE, "pages_expected": 8, "pages_tested": len(PAGES), "viewports": list(VIEWPORTS), "checks": len(results), "errors": errors, "results": results}
(ROOT / "qa-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"pages_tested": len(PAGES), "checks": len(results), "errors": errors, "screenshots": [str(OUT / f"{s}-{v}.png") for v in VIEWPORTS for s,_ in PAGES]}, ensure_ascii=False, indent=2))
raise SystemExit(1 if errors else 0)
