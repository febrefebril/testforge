"""
Approach A — Injeção Playwright (CORRIGIDA)
=============================================
add_init_script com guarda DOM: espera document.documentElement existir
antes de manipular o DOM. Isso resolve a falha de injeção inicial.

Testa Firefox + Chromium nos 6 cenários.
"""
import asyncio, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
from playwright.async_api import async_playwright

OVERLAY = """
window.__tfSteps = [];
window.addTFStep = function(a,d) { window.__tfSteps.push({action:a,detail:d,url:location.href}); };
document.addEventListener('click',function(e){
  var t=e.target||{}; var tag=(t.tagName||'').toLowerCase();
  if(['a','button','input','select'].includes(tag)) window.addTFStep('click',tag+' "'+(t.textContent||'').trim().slice(0,30)+'"');
},true);
(function inject(){
  if(!document.documentElement) return setTimeout(inject,5);
  var o=document.getElementById('__tfov');
  if(o) return;
  o=document.createElement('div'); o.id='__tfov';
  o.style.cssText='position:fixed;top:80px;right:20px;z-index:999999;background:#1a1a2e;color:#4ecca3;padding:10px;border-radius:8px;font:12px monospace;border:1px solid #0f3460;';
  o.innerHTML='<b style="color:#e94560">⛓ TF-{{NAME}}</b>';
  document.documentElement.appendChild(o);
  window.__tfReady=true;
})();
"""

async def run_test(p, engine, name):
    print(f"\n>>> {name}")
    browser = await engine.launch(headless=False)
    ctx = await browser.new_context(viewport={"width": 1280, "height": 720})
    page = await ctx.new_page()

    js = OVERLAY.replace("{{NAME}}", name[:4])
    await page.add_init_script(js)

    r = {}

    print(f"  [1/6] Abrir página")
    await page.goto("https://example.com", wait_until="domcontentloaded")
    await asyncio.sleep(1.5)
    ready = await page.evaluate("() => window.__tfReady === true")
    r["1. Abrir pagina"] = "PASS" if ready else "FAIL"
    print(f"  {'✅' if ready else '❌'} Overlay: {'presente' if ready else 'ausente'}")

    print(f"  [2/6] Navegação SPA")
    await page.evaluate("()=>{history.pushState({},'','/test');document.title='Pg2';}")
    await page.evaluate("()=>document.body.innerHTML+='<button id=a2>SPA</button>'")
    await asyncio.sleep(0.3)
    if ready: await page.click("#a2")
    await asyncio.sleep(0.3)
    s2 = await page.evaluate("()=>window.__tfSteps?window.__tfSteps.length:0")
    r["2. Navegacao SPA"] = "PASS" if s2 > 0 else "FAIL"
    print(f"  {'✅' if s2 > 0 else '❌'} Steps: {s2}")

    print(f"  [3/6] F5")
    await page.reload(wait_until="domcontentloaded")
    await asyncio.sleep(1.5)
    r3 = await page.evaluate("() => window.__tfReady === true")
    s3 = await page.evaluate("()=>window.__tfSteps?window.__tfSteps.length:0")
    r["3. F5"] = "PASS" if r3 else "FAIL"
    print(f"  {'✅' if r3 else '❌'} Overlay: {r3}, Steps: {s3}")

    print(f"  [4/6] Clicar botão")
    await page.evaluate("()=>document.body.innerHTML+='<button id=a4>Btn</button>'")
    if r3: await page.click("#a4")
    await asyncio.sleep(0.3)
    s4 = await page.evaluate("()=>window.__tfSteps?window.__tfSteps.length:0")
    r["4. Clicar botao"] = "PASS" if s4 > 0 else "FAIL"
    print(f"  {'✅' if s4 > 0 else '❌'} Steps: {s4}")

    print(f"  [5/6] Assert")
    try:
        await page.evaluate("()=>window.addTFStep('assert','visible')")
        s5 = await page.evaluate("()=>window.__tfSteps?window.__tfSteps.length:0")
        r["5. Adicionar assert"] = "PASS" if s5 > s4 else "FAIL"
        print(f"  {'✅' if s5 > s4 else '❌'} Steps: {s5}")
    except:
        r["5. Adicionar assert"] = "FAIL"
        print(f"  ❌ Erro")

    print(f"  [6/6] Finalizar")
    try:
        final = await page.evaluate("()=>window.__tfSteps||[]")
        r["6. Finalizar"] = "PASS" if len(final) > 0 else "FAIL"
        print(f"  {'✅' if len(final) > 0 else '❌'} Steps: {len(final)}")
    except:
        r["6. Finalizar"] = "FAIL"

    await browser.close()
    return r

async def main():
    print("="*60)
    print("A — INJEÇÃO PLAYWRIGHT (CORRIGIDA)")
    print("Com guarda DOM + Firefox + Chromium")
    print("="*60)

    async with async_playwright() as p:
        all_results = {
            "Firefox + add_init_script": await run_test(p, p.firefox, "Firefox"),
            "Chromium + add_init_script": await run_test(p, p.chromium, "Chromium"),
        }

    print("\n"+"="*60)
    print("RESULTADO FINAL")
    print("="*60)
    for label, results in all_results.items():
        passed = sum(1 for s in results.values() if s=="PASS")
        print(f"\n{label}: {passed}/{len(results)}")
        for s, v in results.items():
            print(f"  {'✅' if v=='PASS' else '❌'} {s}: {v}")

asyncio.run(main())
