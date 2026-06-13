/**
 * TestForge — Event Recorder Injection Script
 * Captures all user interactions with multi-selector strategy.
 * Injected via page.add_init_script() by js_recorder.py
 */
(function () {
  if (window.__testforge_initialized__) return;
  window.__testforge_initialized__ = true;

  const events = [];
  const startTime = Date.now();

  // ── Utility: generate all 5 selector types for an element ──────────────────
  function getSelectors(el) {
    const selectors = {};

    // 1. data-testid / data-cy / data-qa
    const testId =
      el.getAttribute("data-testid") ||
      el.getAttribute("data-cy") ||
      el.getAttribute("data-qa") ||
      el.getAttribute("data-test");
    if (testId) {
      const attr = el.hasAttribute("data-testid")
        ? "data-testid"
        : el.hasAttribute("data-cy")
        ? "data-cy"
        : el.hasAttribute("data-qa")
        ? "data-qa"
        : "data-test";
      selectors.data_testid = `[${attr}="${testId}"]`;
    }

    // 2. ARIA / accessibility selector
    const role = el.getAttribute("role");
    const ariaLabel =
      el.getAttribute("aria-label") ||
      el.getAttribute("aria-labelledby");
    const name = el.getAttribute("name");
    const id = el.getAttribute("id");
    if (ariaLabel) {
      selectors.aria = role
        ? `[role="${role}"][aria-label="${ariaLabel}"]`
        : `[aria-label="${ariaLabel}"]`;
    } else if (id) {
      selectors.aria = `#${CSS.escape(id)}`;
    } else if (role && name) {
      selectors.aria = `[role="${role}"][name="${name}"]`;
    }

    // 3. Text-based selector (for buttons, links, labels)
    const textContent = (el.textContent || "").trim().slice(0, 60);
    const tag = el.tagName.toLowerCase();
    if (
      textContent &&
      ["button", "a", "label", "h1", "h2", "h3", "span", "p", "li"].includes(tag)
    ) {
      selectors.text = `text=${textContent}`;
    } else if (el.getAttribute("placeholder")) {
      selectors.text = `[placeholder="${el.getAttribute("placeholder")}"]`;
    } else if (el.getAttribute("value") && tag === "input") {
      selectors.text = `[value="${el.getAttribute("value")}"]`;
    }

    // 4. CSS path
    selectors.css = getCssPath(el);

    // 5. XPath
    selectors.xpath = getXPath(el);

    return selectors;
  }

  function getCssPath(el) {
    const parts = [];
    let current = el;
    while (current && current !== document.body) {
      let selector = current.tagName.toLowerCase();
      if (current.id) {
        selector += `#${CSS.escape(current.id)}`;
        parts.unshift(selector);
        break;
      }
      if (current.className) {
        const classes = Array.from(current.classList)
          .filter((c) => !c.match(/^(active|hover|focus|selected|disabled|ng-|v-|js-)/))
          .slice(0, 2);
        if (classes.length) selector += "." + classes.join(".");
      }
      const siblings = current.parentElement
        ? Array.from(current.parentElement.children).filter(
            (c) => c.tagName === current.tagName
          )
        : [];
      if (siblings.length > 1) {
        const idx = siblings.indexOf(current) + 1;
        selector += `:nth-of-type(${idx})`;
      }
      parts.unshift(selector);
      current = current.parentElement;
    }
    return parts.join(" > ") || el.tagName.toLowerCase();
  }

  function getXPath(el) {
    // Relative XPath using text when available
    const text = (el.textContent || "").trim().slice(0, 40);
    if (text && ["button", "a", "label"].includes(el.tagName.toLowerCase())) {
      return `//${el.tagName.toLowerCase()}[contains(text(),'${text.replace(/'/g, "\\'")}')]`;
    }
    // Absolute XPath fallback
    const parts = [];
    let current = el;
    while (current && current.nodeType === Node.ELEMENT_NODE) {
      let index = 1;
      let sibling = current.previousElementSibling;
      while (sibling) {
        if (sibling.tagName === current.tagName) index++;
        sibling = sibling.previousElementSibling;
      }
      parts.unshift(`${current.tagName.toLowerCase()}[${index}]`);
      current = current.parentElement;
    }
    return "/" + parts.join("/");
  }

  // ── Utility: detect if element is in iframe ─────────────────────────────────
  function getIframeInfo(el) {
    try {
      if (window.self !== window.top) {
        return { in_iframe: true, iframe_src: document.location.href };
      }
    } catch (e) {
      return { in_iframe: true, iframe_src: "cross-origin" };
    }
    return { in_iframe: false, iframe_src: null };
  }

  // ── Utility: detect shadow DOM ──────────────────────────────────────────────
  function getShadowInfo(el) {
    let host = el.getRootNode();
    if (host instanceof ShadowRoot) {
      return {
        in_shadow: true,
        shadow_host: getCssPath(host.host),
      };
    }
    return { in_shadow: false, shadow_host: null };
  }

  // ── Utility: element context (parent text, siblings) ───────────────────────
  function getContext(el) {
    const parent = el.parentElement;
    return {
      parent_tag: parent ? parent.tagName.toLowerCase() : null,
      parent_text: parent ? (parent.textContent || "").trim().slice(0, 80) : null,
      element_tag: el.tagName.toLowerCase(),
      element_type: el.getAttribute("type") || null,
      element_text: (el.textContent || "").trim().slice(0, 80),
      element_placeholder: el.getAttribute("placeholder") || null,
      element_name: el.getAttribute("name") || null,
      element_id: el.getAttribute("id") || null,
      element_class: el.className || null,
      visible_label: getVisibleLabel(el),
    };
  }

  function getVisibleLabel(el) {
    const id = el.getAttribute("id");
    if (id) {
      const label = document.querySelector(`label[for="${id}"]`);
      if (label) return (label.textContent || "").trim();
    }
    const ariaLabel = el.getAttribute("aria-label");
    if (ariaLabel) return ariaLabel;
    const parent = el.closest("label");
    if (parent) return (parent.textContent || "").trim().slice(0, 60);
    return null;
  }

  // ── Record event ────────────────────────────────────────────────────────────
  function record(type, el, extra = {}) {
    if (!el || el === document.body || el === document.documentElement) return;

    const event = {
      id: events.length,
      type,
      timestamp_ms: Date.now() - startTime,
      url: window.location.href,
      page_title: document.title,
      selectors: getSelectors(el),
      context: getContext(el),
      iframe: getIframeInfo(el),
      shadow: getShadowInfo(el),
      ...extra,
    };

    // Deduplicate rapid repeat events on same element
    const last = events[events.length - 1];
    if (
      last &&
      last.type === type &&
      last.selectors.css === event.selectors.css &&
      event.timestamp_ms - last.timestamp_ms < 100
    ) {
      return;
    }

    events.push(event);

    // Expose as global for Python to retrieve
    window.__testforge_events__ = events;
  }

  // ── Event listeners ─────────────────────────────────────────────────────────
  document.addEventListener(
    "click",
    (e) => {
      record("click", e.target);
    },
    { capture: true, passive: true }
  );

  document.addEventListener(
    "input",
    (e) => {
      record("input", e.target, {
        value: e.target.value,
        input_type: e.target.type || "text",
      });
    },
    { capture: true, passive: true }
  );

  document.addEventListener(
    "change",
    (e) => {
      const val =
        e.target.type === "checkbox" || e.target.type === "radio"
          ? e.target.checked
          : e.target.value;
      record("change", e.target, { value: val, input_type: e.target.type });
    },
    { capture: true, passive: true }
  );

  document.addEventListener(
    "submit",
    (e) => {
      record("submit", e.target, {
        form_action: e.target.action || null,
        form_method: e.target.method || "get",
      });
    },
    { capture: true, passive: true }
  );

  // Throttled scroll
  let lastScroll = 0;
  document.addEventListener(
    "scroll",
    (e) => {
      const now = Date.now();
      if (now - lastScroll < 500) return;
      lastScroll = now;
      record("scroll", document.body, {
        scroll_x: window.scrollX,
        scroll_y: window.scrollY,
      });
    },
    { capture: true, passive: true }
  );

  // Key presses (Enter/Tab/Escape only — avoid logging typed text twice)
  document.addEventListener(
    "keydown",
    (e) => {
      if (["Enter", "Tab", "Escape", "ArrowDown", "ArrowUp"].includes(e.key)) {
        record("keydown", e.target, { key: e.key });
      }
    },
    { capture: true, passive: true }
  );

  // Navigation / URL changes (SPA support)
  const origPushState = history.pushState;
  history.pushState = function (...args) {
    origPushState.apply(this, args);
    events.push({
      id: events.length,
      type: "navigation",
      timestamp_ms: Date.now() - startTime,
      url: window.location.href,
      page_title: document.title,
      selectors: {},
      context: {},
    });
    window.__testforge_events__ = events;
  };

  window.addEventListener("popstate", () => {
    events.push({
      id: events.length,
      type: "navigation",
      timestamp_ms: Date.now() - startTime,
      url: window.location.href,
      page_title: document.title,
      selectors: {},
      context: {},
    });
    window.__testforge_events__ = events;
  });

  console.log("[TestForge] Recorder initialized ✓");
  window.__testforge_events__ = events;
})();
