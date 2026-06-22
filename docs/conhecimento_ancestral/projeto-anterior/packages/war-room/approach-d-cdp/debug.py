"""Debug rápido: testa CDP Session no Chromium"""
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        ctx = await browser.new_context()
        page = await ctx.new_page()

        cdp = await ctx.new_cdp_session(page)
        print("[OK] CDPSession criada")

        # Testa se CDP responde
        versao = await cdp.send("Browser.getVersion")
        print(f"[OK] Browser: {versao.get('product', '?')[:60]}")

        # Testa Page.addScriptToEvaluateOnNewDocument
        result = await cdp.send("Page.addScriptToEvaluateOnNewDocument", {
            "source": "console.log('CDP_INJECTED'); window.__cdpTest = 42;"
        })
        print(f"[OK] Script injection ID: {result.get('identifier', '?')}")

        await page.goto("https://example.com", wait_until="domcontentloaded")
        await asyncio.sleep(2)

        val = await page.evaluate("() => window.__cdpTest")
        print(f"[TEST] window.__cdpTest = {val}")

        # Tenta Runtime.evaluate via CDP
        rt = await cdp.send("Runtime.evaluate", {
            "expression": "document.title + ' | testado via CDP'",
            "returnByValue": True
        })
        print(f"[TEST] Runtime.evaluate: {rt.get('result', {}).get('value', '?')}")

        await asyncio.get_event_loop().run_in_executor(None,
            lambda: input("\nEnter para fechar..."))
        await browser.close()

asyncio.run(main())
