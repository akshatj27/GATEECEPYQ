from playwright.sync_api import sync_playwright

def verify_frontend():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 1900})

        # Test analytics page
        page.goto("http://localhost:8000/analytics.html")
        page.wait_for_selector("#total-questions", state="visible")

        # Take a screenshot
        page.screenshot(path="/home/jules/verification/analytics_page_new.png", full_page=True)

        browser.close()
        print("Verification complete. Screenshot saved.")

if __name__ == "__main__":
    verify_frontend()
