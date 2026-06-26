// TestForge Recorder Overlay — injected into page via add_init_script
// Captures user interactions, assert mode, keyboard shortcuts, postback detection
// Identity attributes only (no CSS path generation — Playwright compiler handles locators)

(function() {
  "use strict";

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
    var elText = (el.textContent||'').trim().substring(0,200) || null;
    // Simple CSS path: tag + id (no full DOM walk)
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
    return {
      tag: (el.tagName||'').toLowerCase(),
      text: elText,
      role: el.getAttribute('role') || null,
      accessible_name: el.getAttribute('aria-label') || el.getAttribute('title') || (allAttrs['aria-label'] || null),
      element_id: el.id || null,
      name: el.getAttribute('name') || null,
      test_id: el.getAttribute('data-testid') || el.getAttribute('data-test-id') || null,
      placeholder: el.getAttribute('placeholder') || null,
      label: labelEl ? labelEl.textContent.trim() : null,
      class_list: classList,
      attributes: allAttrs,
      type: el.getAttribute('type') || null,
      value: (el.value||'').substring(0,100) || null,
      href: el.getAttribute('href') || null,
      onclick: el.getAttribute('onclick') || null,
      css_path: cssParts.join(' > ') || ''
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
    window.__tfEventQueue.push({
      event_id: 'evt_' + String(++window.__tfEventCounter).padStart(5,'0'),
      type: type,
      timestamp: new Date().toISOString(),
      url: window.location.href,
      page_title: document.title,
      target: target,
      value: (el && el.value) ? el.value.substring(0,200) : null
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

  // ---- Value mutation setter hooks ----
  function _hookValue(proto) {
    var orig = Object.getOwnPropertyDescriptor(proto, 'value');
    if (!orig || !orig.set) return;
    Object.defineProperty(proto, 'value', {
      get: orig.get,
      set: function(v) {
        orig.set.call(this, v);
        window.__tfValueMutationQueue.push({
          type: 'value_mutation',
          timestamp: new Date().toISOString(),
          fingerprint: this.tagName.toLowerCase() + '#' + (this.id||'') + '[name=' + (this.name||'') + ']',
          value: String(v).substring(0, 200)
        });
      },
      configurable: true
    });
  }
  _hookValue(HTMLInputElement.prototype);
  _hookValue(HTMLSelectElement.prototype);
  _hookValue(HTMLTextAreaElement.prototype);

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
        attributeFilter: ['aria-valuenow', 'aria-valuetext', 'contenteditable']
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
    if (el && el.tagName === 'SELECT') return;
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
    var key = _fillKey(el);
    var val = (el.value || el.textContent || '').trim();
    if (window.__tfLastFillValue[key] === val) return;
    window.__tfLastFillValue[key] = val;
    _pushEvent('fill', el);
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
      _pushEvent(evtType, el);
    }
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
        window.__tfEventQueue.push({
          event_id: 'evt_' + String(++window.__tfEventCounter).padStart(5,'0'),
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
  window.__tfFieldSnapshotInterval = setInterval(function() { _tf_snapshotFields(); }, 2000);
})();
