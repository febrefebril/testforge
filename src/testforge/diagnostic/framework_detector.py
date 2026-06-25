"""Sprint 0 — FrameworkDetector (A3 + A4 combined for maximum precision).

Four detection techniques run together; each produces evidence strings.
The aggregate `evidence` list explains *why* a framework was claimed.

- A1 window.* sniff               (`window.ng`, `window.Vue`, `window.React`, ...)
- A2 DOM markers                  (`[ng-version]`, `mat-form-field`, `ui-widget`, MUI Mui*)
- A3 HTTP bundle analysis (CDP)   names of JS bundles loaded
- A4 custom elements list         non-standard tags `<dsc-input-currency>` etc.

Designed to be resilient: each technique is independently fault-tolerant.
A failure in CDP does not break window/DOM detection.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


_BUNDLE_SIGNATURES = {
    "angular": [
        r"/@angular/",
        r"runtime[.\-][\w.\-]+\.js",
        r"polyfills[.\-][\w.\-]+\.js",
        r"angular[.\-]\d+\.\d+\.\d+",
    ],
    "angular_material": [r"/@angular/material", r"material(?:\.umd)?[.\-][\w.\-]+\.js"],
    "primefaces": [r"primefaces(?:[/.])", r"primefaces\.js"],
    "mui": [r"/@mui/", r"material-ui", r"/mui-"],
    "vue": [r"vue@", r"/vue[.\-][\w.\-]+\.js", r"/vue\.runtime"],
    "react": [r"/react@", r"/react-dom", r"react\.production\.min\.js"],
    "jsf": [r"javax\.faces\.resource", r"/javax\.faces\."],
}

# Standard HTML tags we don't count as custom
_STANDARD_TAGS = {
    "html", "head", "body", "div", "span", "p", "a", "button", "input",
    "select", "option", "textarea", "form", "label", "img", "ul", "ol",
    "li", "table", "tr", "td", "th", "thead", "tbody", "tfoot", "h1", "h2",
    "h3", "h4", "h5", "h6", "header", "footer", "nav", "main", "section",
    "article", "aside", "iframe", "br", "hr", "script", "style", "link",
    "meta", "title", "code", "pre", "strong", "em", "b", "i", "u", "small",
    "video", "audio", "canvas", "svg", "path", "g", "rect", "circle",
    "fieldset", "legend", "datalist", "details", "summary", "dialog",
    "figcaption", "figure", "picture", "source", "track", "time", "mark",
    "abbr", "address", "blockquote", "cite", "del", "dfn", "ins", "kbd",
    "q", "samp", "sub", "sup", "var", "wbr", "noscript", "template",
    "object", "embed", "param", "menu", "menuitem",
}


class FrameworkDetector:
    """Multi-technique framework detection.

    Usage:
        det = FrameworkDetector(page, cdp_session)  # cdp may be None
        det.attach()           # starts watching bundles
        # ... user navigates ...
        result = det.detect()  # snapshot now
        det.detach()
    """

    def __init__(self, page, cdp_session=None) -> None:
        self._page = page
        self._cdp = cdp_session
        self._bundles_seen: list[str] = []
        self._listener = None
        # Hotfix BUG 6: cache last successful detection so finalize() after
        # browser close still reports the real framework rather than 'unknown'.
        self._last_detection: dict | None = None

    # ------------------------------------------------------------------
    def attach(self) -> None:
        """Subscribe to CDP Network events (A3). Safe to call when no CDP."""
        if self._cdp is None:
            return
        try:
            self._cdp.send("Network.enable")
            self._cdp.on("Network.responseReceived", self._on_response)
            self._listener = self._on_response
            logger.info("FrameworkDetector A3 listener attached")
        except Exception as exc:
            logger.warning("FrameworkDetector A3 attach failed: %s", exc)

    def detach(self) -> None:
        # CDP listeners auto-clean with the session; nothing explicit needed.
        self._listener = None

    def _on_response(self, evt: dict) -> None:
        try:
            url = (evt.get("response") or {}).get("url") or ""
            if url:
                self._bundles_seen.append(url)
        except Exception:
            pass

    # ------------------------------------------------------------------
    def detect(self) -> dict:
        """Run all 4 techniques and combine. Safe to call multiple times."""
        evidence: list[str] = []
        flags: dict[str, Any] = {
            "angular_version": None,
            "angular_material": False,
            "primefaces": False,
            "mui": False,
            "vue": None,
            "react": None,
            "jsf": False,
            "zone_js": False,
        }

        # A3: bundle analysis
        bundle_flags = self._analyze_bundles()
        for fw, hits in bundle_flags.items():
            if hits:
                if fw == "angular":
                    # Try to extract version from URL like 'runtime.angular-16.2.0.js'
                    for h in hits:
                        m = re.search(r"angular[/-](\d+\.\d+\.\d+)", h)
                        if m:
                            flags["angular_version"] = m.group(1)
                            break
                if fw == "angular_material":
                    flags["angular_material"] = True
                if fw == "primefaces":
                    flags["primefaces"] = True
                if fw == "mui":
                    flags["mui"] = True
                if fw == "vue":
                    flags["vue"] = True
                if fw == "react":
                    flags["react"] = True
                if fw == "jsf":
                    flags["jsf"] = True
                for h in hits[:2]:
                    evidence.append(f"bundle[{fw}]:{h.split('?')[0][-80:]}")

        # A1 + A2 + A4: in-page evaluation
        page_signals = self._page_eval()
        for k, v in page_signals.items():
            if k == "evidence":
                evidence.extend(v)
                continue
            if k == "angular_version" and v and not flags["angular_version"]:
                flags["angular_version"] = v
                continue
            if k in flags and v:
                flags[k] = v
            else:
                flags.setdefault(k, v)

        flags["custom_components"] = page_signals.get("custom_components", [])
        flags["shadow_dom_count"] = page_signals.get("shadow_dom_count", 0)
        flags["iframe_count"] = page_signals.get("iframe_count", 0)
        flags["dom_size"] = page_signals.get("dom_size", 0)
        flags["max_depth"] = page_signals.get("max_depth", 0)
        flags["interactive_elements"] = page_signals.get("interactive_elements", 0)
        flags["form_count"] = page_signals.get("form_count", 0)

        flags["primary"] = self._pick_primary(flags)
        flags["evidence"] = evidence
        # Hotfix BUG 6: cache result iff page evaluation didn't fail
        # (page_eval_failed shows up in evidence on a closed page).
        page_failed = any("page_eval_failed" in e for e in evidence)
        if not page_failed and flags["primary"] != "unknown":
            self._last_detection = dict(flags)
        elif page_failed and self._last_detection is not None:
            cached = dict(self._last_detection)
            cached.setdefault("evidence", []).append(
                "page_eval_failed_at_finalize: served from cache")
            return cached
        return flags

    # ------------------------------------------------------------------
    def _analyze_bundles(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {fw: [] for fw in _BUNDLE_SIGNATURES}
        for url in self._bundles_seen:
            low = url.lower()
            for fw, patterns in _BUNDLE_SIGNATURES.items():
                for p in patterns:
                    if re.search(p, low):
                        out[fw].append(url)
                        break
        return out

    def _page_eval(self) -> dict:
        """A1 + A2 + A4 inside one page.evaluate to minimize roundtrips."""
        js = """
        () => {
          const evidence = [];
          // A1 — window.*
          const hasNg = !!(window.ng || window.getAllAngularRootElements);
          const hasVue = !!window.Vue;
          const hasReact = !!(window.React || window.ReactDOM);
          const hasPF = !!(window.PrimeFaces);
          const hasZone = !!window.Zone;
          if (hasNg) evidence.push('window.ng present');
          if (hasVue) evidence.push('window.Vue present');
          if (hasReact) evidence.push('window.React present');
          if (hasPF) evidence.push('window.PrimeFaces present');
          if (hasZone) evidence.push('Zone.js present');

          // A2 — DOM markers
          const ngVerEl = document.querySelector('[ng-version]');
          const ngVersion = ngVerEl ? ngVerEl.getAttribute('ng-version') : null;
          if (ngVersion) evidence.push('[ng-version=' + ngVersion + ']');
          const matFormField = document.querySelectorAll('mat-form-field').length;
          const matSelect = document.querySelectorAll('mat-select').length;
          const matAny = matFormField + matSelect + document.querySelectorAll('[class*="mat-mdc-"]').length;
          if (matAny) evidence.push('Angular Material markers x' + matAny);
          const pfWidget = document.querySelectorAll('.ui-widget,[class*="ui-selectonemenu"],[class*="ui-dropdown"]').length;
          if (pfWidget) evidence.push('PrimeFaces ui-widget x' + pfWidget);
          const muiAny = document.querySelectorAll('[class*="MuiSelect"],[class*="MuiButton"],[class*="MuiInputBase"]').length;
          if (muiAny) evidence.push('MUI Mui* markers x' + muiAny);
          const jsfAny = document.querySelectorAll('[id*="j_idt"]').length;
          if (jsfAny) evidence.push('JSF j_idt markers x' + jsfAny);

          // A4 — custom elements
          const std = new Set([
            'html','head','body','div','span','p','a','button','input',
            'select','option','textarea','form','label','img','ul','ol',
            'li','table','tr','td','th','thead','tbody','tfoot','h1','h2',
            'h3','h4','h5','h6','header','footer','nav','main','section',
            'article','aside','iframe','br','hr','script','style','link',
            'meta','title','code','pre','strong','em','b','i','u','small',
            'video','audio','canvas','svg','path','g','rect','circle',
            'fieldset','legend','datalist','details','summary','dialog',
            'figcaption','figure','picture','source','track','time','mark',
            'abbr','address','blockquote','cite','del','dfn','ins','kbd',
            'q','samp','sub','sup','var','wbr','noscript','template',
            'object','embed','param','menu','menuitem'
          ]);
          const customCounts = {};
          document.querySelectorAll('*').forEach(el => {
            const tag = el.tagName.toLowerCase();
            if (tag.includes('-') && !std.has(tag)) {
              customCounts[tag] = (customCounts[tag] || 0) + 1;
            }
          });
          const customList = Object.keys(customCounts)
            .sort((a,b) => customCounts[b] - customCounts[a])
            .slice(0, 25);
          if (customList.length) {
            evidence.push('custom elements: ' + customList.slice(0,5).join(', '));
          }

          // Page complexity
          let maxDepth = 0;
          (function walk(node, d){
            if (d > maxDepth) maxDepth = d;
            for (let c = node.firstElementChild; c; c = c.nextElementSibling) walk(c, d+1);
          })(document.documentElement, 0);

          const shadowCount = document.querySelectorAll('*').length
            ? Array.from(document.querySelectorAll('*')).filter(el => el.shadowRoot).length
            : 0;

          return {
            angular: hasNg || !!ngVersion,
            angular_version: ngVersion,
            vue: hasVue,
            react: hasReact,
            primefaces: hasPF || (pfWidget > 0) || (jsfAny > 0),
            mui: muiAny > 0,
            jsf: jsfAny > 0,
            angular_material: matAny > 0,
            zone_js: hasZone,
            custom_components: customList,
            shadow_dom_count: shadowCount,
            iframe_count: document.querySelectorAll('iframe').length,
            dom_size: document.querySelectorAll('*').length,
            max_depth: maxDepth,
            interactive_elements: document.querySelectorAll(
              'a,button,input,select,textarea,[role="button"],[role="link"],[tabindex]'
            ).length,
            form_count: document.querySelectorAll('form').length,
            evidence: evidence
          };
        }
        """
        try:
            return self._page.evaluate(js)
        except Exception as exc:
            logger.warning("FrameworkDetector page eval failed: %s", exc)
            return {"evidence": [f"page_eval_failed: {exc}"], "custom_components": []}

    @staticmethod
    def _pick_primary(flags: dict) -> str:
        # Order of precedence: angular_material > angular > primefaces > mui >
        #                      react > vue > jsf > custom > unknown
        if flags.get("angular_material"):
            return "angular-material"
        if flags.get("angular_version") or flags.get("angular"):
            return "angular"
        if flags.get("primefaces"):
            return "primefaces"
        if flags.get("mui"):
            return "mui"
        if flags.get("react"):
            return "react"
        if flags.get("vue"):
            return "vue"
        if flags.get("jsf"):
            return "jsf"
        if flags.get("custom_components"):
            return "custom"
        return "unknown"
