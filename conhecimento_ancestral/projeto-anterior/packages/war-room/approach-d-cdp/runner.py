"""
Approach D — Proxy CDP (Chrome DevTools Protocol)
Testa 2 formas: CDP native + Playwright add_init_script no Chromium.
6 cenários da War Room.
"""
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from playwright.async_api import async_playwright

OVERLAY_JS = """
window.__tfSteps = []; window.__tfReady = false;
window.addTFStep = function(a,d) { window.__tfSteps.push({action:a,detail:d,url:location.href,ts:Date.now()}); };
document.addEventListener('click',function(e){
  var t=e.target||{}; var tag=(t.tagName||'').toLowerCase();
  if(['a','button','input','select'].includes(tag)) window.addTFStep('click',tag+' "'+(t.textContent||'').trim().slice(0,30)+'"');
},true);
var o=document.createElement('div'); o.id='__tfov';
o.style.cssText='position:fixed;top:80px;right:20px;z-index:999999;background:#1a1a2e;color:#4ecca3;padding:10px;border-radius:8px;font:12px monospace;border:1px solid #0f3460;';
o.innerHTML='<b style="color:#e94560">⛓ TF-'+'{{NAME}}</b>';
document.documentElement.appendChild(o); window.__tfReady=true;
"""

async def run_all(page, browser, label):
    r = {}
    print(f"  [1/6] Abrir página")
    await page.goto("https://example.com", wait_until="domcontentloaded")
    await asyncio.sleep(1.5)
    ready = await page.evaluate("() => window.__tfReady === true")
    r["1. Abrir pagina"] = "PASS" if ready else "FAIL"
    print(f"  {'✅' if ready else '❌'} Overlay: {'presente' if ready else 'ausente'}")

    if not ready:
        await page.evaluate(OVERLAY_JS.replace("{{NAME}}", "pos"))
        ready = await page.evaluate("() => window.__tfReady === true")
        print(f"  {'✅' if ready else '❌'} Pós-injeção: {'OK' if ready else 'falhou'}")

    print(f"  [2/6] Navegação SPA")
    await page.evaluate("()=>{history.pushState({},'','/test');document.title='Pg2';}")
    await page.evaluate("()=>document.body.innerHTML+='<button id=ds2>SPA</button>'")
    await asyncio.sleep(0.3)
    if ready: await page.click("#ds2")
    await asyncio.sleep(0.3)
    steps2 = await page.evaluate("()=>window.__tfSteps?window.__tfSteps.length:0")
    r["2. Navegacao SPA"] = "PASS" if steps2 > 0 else "FAIL"
    print(f"  {'✅' if steps2 > 0 else '❌'} Steps: {steps2}")

    print(f"  [3/6] F5")
    await page.reload(wait_until="domcontentloaded")
    await asyncio.sleep(1.5)
    ready3 = await page.evaluate("() => window.__tfReady === true")
    steps3 = await page.evaluate("()=>window.__tfSteps?window.__tfSteps.length:0")
    r["3. F5"] = "PASS" if ready3 else "FAIL"
    print(f"  {'✅' if ready3 else '❌'} Overlay: {ready3}, Steps: {steps3}")

    print(f"  [4/6] Clicar botão")
    await page.evaluate("()=>document.body.innerHTML+='<button id=ds4>Btn</button>'")
    if ready3: await page.click("#ds4")
    await asyncio.sleep(0.3)
    steps4 = await page.evaluate("()=>window.__tfSteps?window.__tfSteps.length:0")
    r["4. Clicar botao"] = "PASS" if steps4 > 0 else "FAIL"
    print(f"  {'✅' if steps4 > 0 else '❌'} Steps: {steps4}")

    print(f"  [5/6] Assert")
    try:
        await page.evaluate("() => window.addTFStep('assert','visible')")
        steps5 = await page.evaluate("()=>window.__tfSteps?window.__tfSteps.length:0")
        r["5. Adicionar assert"] = "PASS" if steps5 > steps4 else "FAIL"
        print(f"  {'✅' if steps5 > steps4 else '❌'} Steps: {steps5}")
    except Exception as e:
        r["5. Adicionar assert"] = "FAIL"
        print(f"  ❌ Erro: {str(e)[:60]}")

    print(f"  [6/6] Finalizar")
    try:
        final = await page.evaluate("() => window.__tfSteps || []")
        r["6. Finalizar"] = "PASS" if len(final) > 0 else "FAIL"
        print(f"  {'✅' if len(final) > 0 else '❌'} Steps: {len(final)}")
    except: r["6. Finalizar"] = "FAIL"

    await browser.close()
    return r

async def test_cdp_direct(p):
    print("\n>>> CDP native (Page.addScriptToEvaluateOnNewDocument)")
    browser = await p.chromium.launch(headless=False)
    ctx = await browser.new_context(viewport={"width": 1280, "height": 720})
    page = await ctx.new_page()
    cdp = await ctx.new_cdp_session(page)
    await cdp.send("Page.addScriptToEvaluateOnNewDocument", {"source": OVERLAY_JS.replace("{{NAME}}","cdp")})
    return await run_all(page, browser, "CDP")

async def test_add_init_script(p):
    print("\n>>> add_init_script Chromium (usa CDP internamente)")
    browser = await p.chromium.launch(headless=False)
    ctx = await browser.new_context(viewport={"width": 1280, "height": 720})
    page = await ctx.new_page()
    await page.add_init_script(OVERLAY_JS.replace("{{NAME}}","init"))
    return await run_all(page, browser, "add_init_script")

async def main():
    print("="*60)
    print("D — PROXY CDP (Chromium)")
    print("="*60)
    async with async_playwright() as p:
        all_results = {
            "CDP Page.addScriptToEvaluateOnNewDocument": await test_cdp_direct(p),
            "add_init_script (usa CDP internamente)": await test_add_init_script(p),
        }
    print("\n"+"="*60)
    print("RESULTADO D — PROXY CDP")
    print("="*60)
    for label, results in all_results.items():
        passed = sum(1 for s in results.values() if s == "PASS")
        print(f"\n{label}: {passed}/{len(results)}")
        for s, v in results.items():
            print(f"  {'✅' if v=='PASS' else '❌'} {s}: {v}")

asyncio.run(main())
