(function inject() {
  try {
  if (!document.documentElement || !document.body) return setTimeout(inject, 5);
  if (window.__tfReady) return;

  var _tf_isIframe = window !== window.parent;
  var _tf_iframeSelector = '';
  if (_tf_isIframe) {
    try {
      if (window.parent.__tfSteps) {
        window.__tfSteps = window.parent.__tfSteps;
        window.__tfCommands = window.parent.__tfCommands || (window.parent.__tfCommands = []);
      }
      var frameEl = window.frameElement;
      if (frameEl) {
        var ftag = frameEl.tagName.toLowerCase();
        var fattrs = {id: frameEl.id, name: frameEl.getAttribute('name') || '', classes: '', type: 'iframe'};
        var ftext = (frameEl.textContent || '').trim().slice(0, 120);
        _tf_iframeSelector = generateBestSelector(frameEl, ftag, fattrs, ftext, '');
      }
    } catch(e) { return; }
  }

  var MODE = window.__tfMode || 'full';
  var NAME = 'TestForge';

  window.__tfSteps = window.__tfSteps || [];
  window.__tfReady = false;
  window.__tfCommands = window.__tfCommands || [];
  window.__tfAssertWaiting = false;
  window.__tfAssertElement = null;

  function _tf_detectPageTech() {
    var techs = [];
    if (typeof PrimeFaces !== 'undefined') techs.push('primefaces');
    if (typeof jQuery !== 'undefined' && jQuery.ui) techs.push('jquery-ui');
    if (typeof kendo !== 'undefined') techs.push('kendo');
    if (typeof angular !== 'undefined') techs.push('angular');
    window.__tfPageTech = techs.join(',');
  }
  _tf_detectPageTech();
  /* Re-detect after 3s for async-loaded frameworks (Kendo, Angular) */
  setTimeout(function() { _tf_detectPageTech(); }, 3000);

  function addTFStep(step) {
    step.url = location.href;
    if (_tf_isIframe && _tf_iframeSelector) {
      if (!step.attrs) step.attrs = {};
      step.attrs.iframeSelector = _tf_iframeSelector;
    }
    if (!step.attrs) step.attrs = {};
    step.attrs.pageTechnology = window.__tfPageTech || '';
    step.fallbacks = step.fallbacks || [];
    window.__tfSteps.push(step);
    var c = document.getElementById('tf-step-count');
    if (c) c.textContent = window.__tfSteps.length;
  }

  function generateStrategies(el, tag, attrs, text, value) {
    var strategies = [];
    var at = attrs || {};
    var t = tag || (el.tagName || '').toLowerCase();
    var txt = (text || el.textContent || at.labelText || '').trim().slice(0, 60);

    if (at.dataTestid)
      strategies.push({strategy: 'data-testid', selector: '[data-testid="' + at.dataTestid + '"]'});

    if (el.id)
      strategies.push({strategy: 'id', selector: '#' + el.id});

    if (at.name)
      strategies.push({strategy: 'name', selector: t + '[name="' + at.name + '"]'});

    if (at.ariaLabel)
      strategies.push({strategy: 'aria-label', selector: t + '[aria-label="' + at.ariaLabel + '"]'});

    if (at.placeholder)
      strategies.push({strategy: 'placeholder', selector: t + '[placeholder="' + at.placeholder + '"]'});

    var hasTextTags = ['a', 'button', 'option', 'li', 'label', 'h1', 'h2', 'h3', 'h4', 'span', 'div'];
    if (txt && hasTextTags.indexOf(t) !== -1 && t !== 'div')
      strategies.push({strategy: 'has-text', selector: t + ':has-text("' + txt.replace(/"/g, '\\"') + '")'});
    else if (txt && t === 'div' && (at.role === 'option' || el.getAttribute('role') === 'option'))
      strategies.push({strategy: 'has-text', selector: t + ':has-text("' + txt.replace(/"/g, '\\"') + '")'});
    else if (txt && at.labelText)
      strategies.push({strategy: 'has-text', selector: t + ':has-text("' + at.labelText.replace(/"/g, '\\"') + '")'});

    if (at.href && t === 'a' && at.href !== '#' && at.href !== '' && at.href !== 'javascript:void(0)')
      strategies.push({strategy: 'href', selector: 'a[href="' + at.href + '"]'});

    if (at.alt && t === 'img')
      strategies.push({strategy: 'alt', selector: 'img[alt="' + at.alt + '"]'});

    if (at.classes && t) {
      var cls = at.classes.split(/\s+/).filter(function(c) { return c && !c.startsWith('tf-'); }).join('.');
      if (cls) strategies.push({strategy: 'class', selector: t + '.' + cls});
    }

    var domPath = getSelector(el);
    if (domPath)
      strategies.push({strategy: 'dom-path', selector: domPath});

    return strategies;
  }

  function getParentChain(el) {
    var chain = [];
    var current = el;
    while (current && current !== document.body && current !== document.documentElement) {
      var tag = current.tagName.toLowerCase();
      if (current.id) { chain.unshift(tag + '#' + current.id); break; }
      var parent = current.parentElement;
      if (parent) {
        var idx = 1;
        for (var sib = parent.firstElementChild; sib; sib = sib.nextElementSibling) {
          if (sib === current) break;
          if (sib.tagName === current.tagName) idx++;
        }
        chain.unshift(tag + ':nth-child(' + idx + ')');
      } else { chain.unshift(tag); }
      current = parent;
    }
    return chain.join(' > ');
  }

  function getSimpleSelector(el) {
    var tag = el.tagName.toLowerCase();
    if (el.id) return '#' + el.id;
    if (el.className && typeof el.className === 'string') {
      var cls = el.className.trim().split(/\s+/).filter(function(c) { return c && !c.startsWith('tf-'); }).slice(0, 2).join('.');
      if (cls) return tag + '.' + cls;
    }
    return tag;
  }

  function getSelector(el) {
    if (el.id) return '#' + el.id;
    if (el.getAttribute('data-testid')) return '[data-testid="' + el.getAttribute('data-testid') + '"]';
    if (el.getAttribute('data-test')) return '[data-test="' + el.getAttribute('data-test') + '"]';
    if (el.getAttribute('name')) return el.tagName.toLowerCase() + '[name="' + el.getAttribute('name') + '"]';
    var path = [];
    var current = el;
    while (current && current !== document.body && current !== document.documentElement) {
      var root = current.getRootNode ? current.getRootNode() : null;
      if (root && root instanceof ShadowRoot) {
        var host = root.host;
        if (host) {
          path.unshift('>>>');
          path.unshift(getSimpleSelector(current));
          current = host;
          continue;
        }
      }
      var tag = current.tagName.toLowerCase();
      if (current.id) { path.unshift('#' + current.id); break; }
      var parent = current.parentElement || (current.parentNode && current.parentNode.host ? null : current.parentElement);
      if (parent) {
        var idx = 1;
        for (var sib = parent.firstElementChild; sib; sib = sib.nextElementSibling) {
          if (sib === current) break;
          if (sib.tagName === current.tagName) idx++;
        }
        path.unshift(tag + ':nth-of-type(' + idx + ')');
      } else {
        path.unshift(tag);
      }
      current = parent;
    }
    return path.join(' > ');
  }

  function getTagInfo(el) {
    var tag = (el.tagName || '').toLowerCase();
    var info = tag;
    if (el.id) info += '#' + el.id;
    if (el.className && typeof el.className === 'string') info += '.' + el.className.trim().split(/\s+/).slice(0,2).join('.');
    return info;
  }

  function detectFramework(el) {
    if (!el) return '';
    var c = el.closest('.ui-selectonemenu');
    if (c) return 'primefaces';
    c = el.closest('.ui-autocomplete');
    if (c && c.querySelector('.ui-autocomplete-panel')) return 'primefaces';
    c = el.closest('.k-dropdownlist, [data-role="dropdownlist"], span.k-widget');
    if (c) return 'kendo';
    if (el.tagName === 'SELECT' && el.closest('span.k-dropdownlist, span.k-widget, .k-input')) return 'kendo';
    c = el.closest('mat-select, [role="listbox"]');
    if (c) return 'angular';
    c = el.closest('.mat-calendar, .mat-datepicker-content, .mat-datepicker-toggle');
    if (c) return 'angular';
    if (typeof PrimeFaces !== 'undefined' && el.closest('[class*="ui-"]')) return 'primefaces';
    if (typeof jQuery !== 'undefined' && jQuery.ui && el.closest('.ui-selectmenu-button')) return 'jquery-ui';
    if (typeof kendo !== 'undefined') return 'kendo';
    return '';
  }

  function captureAttributes(el) {
    var attrs = {
      id: el.id || '',
      name: el.getAttribute('name') || '',
      classes: (el.className && typeof el.className === 'string') ? el.className.trim() : '',
      type: el.getAttribute('type') || '',
      placeholder: el.getAttribute('placeholder') || '',
      ariaLabel: el.getAttribute('aria-label') || '',
      role: el.getAttribute('role') || '',
      href: el.getAttribute('href') || '',
      alt: el.getAttribute('alt') || '',
      dataTestid: el.getAttribute('data-testid') || el.getAttribute('data-test') || '',
      labelText: '',
      parentTag: '',
      parentText: '',
      parentId: '',
      framework: detectFramework(el),
      pageTechnology: window.__tfPageTech || '',
    };
    var parent = el.parentElement;
    if (parent) {
      attrs.parentTag = parent.tagName.toLowerCase();
      attrs.parentId = parent.id || '';
      var lbl = parent.querySelector('label[for="' + el.id + '"]');
      if (!lbl) lbl = parent.querySelector('label');
      if (lbl) attrs.labelText = lbl.textContent.trim().slice(0, 80);
      var pt = parent.textContent.trim().slice(0, 100);
      attrs.parentText = pt;
    }
    var rect = el.getBoundingClientRect();
    attrs.elementRect = {x: Math.round(rect.x), y: Math.round(rect.y), w: Math.round(rect.width), h: Math.round(rect.height)};
    attrs.elementParentChain = getParentChain(el);
    return attrs;
  }

  function detectElementState(el) {
    var tag = (el.tagName || '').toLowerCase();
    if ((tag === 'input' && (el.type === 'checkbox' || el.type === 'radio')) || tag === 'option') {
      return el.checked ? 'checked' : 'unchecked';
    }
    if (el.disabled !== undefined) {
      return el.disabled ? 'disabled' : 'enabled';
    }
    return 'enabled';
  }

  function getExpectedValue(el, assertType) {
    if (assertType === 'textual') return (el.textContent || '').trim().slice(0, 200);
    if (assertType === 'estado') return detectElementState(el);
    if (assertType === 'visivel') {
      var rect = el.getBoundingClientRect();
      return (rect.width > 0 && rect.height > 0) ? 'visible' : 'hidden';
    }
    return (el.textContent || '').trim().slice(0, 200);
  }

  function generateBestSelector(el, tag, attrs, text, value) {
    var at = attrs || {};
    if (at.dataTestid) return '[data-testid="' + at.dataTestid + '"]';
    /* For radio/checkbox inside a label, click the visible label text instead of the hidden input */
    if (tag === 'input' && (at.type === 'radio' || at.type === 'checkbox') && at.parentTag === 'label' && at.parentText) {
      return at.parentTag + ':has-text("' + at.parentText.replace(/"/g, '\\"') + '")';
    }
    if (el.id) return '#' + el.id;
    if (at.name) return tag + '[name="' + at.name + '"]';
    if (at.ariaLabel) return tag + '[aria-label="' + at.ariaLabel + '"]';
    if (at.placeholder) return tag + '[placeholder="' + at.placeholder + '"]';
    if (tag === 'a' || tag === 'button' || tag === 'option' || tag === 'li') {
      var txt = (text || el.textContent || '').trim().slice(0, 60);
      if (txt) return tag + ':has-text("' + txt.replace(/"/g, '\\"') + '")';
    }
    if (at.href && tag === 'a' && at.href !== '#' && at.href !== '' && at.href !== 'javascript:void(0)') return 'a[href="' + at.href + '"]';
    if (at.alt && tag === 'img') return 'img[alt="' + at.alt + '"]';
    if (at.labelText) return tag + ':has-text("' + at.labelText.replace(/"/g, '\\"') + '")';
    if (at.classes && tag) {
      var cls = at.classes.split(/\s+/).filter(function(c) { return c && !c.startsWith('tf-'); }).join('.');
      if (cls) return tag + '.' + cls;
    }
    return getSelector(el);
  }

  function resolveElement(el) {
    var tag = (el.tagName || '').toLowerCase();

    /* Framework widgets: check BEFORE generic ID rule */

    /* PrimeFaces SelectOneMenu */
    var pfSelect = el.closest('.ui-selectonemenu');
    if (pfSelect) {
      if (el.closest('.ui-selectonemenu-item') || (tag === 'li' && el.closest('.ui-selectonemenu-panel'))) return el;
      var hiddenSelect = pfSelect.querySelector('select');
      if (hiddenSelect) return hiddenSelect;
      var inp = pfSelect.querySelector('input');
      if (inp) return inp;
      return pfSelect;
    }

    /* Kendo DropDownList */
    var kendo = el.closest('.k-dropdownlist');
    if (kendo) {
      if (el.closest('.k-item') || el.closest('.k-list')) return el;
      var kInp = kendo.querySelector('input, .k-input');
      if (kInp) return kInp;
      return kendo;
    }

    /* Angular Material mat-select */
    var matS = el.closest('mat-select, [role="listbox"]');
    if (matS) {
      if (el.closest('.mat-option') || el.getAttribute('role') === 'option') return el;
      return matS;
    }

    /* Angular Material datepicker - resolve inner span/td to the clickable <button> parent */
    var matCell = el.closest('.mat-calendar-body-cell-content');
    if (matCell) return matCell.closest('button') || matCell;
    var matPeriod = el.closest('.mat-calendar-period-button');
    if (matPeriod) return matPeriod;
    var matNav = el.closest('.mat-calendar-previous-button, .mat-calendar-next-button');
    if (matNav) return matNav;

    /* Generic rules */
    if (el.id) return el;

    if (tag === 'label') {
      var forId = el.getAttribute('for');
      if (forId) {
        var forEl = document.getElementById(forId);
        if (forEl) return forEl;
      }
      var nestedInput = el.querySelector('input, select, textarea');
      if (nestedInput) return nestedInput;
    }

    if (tag === 'div' || tag === 'span' || tag === 'li' || tag === 'body' || tag === 'td') {
      var container = el.closest('[class*="combobox" i], [class*="ui-autocomplete" i], [class*="ui-combobox" i]');
      if (container) {
        var inp = container.querySelector('input.ui-autocomplete-input, input.combobox, input[id], select[id]');
        if (inp) return inp;
        return container;
      }

      var meaningful = el.querySelector('input[id]:not([id=""]), select[id]:not([id=""]), button[id]:not([id=""]), a[id]:not([id=""]), textarea[id]:not([id=""])');
      if (meaningful) return meaningful;
      meaningful = el.querySelector('[data-testid], [data-test], [aria-label]');
      if (meaningful) return meaningful;
    }

    return el;
  }

  function createUI() {
    var container = document.createElement('div');
    container.id = 'tf-overlay';

    var base = 'all:initial;position:fixed;z-index:2147483647;font-family:-apple-system,BlinkMacSystemFont,sans-serif;font-size:13px;';
    container.style.cssText = base + 'top:12px;right:12px;background:#1a1a2e;color:#fff;padding:0;border-radius:10px;box-shadow:0 8px 24px rgba(0,0,0,0.4);min-width:260px;overflow:hidden;cursor:move;';

    container.innerHTML =
      '<div id="tf-header" style="display:flex;align-items:center;padding:10px 14px;background:#16213e;gap:8px;">' +
        '<span id="tf-rec-dot" style="color:#e94560;font-size:10px;">\u25CF</span>' +
        '<span style="flex:1;font-weight:600;font-size:13px;">' + NAME + '</span>' +
        '<button id="tf-hide-btn" style="background:0;border:1px solid #555;color:#8899aa;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:11px;">\u2013</button>' +
        '<button id="tf-pause-btn" style="background:0;border:1px solid #0f3460;color:#a0a0b0;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:11px;">\u23F8</button>' +
        '<button id="tf-stop-btn" style="background:0;border:1px solid #e94560;color:#e94560;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:11px;">\u2B05</button>' +
      '</div>' +
      '<div id="tf-body" style="padding:8px 14px 10px;">' +
        '<div id="tf-status" style="color:#4ecca3;font-size:11px;font-weight:500;">Gravando...</div>' +
        '<div style="display:flex;gap:12px;margin-top:6px;font-size:11px;color:#8899aa;">' +
          '<span>Passos: <strong id="tf-step-count" style="color:#fff;">0</strong></span>' +
          '<span>Asserts: <strong id="tf-assert-count" style="color:#ffd93d;">0</strong></span>' +
        '</div>' +
        '<div id="tf-assert-menu" style="display:none;border-top:1px solid #0f3460;padding:8px 0 0;margin-top:6px;">' +
          '<div style="font-size:11px;color:#8899aa;margin-bottom:4px;">Assert sobre:</div>' +
          '<div id="tf-assert-target" style="font-size:10px;color:#4ecca3;margin-bottom:6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;"></div>' +
          '<div style="display:flex;gap:4px;flex-wrap:wrap;">' +
            '<button class="tf-assert-btn" data-type="textual" style="background:#0f3460;border:0;color:#fff;border-radius:4px;padding:3px 8px;cursor:pointer;font-size:11px;">\uD83D\uDD0D Texto</button>' +
            '<button class="tf-assert-btn" data-type="estado" style="background:#0f3460;border:0;color:#fff;border-radius:4px;padding:3px 8px;cursor:pointer;font-size:11px;">\u2328 Estado</button>' +
            '<button class="tf-assert-btn" data-type="visivel" style="background:#0f3460;border:0;color:#fff;border-radius:4px;padding:3px 8px;cursor:pointer;font-size:11px;">\uD83D\uDC41 Vis\u00EDvel</button>' +
            '<button class="tf-assert-btn" data-type="automatico" style="background:#0f3460;border:0;color:#fff;border-radius:4px;padding:3px 8px;cursor:pointer;font-size:11px;">\uD83E\uDD16 Auto</button>' +
          '</div>' +
          '<div style="margin-top:4px;">' +
            '<button id="tf-assert-cancel" style="background:0;border:1px solid #555;color:#aaa;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:10px;">Cancelar</button>' +
          '</div>' +
        '</div>' +
        '<div style="margin-top:6px;font-size:10px;color:#5a6a7a;border-top:1px solid #0f3460;padding-top:6px;">' +
          '<span>Shift+P pausa | Shift+H ocultar | Shift+A assert | Shift+S parar</span>' +
        '</div>' +
      '</div>';

    document.body.appendChild(container);

    var style = document.createElement('style');
    style.textContent = '@keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.3; } }';
    document.head.appendChild(style);

    function makeDraggable(el) {
      var x1 = 0, y1 = 0, x2 = 0, y2 = 0;
      el.onmousedown = function(e) {
        e.preventDefault();
        x1 = e.clientX; y1 = e.clientY;
        document.onmousemove = function(ev) {
          ev.preventDefault();
          x2 = x1 - ev.clientX; y2 = y1 - ev.clientY;
          x1 = ev.clientX; y1 = ev.clientY;
          el.style.top = (el.offsetTop - y2) + 'px';
          el.style.right = 'auto';
          el.style.left = (el.offsetLeft - x2) + 'px';
        };
        document.onmouseup = function() { document.onmousemove = null; document.onmouseup = null; };
      };
    }
    makeDraggable(container);

    var hideBtn = document.getElementById('tf-hide-btn');
    if (hideBtn) {
      hideBtn.addEventListener('click', function() {
        toggleOverlay();
      });
    }

    var pauseBtn = document.getElementById('tf-pause-btn');
    if (pauseBtn) {
      pauseBtn.addEventListener('click', function() {
        window.__tfCommands.push('TOGGLE_PAUSE');
      });
    }

    var stopBtn = document.getElementById('tf-stop-btn');
    if (stopBtn) {
      stopBtn.addEventListener('click', function() {
        window.__tfCommands.push('STOP');
      });
    }

    setupAssertMenu();
  }

  var overlayVisible = true;

  function toggleOverlay() {
    var container = document.getElementById('tf-overlay');
    if (!container) return;
    overlayVisible = !overlayVisible;
    container.style.display = overlayVisible ? '' : 'none';
  }

  function setupAssertMenu() {
    document.querySelectorAll('.tf-assert-btn').forEach(function(btn) {
      btn.addEventListener('click', function(e) {
        e.stopPropagation();
        var assertType = btn.getAttribute('data-type');
        var el = window.__tfAssertElement;
        if (!el) return;

        var menu = document.getElementById('tf-assert-menu');
        if (!menu) return;

        var attrs = captureAttributes(el);
        var selector = menu.getAttribute('data-selector') || getSelector(el);
        var tagName = menu.getAttribute('data-tagname') || (el.tagName || '').toLowerCase();
        var text = menu.getAttribute('data-text') || (el.textContent || '').trim().slice(0, 120);
        var value = menu.getAttribute('data-value') || el.value || '';
        var tagInfo = getTagInfo(el);

        var expected = getExpectedValue(el, assertType);
        var state = detectElementState(el);

        addTFStep({
          action: 'assert',
          assert_type: assertType,
          assert_state: state,
          expected_value: expected,
          tagName: tagName,
          selector: selector,
          tagInfo: tagInfo,
          text: text,
          value: value,
          attrs: attrs
        });
        incrementAssertCount();
        hideAssertMenu();
      });
    });

    var cancelBtn = document.getElementById('tf-assert-cancel');
    if (cancelBtn) {
      cancelBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        hideAssertMenu();
      });
    }
  }

  function hideAssertMenu() {
    var menu = document.getElementById('tf-assert-menu');
    if (menu) menu.style.display = 'none';
    var status = document.getElementById('tf-status');
    if (status) status.textContent = 'Gravando...';
    var dot = document.getElementById('tf-rec-dot');
    if (dot) dot.style.color = '#e94560';
    window.__tfAssertWaiting = false;
    window.__tfAssertElement = null;
  }

  function incrementAssertCount() {
    var c = document.getElementById('tf-assert-count');
    if (c) {
      var current = parseInt(c.textContent || '0', 10);
      c.textContent = current + 1;
    }
  }

  function highlightElement(el) {
    if (!el) return;
    var prev = {outline: el.style.outline, outlineOffset: el.style.outlineOffset};
    el.style.outline = '2px solid #e94560';
    el.style.outlineOffset = '2px';
    setTimeout(function() {
      if (el) {
        el.style.outline = prev.outline;
        el.style.outlineOffset = prev.outlineOffset;
      }
    }, 1500);
  }

  function showAssertMenu(el) {
    var menu = document.getElementById('tf-assert-menu');
    var target = document.getElementById('tf-assert-target');
    if (!menu || !target) return;
    var tag = (el.tagName || '').toLowerCase();
    var tagInfo = getTagInfo(el);
    var text = (el.textContent || '').trim().slice(0, 50);
    target.textContent = tagInfo + (text ? ' - "' + text + '"' : '');
    menu.style.display = 'block';
    var attrs = captureAttributes(el);
    menu.setAttribute('data-selector', generateBestSelector(el, tag, attrs, text, el.value || ''));
    menu.setAttribute('data-tagname', (el.tagName || '').toLowerCase());
    menu.setAttribute('data-text', (el.textContent || '').trim().slice(0, 120));
    menu.setAttribute('data-value', el.value || '');
  }

  if (MODE !== 'shortcuts') {
    createUI();
  }

  /* --- Event listeners (always active) --- */

  /* Dedup guard: skip change handler if pointerup already captured this element */
  var _tf_lastCaptured = null;
  var _tf_lastCapturedTime = 0;

  function _tf_wasRecentlyCaptured(el) {
    var now = Date.now();
    if (!el || !_tf_lastCaptured) return false;
    if (el === _tf_lastCaptured && (now - _tf_lastCapturedTime) < 600) return true;
    return false;
  }

  function _tf_markCaptured(el) {
    _tf_lastCaptured = el;
    _tf_lastCapturedTime = Date.now();
  }

  function capturePointerUp(e) {
    try {
      if (e.button !== 0) return;
      var origEl = e.target;
      if (!origEl) return;
      var el = resolveElement(origEl);
      if (!el) return;
      if (el.closest('#tf-overlay')) return;

      if (window.__tfAssertWaiting) {
        e.preventDefault();
        e.stopPropagation();
        window.__tfAssertElement = el;
        highlightElement(el);
        showAssertMenu(el);
        return;
      }

      var attrs = captureAttributes(el);
      var tag = (el.tagName || '').toLowerCase();
      var text = (el.textContent || '').trim().slice(0, 120);
      var value = el.value || '';
      var strategies = generateStrategies(el, tag, attrs, text, value);
      var primarySelector = strategies.length > 0 ? strategies[0].selector : generateBestSelector(el, tag, attrs, text, value);
      var fallbackSelectors = strategies.slice(1).map(function(s) { return s.selector; });
      var tagInfo = getTagInfo(el);
      var rawSelector = getSelector(el);

      if (origEl.disabled && (origEl.tagName === 'INPUT' || origEl.tagName === 'SELECT' || origEl.tagName === 'TEXTAREA' || origEl.tagName === 'BUTTON')) {
        var disabledEl = origEl;
        var coords = {clientX: e.clientX, clientY: e.clientY, screenX: e.screenX, screenY: e.screenY, bubbles: true, cancelable: true, view: window};
        disabledEl.dispatchEvent(new MouseEvent('mousedown', coords));
        disabledEl.dispatchEvent(new MouseEvent('mouseup', coords));
        disabledEl.dispatchEvent(new MouseEvent('click', coords));
      }

      /* If clicked a text-like input that already has a real value, fill immediately */
      if (_tf_isInput(el) && (el.value || '').trim()) {
        var v = el.value.trim();
        if (v !== _tf_lastFillValue && !_tf_isPromptText(v, el.placeholder)) {
          _tf_lastFillValue = v;
          var key1 = el.id || el.name || el.className || 'input_0';
          _tf_knownValues[key1] = v;
          var a1 = captureAttributes(el);
          var str1 = generateStrategies(el, tag, a1, a1.labelText || el.placeholder || '', v);
          var ps1 = str1.length > 0 ? str1[0].selector : '';
          var fb1 = str1.slice(1).map(function(s) { return s.selector; });
          highlightElement(el);
          addTFStep({
            action: 'fill', tagName: tag, selector: ps1,
            fallbacks: fb1, strategies: str1,
            tagInfo: getTagInfo(el), value: v,
            text: a1.labelText || el.placeholder || '', attrs: a1
          });
        }
      }

      addTFStep({
        action: 'click',
        tagName: tag,
        selector: primarySelector,
        fallbacks: fallbackSelectors,
        strategies: strategies,
        rawSelector: rawSelector,
        tagInfo: tagInfo,
        text: text,
        value: value,
        attrs: attrs
      });
      _tf_markCaptured(el);

      /* Detect autocomplete/combobox/suggestion click — capture final input value */
      var isSuggestion = origEl.closest && (origEl.closest('.ui-menu-item, .ui-autocomplete, li.ui-menu-item, .ui-autocomplete-item, .ui-autocomplete-panel') || origEl.closest('[role="listbox"]') || origEl.closest('[class*="ui-menu"]') || origEl.closest('.ui-selectonemenu-item, .ui-selectonemenu-panel') || origEl.closest('.k-item, .k-popup') || origEl.closest('.mat-option'));
      if (isSuggestion) {
        var focused = document.activeElement;
        if (focused && _tf_resolveToInput(focused)) {
          setTimeout(function() {
            var fv = (focused.value || '').trim();
            if (fv && fv !== _tf_lastFillValue) {
              _tf_lastFillValue = fv;
              var key2 = focused.id || focused.name || focused.className || 'input_0';
              _tf_knownValues[key2] = fv;
              var a2 = captureAttributes(focused);
              var t2 = focused.tagName.toLowerCase();
              var str2 = generateStrategies(focused, t2, a2, a2.labelText || focused.placeholder || '', fv);
              var ps2 = str2.length > 0 ? str2[0].selector : '';
              var fb2 = str2.slice(1).map(function(s) { return s.selector; });
              highlightElement(focused);
              addTFStep({
                action: 'fill', tagName: t2, selector: ps2,
                fallbacks: fb2, strategies: str2,
                tagInfo: getTagInfo(focused), value: fv,
                text: a2.labelText || focused.placeholder || '', attrs: a2
              });
            }
          }, 300);
        }
      }
    } catch(ex) { console.warn('[TestForge] pointerup error:', ex); }
  }
  window.addEventListener('pointerup', capturePointerUp, true);

  /* Prevent native click behavior during assert mode (checkbox toggle, panel open, etc.) */
  window.addEventListener('pointerdown', function(e) {
    if (window.__tfAssertWaiting) {
      e.preventDefault();
      e.stopPropagation();
    }
  }, true);

  document.addEventListener('change', function(e) {
    var el = e.target;
    if (!el || el.closest('#tf-overlay')) return;
    var tag = (el.tagName || '').toLowerCase();
    if (tag === 'select') {
      var attrs = captureAttributes(el);
      var opt = el.options[el.selectedIndex];
      var text = opt ? opt.text : '';
      var strategies = generateStrategies(el, tag, attrs, text, el.value || '');
      var selector = strategies.length > 0 ? strategies[0].selector : '';
      var fallbacks = strategies.slice(1).map(function(s) { return s.selector; });
      var tagInfo = getTagInfo(el);
      highlightElement(el);
      addTFStep({
        action: 'select',
        tagName: tag,
        selector: selector,
        fallbacks: fallbacks,
        strategies: strategies,
        tagInfo: tagInfo,
        text: text,
        value: el.value || '',
        attrs: attrs
      });
    }
    if (tag === 'input' && (el.type === 'radio' || el.type === 'checkbox')) {
      if (_tf_wasRecentlyCaptured(el)) return;
      var attrs = captureAttributes(el);
      var selector = generateBestSelector(el, tag, attrs, attrs.labelText || '', el.value || '');
      var tagInfo = getTagInfo(el);
      highlightElement(el);
      addTFStep({
        action: 'click',
        tagName: tag,
        selector: selector,
        tagInfo: tagInfo,
        text: attrs.labelText || '',
        value: el.type === 'checkbox' ? (el.checked ? 'true' : 'false') : (el.value || ''),
        attrs: attrs
      });
      _tf_markCaptured(el);
    }
    if (tag === 'input' && el.type === 'file') {
      var files = el.files;
      if (files && files.length > 0) {
        var fileList = [];
        for (var fi = 0; fi < files.length; fi++) {
          var f = files[fi];
          fileList.push({name: f.name, type: f.type || 'application/octet-stream', size: f.size});
        }
        var attrs = captureAttributes(el);
        var selector = generateBestSelector(el, tag, '', el.value || '');
        var tagInfo = getTagInfo(el);
        highlightElement(el);
        addTFStep({
          action: 'upload',
          tagName: tag,
          selector: selector,
          tagInfo: tagInfo,
          text: JSON.stringify(fileList),
          value: files[0].name,
          attrs: attrs
        });
      }
    }
  }, true);

  /* --- Fill detection: unified (input + keydown + change + polling) --- */
  var _tf_fillEl = null;
  var _tf_fillVal = '';
  var _tf_fillTimer = null;
  var _tf_lastFillValue = '';

  function _tf_isInput(el) {
    if (!el || el.closest('#tf-overlay')) return false;
    var tag = (el.tagName || '').toLowerCase();
    if (tag !== 'input' && tag !== 'textarea') return false;
    return el.type !== 'checkbox' && el.type !== 'radio' && el.type !== 'file';
  }

  function _tf_resolveToInput(el) {
    if (!el || (el.closest && el.closest('#tf-overlay'))) return null;
    var tag = (el.tagName || '').toLowerCase();
    if ((tag === 'input' || tag === 'textarea') && el.type !== 'checkbox' && el.type !== 'radio' && el.type !== 'file') {
      return el;
    }
    if (el.shadowRoot) {
      var active = el.shadowRoot.activeElement;
      if (active) {
        var aTag = active.tagName.toLowerCase();
        if ((aTag === 'input' || aTag === 'textarea') && active.type !== 'checkbox' && active.type !== 'radio' && active.type !== 'file') {
          return active;
        }
      }
    }
    return null;
  }

  function _tf_scheduleFillCheck(el) {
    if (!el) return;
    _tf_fillEl = el;
    if (_tf_fillTimer) clearTimeout(_tf_fillTimer);
    _tf_fillTimer = setTimeout(_tf_doFillCheck, 500);
  }

  function _tf_doFillCheck() {
    _tf_fillTimer = null;
    var el = _tf_fillEl;
    if (!el) return;
    var val = (el.value || '').trim();
    if (val && val !== _tf_lastFillValue) {
      _tf_lastFillValue = val;
      var key = el.id || el.name || el.className || 'input_0';
      _tf_knownValues[key] = val;
      var attrs = captureAttributes(el);
      var tag = el.tagName.toLowerCase();
      var strategies = generateStrategies(el, tag, attrs, attrs.labelText || el.placeholder || '', val);
      var selector = strategies.length > 0 ? strategies[0].selector : '';
      var fallbacks = strategies.slice(1).map(function(s) { return s.selector; });
      var tagInfo = getTagInfo(el);
      highlightElement(el);
      addTFStep({
        action: 'fill',
        tagName: tag,
        selector: selector,
        fallbacks: fallbacks,
        strategies: strategies,
        tagInfo: tagInfo,
        value: val,
        text: attrs.labelText || el.placeholder || '',
        attrs: attrs
      });
    }
  }

  document.addEventListener('input', function(e) {
    var input = _tf_resolveToInput(e.target);
    if (input) _tf_scheduleFillCheck(input);
  }, true);

  document.addEventListener('change', function(e) {
    var input = _tf_resolveToInput(e.target);
    if (input) _tf_scheduleFillCheck(input);
  }, true);

  document.addEventListener('keydown', function(e) {
    var input = _tf_resolveToInput(e.target);
    if (input && e.key.length === 1) {
      _tf_scheduleFillCheck(input);
    }
  }, true);

  /* Force change+blur on active input on mousedown outside it —
     commits Angular/RxJS FormControl value BEFORE target click handler.
     Fix: mask fields where Angular processes blur asynchronously,
     causing calculation to run with stale FormControl value. */
  document.addEventListener('mousedown', function(e) {
    if (window.__tfAssertWaiting) return;
    var active = document.activeElement;
    if (!active) return;
    var tag = (active.tagName || '').toLowerCase();
    if (tag !== 'input' && tag !== 'textarea') return;
    if (active.type === 'checkbox' || active.type === 'radio' || active.type === 'file') return;
    if (active === e.target || active.contains(e.target)) return;
    if (e.target.closest && e.target.closest('#tf-overlay')) return;
    active.dispatchEvent(new Event('change', {bubbles: true}));
    active.dispatchEvent(new Event('blur', {bubbles: true}));
  }, true);

  document.addEventListener('keydown', function(e) {
    var key = e.key.toUpperCase();
    if (e.shiftKey && key === 'P') {
      window.__tfCommands.push('TOGGLE_PAUSE');
      e.preventDefault();
    }
    if (e.shiftKey && key === 'S') {
      window.__tfCommands.push('STOP');
      e.preventDefault();
    }
    if (e.shiftKey && key === 'H') {
      toggleOverlay();
      var status = document.getElementById('tf-status');
      if (status) status.textContent = overlayVisible ? 'Gravando...' : 'Oculto (Shift+H)';
      e.preventDefault();
    }
    if (e.shiftKey && key === 'A') {
      if (!window.__tfAssertWaiting) {
        window.__tfAssertWaiting = true;
        window.__tfCommands.push('ASSERT');
        var status = document.getElementById('tf-status');
        if (status) status.textContent = 'Clique em um elemento para assert';
        var dot = document.getElementById('tf-rec-dot');
        if (dot) dot.style.color = '#ffd93d';
      }
      e.preventDefault();
    }
  }, true);

  /* --- Drag-and-drop capture (INP-005) --- */
  var _tf_dragSource = null;
  window.addEventListener('dragstart', function(e) {
    if (e.target && e.target.closest && e.target.closest('#tf-overlay')) return;
    _tf_dragSource = e.target;
  }, true);
  window.addEventListener('drop', function(e) {
    if (!_tf_dragSource) return;
    var targetEl = e.target;
    if (!targetEl || (targetEl.closest && targetEl.closest('#tf-overlay'))) { _tf_dragSource = null; return; }
    var sourceEl = _tf_dragSource;
    _tf_dragSource = null;
    var srcAttrs = captureAttributes(sourceEl);
    var srcTag = sourceEl.tagName.toLowerCase();
    var srcText = (sourceEl.textContent || '').trim().slice(0, 120);
    var srcSelector = generateBestSelector(sourceEl, srcTag, srcAttrs, srcText, sourceEl.value || '');
    var tgtAttrs = captureAttributes(targetEl);
    var tgtTag = targetEl.tagName.toLowerCase();
    var tgtText = (targetEl.textContent || '').trim().slice(0, 120);
    var tgtSelector = generateBestSelector(targetEl, tgtTag, tgtAttrs, tgtText, targetEl.value || '');
    addTFStep({
      action: 'drag',
      tagName: srcTag,
      selector: srcSelector,
      rawSelector: getSelector(sourceEl),
      tagInfo: getTagInfo(sourceEl),
      text: srcText.slice(0, 60) + ' -> ' + tgtText.slice(0, 60),
      value: tgtSelector,
      attrs: srcAttrs
    });
  }, true);

  /* --- Periodic fill scan: catch JS-masked inputs that miss events --- */
  var _tf_knownValues = {};

  function _tf_isPromptText(val, placeholder) {
    if (!val) return true;
    if (placeholder && val === placeholder) return true;
    var prompts = ['informe', 'selecione', 'digite', 'escolha', 'uf', 'selecionar'];
    var lower = val.toLowerCase();
    for (var pp = 0; pp < prompts.length; pp++) {
      if (lower === prompts[pp] || lower.indexOf(prompts[pp]) === 0) return true;
    }
    return false;
  }

  function _tf_findInputs(root) {
    var result = [];
    var inputs = root.querySelectorAll('input:not([type="checkbox"]):not([type="radio"]):not([type="file"]):not([type="submit"]):not([type="button"]):not([type="hidden"]):not([type="password"]), textarea');
    for (var fi = 0; fi < inputs.length; fi++) result.push(inputs[fi]);
    var all = root.querySelectorAll('*');
    for (var fi = 0; fi < all.length; fi++) {
      if (all[fi].shadowRoot) {
        var childInputs = _tf_findInputs(all[fi].shadowRoot);
        for (var cj = 0; cj < childInputs.length; cj++) result.push(childInputs[cj]);
      }
    }
    return result;
  }

  function _tf_scanInputs() {
    try {
      var inputs = _tf_findInputs(document);
      for (var pi = 0; pi < inputs.length; pi++) {
        var inp = inputs[pi];
        if (inp.closest && inp.closest('#tf-overlay')) continue;
        var val = (inp.value || '').trim();
        if (!val || _tf_isPromptText(val, inp.placeholder)) continue;
        var key = inp.id || inp.name || inp.className || 'input_' + pi;
        if (_tf_knownValues[key] === undefined) {
          _tf_knownValues[key] = val;
        } else if (_tf_knownValues[key] !== val && val !== _tf_lastFillValue) {
          _tf_lastFillValue = val;
          _tf_knownValues[key] = val;
          var a = captureAttributes(inp);
          var t = inp.tagName.toLowerCase();
          var str = generateStrategies(inp, t, a, a.labelText || inp.placeholder || '', val);
          var ps = str.length > 0 ? str[0].selector : '';
          var fb = str.slice(1).map(function(s) { return s.selector; });
          highlightElement(inp);
          addTFStep({
            action: 'fill', tagName: t, selector: ps,
            fallbacks: fb, strategies: str,
            tagInfo: getTagInfo(inp), value: val,
            text: a.labelText || inp.placeholder || '', attrs: a
          });
        }
      }
    } catch(ex) { /* periodic scan error */ }
  }
  /* Delay first scan 3s to let page JS initialize, then scan every 2s */
  setTimeout(function() { _tf_scanInputs(); setInterval(_tf_scanInputs, 2000); }, 3000);

  /* Inject overlay into same-origin child iframes */
  if (!_tf_isIframe) {
    setTimeout(function _tf_injectIframes() {
      var iframes = document.querySelectorAll('iframe');
      for (var fi = 0; fi < iframes.length; fi++) {
        try {
          var iWin = iframes[fi].contentWindow;
          if (iWin && !iWin.__tfReady) {
            var s = iframes[fi].contentDocument.createElement('script');
            s.textContent = '(' + inject.toString() + ')();';
            iframes[fi].contentDocument.head.appendChild(s);
          }
        } catch(e) { /* cross-origin iframe, skip */ }
      }
    }, 1000);
  }

  window.__tfReady = true;
  } catch(e) { console.warn('[TestForge] overlay failed:', e); }
})();
