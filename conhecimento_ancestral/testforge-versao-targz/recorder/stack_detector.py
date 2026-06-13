"""
TestForge — Stack Detector
Fingerprints the frontend technology stack by inspecting the live DOM.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import logging

log = logging.getLogger("testforge.stack_detector")


@dataclass
class StackInfo:
    name: str
    version: Optional[str]
    category: str          # "modern_spa" | "legacy" | "ssr" | "unknown"
    has_shadow_dom: bool
    has_iframes: bool
    notes: list[str]


DETECTION_SCRIPT = """
(function() {
  const info = {
    frameworks: [],
    has_shadow_dom: false,
    has_iframes: false,
    notes: []
  };

  // React
  const reactRoot = document.querySelector('[data-reactroot], #root, #app');
  if (reactRoot && (reactRoot._reactFiber || reactRoot.__reactFiber$ ||
      Object.keys(reactRoot).some(k => k.startsWith('__reactFiber') ||
                                       k.startsWith('__reactInternalInstance')))) {
    info.frameworks.push({name: 'react', version: window.React?.version || null});
  }
  if (window.__NEXT_DATA__) {
    info.frameworks.push({name: 'nextjs', version: null});
  }

  // Vue
  const vueEl = document.querySelector('[data-v-app], #app');
  if (vueEl && vueEl.__vue_app__) {
    info.frameworks.push({name: 'vue3', version: vueEl.__vue_app__.version || null});
  } else if (window.Vue || document.querySelector('[data-v-]')) {
    info.frameworks.push({name: 'vue2', version: window.Vue?.version || null});
  }
  if (window.__nuxt__) {
    info.frameworks.push({name: 'nuxtjs', version: null});
  }

  // Angular
  const ngVersion = document.querySelector('[ng-version]');
  if (ngVersion) {
    info.frameworks.push({name: 'angular', version: ngVersion.getAttribute('ng-version')});
  } else if (window.angular) {
    info.frameworks.push({name: 'angularjs', version: window.angular.version?.full || null});
  }

  // Svelte
  if (document.querySelector('[class*="svelte-"]')) {
    info.frameworks.push({name: 'svelte', version: null});
  }

  // jQuery
  if (window.jQuery || window.$?.fn?.jquery) {
    info.frameworks.push({name: 'jquery', version: window.jQuery?.fn?.jquery || null});
    info.notes.push('legacy_jquery');
  }

  // AJAX patterns
  if (window.XMLHttpRequest && !window.fetch) {
    info.notes.push('xhr_only');
  }

  // Bootstrap
  if (window.bootstrap || window.$.fn?.modal) {
    info.notes.push('bootstrap');
  }

  // Shadow DOM detection
  const allEls = document.querySelectorAll('*');
  for (let el of allEls) {
    if (el.shadowRoot) {
      info.has_shadow_dom = true;
      break;
    }
  }

  // iFrame detection
  info.has_iframes = document.querySelectorAll('iframe').length > 0;

  // SSR hints
  if (document.querySelector('meta[name="generator"]')) {
    const gen = document.querySelector('meta[name="generator"]').content;
    info.notes.push('generator:' + gen);
  }

  return info;
})()
"""


def detect_stack(page) -> StackInfo:
    """Run fingerprinting script on the page and return StackInfo."""
    try:
        result = page.evaluate(DETECTION_SCRIPT)
    except Exception as e:
        log.warning(f"Stack detection failed: {e}")
        return StackInfo("unknown", None, "unknown", False, False, [])

    frameworks = result.get("frameworks", [])
    notes = result.get("notes", [])
    has_shadow = result.get("has_shadow_dom", False)
    has_iframes = result.get("has_iframes", False)

    if not frameworks:
        # Fallback: check title / meta tags
        title = page.title()
        url = page.url
        name = "html_vanilla"
        category = "legacy" if "legacy_jquery" in notes else "ssr"
    else:
        fw = frameworks[0]
        name = fw["name"]
        version = fw.get("version")

        modern = {"react", "nextjs", "vue2", "vue3", "nuxtjs", "angular", "svelte"}
        legacy = {"jquery", "angularjs"}

        if name in modern:
            category = "modern_spa"
        elif name in legacy:
            category = "legacy"
        else:
            category = "ssr"

        stack = StackInfo(
            name=name,
            version=version,
            category=category,
            has_shadow_dom=has_shadow,
            has_iframes=has_iframes,
            notes=notes + [f"{f['name']}:{f.get('version','?')}" for f in frameworks[1:]],
        )
        log.info(f"Detected stack: {stack.name} v{stack.version} [{stack.category}]")
        return stack

    return StackInfo(name, None, category, has_shadow, has_iframes, notes)
