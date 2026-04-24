from playwright.sync_api import sync_playwright

proxy_config = {
    "server": "http://gw-resi-gb.coldproxy.com:30827",
    "username": "netphinnwb_98165-package-ipv4resiprem",
    "password": "3DS5eiErHbYed"
}

bin_path = "/Users/lugon/dev/2026-3/tegufox-browser/build/Tegufox.app/Contents/MacOS/tegufox"

with sync_playwright() as p:
    print(f"Launching custom binary: {bin_path}")
    browser = p.firefox.launch(
        executable_path=bin_path,
        headless=True,
        proxy=proxy_config,
        firefox_user_prefs={
            "network.proxy.socks_remote_dns": False,
            "network.proxy.allow_hijacking_localhost": False
        }
    )
    context = browser.new_context()
    page = context.new_page()
    print("Navigating...")
    try:
        page.goto("https://httpbin.org/ip", timeout=15000)
        print(page.content()[:200])
    except Exception as e:
        print(f"Error: {e}")
    browser.close()
