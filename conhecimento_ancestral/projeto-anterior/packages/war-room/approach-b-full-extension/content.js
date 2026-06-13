(function () {
  'use strict';

  const WS_URL = 'ws://localhost:9199';

  let state = {
    recording: false,
    steps: [],
    ws: null,
    reconnectAttempts: 0,
    maxReconnect: 10,
    pageTechnology: null,
    currentUrl: location.href,
  };

  /* ---- Background sync ---- */
  function bgSend(msg) {
    return chrome.runtime.sendMessage(msg).catch(() => {});
  }

  function bgFetchState() {
    return new Promise((resolve) => {
      chrome.runtime.sendMessage({ type: 'getState' }, (res) => {
        resolve(res?.state || null);
      });
    });
  }

  /* ---- Overlay UI ---- */
  const overlay = document.createElement('div');
  overlay.id = 'testforge-overlay';

  let isDragging = false, dragOffsetX = 0, dragOffsetY = 0;

  overlay.innerHTML = `
    <div id="testforge-header">
      <span id="testforge-title">⛓ TestForge</span>
      <span id="testforge-status" class="offline"></span>
    </div>
    <div id="testforge-body">
      <div id="testforge-toolbar">
        <button id="tf-record-btn" class="testforge-btn">⏺ Gravar</button>
        <button id="tf-assert-btn" class="testforge-btn" disabled>✓ Assert</button>
        <button id="tf-finalize-btn" class="testforge-btn primary" disabled>⏹ Finalizar</button>
      </div>
      <ul id="testforge-step-list"></ul>
    </div>
    <div id="testforge-footer">
      <span id="tf-step-count">0 passos</span>
      <button id="testforge-clear-btn">Limpar</button>
    </div>
  `;

  document.documentElement.appendChild(overlay);

  /* ---- Drag ---- */
  const header = overlay.querySelector('#testforge-header');
  header.addEventListener('mousedown', (e) => {
    isDragging = true;
    dragOffsetX = e.clientX - overlay.getBoundingClientRect().left;
    dragOffsetY = e.clientY - overlay.getBoundingClientRect().top;
    overlay.style.cursor = 'grabbing';
  });
  document.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    overlay.style.left = (e.clientX - dragOffsetX) + 'px';
    overlay.style.top = (e.clientY - dragOffsetY) + 'px';
    overlay.style.right = 'auto';
  });
  document.addEventListener('mouseup', () => {
    isDragging = false;
    overlay.style.cursor = '';
  });

  /* ---- DOM helpers ---- */
  function getSelector(el) {
    if (!el || el === document) return 'html';
    if (el.id) return '#' + CSS.escape(el.id);
    const testId = el.getAttribute('data-testid') || el.getAttribute('data-test-id');
    if (testId) return `[data-testid="${CSS.escape(testId)}"]`;
    return getUniqueSelector(el);
  }

  function getUniqueSelector(el) {
    const path = [];
    let current = el;
    while (current && current !== document.body && current !== document.documentElement) {
      let selector = current.tagName.toLowerCase();
      if (current.id) { path.unshift('#' + CSS.escape(current.id)); break; }
      if (current.className && typeof current.className === 'string') {
        const classes = current.className.trim().split(/\s+/).filter(c => c && !c.startsWith('tf-') && !c.startsWith('testforge'));
        if (classes.length) selector += '.' + classes.map(c => CSS.escape(c)).join('.');
      }
      const parent = current.parentElement;
      if (parent) {
        const siblings = Array.from(parent.children).filter(s => s.tagName === current.tagName);
        if (siblings.length > 1) {
          const idx = siblings.indexOf(current) + 1;
          selector += `:nth-of-type(${idx})`;
        }
      }
      path.unshift(selector);
      current = current.parentElement;
    }
    return path.join(' > ');
  }

  function getDomSnapshot(el, depth = 3) {
    if (!el || depth <= 0) return '';
    const clone = el.cloneNode(true);
    const walker = document.createTreeWalker(clone, NodeFilter.SHOW_ELEMENT, null, false);
    let node;
    const removeNodes = [];
    while ((node = walker.nextNode())) {
      if (node.children.length === 0 && !node.textContent.trim()) {
        removeNodes.push(node);
        continue;
      }
      const attrs = node.attributes;
      for (let i = attrs.length - 1; i >= 0; i--) {
        if (['style', 'onclick', 'onchange', 'onsubmit', 'onmouseover', 'onmouseout'].includes(attrs[i].name)) {
          node.removeAttribute(attrs[i].name);
        }
      }
    }
    removeNodes.forEach(n => n.parentNode?.removeChild(n));
    return clone.outerHTML.substring(0, 2000);
  }

  function getSourceElement(el) {
    if (el.nodeType === Node.TEXT_NODE) return el.parentElement;
    return el;
  }

  function detectTechnology() {
    const libs = {
      'angular': () => !!window.ng || !!document.querySelector('[ng-app], [ng-controller]'),
      'react': () => !!document.querySelector('#root, #__next, [data-reactroot]') || !!(document.querySelector('[class^="css-"]') && document.querySelector('[class*="Mui"]')),
      'vue': () => !!document.querySelector('[v-app], [data-v-app], [v-if], [v-for]') || !!window.Vue,
      'jquery': () => !!window.jQuery,
      'svelte': () => !!document.querySelector('[svelte-h]'),
      'plain': () => true,
    };
    for (const [name, check] of Object.entries(libs)) {
      if (check()) return name;
    }
    return 'unknown';
  }

  function getElementTagInfo(el) {
    const tag = el.tagName.toLowerCase();
    const type = el.getAttribute('type') || '';
    const role = el.getAttribute('role') || '';
    const inputTypes = ['text', 'email', 'password', 'number', 'tel', 'url', 'search', 'date', 'textarea'];
    if (tag === 'input' && inputTypes.includes(type)) return 'input';
    if (tag === 'input' && ['checkbox', 'radio'].includes(type)) return type;
    if (tag === 'select') return 'select';
    if (tag === 'textarea' || type === 'textarea') return 'input';
    if (tag === 'a' || role === 'link') return 'link';
    if (tag === 'button' || role === 'button' || type === 'submit' || type === 'button') return 'button';
    if (['click', 'dblclick', 'contextmenu'].includes(tag)) return 'clickable';
    return 'other';
  }

  /* ---- Step Recording ---- */
  function addStep(action, details) {
    if (!state.recording) return;

    const selector = details.selector || getSelector(details.element);
    const tagInfo = details.tagInfo || getElementTagInfo(details.element);
    const snapshot = getDomSnapshot(details.element?.closest('form, div, section') || details.element, 3);

    const step = {
      id: 'step_' + Date.now() + '_' + Math.random().toString(36).slice(2, 6),
      timestamp: new Date().toISOString(),
      action,
      selector,
      tagInfo,
      value: details.value || '',
      text: details.text || details.element?.textContent?.trim().substring(0, 100) || '',
      domSnapshot: snapshot,
      pageUrl: location.href,
      pageTechnology: state.pageTechnology,
    };

    state.steps.push(step);
    bgSend({ type: 'addStep', step });
    renderStep(step);
    sendToBridge('step:recorded', step);
  }

  function renderStep(step) {
    const list = overlay.querySelector('#testforge-step-list');
    const li = document.createElement('li');
    li.className = 'testforge-step';
    const icons = { click: '🖱', input: '⌨', select: '📋', navigate: '🔗', assert: '✓' };
    li.innerHTML = `
      <span class="step-icon">${icons[step.action] || '•'}</span>
      <span class="step-text">
        <strong>${step.action}</strong>
        ${step.text ? `"${step.text.substring(0, 60)}"` : ''}
        <div class="step-selector">${step.selector}</div>
      </span>
    `;
    list.appendChild(li);
    list.scrollTop = list.scrollHeight;
    updateCount();
  }

  function renderAllSteps(steps) {
    const list = overlay.querySelector('#testforge-step-list');
    list.innerHTML = '';
    steps.forEach(s => {
      const li = document.createElement('li');
      li.className = 'testforge-step';
      const icons = { click: '🖱', input: '⌨', select: '📋', navigate: '🔗', assert: '✓' };
      li.innerHTML = `
        <span class="step-icon">${icons[s.action] || '•'}</span>
        <span class="step-text">
          <strong>${s.action}</strong>
          ${s.text ? `"${s.text.substring(0, 60)}"` : ''}
          <div class="step-selector">${s.selector}</div>
        </span>
      `;
      list.appendChild(li);
    });
    list.scrollTop = list.scrollHeight;
    updateCount();
  }

  function updateCount() {
    overlay.querySelector('#tf-step-count').textContent = `${state.steps.length} passos`;
  }

  /* ---- Event Listeners ---- */
  function handleClick(e) {
    if (!state.recording) return;
    const el = getSourceElement(e.target);
    const tagInfo = getElementTagInfo(el);
    if (tagInfo === 'other') return;
    addStep('click', { element: el, tagInfo });
  }

  function handleChange(e) {
    if (!state.recording) return;
    const el = getSourceElement(e.target);
    const tag = el.tagName.toLowerCase();
    if (tag === 'select') {
      addStep('select', {
        element: el,
        value: el.value,
        text: el.options[el.selectedIndex]?.text,
        tagInfo: 'select',
      });
    }
  }

  function handleInput(e) {
    if (!state.recording) return;
    const el = getSourceElement(e.target);
    const tagInfo = getElementTagInfo(el);
    if (tagInfo !== 'input') return;
    if (e.inputType === 'insertText' && el.value.length <= 1) {
      addStep('input', { element: el, value: el.value, tagInfo });
    }
  }

  function handleNavigation() {
    if (!state.recording) return;
    const url = location.href;
    if (url === state.currentUrl) return;
    state.currentUrl = url;
    if (!state.pageTechnology) {
      state.pageTechnology = detectTechnology();
    }
    addStep('navigate', {
      element: document.body,
      value: url,
      text: document.title,
    });
    sendToBridge('navigation:detected', {
      url,
      title: document.title,
      technology: state.pageTechnology,
    });
  }

  /* ---- Navigation detection (SPA + regular) ---- */
  let lastUrl = location.href;
  const observer = new MutationObserver(() => {
    const url = location.href;
    if (url !== lastUrl) {
      lastUrl = url;
      setTimeout(handleNavigation, 300);
    }
  });
  observer.observe(document, { subtree: true, childList: true });

  window.addEventListener('popstate', handleNavigation);
  window.addEventListener('hashchange', handleNavigation);

  /* ---- WebSocket ---- */
  function connectWebSocket() {
    if (state.ws?.readyState === WebSocket.OPEN) return;
    try {
      state.ws = new WebSocket(WS_URL);
    } catch (err) {
      setStatus('offline');
      scheduleReconnect();
      return;
    }

    state.ws.onopen = () => {
      state.reconnectAttempts = 0;
      setStatus('paused');
      console.log('[TestForge] Bridge conectado');
    };

    state.ws.onmessage = (msg) => {
      try {
        const cmd = JSON.parse(msg.data);
        handleCommand(cmd);
      } catch (err) {
        console.warn('[TestForge] Mensagem inválida:', msg.data);
      }
    };

    state.ws.onclose = () => {
      setStatus('offline');
      scheduleReconnect();
    };

    state.ws.onerror = () => {
      state.ws?.close();
    };
  }

  function scheduleReconnect() {
    if (state.reconnectAttempts >= state.maxReconnect) return;
    state.reconnectAttempts++;
    const delay = Math.min(1000 * Math.pow(2, state.reconnectAttempts), 30000);
    setTimeout(connectWebSocket, delay);
  }

  function sendToBridge(type, payload) {
    if (state.ws?.readyState !== WebSocket.OPEN) return;
    state.ws.send(JSON.stringify({
      type,
      id: 'msg_' + Date.now(),
      timestamp: new Date().toISOString(),
      payload,
    }));
  }

  function setStatus(status) {
    const el = overlay.querySelector('#testforge-status');
    el.className = status;
  }

  /* ---- Commands from Bridge ---- */
  function handleCommand(cmd) {
    switch (cmd.type) {
      case 'recording:start':
        startRecording(cmd.payload?.url);
        break;
      case 'recording:stop':
        stopRecording();
        break;
      case 'assert:suggest':
        suggestAssert(cmd.payload);
        break;
      case 'ping':
        sendToBridge('pong', {});
        break;
    }
  }

  function syncUI() {
    const btn = overlay.querySelector('#tf-record-btn');
    const assertBtn = overlay.querySelector('#tf-assert-btn');
    const finalBtn = overlay.querySelector('#tf-finalize-btn');

    if (state.recording) {
      btn.textContent = '⏹ Parar';
      btn.classList.add('recording');
      assertBtn.disabled = false;
      finalBtn.disabled = false;
      setStatus('recording');
    } else {
      btn.textContent = '⏺ Gravar';
      btn.classList.remove('recording');
      assertBtn.disabled = true;
      finalBtn.disabled = state.steps.length === 0;
      setStatus(state.ws?.readyState === WebSocket.OPEN ? 'paused' : 'offline');
    }

    renderAllSteps(state.steps);
  }

  function startRecording(url) {
    if (state.recording) return;
    state.recording = true;
    state.steps = [];
    state.pageTechnology = detectTechnology();
    bgSend({ type: 'setRecording', value: true });
    bgSend({ type: 'clearSteps' });
    syncUI();
    sendToBridge('navigation:detected', {
      url: location.href,
      title: document.title,
      technology: state.pageTechnology,
    });
  }

  function stopRecording() {
    state.recording = false;
    bgSend({ type: 'setRecording', value: false });
    syncUI();
  }

  function suggestAssert(payload) {
    const step = {
      id: 'assert_' + Date.now(),
      timestamp: new Date().toISOString(),
      action: 'assert',
      selector: payload?.selector || '',
      text: payload?.text || payload?.suggestedAssert || '',
      tagInfo: 'assert',
      domSnapshot: '',
      pageUrl: location.href,
      pageTechnology: state.pageTechnology,
    };
    if (state.recording) {
      state.steps.push(step);
      bgSend({ type: 'addStep', step });
      renderStep(step);
    }
    sendToBridge('step:recorded', step);
  }

  /* ---- UI Event Bindings ---- */
  overlay.querySelector('#tf-record-btn').addEventListener('click', () => {
    if (state.recording) {
      stopRecording();
    } else {
      startRecording();
    }
  });

  overlay.querySelector('#tf-assert-btn').addEventListener('click', () => {
    const sel = window.getSelection()?.toString() || '';
    const el = document.activeElement;
    const selector = el ? getSelector(el) : '';
    const text = sel || el?.textContent?.trim()?.substring(0, 100) || '';
    suggestAssert({ selector, text: text || 'assert visible', suggestedAssert: text || 'visible' });
  });

  overlay.querySelector('#tf-finalize-btn').addEventListener('click', () => {
    chrome.runtime.sendMessage({ type: 'finalizeSteps' }, (res) => {
      const finalSteps = res?.steps || state.steps;
      sendToBridge('recording:stop', { steps: finalSteps });
    });
    state.steps = [];
    state.recording = false;
    syncUI();
  });

  overlay.querySelector('#testforge-clear-btn').addEventListener('click', () => {
    state.steps = [];
    bgSend({ type: 'clearSteps' });
    overlay.querySelector('#testforge-step-list').innerHTML = '';
    updateCount();
  });

  /* ---- DOM event capture ---- */
  document.addEventListener('click', handleClick, true);
  document.addEventListener('change', handleChange, true);
  document.addEventListener('input', handleInput, true);

  /* ---- Init ---- */
  async function init() {
    state.pageTechnology = detectTechnology();
    state.currentUrl = location.href;

    const bgState = await bgFetchState();
    if (bgState) {
      state.recording = bgState.recording || false;
      state.steps = bgState.steps || [];
    }

    connectWebSocket();
    syncUI();
    console.log('[TestForge] Overlay restaurado -', state.steps.length, 'passos do background');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
