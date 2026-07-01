// TestForge Recorder Overlay — injected into page via add_init_script
// Captures user interactions, assert mode, keyboard shortcuts, postback detection
// Identity attributes only (no CSS path generation — Playwright compiler handles locators)

(function() {
  "use strict";

  // ---- Sprint P: finder.js (antonmedv/finder MIT) bundled inline ----
  // Generates minimum unique CSS selector. Replaces naive cssParts DOM walk.
  // Sprint P fix: exclude Angular/framework RUNTIME STATE classes — they are
  // volatile (change between record and replay) and produce unstable selectors.
  var _VOLATILE_CLASS_RE = /^(ng-|mat-calendar-body-active|mat-calendar-body-today|mat-calendar-body-selected|mat-focus-indicator|mat-ripple|cdk-|focused|active|selected|hover|disabled|invalid|valid|pristine|dirty|touched|untouched|open|closed|expanded|collapsed)/;
  var _tfFinder = (function() {
    var _acceptedAttrNames = new Set(['role', 'name', 'aria-label', 'rel', 'href']);
    function _finderAttr(name, value) {
      var nameOk = _acceptedAttrNames.has(name) || (name.startsWith('data-') && _wordLike(name));
      var valueOk = (_wordLike(value) && value.length < 100) || (value.startsWith('#') && _wordLike(value.slice(1)));
      return nameOk && valueOk;
    }
    function _wordLike(name) {
      // Reject volatile runtime-state class names
      if (_VOLATILE_CLASS_RE.test(name)) return false;
      if (/^[a-z\-]{3,}$/i.test(name)) {
        var words = name.split(/-|[A-Z]/);
        for (var wi = 0; wi < words.length; wi++) {
          if (words[wi].length <= 2 || /[^aeiou]{4,}/i.test(words[wi])) return false;
        }
        return true;
      }
      return false;
    }
    function _tie(element, config) {
      var level = [];
      var elementId = element.getAttribute('id');
      if (elementId && config.idName(elementId)) level.push({ name: '#' + CSS.escape(elementId), penalty: 0 });
      for (var ci = 0; ci < element.classList.length; ci++) {
        var cn = element.classList[ci];
        if (config.className(cn)) level.push({ name: '.' + CSS.escape(cn), penalty: 1 });
      }
      for (var ai = 0; ai < element.attributes.length; ai++) {
        var a = element.attributes[ai];
        if (config.attr(a.name, a.value)) level.push({ name: '[' + CSS.escape(a.name) + '="' + CSS.escape(a.value) + '"]', penalty: 2 });
      }
      var tName = element.tagName.toLowerCase();
      if (config.tagName(tName)) {
        level.push({ name: tName, penalty: 5 });
        var idx = _indexOf(element, tName);
        if (idx !== undefined) level.push({ name: tName + ':nth-of-type(' + idx + ')', penalty: 10 });
      }
      var nth = _indexOf(element);
      if (nth !== undefined) level.push({ name: tName + ':nth-child(' + nth + ')', penalty: 50 });
      return level;
    }
    function _indexOf(input, tName) {
      var parent = input.parentNode;
      if (!parent) return undefined;
      var child = parent.firstChild;
      if (!child) return undefined;
      var i = 0;
      while (child) {
        if (child.nodeType === Node.ELEMENT_NODE && (tName === undefined || child.tagName.toLowerCase() === tName)) i++;
        if (child === input) break;
        child = child.nextSibling;
      }
      return i;
    }
    function _selectorStr(path) {
      var node = path[0];
      var query = node.name;
      for (var i = 1; i < path.length; i++) {
        var lv = path[i].level || 0;
        query = node.level === lv - 1 ? path[i].name + ' > ' + query : path[i].name + ' ' + query;
        node = path[i];
      }
      return query;
    }
    function _penaltySum(path) { return path.reduce(function(acc, n) { return acc + n.penalty; }, 0); }
    function _byPenalty(a, b) { return _penaltySum(a) - _penaltySum(b); }
    function _unique(path, root) {
      var css = _selectorStr(path);
      switch (root.querySelectorAll(css).length) {
        case 0: throw new Error('No node: ' + css);
        case 1: return true;
        default: return false;
      }
    }
    function* _combinations(stack, path) {
      path = path || [];
      if (stack.length > 0) {
        for (var ni = 0; ni < stack[0].length; ni++) yield* _combinations(stack.slice(1), path.concat(stack[0][ni]));
      } else {
        yield path;
      }
    }
    function* _search(input, config, root) {
      var stack = [], paths = [], current = input, i = 0;
      while (current && current !== root) {
        var level = _tie(current, config);
        for (var li = 0; li < level.length; li++) level[li].level = i;
        stack.push(level);
        current = current.parentElement;
        i++;
        paths.push(..._combinations(stack));
        if (i >= config.seedMinLength) {
          paths.sort(_byPenalty);
          for (var pi = 0; pi < paths.length; pi++) yield paths[pi];
          paths = [];
        }
      }
      paths.sort(_byPenalty);
      for (var pi2 = 0; pi2 < paths.length; pi2++) yield paths[pi2];
    }
    function* _optimize(path, input, config, root, startTime) {
      if (path.length > 2 && path.length > config.optimizedMinLength) {
        for (var i = 1; i < path.length - 1; i++) {
          if (new Date().getTime() - startTime.getTime() > config.timeoutMs) return;
          var np = path.slice();
          np.splice(i, 1);
          if (_unique(np, root) && root.querySelector(_selectorStr(np)) === input) {
            yield np;
            yield* _optimize(np, input, config, root, startTime);
          }
        }
      }
    }
    function _findRootDoc(rootNode, defaults, input) {
      var sr = input.getRootNode && input.getRootNode();
      if (sr && sr.constructor && sr.constructor.name === 'ShadowRoot') return sr;
      if (rootNode.nodeType === Node.DOCUMENT_NODE) return rootNode;
      if (rootNode === defaults.root) return rootNode.ownerDocument;
      return rootNode;
    }
    function finder(input, options) {
      if (!input || input.nodeType !== Node.ELEMENT_NODE) throw new Error('Not an element');
      if (input.tagName.toLowerCase() === 'html') return 'html';
      var defaults = { root: document.body, idName: _wordLike, className: _wordLike, tagName: function() { return true; }, attr: _finderAttr, timeoutMs: 1000, seedMinLength: 3, optimizedMinLength: 2, maxNumberOfPathChecks: Infinity };
      var config = Object.assign({}, defaults, options || {});
      var startTime = new Date();
      var root = _findRootDoc(config.root, defaults, input);
      var foundPath, count = 0;
      for (var cand of _search(input, config, root)) {
        if (new Date().getTime() - startTime.getTime() > config.timeoutMs || count >= config.maxNumberOfPathChecks) {
          throw new Error('Timeout');
        }
        count++;
        if (_unique(cand, root)) { foundPath = cand; break; }
      }
      if (!foundPath) throw new Error('Selector not found');
      var optimized = [..._optimize(foundPath, input, config, root, startTime)];
      optimized.sort(_byPenalty);
      return _selectorStr(optimized.length > 0 ? optimized[0] : foundPath);
    }
    return finder;
  })();

  // ---- State Init ----
  window.__tfEventQueue = window.__tfEventQueue || [];
  window.__tfStepQueue = window.__tfStepQueue || [];
  window.__tfCommandQueue = window.__tfCommandQueue || [];
  window.__tfFieldSnapshotQueue = window.__tfFieldSnapshotQueue || [];
  window.__tfValueMutationQueue = window.__tfValueMutationQueue || [];
  window.__tfEventCounter = window.__tfEventCounter || 0;
  window.__tfAssertWaiting = false;
  window.__tfDragMode = false;
  window.__tfDragState = null;
  window.__tfPendingSubmit = null;
  window.__tfLastFillValue = {};
  window.__tfLastSnapshotKey = {};
  window.__tfFillDebounceTimers = window.__tfFillDebounceTimers || new WeakMap();
  // Hotfix 22: era 400ms; digitacao humana em campo currencymask (SIOPI) pausa
  // ~500-700ms entre digitos enquanto Angular formatta -> a cada pausa disparava
  // fill separado (0,01 -> 10 -> 100 -> 1000 = 4 fills). Sobe pra 800ms so o
  // burst final fica. Blur/change tambem forcam flush (change listener em 1133).
  window.__tfFillDebounceMs = 800;
  // Sprint L (2026-06-30): keystroke buffer por target. Captura keydown
  // raw como ground-truth do digitado, bypassa setter hook + mask. Diferente
  // do value_mutations (que so vê o resultado pos-mask), aqui temos a
  // sequencia exata de teclas — backspace, dead keys, ctrl+a, etc.
  // Reconstrucao do valor final fica em normalizer._ir_keystroke_buffer.
  window.__tfKeystrokeQueue = window.__tfKeystrokeQueue || [];
  // Sprint R: rrweb-lite DOM mutation timeline. Lightweight MutationObserver-based
  // replay recorder. Format compatible with rrweb incremental snapshots (type=3).
  // Used as tiebreaker for ambiguous steps in normalizer.
  window.__tfRrwebQueue = window.__tfRrwebQueue || [];

  // ---- Cross-page state restoration ----
  try {
    var storedPending = sessionStorage.getItem('__tfPendingSubmit');
    if (storedPending) {
      window.__tfPendingSubmit = JSON.parse(storedPending);
      sessionStorage.removeItem('__tfPendingSubmit');
    }
  } catch(_e) {}

  try {
    var unflushedEvents = sessionStorage.getItem('__tfUnflushedEvents');
    if (unflushedEvents) {
      var evts = JSON.parse(unflushedEvents);
      if (window.__tfPendingSubmit) {
        for (var i = 0; i < evts.length; i++) {
          if (evts[i].type === 'submit') {
            evts[i].is_postback = true;
            evts[i].submit_method = evts[i].submit_method || window.__tfPendingSubmit.method;
            evts[i].postback_url = window.__tfPendingSubmit.url;
          }
        }
      }
      window.__tfEventQueue = evts;
      sessionStorage.removeItem('__tfUnflushedEvents');
    }
    var unflushedSteps = sessionStorage.getItem('__tfUnflushedSteps');
    if (unflushedSteps) {
      window.__tfStepQueue = JSON.parse(unflushedSteps);
      sessionStorage.removeItem('__tfUnflushedSteps');
    }
  } catch(_e) {}

  // ---- Target extraction (identity attributes only) ----
  // Shadow DOM walker (B14/B17). When the element lives inside an open
  // shadow root, record the host's CSS selector so the runner can do
  // `page.locator(host).locator(child)` instead of blind-piercing.
  // Closed shadow roots cannot be walked from outside — flagged but
  // not resolved.
  function _findShadowHost(el) {
    if (!el) return null;
    var cur = el;
    while (cur) {
      var root = cur.getRootNode && cur.getRootNode();
      if (root && root !== document && root.host) {
        // Open shadow root: root.host is the shadow host element.
        var host = root.host;
        var sel = host.tagName.toLowerCase();
        if (host.id) sel += '#' + host.id;
        else if (typeof host.className === 'string' && host.className.trim()) {
          var firstClass = host.className.trim().split(/\s+/)[0];
          if (firstClass && !firstClass.startsWith('tf-')) sel += '.' + firstClass;
        }
        return {
          host_selector: sel,
          host_tag: host.tagName.toLowerCase(),
          host_id: host.id || null,
          mode: root.mode || 'open',
        };
      }
      cur = cur.parentNode || (cur.host || null);
      if (cur === document) return null;
    }
    return null;
  }

  // Sprint O: ACCNAME 1.2 subset — generalizes accessible name for any framework.
  // Replaces Material-only _extractMaterialFieldLabel.
  // Priority: aria-labelledby > aria-label > label[for] / wrapping label >
  //           framework wrapper label (mat-label, .v-label, .p-float-label, MUI, etc) > title.
  function _computeAccessibleName(el) {
    if (!el) return null;
    // 1. aria-labelledby (highest priority per ACCNAME)
    var lby = el.getAttribute && el.getAttribute('aria-labelledby');
    if (lby) {
      var ids = lby.trim().split(/\s+/);
      var parts = [];
      for (var li = 0; li < ids.length; li++) {
        var ref = document.getElementById(ids[li]);
        if (ref) { var t = (ref.textContent || '').trim(); if (t) parts.push(t); }
      }
      if (parts.length) return parts.join(' ').substring(0, 200);
    }
    // 2. aria-label
    var al = el.getAttribute && el.getAttribute('aria-label');
    if (al && al.trim()) return al.trim().substring(0, 200);
    // 3. label[for=id]
    if (el.id) {
      var lf = document.querySelector('label[for="' + CSS.escape(el.id) + '"]');
      if (lf) { var lt = (lf.textContent || '').trim(); if (lt) return lt.substring(0, 200); }
    }
    // 4. Wrapping <label>
    var cur = el.parentElement;
    var hops = 0;
    while (cur && cur !== document.body && hops < 6) {
      if (cur.tagName === 'LABEL') {
        var wt = (cur.textContent || '').replace((el.value || ''), '').trim();
        if (wt) return wt.substring(0, 200);
      }
      cur = cur.parentElement;
      hops++;
    }
    // 5. Framework wrapper label (Angular Material, MUI, Vuetify, PrimeVue, etc.)
    var WRAPPER_SELECTORS = [
      'mat-form-field', '.mat-form-field', '.mat-mdc-form-field',  // Angular Material
      '.MuiFormControl-root', '.MuiTextField-root',                 // MUI
      '.v-input', '.v-field',                                       // Vuetify
      '.p-float-label', '.p-field',                                 // PrimeVue
      '.field', '.form-group', '.form-field',                       // generic
    ];
    var LABEL_SELECTORS = [
      'mat-label', '.mat-form-field-label', '.mat-mdc-form-field-label',
      '.MuiInputLabel-root', '.v-label', 'legend', 'label',
    ];
    cur = el.parentElement;
    hops = 0;
    while (cur && cur !== document.body && hops < 10) {
      var curTag = (cur.tagName || '').toLowerCase();
      var isWrapper = WRAPPER_SELECTORS.some(function(sel) {
        try { return cur.matches(sel); } catch(_e) { return false; }
      });
      if (isWrapper || curTag === 'fieldset') {
        for (var si = 0; si < LABEL_SELECTORS.length; si++) {
          try {
            var labelEl = cur.querySelector(LABEL_SELECTORS[si]);
            if (labelEl) {
              var txt = (labelEl.textContent || '').trim();
              if (txt) return txt.substring(0, 200);
            }
          } catch(_e) {}
        }
        break;
      }
      cur = cur.parentElement;
      hops++;
    }
    // 6. title fallback
    var ti = el.getAttribute && el.getAttribute('title');
    if (ti && ti.trim()) return ti.trim().substring(0, 200);
    return null;
  }

  // Sprint J callers expect material_field_label. Fast-path for Angular Material
  // (mat-form-field ancestor walk with hops limit); falls back to _computeAccessibleName
  // (Sprint O ACCNAME superset) for MUI/Vuetify/PrimeFaces/generic.
  function _extractMaterialFieldLabel(el) {
    if (!el) return null;
    var cur = el;
    var hops = 0;
    while (cur && cur !== document.body && cur !== document.documentElement && hops < 8) {
      var tag = (cur.tagName || '').toLowerCase();
      if (tag === 'mat-form-field' || (cur.classList && cur.classList.contains('mat-form-field'))) {
        var matLabel = cur.querySelector('mat-label, .mat-form-field-label, .mat-mdc-form-field-label, label.mat-label');
        if (matLabel) {
          var text = (matLabel.textContent || '').trim();
          if (text) return text.substring(0, 120);
        }
        break;
      }
      cur = cur.parentElement;
      hops += 1;
    }
    // Sprint O: fall through to ACCNAME for non-Material frameworks
    return _computeAccessibleName(el);
  }

  function _extractTarget(el) {
    if (!el || el === document.body || el === document.documentElement) return null;
    var rect = el.getBoundingClientRect ? el.getBoundingClientRect() : {};
    var allAttrs = {};
    if (el.attributes) {
      for (var ai = 0; ai < el.attributes.length; ai++) {
        var attr = el.attributes[ai];
        allAttrs[attr.name] = attr.value;
      }
    }
    var classList = [];
    if (typeof el.className === 'string' && el.className.trim()) {
      classList = el.className.trim().split(/\s+/).filter(function(c) { return c && !c.startsWith('tf-'); });
    }
    var labelEl = el.id ? document.querySelector('label[for="' + el.id + '"]') : null;
    // Hotfix 22: normaliza whitespace (nbsp, tab, multi-space) antes de serializar.
    // DOM contem `R$&nbsp;1.000.000,00` mas expected_value armazena `R$ 1.000.000,00`
    // com espaco regular; runners downstream nao devem se preocupar com essa
    // divergencia — o overlay ja entrega texto canonico.
    var elText = ((el.textContent||'')
      .replace(/ /g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .substring(0, 200)) || null;
    var materialLabel = _extractMaterialFieldLabel(el);
    // Hotfix 22: Angular reactive forms — formControlName eh chave estavel
    // entre runs (diferente de id dinamico como `mat-input-2`). Se presente,
    // vira ancora principal.
    var formControlName = (el.getAttribute && (
      el.getAttribute('formcontrolname') ||
      el.getAttribute('ng-reflect-name') ||
      allAttrs['formcontrolname'] ||
      allAttrs['ng-reflect-name']
    )) || null;
    // Hotfix 22: Angular expoe estado do modelo via `ng-reflect-*`. Extrai
    // pares para o normalizer usar como sinais adicionais (ex.: ng-reflect-model,
    // ng-reflect-required, ng-reflect-disabled, ng-reflect-form).
    var ngReflect = {};
    for (var attrKey in allAttrs) {
      if (attrKey && attrKey.indexOf('ng-reflect-') === 0) {
        var short = attrKey.substring('ng-reflect-'.length);
        if (short && short.length < 40 && allAttrs[attrKey].length < 200) {
          ngReflect[short] = allAttrs[attrKey];
        }
      }
    }
    // Sprint P: finder generates minimum unique CSS selector; fallback to naive walk
    var cssPath = '';
    try {
      cssPath = _tfFinder(el, { seedMinLength: 4 });
    } catch (_fe) {
      var cssParts = [];
      var cur = el;
      while (cur && cur !== document.body && cur !== document.documentElement) {
        var s = (cur.tagName||'').toLowerCase();
        if (cur.id) { s += '#' + cur.id; }
        else if (typeof cur.className === 'string') {
          var firstClass = cur.className.trim().split(/\s+/)[0];
          if (firstClass && !firstClass.startsWith('tf-')) s += '.' + firstClass;
        }
        cssParts.unshift(s);
        cur = cur.parentElement;
      }
      cssPath = cssParts.join(' > ');
    }
    var shadow = _findShadowHost(el);
    var elementId = el.id || null;
    var accessibleName = el.getAttribute('aria-label') || el.getAttribute('title') || (allAttrs['aria-label'] || null);
    var testId = el.getAttribute('data-testid') || el.getAttribute('data-test-id') || null;
    // Hotfix 22: detecta id dinamico Material (mat-input-N, mat-mdc-error-N,
    // mat-select-N, cdk-overlay-N) — o contador N muda entre runs. Marca
    // como low-signal para o compiler nao ancorar nele.
    var idIsDynamic = elementId && /^(mat-(input|mdc-error|option|select|dialog|autocomplete|slider|expansion|checkbox|radio|tab|menu)|cdk-overlay|cdk-drop)-\d+$/.test(elementId);

    // Hotfix 22: capture confidence — score de 0.0..1.0 que reflete quao
    // ancoravel eh o target. Consumido pelo compiler pra priorizar locators.
    // Sinais fortes (id explicito, formControlName, test-id, accessible_name)
    // -> alta; so css_path posicional -> baixa.
    var confidence = 0.3;  // baseline
    if (testId) confidence = Math.max(confidence, 0.95);
    if (formControlName) confidence = Math.max(confidence, 0.9);
    if (elementId && !idIsDynamic) confidence = Math.max(confidence, 0.85);
    if (accessibleName) confidence = Math.max(confidence, 0.8);
    if (el.getAttribute('name')) confidence = Math.max(confidence, 0.7);
    if (labelEl) confidence = Math.max(confidence, 0.7);
    if (el.getAttribute('placeholder')) confidence = Math.max(confidence, 0.55);
    if (materialLabel) confidence = Math.max(confidence, 0.65);

    return {
      tag: (el.tagName||'').toLowerCase(),
      text: elText,
      role: el.getAttribute('role') || null,
      accessible_name: accessibleName,
      element_id: elementId,
      element_id_dynamic: idIsDynamic || false,
      name: el.getAttribute('name') || null,
      form_control_name: formControlName,
      test_id: testId,
      placeholder: el.getAttribute('placeholder') || null,
      label: labelEl ? labelEl.textContent.replace(/ /g, ' ').replace(/\s+/g, ' ').trim() : null,
      class_list: classList,
      attributes: allAttrs,
      type: el.getAttribute('type') || null,
      value: (el.value||'').substring(0,100) || null,
      href: el.getAttribute('href') || null,
      onclick: el.getAttribute('onclick') || null,
      css_path: cssPath || '',
      capture_confidence: Math.round(confidence * 100) / 100,
      ng_reflect: Object.keys(ngReflect).length ? ngReflect : null,
      // Shadow DOM context (B14/B17). Mabl-style "shadow_parent" so the
      // runner can do page.locator(host).locator(child) when the element
      // lives inside an OPEN shadow root. Closed roots can't be walked
      // from outside; expect shadow=null in that case.
      shadow_host: shadow,
      material_field_label: materialLabel
    };
  }

  // ---- Postback / submit detection ----
  function _isSubmitTrigger(el) {
    if (!el) return false;
    var tag = (el.tagName || '').toLowerCase();
    if (tag === 'input' && (el.type === 'submit' || el.type === 'image')) return true;
    if (tag === 'button' && (!el.type || el.type === 'submit')) return true;
    if (tag !== 'a') return false;
    var href = (el.href || el.getAttribute('href') || '').toLowerCase();
    var onclick = (el.getAttribute('onclick') || '').toLowerCase();
    if (href.indexOf('__dopostback') !== -1) return true;
    if (onclick.indexOf('__dopostback') !== -1) return true;
    if (href.indexOf('webform_dopostbackwithoptions') !== -1) return true;
    if (onclick.indexOf('webform_dopostbackwithoptions') !== -1) return true;
    if (href.indexOf('document.forms') !== -1) return true;
    if (onclick.indexOf('document.forms') !== -1) return true;
    return false;
  }

  // ---- Push event to queue ----
  function _pushEvent(type, el) {
    var target = _extractTarget(el || document.activeElement);
    ++window.__tfEventCounter;
    var maskedVal = (el && el.value) ? el.value.substring(0, 200) : null;
    var rawVal = (type === 'fill' || type === 'fill_intermediate') ? _extractRawMaskValue(el) : null;
    window.__tfEventQueue.push({
      type: type,
      timestamp: new Date().toISOString(),
      url: window.location.href,
      page_title: document.title,
      target: target,
      value: maskedVal,
      raw_value: rawVal  // Sprint Q: unmasked value when mask lib detected; null otherwise
    });
  }

  // ---- Field snapshot ----
  function _snapshotFields() {
    var snapshots = [];
    document.querySelectorAll('input, textarea, select').forEach(function(el) {
      var tag = el.tagName.toLowerCase();
      var rect = el.getBoundingClientRect();
      snapshots.push({
        timestamp: new Date().toISOString(),
        fingerprint: tag + '#' + (el.id||'') + '[name=' + (el.name||'') + ']',
        identifiers: {
          id: el.id || null,
          name: el.name || null,
          label: el.labels && el.labels[0] ? el.labels[0].textContent.trim() : null,
          placeholder: el.placeholder || null,
          'aria-label': el.getAttribute('aria-label') || null
        },
        tag: tag,
        type: el.getAttribute('type') || null,
        value: (el.value || '').substring(0, 200),
        raw_value: _extractRawMaskValue(el),  // Sprint Q: unmasked value when mask detected
        checked: (el.type === 'checkbox' || el.type === 'radio') ? el.checked : null,
        visibility: (rect.width > 0 && rect.height > 0) ? 'visible' : 'hidden',
        enabled: !el.disabled
      });
    });
    document.querySelectorAll('[contenteditable="true"], [contenteditable=""]').forEach(function(el) {
      var rect = el.getBoundingClientRect();
      snapshots.push({
        timestamp: new Date().toISOString(),
        fingerprint: 'contenteditable#' + (el.id||''),
        identifiers: {
          id: el.id || null,
          role: el.getAttribute('role') || null,
          'aria-label': el.getAttribute('aria-label') || null
        },
        tag: el.tagName.toLowerCase(),
        type: 'contenteditable',
        value: (el.textContent || '').substring(0, 200),
        checked: null,
        visibility: (rect.width > 0 && rect.height > 0) ? 'visible' : 'hidden',
        enabled: !el.disabled
      });
    });
    document.querySelectorAll('[role="combobox"], [role="listbox"], [role="slider"], [role="spinbutton"], [role="searchbox"], [role="textbox"]').forEach(function(el) {
      if (el.isContentEditable) return;
      if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.tagName === 'SELECT') return;
      var rect = el.getBoundingClientRect();
      var ariaVal = el.getAttribute('aria-valuenow') || el.getAttribute('aria-valuetext') || null;
      snapshots.push({
        timestamp: new Date().toISOString(),
        fingerprint: 'aria-' + (el.getAttribute('role')||'widget') + '#' + (el.id||''),
        identifiers: {
          id: el.id || null,
          role: el.getAttribute('role') || null,
          'aria-label': el.getAttribute('aria-label') || null,
          'aria-labelledby': el.getAttribute('aria-labelledby') || null
        },
        tag: el.tagName.toLowerCase(),
        type: 'aria-' + (el.getAttribute('role') || 'widget'),
        value: ariaVal || (el.textContent || '').substring(0, 200),
        checked: null,
        visibility: (rect.width > 0 && rect.height > 0) ? 'visible' : 'hidden',
        enabled: !el.disabled && el.getAttribute('aria-disabled') !== 'true'
      });
    });
    return snapshots;
  }

  function _captureFinalState(reason) {
    var snapshots = _snapshotFields();
    try {
      sessionStorage.setItem('__tfFinalState', JSON.stringify({
        reason: reason || 'unknown',
        timestamp: new Date().toISOString(),
        url: window.location.href,
        page_title: document.title,
        fields: snapshots
      }));
    } catch(_e) { /* ignore oversized */ }
  }

  // ---- H21: inline value prompt on mask-intercepted typing ----
  // Tracks keystroke counts per <input>/<textarea>. On blur, if the
  // input is empty despite >= 2 keystrokes, the mask almost certainly
  // intercepted the value — ask the user inline so they don't have to
  // recall every masked field at the end via --complete. Source on the
  // resulting field_value_map entry is `user_supplied_inline`.
  (function _h21_install_inline_prompt() {
    var _keystrokeCount = new WeakMap();
    document.addEventListener('keydown', function(e) {
      var el = e.target;
      if (!el) return;
      var tag = (el.tagName || '').toLowerCase();
      if (tag !== 'input' && tag !== 'textarea') return;
      // Skip non-character keys.
      if (e.key && e.key.length === 1) {
        _keystrokeCount.set(el, (_keystrokeCount.get(el) || 0) + 1);
      } else if (e.key === 'Backspace' || e.key === 'Delete') {
        _keystrokeCount.set(el, (_keystrokeCount.get(el) || 0) + 1);
      }
    }, true);
    document.addEventListener('blur', function(e) {
      var el = e.target;
      if (!el) return;
      var tag = (el.tagName || '').toLowerCase();
      if (tag !== 'input' && tag !== 'textarea') return;
      var keys = _keystrokeCount.get(el) || 0;
      if (keys < 2) return;
      var raw_value = '';
      try { raw_value = (el.value || '').trim(); } catch (_e) { raw_value = ''; }
      if (raw_value) { _keystrokeCount.set(el, 0); return; }
      // Empty value after >= 2 keystrokes → mask intercepted. Prompt
      // the user inline.
      var labelEl = el.id ? document.querySelector('label[for="' + el.id + '"]') : null;
      var label = (labelEl && labelEl.textContent && labelEl.textContent.trim())
        || el.getAttribute('aria-label')
        || el.getAttribute('placeholder')
        || el.name
        || el.id
        || tag;
      var typed = '';
      try {
        typed = window.prompt(
          'Valor para "' + label.substring(0, 60) + '" (mascara interceptou):',
          ''
        );
      } catch (_e) { typed = null; }
      _keystrokeCount.set(el, 0);
      if (!typed) return;
      var fingerprint = tag + '#' + (el.id || '') + '[name=' + (el.name || '') + ']';
      if (window.__tfEventQueue) {
        window.__tfEventQueue.push({
          type: 'inline_field_value',
          timestamp: new Date().toISOString(),
          fingerprint: fingerprint,
          label: label.substring(0, 200),
          placeholder: el.getAttribute('placeholder') || '',
          aria_label: el.getAttribute('aria-label') || '',
          element_id: el.id || '',
          name: el.name || '',
          tag: tag,
          value: String(typed).substring(0, 200),
          source: 'user_supplied_inline',
        });
      }
    }, true);
  })();

  // ---- Sprint L: keystroke buffer (ground-truth do digitado) ----
  // Captura toda keydown em campos editaveis com fingerprint do alvo +
  // metadata (key, code, modifiers, inputType). Bypassa setter hook +
  // mask + framework controlled input — keystrokes sao sempre disparados
  // pelo browser independente do que React/Angular/mask fazem depois.
  function _keystrokeFingerprint(el) {
    if (!el || !el.tagName) return "unknown";
    var tag = el.tagName.toLowerCase();
    return tag + "#" + (el.id || "") + "[name=" + (el.name || "") + "]";
  }
  function _isTextEditable(el) {
    if (!el || !el.tagName) return false;
    var tag = el.tagName.toLowerCase();
    if (tag === "input") {
      var t = (el.type || "text").toLowerCase();
      return t !== "checkbox" && t !== "radio" && t !== "hidden"
        && t !== "submit" && t !== "button" && t !== "file";
    }
    return tag === "textarea" || el.isContentEditable === true;
  }
  document.addEventListener("keydown", function(e) {
    if (window.__tfAssertWaiting) return;
    var el = e.target;
    if (!_isTextEditable(el)) return;
    try {
      window.__tfKeystrokeQueue.push({
        timestamp: new Date().toISOString(),
        fingerprint: _keystrokeFingerprint(el),
        key: e.key || "",
        code: e.code || "",
        ctrl: !!e.ctrlKey, meta: !!e.metaKey, alt: !!e.altKey, shift: !!e.shiftKey,
        // length-1 visible char or named key (Backspace, Enter, Tab, Delete, ...)
        kind: (e.key && e.key.length === 1) ? "char" : "named",
        // accessible_name + placeholder + material_field_label permite ao
        // normalizer correlacionar keystrokes ao semantic intent sem precisar
        // re-walking DOM no normalizer time
        accessible_name: (el.getAttribute && (el.getAttribute("aria-label") || "")) || "",
        placeholder: (el.getAttribute && (el.getAttribute("placeholder") || "")) || "",
        url: window.location.href,
      });
      // Cap buffer para evitar OOM em sessoes longas
      if (window.__tfKeystrokeQueue.length > 5000) {
        window.__tfKeystrokeQueue.splice(0, window.__tfKeystrokeQueue.length - 5000);
      }
    } catch(_e) {}
  }, true);

  // ---- Sprint Q: mask raw value extraction ----
  // Detects common mask libs and extracts raw (unmasked) value.
  // Covers ng-currency-mask (Caixa SIOPI: el._mask), Inputmask (RobinHerbots),
  // Cleave.js (el._cleave), IMask (el.imask), data-raw-value attribute.
  // Returns null when no mask detected (caller uses el.value as-is).
  function _extractRawMaskValue(el) {
    if (!el) return null;
    try {
      // ng-currency-mask (Caixa SIOPI) — el._mask with getRawValue()
      if (el._mask && typeof el._mask.getRawValue === 'function') {
        var rv = el._mask.getRawValue();
        if (rv !== null && rv !== undefined) return String(rv);
      }
      // ng-currency-mask fallback — _maskedValue vs value diverge; look for _rawValue
      if (el._rawValue !== undefined && el._rawValue !== null) return String(el._rawValue);
      // Inputmask (RobinHerbots): el.inputmask.unmaskedvalue()
      if (el.inputmask && typeof el.inputmask.unmaskedvalue === 'function') {
        return String(el.inputmask.unmaskedvalue());
      }
      // Cleave.js: el._cleave.getRawValue()
      if (el._cleave && typeof el._cleave.getRawValue === 'function') {
        return String(el._cleave.getRawValue());
      }
      // IMask: el.imask.unmaskedValue
      if (el.imask && el.imask.unmaskedValue !== undefined) {
        return String(el.imask.unmaskedValue);
      }
      // data-raw-value attribute (some custom masks)
      var dRaw = el.getAttribute && (el.getAttribute('data-raw-value') || el.getAttribute('data-unmasked'));
      if (dRaw !== null && dRaw !== undefined && dRaw !== '') return dRaw;

      // Hotfix 22: Angular directive-only mask (ex.: SIOPI Caixa `currencymask=""`
      // sem lib JS). Detecta pela presenca do atributo diretiva e faz parse do
      // valor formatado. Cobre BR (R$ 1.000,00), US ($1,000.00), etc.
      // NAO aplica a inputs DATE (placeholder DD/MM/AAAA, HH:MM etc) — mesmo
      // que tenham atributo `mask`, o parse quebraria "01/01/1968" -> "01011968"
      // e o downstream picker-echo detector nao reconheceria.
      var hasCurrencyDirective = el.getAttribute && (
        el.hasAttribute('currencymask') ||
        el.hasAttribute('currencyMask')
      );
      // `mask` generico apenas se placeholder NAO parecer data/hora
      if (!hasCurrencyDirective && el.getAttribute && el.hasAttribute('mask')) {
        var _ph = el.getAttribute('placeholder') || '';
        var _isDateLike = /^\s*[dDmMaAyYhHsS][dDmMaAyYhHsS\/\-\.:]{4,}/.test(_ph);
        if (!_isDateLike) hasCurrencyDirective = true;
      }
      if (hasCurrencyDirective && typeof el.value === 'string' && el.value.length > 0) {
        var v = el.value.replace(/[^\d,.\-]/g, '');
        // BR format: 1.000,00 -> 1000.00 (dots as thousands, comma as decimal)
        if (v.indexOf(',') !== -1) {
          v = v.replace(/\./g, '').replace(',', '.');
        }
        // Strip trailing/leading noise
        v = v.replace(/^\.+|\.+$/g, '');
        if (v && !isNaN(parseFloat(v))) {
          return v;
        }
      }
    } catch (_e) {}
    return null;
  }

  // ---- Sprint R: rrweb-lite — lightweight DOM mutation timeline ----
  // MutationObserver watching attributes + childList on form-bearing subtrees.
  // Emits rrweb-compatible records (type=3 IncrementalSnapshot, source=0 Mutation).
  // Python side collects __tfRrwebQueue and writes rrweb_events.jsonl.
  (function _sprintR_rrwebLite() {
    var _rrwebSeq = 0;
    function _rrPush(data) {
      try {
        window.__tfRrwebQueue.push({ timestamp: Date.now(), seq: ++_rrwebSeq, data: data });
        if (window.__tfRrwebQueue.length > 2000) window.__tfRrwebQueue.splice(0, 500);
      } catch(_e) {}
    }
    function _elFingerprint(el) {
      if (!el || !el.tagName) return null;
      var tag = el.tagName.toLowerCase();
      return tag + '#' + (el.id || '') + '[name=' + ((el.getAttribute && el.getAttribute('name')) || '') + ']';
    }
    // Watch attribute + value changes on all input/textarea/select
    function _attachValueWatcher(el) {
      if (!el || el.__tfRrwatched) return;
      el.__tfRrwatched = true;
      var lastVal = el.value !== undefined ? el.value : el.textContent;
      function _check() {
        var cur = el.value !== undefined ? el.value : el.textContent;
        if (cur !== lastVal) {
          _rrPush({ type: 3, source: 5 /* Input */, id: _elFingerprint(el), text: String(cur).substring(0, 200), isChecked: el.checked });
          lastVal = cur;
        }
      }
      el.addEventListener('input', _check, true);
      el.addEventListener('change', _check, true);
    }
    function _scanInputs() {
      try {
        document.querySelectorAll('input, textarea, select, [contenteditable]').forEach(_attachValueWatcher);
      } catch(_e) {}
    }
    // MutationObserver for DOM changes (new elements, attribute changes)
    try {
      var _rr_mo = new MutationObserver(function(mutations) {
        for (var mi = 0; mi < mutations.length; mi++) {
          var m = mutations[mi];
          if (m.type === 'childList') {
            m.addedNodes.forEach(function(n) {
              if (n.nodeType !== Node.ELEMENT_NODE) return;
              _rrPush({ type: 3, source: 0 /* Mutation */, adds: [{ tag: (n.tagName||'').toLowerCase(), id: _elFingerprint(n), attrs: { id: n.id || null, class: (n.className || null) } }] });
              n.querySelectorAll && n.querySelectorAll('input, textarea, select').forEach(_attachValueWatcher);
              _attachValueWatcher(n);
            });
            m.removedNodes.forEach(function(n) {
              if (n.nodeType !== Node.ELEMENT_NODE) return;
              _rrPush({ type: 3, source: 0, removes: [{ id: _elFingerprint(n) }] });
            });
          } else if (m.type === 'attributes') {
            var target = m.target;
            var attrVal = target.getAttribute && target.getAttribute(m.attributeName);
            _rrPush({ type: 3, source: 0, attributeName: m.attributeName, attributeValue: attrVal, id: _elFingerprint(target) });
          }
        }
      });
      _rr_mo.observe(document.documentElement, { childList: true, subtree: true, attributes: true, attributeFilter: ['aria-hidden', 'aria-expanded', 'disabled', 'class', 'style', 'value'] });
    } catch(_e) {}
    // Initial scan + periodic rescan for dynamically added inputs
    _scanInputs();
    setInterval(_scanInputs, 2000);
    // Full DOM snapshot marker at start
    _rrPush({ type: 2 /* FullSnapshot */, url: window.location.href });
  })();

  // ---- Value mutation setter hooks ----
  // Bug fix (Sprint A, 2026-06-29): Material currencymask + datepicker use
  // the native value setter directly (el.value = ...) instead of letting the
  // browser dispatch an 'input' event. Pure addEventListener('input') never
  // fires for those fields, so raw_events.jsonl was getting zero fill events
  // for currency / date inputs. The setter hook now also schedules a debounced
  // _pushEvent('fill', el) so those values land in raw_events for the
  // normalizer to pick up. Diagnostic in [[project-recorder-input-capture-gap]].
  function _scheduleFillFromMutation(el) {
    if (!el || !el.tagName) return;
    if (window.__tfAssertWaiting) return;
    if (el.tagName !== 'INPUT' && el.tagName !== 'TEXTAREA') return;
    try {
      var prev = window.__tfFillDebounceTimers.get(el);
      if (prev) clearTimeout(prev);
    } catch(_e) {}
    var t = setTimeout(function() {
      try {
        var key = _fillKey(el);
        var val = (el.value || '').trim();
        if (val === '') return;
        if (window.__tfLastFillValue[key] === val) return;
        window.__tfLastFillValue[key] = val;
        _pushEvent('fill', el);
      } catch(_e) {}
    }, window.__tfFillDebounceMs);
    try { window.__tfFillDebounceTimers.set(el, t); } catch(_e) {}
  }

  function _hookValue(proto) {
    var orig = Object.getOwnPropertyDescriptor(proto, 'value');
    if (!orig || !orig.set) return;
    Object.defineProperty(proto, 'value', {
      get: orig.get,
      set: function(v) {
        // React controlled inputs use _valueTracker (internal SyntheticEvent
        // shadow value) to short-circuit re-renders. If we set value without
        // resetting the tracker, React sees old === new and the onChange
        // handler never fires — meaning the framework state stays stale.
        // Resetting tracker to '' forces React to detect the diff on next
        // render and fire onChange properly. No-op when not on React.
        // Reference: refined-github/set-react-input-value.ts pattern.
        try {
          if (this._valueTracker && typeof this._valueTracker.setValue === 'function') {
            this._valueTracker.setValue('');
          }
        } catch(_e) {}
        orig.set.call(this, v);
        window.__tfValueMutationQueue.push({
          type: 'value_mutation',
          timestamp: new Date().toISOString(),
          fingerprint: this.tagName.toLowerCase() + '#' + (this.id||'') + '[name=' + (this.name||'') + ']',
          value: String(v).substring(0, 200)
        });
        try { _scheduleFillFromMutation(this); } catch(_e) {}
      },
      configurable: true
    });
  }
  _hookValue(HTMLInputElement.prototype);
  _hookValue(HTMLSelectElement.prototype);
  _hookValue(HTMLTextAreaElement.prototype);

  // ---- Periodic snapshot fallback ----
  // Defensive fallback when the setter hook itself is bypassed (e.g. mask
  // composing value via DOM property setter on a wrapped element, or framework
  // dispatching value updates after hookValue but before our debounce can flush).
  // Scans visible input/textarea every 500ms and emits a fill event when the
  // current value differs from the cached last-known value. Dedup via
  // __tfLastFillValue so we never double-emit something the input listener or
  // setter hook already captured.
  window.__tfPeriodicFillScanInterval = window.__tfPeriodicFillScanInterval || null;
  // Hotfix 22: periodic scan sabotava o debounce dos listeners input/setter
  // — cada digito digitado durante typing burst ficava visivel ao scan e
  // gerava fill separado. Solucao: exige valor ESTAVEL por 2 scans (~1s)
  // antes de emitir. Se usuario ainda esta digitando, valor muda no proximo
  // tick e o candidato eh descartado.
  window.__tfPeriodicScanPending = window.__tfPeriodicScanPending || {};
  function _periodicFillScan() {
    if (window.__tfAssertWaiting) return;
    var els = document.querySelectorAll('input, textarea');
    var seen = {};
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      if (el.type === 'checkbox' || el.type === 'radio' || el.type === 'hidden') continue;
      var rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) continue;
      var val = (el.value || '').trim();
      if (val === '') continue;
      var key = _fillKey(el);
      seen[key] = true;
      if (window.__tfLastFillValue[key] === val) {
        delete window.__tfPeriodicScanPending[key];
        continue;
      }
      // Skip if the input is currently focused — user is actively typing.
      if (document.activeElement === el) {
        window.__tfPeriodicScanPending[key] = val;
        continue;
      }
      var pending = window.__tfPeriodicScanPending[key];
      if (pending !== val) {
        // Value just changed on this scan — wait one more tick to confirm stability.
        window.__tfPeriodicScanPending[key] = val;
        continue;
      }
      // Stable for 2 scans (~1s) AND element not focused. Safe to emit.
      window.__tfLastFillValue[key] = val;
      delete window.__tfPeriodicScanPending[key];
      _pushEvent('fill', el);
    }
    // Clean up pending entries for elements that vanished (SPA nav).
    for (var pk in window.__tfPeriodicScanPending) {
      if (!seen[pk]) delete window.__tfPeriodicScanPending[pk];
    }
  }
  try {
    if (window.__tfPeriodicFillScanInterval) clearInterval(window.__tfPeriodicFillScanInterval);
    window.__tfPeriodicFillScanInterval = setInterval(_periodicFillScan, 500);
  } catch(_e) {}

  // ---- Assert helpers ----
  function _detectState(el) {
    var tag = (el.tagName||'').toLowerCase();
    if ((tag === 'input' && (el.type === 'checkbox' || el.type === 'radio')) || tag === 'option') {
      return el.checked ? 'checked' : 'unchecked';
    }
    return el.disabled ? 'disabled' : 'enabled';
  }

  function _getExpectedValue(el, assertType) {
    switch(assertType) {
      case 'textual':
      case 'automatico':
        var clone = el.cloneNode(true);
        clone.querySelectorAll('mat-icon,svg,[aria-hidden="true"]').forEach(function(n){n.remove();});
        return (clone.textContent||'').trim().replace(/\s+/g,' ').substring(0,200);
      case 'estado':
        return _detectState(el);
      case 'visivel':
        var rect = el.getBoundingClientRect();
        return (rect.width > 0 && rect.height > 0) ? 'visible' : 'hidden';
    }
    return '';
  }

  function _addStep(action, el, assertType) {
    try {
      if (!el || el === document.body || el === document.documentElement ||
          (el.tagName && (el.tagName === 'BODY' || el.tagName === 'HTML'))) {
        _showToast('[AVISO] Selecione um elemento especifico, nao a pagina inteira');
        window.__tfAssertWaiting = false;
        var dot = document.getElementById('tf-rec-dot');
        var status = document.getElementById('tf-status');
        if (dot) dot.style.color = '#e94560';
        if (status) status.textContent = 'Gravando...';
        return false;
      }
      var target = _extractTarget(el);
      var step = {
        action: action,
        tagName: target.tag,
        text: target.text,
        value: target.value,
        element_id: target.element_id,
        aria_label: target.accessible_name,
        role: target.role,
        name: target.name,
        placeholder: target.placeholder,
        test_id: target.test_id,
        label: target.label,
        css_path: target.css_path,
        attrs: {},
        timestamp: new Date().toISOString()
      };
      try { step.attrs = el.attributes; } catch(e) {}
      if (assertType) {
        step.assert_type = assertType;
        step.assert_state = assertType === 'estado' ? _detectState(el) : '';
        step.expected_value = _getExpectedValue(el, assertType);
      }
      window.__tfStepQueue.push(step);
      return true;
    } catch(e) {
      console.error('[TestForge] _addStep ERROR:', e.message);
      return false;
    }
  }

  // ---- Mutations for contenteditable + ARIA ----
  (function() {
    try {
      var observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mut) {
          var el = mut.target;
          if (!el || el === document.body || el === document.documentElement) return;
          if (el.isContentEditable) {
            window.__tfFieldSnapshotQueue.push({
              type: 'content_edit',
              timestamp: new Date().toISOString(),
              fingerprint: 'contenteditable#' + (el.id||''),
              value: (el.textContent || '').substring(0, 200),
              tag: el.tagName.toLowerCase()
            });
            return;
          }
          if (mut.type === 'attributes' && mut.attributeName) {
            if (mut.attributeName === 'value') {
              var el = mut.target;
              if (el && el.tagName) {
                var tag = el.tagName.toLowerCase();
                if ((tag === 'input' || tag === 'textarea') && !window.__tfAssertWaiting) {
                  _scheduleFillFromMutation(el);
                }
              }
              return;
            }
            var attrRole = mut.target.getAttribute && mut.target.getAttribute('role');
            if (attrRole && ['combobox', 'listbox', 'slider', 'spinbutton', 'searchbox', 'textbox'].indexOf(attrRole) !== -1) {
              if (mut.attributeName === 'aria-valuenow' || mut.attributeName === 'aria-valuetext') {
                window.__tfFieldSnapshotQueue.push({
                  type: 'aria_mutation',
                  timestamp: new Date().toISOString(),
                  fingerprint: 'aria-' + attrRole + '#' + (mut.target.id||''),
                  value: mut.target.getAttribute('aria-valuenow') || mut.target.getAttribute('aria-valuetext') || '',
                  tag: mut.target.tagName.toLowerCase(),
                  role: attrRole,
                  attribute: mut.attributeName
                });
              }
            }
          }
        });
      });
      observer.observe(document.documentElement, {
        childList: true,
        subtree: true,
        characterData: true,
        attributes: true,
        attributeFilter: ['aria-valuenow', 'aria-valuetext', 'contenteditable', 'value']
      });
      window.__tfMutationObserver = observer;
    } catch(_e) { /* MutationObserver unavailable */ }
  })();

  // ======== EVENT LISTENERS ========

  // ---- Pointer guard for assert mode ----
  window.addEventListener('pointerdown', function(e) {
    if (window.__tfAssertWaiting) {
      if (e.target && e.target.closest && e.target.closest('#tf-assert-menu, #tf-assert-confirm, #tf-overlay, #tf-stop-confirm')) return;
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
    }
  }, true);

  window.addEventListener('mousedown', function(e) {
    if (window.__tfAssertWaiting) {
      if (e.target && e.target.closest && e.target.closest('#tf-assert-menu, #tf-assert-confirm, #tf-overlay, #tf-stop-confirm')) return;
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
    }
  }, true);

  // ---- Click capture (primary) ----
  window.addEventListener('click', function(e) {
    var el = e.target;
    if (window.__tfAssertWaiting) {
      if (e.target && e.target.closest && e.target.closest('#tf-assert-menu, #tf-assert-confirm, #tf-overlay, #tf-stop-confirm')) return;
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation();
      window.__tfAssertElement = el;
      _highlight(el);
      var elDesc = el.getAttribute('aria-label') || el.getAttribute('placeholder') ||
                    (el.textContent||'').trim().replace(/\s+/g,' ').substring(0,40) ||
                    el.tagName.toLowerCase();
      _showToast('Element: "' + elDesc + '" — choose assert type');
      _showAssertMenu(e.clientX, e.clientY);
      return;
    }
    if (el && el.closest) {
      var interactive = el.closest('button, a, input, select, textarea, [role="button"], [role="listitem"], [role="option"], [role="menuitem"], mat-icon, .mat-icon, [class*="mat-"]');
      if (interactive) el = interactive;
    }
    if (_isSubmitTrigger(el)) {
      var form = null;
      if (el && el.form) { form = el.form; }
      else if (el && el.closest) { form = el.closest('form'); }
      var pending = {
        url: form ? (form.action || window.location.href) : window.location.href,
        method: (form && form.method) ? form.method.toUpperCase() : 'POST',
        timestamp: Date.now()
      };
      window.__tfPendingSubmit = pending;
      try { sessionStorage.setItem('__tfPendingSubmit', JSON.stringify(pending)); } catch(_e) {}
      _captureFinalState('form_submit');
      _pushEvent('submit', el);
      var _scS = document.getElementById('tf-step-count');
      if (_scS) {
        var _nS = parseInt(_scS.textContent || 0) + 1;
        _scS.textContent = _nS;
        try { sessionStorage.setItem('__tfStepCount', _nS); } catch(_e) {}
      }
      // Capture form field values at submit time
      try {
        var formInputs = (form || document).querySelectorAll('input, textarea, select');
        var formValues = {};
        formInputs.forEach(function(inp) {
          var name = inp.name || inp.getAttribute('aria-label') || inp.placeholder || inp.id || '';
          if (name && inp.value && inp.value.trim()) {
            formValues[name] = inp.value.trim().substring(0, 200);
          }
        });
        if (Object.keys(formValues).length) {
          if (!window.__tfEventQueue.length) return;
          var last = window.__tfEventQueue[window.__tfEventQueue.length - 1];
          if (last && last.type === 'submit') last.form_values = formValues;
        }
      } catch(_ignore) {}
      return;
    }
    if (el && el.tagName === 'SELECT') {
      _pushEvent('select_option', el);
      return;
    }
    _pushEvent('click', el);
    setTimeout(function() {
      var _sc = document.getElementById('tf-step-count');
      if (_sc) {
        var _n = parseInt(_sc.textContent || 0) + 1;
        _sc.textContent = _n;
        try { sessionStorage.setItem('__tfStepCount', _n); } catch(_e) {}
      }
    }, 0);
  }, true);

  // ---- Fill capture (input / change) ----
  function _fillKey(el) {
    var base = el.name || el.getAttribute('aria-label') || el.placeholder || el.id;
    if (base) return base;
    var all = document.querySelectorAll(el.tagName);
    var idx = Array.prototype.indexOf.call(all, el);
    return el.tagName + ':' + idx;
  }

  window.addEventListener('input', function(e) {
    if (window.__tfAssertWaiting) return;
    var el = e.target;
    if (!el) return;
    _scheduleFillFromMutation(el);
  }, true);

  window.addEventListener('change', function(e) {
    if (window.__tfAssertWaiting) return;
    var el = e.target;
    if (el && (el.tagName === 'INPUT' || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA')) {
      var key = _fillKey(el);
      var val = (el.value || '').trim();
      if (window.__tfLastFillValue[key] === val) return;
      window.__tfLastFillValue[key] = val;
      var evtType = (el.tagName === 'SELECT') ? 'select_option' : 'fill';
      // Hotfix 22: <input type=file> — dispara change com el.files. Marca
      // com file_names para o runner reproduzir via setInputFiles.
      if (el.tagName === 'INPUT' && el.type === 'file' && el.files && el.files.length) {
        try {
          var fnames = Array.prototype.map.call(el.files, function(f) {
            return { name: f.name, size: f.size, type: f.type };
          });
          if (!window.__tfEventQueue.length) {
            _pushEvent('fill', el);
          } else {
            _pushEvent('fill', el);
          }
          var last = window.__tfEventQueue[window.__tfEventQueue.length - 1];
          if (last) last.file_upload = fnames;
        } catch(_ignore) {}
        return;
      }
      _pushEvent(evtType, el);
    }
  }, true);

  // Hotfix 22: paste event — cobre usuarios que colam valor no campo (Ctrl+V)
  // sem keystrokes. `input` event dispara mas sem historico intermediario;
  // marcamos o fill com paste=true para o normalizer nao esperar burst.
  window.addEventListener('paste', function(e) {
    if (window.__tfAssertWaiting) return;
    var el = e.target;
    if (!el || (el.tagName !== 'INPUT' && el.tagName !== 'TEXTAREA')) return;
    setTimeout(function() {
      try {
        var key = _fillKey(el);
        var val = (el.value || '').trim();
        if (val && window.__tfLastFillValue[key] !== val) {
          window.__tfLastFillValue[key] = val;
          _pushEvent('fill', el);
          var last = window.__tfEventQueue[window.__tfEventQueue.length - 1];
          if (last) last.paste = true;
        }
      } catch(_e) {}
    }, 50);
  }, true);

  // ---- Beforeunload: clear intervals, save final state ----
  window.addEventListener('beforeunload', function() {
    _captureFinalState('beforeunload');
  });

  // ---- Persist unflushed events across navigation ----
  window.addEventListener('beforeunload', function() {
    try {
      if (window.__tfEventQueue && window.__tfEventQueue.length > 0) {
        sessionStorage.setItem('__tfUnflushedEvents', JSON.stringify(window.__tfEventQueue));
      }
      if (window.__tfStepQueue && window.__tfStepQueue.length > 0) {
        sessionStorage.setItem('__tfUnflushedSteps', JSON.stringify(window.__tfStepQueue));
      }
    } catch(_e) {}
  });

  // ---- Assert mode hover highlight ----
  window.__tfAssertHoverEl = null;
  window.__tfAssertHoverStyle = '';
  window.addEventListener('mouseover', function(e) {
    if (!window.__tfAssertWaiting) return;
    if (e.target && e.target.closest && e.target.closest('#tf-assert-menu, #tf-overlay')) return;
    var el = e.target;
    if (el === window.__tfAssertHoverEl) return;
    if (window.__tfAssertHoverEl) {
      window.__tfAssertHoverEl.style.outline = window.__tfAssertHoverStyle;
      window.__tfAssertHoverEl = null;
    }
    if (!el || el === document.body || el === document.documentElement) return;
    window.__tfAssertHoverStyle = el.style.outline || '';
    el.style.outline = '2px dashed #f59e0b';
    window.__tfAssertHoverEl = el;
  }, true);
  window.addEventListener('mouseout', function(e) {
    if (!window.__tfAssertWaiting) return;
    if (e.target === window.__tfAssertHoverEl) {
      e.target.style.outline = window.__tfAssertHoverStyle;
      window.__tfAssertHoverEl = null;
    }
  }, true);

  // ---- Cancel assert mode ----
  window._tf_cancelAssertMode = function() {
    window.__tfAssertWaiting = false;
    window.__tfAssertElement = null;
    if (window.__tfAssertTimeout) { clearTimeout(window.__tfAssertTimeout); window.__tfAssertTimeout = null; }
    var menu = document.getElementById('tf-assert-menu');
    if (menu) menu.style.display = 'none';
    var dot = document.getElementById('tf-rec-dot');
    var status = document.getElementById('tf-status');
    if (dot) dot.style.color = '#e94560';
    if (status) status.textContent = 'Gravando...';
    document.body.style.outline = '';
  };

  window._tf_enterAssertMode = function() {
    window.__tfAssertWaiting = true;
    window.__tfCommandQueue.push('ASSERT');
    _showToast('Modo Assert — clique no elemento (Esc para cancelar)');
    var dot = document.getElementById('tf-rec-dot');
    var status = document.getElementById('tf-status');
    if (dot) dot.style.color = '#f59e0b';
    if (status) status.textContent = 'Assert — clique no elemento (Esc para cancelar)';
    document.body.style.outline = '3px solid #f59e0b';
    if (window.__tfAssertTimeout) clearTimeout(window.__tfAssertTimeout);
    window.__tfAssertTimeout = setTimeout(function() {
      if (window.__tfAssertWaiting) {
        _showToast('Assert cancelado (timeout 30s)');
        window._tf_cancelAssertMode();
      }
    }, 30000);
  };

  // ---- Keyboard shortcuts ----
  window.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && window.__tfAssertWaiting) {
      e.preventDefault();
      e.stopPropagation();
      _showToast('Assert cancelado');
      window._tf_cancelAssertMode();
      return;
    }
    if (!e.shiftKey) return;
    switch(e.key.toUpperCase()) {
      case 'P':
        window.__tfCommandQueue.push('TOGGLE_PAUSE');
        break;
      case 'S':
        _confirmStop();
        break;
      case 'A':
        window._tf_enterAssertMode();
        break;
      case 'M':
        window.__tfDragMode = !window.__tfDragMode;
        break;
      case 'N':
        // H20: scenario boundary. Pushes a synthetic event into the
        // recorded stream so the normalizer can split the recording
        // into N independent SemanticTestCase instances. A simple
        // prompt() asks for an optional scenario name; the next
        // segment inherits that name. Empty/cancel → auto-numbered.
        var _scenarioName = '';
        try {
          _scenarioName = (window.prompt(
            'Nome do próximo cenário (Enter para auto-numerar):'
          ) || '').trim().substring(0, 80);
        } catch (_e) { /* prompt blocked → auto-numbered */ }
        if (window.__tfEventQueue) {
          window.__tfEventQueue.push({
            type: 'scenario_boundary',
            timestamp: new Date().toISOString(),
            url: window.location.href,
            page_title: document.title || '',
            scenario_name: _scenarioName,
          });
        }
        _showToast(
          _scenarioName
            ? ('Cenário marcado: ' + _scenarioName)
            : 'Cenário marcado (auto-numerar)'
        );
        break;
    }
  }, true);

  // ======== OVERLAY UI ========

  function _showOverlay() {
    var initSteps = 0, initAsserts = 0;
    try {
      initSteps   = parseInt(sessionStorage.getItem('__tfStepCount')   || 0);
      initAsserts = parseInt(sessionStorage.getItem('__tfAssertCount') || 0);
    } catch(_e) {}

    // Build context label from recording info injected by recorder_controller
    var info = window.__tfRecordingInfo || {};
    var ctxParts = [];
    if (info.system)   ctxParts.push(info.system);
    if (info.suite)    ctxParts.push(info.suite);
    if (info.testCase && info.testCase !== info.rid) ctxParts.push(info.testCase);
    var ctxLabel = ctxParts.length ? ctxParts.join(' / ') : (info.rid || '');
    var ctxHtml = ctxLabel
      ? '<div style="font-size:10px;color:#94a3b8;margin-top:3px;letter-spacing:0.03em">' + ctxLabel + '</div>'
      : '';

    var ov = document.createElement('div');
    ov.id = 'tf-overlay';
    ov.innerHTML = [
      '<div id="tf-panel" style="position:fixed;top:8px;right:8px;background:#1a1a2e;color:#fff;padding:8px 14px;border-radius:8px;font:14px monospace;z-index:99999;display:flex;flex-direction:column;gap:4px;box-shadow:0 4px 16px rgba(0,0,0,0.3)">',
        '<div style="display:flex;gap:12px;align-items:center">',
          '<span id="tf-rec-dot" style="color:#e94560;font-size:18px">R</span>',
          '<span id="tf-status">Gravando...</span>',
          '<span style="color:#aaa">|</span>',
          '<button id="tf-btn-pause" style="background:#334155;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font:12px monospace" title="Shift+P">||</button>',
          '<button id="tf-btn-stop" style="background:#991b1b;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font:12px monospace" title="Shift+S">[]</button>',
          '<button id="tf-btn-assert" style="background:#6366f1;color:#fff;border:none;padding:4px 10px;border-radius:4px;cursor:pointer;font:12px monospace" title="Shift+A">Assert</button>',
          '<span style="color:#aaa">|</span>',
          '<span>Passos: <strong id="tf-step-count">' + initSteps + '</strong></span>',
          '<span>|</span>',
          '<span>Asserts: <strong id="tf-assert-count">' + initAsserts + '</strong></span>',
        '</div>',
        ctxHtml,
      '</div>',
      '<div id="tf-toast" style="display:none;position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#10b981;color:#fff;padding:10px 24px;border-radius:8px;font:14px sans-serif;z-index:99999;box-shadow:0 4px 16px rgba(0,0,0,0.3)"></div>'
    ].join('\n');
    document.body.appendChild(ov);
    // Restore saved overlay position from localStorage (persists across page navigations)
    try {
      var savedPos = localStorage.getItem('__tfOverlayPosition');
      if (savedPos) {
        var pos = JSON.parse(savedPos);
        var panel = document.getElementById('tf-panel');
        if (panel && typeof pos.left === 'number' && typeof pos.top === 'number') {
          var clampedX = Math.max(0, Math.min(pos.left, window.innerWidth - panel.offsetWidth));
          var clampedY = Math.max(0, Math.min(pos.top, window.innerHeight - panel.offsetHeight));
          panel.style.right = 'auto';
          panel.style.left = clampedX + 'px';
          panel.style.top = clampedY + 'px';
        }
      }
    } catch(_e) {}
    document.getElementById('tf-btn-pause').onclick = function() { window.__tfCommandQueue.push('TOGGLE_PAUSE'); };
    document.getElementById('tf-btn-stop').onclick = function() { _confirmStop(); };
    document.getElementById('tf-btn-assert').onclick = function() { window._tf_enterAssertMode(); };
  }

  function _showToast(msg) {
    var toast = document.getElementById('tf-toast');
    if (!toast) return;
    toast.textContent = msg;
    toast.style.display = 'block';
    setTimeout(function() { toast.style.display = 'none'; }, 2000);
  }

  function _showAssertMenu(x, y) {
    var old = document.getElementById('tf-assert-menu');
    if (old) old.remove();
    var el = document.createElement('div');
    el.id = 'tf-assert-menu';
    el.style.cssText = [
      'position:fixed',
      'z-index:2147483647',
      'top:60px',
      'left:50%',
      'transform:translateX(-50%)',
      'background:#1e293b',
      'border:2px solid #f59e0b',
      'padding:10px 14px',
      'border-radius:10px',
      'display:flex',
      'flex-direction:column',
      'gap:8px',
      'box-shadow:0 8px 32px rgba(0,0,0,0.7)',
      'font:13px sans-serif',
      'min-width:260px'
    ].join(';');
    var targetEl = window.__tfAssertElement;
    var desc = targetEl ? (
      targetEl.getAttribute('aria-label') || targetEl.getAttribute('placeholder') ||
      (targetEl.textContent||'').trim().replace(/\s+/g,' ').substring(0,50) ||
      targetEl.tagName.toLowerCase()
    ) : '?';
    var header = document.createElement('div');
    header.style.cssText = 'color:#94a3b8;font-size:11px;margin-bottom:2px';
    header.textContent = 'ASSERT em: "' + desc.substring(0,50) + '"';
    el.appendChild(header);
    var btnRow = document.createElement('div');
    btnRow.style.cssText = 'display:flex;gap:6px';
    [
      {type:'textual',  label:'Text',  bg:'#10b981'},
      {type:'estado',   label:'State', bg:'#f59e0b'},
      {type:'visivel',  label:'Visible', bg:'#3b82f6'},
      {type:'automatico', label:'Auto', bg:'#8b5cf6'},
      {type:'_cancel',  label:'X',      bg:'#475569'}
    ].forEach(function(item) {
      var btn = document.createElement('button');
      btn.textContent = item.label;
      btn.style.cssText = 'color:#fff;border:none;padding:8px 12px;border-radius:6px;cursor:pointer;font:13px sans-serif;font-weight:600;background:' + item.bg;
      btn.addEventListener('pointerdown', function(e) { e.stopPropagation(); }, true);
      btn.addEventListener('mousedown',   function(e) { e.stopPropagation(); }, true);
      btn.onclick = function(e) {
        e.stopPropagation();
        e.preventDefault();
        el.remove();
        if (item.type === '_cancel') {
          _showToast('Assert cancelado');
          window._tf_cancelAssertMode();
          return;
        }
        var target = window.__tfAssertElement;
        if (!target) {
          _showToast('[AVISO] Elemento perdido — clique novamente');
          window._tf_cancelAssertMode();
          return;
        }
        _addStep('assert', target, item.type);
        var assertCount = document.getElementById('tf-assert-count');
        if (assertCount) {
          var an = parseInt(assertCount.textContent||0) + 1;
          assertCount.textContent = an;
          try { sessionStorage.setItem('__tfAssertCount', an); } catch(_e){}
        }
        var stepCount = document.getElementById('tf-step-count');
        if (stepCount) {
          var sn = parseInt(stepCount.textContent||0) + 1;
          stepCount.textContent = sn;
          try { sessionStorage.setItem('__tfStepCount', sn); } catch(_e){}
        }
        var expected = _getExpectedValue(target, item.type);
        _showToast('Assert ' + item.type + ': "' + (expected||'').substring(0,40) + '"');
        if (window.__tfAssertTimeout) { clearTimeout(window.__tfAssertTimeout); window.__tfAssertTimeout = null; }
        window.__tfAssertWaiting = false;
        window.__tfAssertElement = null;
        document.body.style.outline = '';
        var dot = document.getElementById('tf-rec-dot');
        var status = document.getElementById('tf-status');
        if (dot) dot.style.color = '#e94560';
        if (status) status.textContent = 'Gravando...';
      };
      btnRow.appendChild(btn);
    });
    el.appendChild(btnRow);
    document.body.appendChild(el);
  }

  function _confirmStop() {
    var assertCount = parseInt((document.getElementById('tf-assert-count') || {}).textContent || 0);
    if (assertCount === 0) {
      var existing = document.getElementById('tf-stop-confirm');
      if (existing) existing.remove();
      var dlg = document.createElement('div');
      dlg.id = 'tf-stop-confirm';
      dlg.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);' +
        'z-index:999999;background:#1e293b;color:#fff;padding:20px 24px;border-radius:12px;' +
        'box-shadow:0 8px 32px rgba(0,0,0,0.6);font:14px sans-serif;text-align:center;max-width:360px';
      dlg.innerHTML =
        '<div style="font-size:22px;margin-bottom:12px">&#9888; Sem asserts</div>' +
        '<div style="margin-bottom:16px">O teste gravado nao tera <strong>nenhum assert</strong>.<br>' +
        '<span style="color:#94a3b8;font-size:12px">Sem asserts o TestForge nao consegue verificar os resultados esperados.</span></div>' +
        '<div style="display:flex;gap:10px;justify-content:center">' +
          '<button id="tf-stop-yes" style="background:#991b1b;color:#fff;border:none;' +
            'padding:9px 20px;border-radius:6px;cursor:pointer;font:13px sans-serif;font-weight:600">Sair mesmo assim</button>' +
          '<button id="tf-stop-no" style="background:#334155;color:#fff;border:none;' +
            'padding:9px 20px;border-radius:6px;cursor:pointer;font:13px sans-serif;font-weight:600">Voltar</button>' +
        '</div>';
      document.body.appendChild(dlg);
      document.getElementById('tf-stop-yes').onclick = function() {
        dlg.remove();
        _captureFinalState('user_stop');
        _showStoppingUI();
        window.__tfCommandQueue.push('STOP');
      };
      document.getElementById('tf-stop-no').onclick = function() { dlg.remove(); };
      return;
    }
    _captureFinalState('user_stop');
    _showStoppingUI();
    window.__tfCommandQueue.push('STOP');
  }

  function _showStoppingUI() {
    // Hotfix 14: when the user presses Shift+S the overlay used to keep
    // showing "Gravando..." until the browser closed seconds later, while
    // Python paused on a blocking Gherkin prompt in the terminal. The user
    // assumed the recorder was stuck and closed the browser by hand.
    // Update the visible state immediately so it is obvious that the stop
    // was received and the next action is in the terminal.
    try {
      var status = document.getElementById('tf-status');
      if (status) status.textContent = 'Encerrando — responda no terminal...';
      var dot = document.getElementById('tf-rec-dot');
      if (dot) {
        dot.style.color = '#fbbf24';  // amber instead of red
        dot.textContent = '⏳';   // hourglass
      }
      var btnStop = document.getElementById('tf-btn-stop');
      if (btnStop) {
        btnStop.disabled = true;
        btnStop.style.opacity = '0.5';
        btnStop.style.cursor = 'not-allowed';
      }
      var btnPause = document.getElementById('tf-btn-pause');
      if (btnPause) {
        btnPause.disabled = true;
        btnPause.style.opacity = '0.5';
        btnPause.style.cursor = 'not-allowed';
      }
      var existing = document.getElementById('tf-stop-notice');
      if (existing) existing.remove();
      var notice = document.createElement('div');
      notice.id = 'tf-stop-notice';
      notice.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);' +
        'z-index:999999;background:#1e293b;color:#fff;padding:20px 28px;border-radius:12px;' +
        'box-shadow:0 8px 32px rgba(0,0,0,0.6);font:14px sans-serif;text-align:center;max-width:380px';
      notice.innerHTML =
        '<div style="font-size:20px;margin-bottom:8px">⏳ Encerrando gravacao</div>' +
        '<div style="color:#cbd5e1;font-size:13px">O navegador vai fechar em instantes.<br>' +
        '<strong>Responda as proximas perguntas no terminal.</strong></div>';
      document.body.appendChild(notice);
    } catch (_ignore) {}
  }

  function _highlight(el) {
    var orig = el.style.outline;
    el.style.outline = '2px solid #e94560';
    el.style.outlineOffset = '2px';
    setTimeout(function() { el.style.outline = orig; }, 1500);
  }

  // ---- Overlay drag ----
  document.addEventListener('mousedown', function(e) {
    if (!window.__tfDragMode) return;
    var panel = document.getElementById('tf-panel');
    if (!panel || !panel.contains(e.target)) return;
    var rect = panel.getBoundingClientRect();
    window.__tfDragState = { dx: e.clientX - rect.left, dy: e.clientY - rect.top };
    panel.style.cursor = 'grabbing';
    e.preventDefault();
  }, true);

  document.addEventListener('mousemove', function(e) {
    if (!window.__tfDragState || !window.__tfDragMode) return;
    var panel = document.getElementById('tf-panel');
    if (!panel) return;
    var x = Math.max(0, Math.min(e.clientX - window.__tfDragState.dx, window.innerWidth  - panel.offsetWidth));
    var y = Math.max(0, Math.min(e.clientY - window.__tfDragState.dy, window.innerHeight - panel.offsetHeight));
    panel.style.right = 'auto';
    panel.style.left  = x + 'px';
    panel.style.top   = y + 'px';
  });

  document.addEventListener('mouseup', function() {
    if (!window.__tfDragState) return;
    window.__tfDragState = null;
    var panel = document.getElementById('tf-panel');
    if (panel && window.__tfDragMode) panel.style.cursor = 'grab';
    // Persist overlay position across page navigations
    try {
      if (panel && panel.style.left && panel.style.left !== '' && panel.style.top && panel.style.top !== '') {
        localStorage.setItem('__tfOverlayPosition', JSON.stringify({
          left: parseInt(panel.style.left),
          top: parseInt(panel.style.top)
        }));
      }
    } catch(_e) {}
  });

  // ---- Load handler ----
  window.addEventListener('load', function() {
    if (window.__tfPendingSubmit) {
      var alreadyRestored = false;
      for (var i = 0; i < window.__tfEventQueue.length; i++) {
        if (window.__tfEventQueue[i].type === 'submit' && window.__tfEventQueue[i].is_postback) {
          alreadyRestored = true;
          break;
        }
      }
      if (!alreadyRestored) {
        var pending = window.__tfPendingSubmit;
        ++window.__tfEventCounter;
        window.__tfEventQueue.push({
          type: 'postback',
          timestamp: new Date().toISOString(),
          url: window.location.href,
          page_title: document.title,
          target: null,
          value: null,
          is_postback: true,
          submit_method: pending.method
        });
      }
      window.__tfPendingSubmit = null;
    }
    setTimeout(function() { _showOverlay(); }, 100);
  });

  // ---- Public aliases ----
  window._tf_snapshotFields = _snapshotFields;
  window._tf_captureFinalState = _captureFinalState;
  // Bug fix (2026-06-30): periodic field snapshot bug — _snapshotFields
  // retorna array mas nunca era enviado ao __tfFieldSnapshotQueue. Resultado:
  // field_snapshots.jsonl nunca era escrito mesmo com infra completa nos dois
  // lados (recorder_controller._save_field_snapshot existe; flush_events
  // ja itera fieldSnapshots). Sprint A2 (input_visibility_check) dependia
  // desse arquivo, entao nunca disparava em recordings reais — A2 era
  // efetivamente no-op nas rodadas test-pos-hotfix14a-16d. Wrap acumula
  // o batch no queue para o flush periodico pegar.
  window.__tfFieldSnapshotInterval = setInterval(function() {
    try {
      var snaps = _tf_snapshotFields();
      if (snaps && snaps.length) {
        window.__tfFieldSnapshotQueue.push({
          timestamp: new Date().toISOString(),
          snapshots: snaps,
        });
      }
    } catch(_e) {}
  }, 2000);

  // ---- Sprint event delegation (2026-06-30) ----
  // Iframe (same-origin) + Shadow DOM (open) event delegation.
  // Listeners no window do top frame nao penetram nem iframe content
  // (different document) nem shadow root closed boundaries. Sites com
  // dialogs Material em mat-dialog overlay tem shadow root open + iframes
  // de mapas + recaptcha frames cross-origin (estes ultimos ignoraveis
  // por browser policy). Aqui scaneia documentos acessiveis e re-registra
  // os listeners criticos. Re-scaneia periodicamente para pegar shadow
  // roots criados dinamicamente.
  window.__tfDelegatedRoots = window.__tfDelegatedRoots || new WeakSet();
  function _delegateToRoot(root) {
    if (!root || window.__tfDelegatedRoots.has(root)) return;
    try { window.__tfDelegatedRoots.add(root); } catch(_e) {}
    try {
      root.addEventListener("click", function(e) {
        try {
          var el = e.target;
          if (!el) return;
          if (el.id === "tf-panel" || (el.closest && el.closest("#tf-panel"))) return;
          if (window.__tfAssertWaiting) return;
          _pushEvent("click", el);
        } catch(_e2) {}
      }, true);
      root.addEventListener("input", function(e) {
        try {
          var el = e.target;
          if (!el) return;
          if (window.__tfAssertWaiting) return;
          _scheduleFillFromMutation(el);
        } catch(_e2) {}
      }, true);
    } catch(_e) {}
  }
  function _scanIframesAndShadows() {
    // Same-origin iframes
    try {
      var iframes = document.querySelectorAll("iframe");
      iframes.forEach(function(iframe) {
        try {
          var iDoc = iframe.contentDocument
                     || (iframe.contentWindow && iframe.contentWindow.document);
          if (iDoc) _delegateToRoot(iDoc);
        } catch(_cross) { /* cross-origin: browser bloqueia */ }
      });
    } catch(_e) {}
    // Open shadow roots — scan all elements and check shadowRoot
    try {
      var all = document.querySelectorAll("*");
      var count = 0;
      for (var i = 0; i < all.length; i++) {
        if (count > 500) break;
        var sr = all[i].shadowRoot;
        if (sr && sr.mode === "open") {
          _delegateToRoot(sr);
          count += 1;
        }
      }
    } catch(_e) {}
  }
  // Initial scan + periodic rescan
  _scanIframesAndShadows();
  window.__tfDelegationInterval = setInterval(_scanIframesAndShadows, 3000);
})();
