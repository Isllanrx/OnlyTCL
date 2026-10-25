(() => {
  const $ = id => document.getElementById(id);
  const KEY = { up: 11, down: 12, left: 13, right: 14, ok: 15, power: 20, enter: 68 };

  ['gesturestart', 'gesturechange', 'gestureend', 'dblclick'].forEach(t =>
    document.addEventListener(t, e => e.preventDefault(), { passive: false }));
  let lastTouchEnd = 0;
  document.addEventListener('touchend', e => {
    const now = Date.now();
    if (now - lastTouchEnd < 350 && e.target.tagName !== 'INPUT') e.preventDefault();
    lastTouchEnd = now;
  }, { passive: false });
  document.addEventListener('touchmove', e => { if (e.touches.length > 1) e.preventDefault(); }, { passive: false });

  let ws = null, retry = 300, timer = null, keepalive = null;

  function setOnline(on) {
    $('status').classList.toggle('on', on);
    if (!on) $('tcast-banner').hidden = true;
    $('status').querySelector('.label').textContent = on ? 'Conectado' : 'Reconectando';
  }

  function connect() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
    clearTimeout(timer);
    ws = new WebSocket(`ws://${location.host}/ws`);
    ws.onopen = () => {
      retry = 300;
      setOnline(true);
      clearInterval(keepalive);
      keepalive = setInterval(() => ws.readyState === WebSocket.OPEN && ws.send('p'), 20000);
      ws.send('i:list');
    };
    ws.onmessage = e => {
      if (typeof e.data !== 'string') return;
      if (e.data.startsWith('inputs:')) renderInputs(e.data.slice(7));
      else if (e.data.startsWith('status:tcast:')) $('tcast-banner').hidden = e.data.endsWith(':up');
    };
    ws.onclose = () => {
      setOnline(false);
      clearInterval(keepalive);
      if (document.visibilityState === 'visible') timer = setTimeout(connect, retry);
      retry = Math.min(retry * 2, 3000);
    };
    ws.onerror = () => ws.close();
  }

  function send(message) {
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(message);
    else connect();
    if (navigator.vibrate) navigator.vibrate(8);
  }

  const sendKey = code => send(`k:${code}`);

  let toastTimer = null;
  function toast(text) {
    const el = $('toast');
    el.textContent = text;
    el.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove('show'), 1600);
  }

  function pressable(el, action, repeat) {
    let hold = null, rep = null;
    const stop = () => { clearTimeout(hold); clearInterval(rep); el.classList.remove('on'); };
    el.addEventListener('pointerdown', e => {
      e.preventDefault();
      el.classList.add('on');
      action();
      if (repeat) hold = setTimeout(() => { rep = setInterval(action, 110); }, 400);
    });
    ['pointerup', 'pointercancel', 'pointerleave'].forEach(t => el.addEventListener(t, stop));
    el.addEventListener('contextmenu', e => e.preventDefault());
  }

  document.querySelectorAll('[data-key]').forEach(btn =>
    pressable(btn, () => sendKey(Number(btn.dataset.key)), btn.hasAttribute('data-repeat')));

  function openApp(pkg, name) {
    send(`a:${pkg}`);
    toast(`Abrindo ${name}`);
  }

  document.querySelectorAll('[data-app]').forEach(btn =>
    btn.addEventListener('click', () => openApp(btn.dataset.app, btn.textContent.trim())));

  let appsLoaded = false;
  async function loadApps() {
    let list;
    try {
      const res = await fetch('/apps.json', { cache: 'no-store' });
      list = await res.json();
    } catch {
      return;
    }
    appsLoaded = true;
    const apps = $('apps');
    apps.replaceChildren();
    list.forEach(({ pkg, name, wide }) => {
      const btn = document.createElement('button');
      btn.className = wide ? 'app' : 'app plain';
      const art = document.createElement('span');
      art.className = 'art';
      const img = document.createElement('img');
      img.src = `/icon/${pkg}`;
      img.alt = '';
      img.loading = 'lazy';
      img.decoding = 'async';
      art.append(img);
      const label = document.createElement('span');
      label.className = 'name';
      label.textContent = name;
      btn.append(art, label);
      btn.addEventListener('click', () => openApp(pkg, name));
      apps.append(btn);
    });
  }

  function renderInputs(json) {
    let items;
    try {
      items = (JSON.parse(json).data || []).filter(i => !i.hidden && i.inputId)
        .sort((a, b) => String(a.label).localeCompare(String(b.label), 'pt-BR', { numeric: true }));
    } catch {
      return;
    }
    const list = $('inputs');
    list.replaceChildren();
    if (!items.length) {
      const empty = document.createElement('p');
      empty.className = 'hint left';
      empty.textContent = 'A TV não informou fontes. Use "Menu de fontes" abaixo.';
      list.append(empty);
      return;
    }
    items.forEach(item => {
      const name = item.label || item.customLabel || item.inputId;
      const hdmi = /hdmi\s*(\d)/i.exec(`${item.label} ${item.inputId}`);
      const btn = document.createElement('button');
      btn.className = 'source';
      const badge = document.createElement('span');
      badge.className = 'badge';
      badge.textContent = hdmi ? `H${hdmi[1]}` : name.replace(/[^A-Za-z0-9]/g, '').slice(0, 2).toUpperCase() || 'TV';
      const text = document.createElement('span');
      const title = document.createElement('div');
      title.className = 'name';
      title.textContent = name;
      text.append(title);
      if (item.customLabel && item.label && item.customLabel !== item.label) {
        const sub = document.createElement('div');
        sub.className = 'sub';
        sub.textContent = item.customLabel;
        text.append(sub);
      }
      btn.append(badge, text);
      btn.addEventListener('click', () => {
        send(`i:${item.inputId}`);
        list.querySelectorAll('.source').forEach(s => s.classList.toggle('on', s === btn));
        toast(`Trocando para ${name}`);
      });
      list.append(btn);
    });
  }

  $('tcast-revive').addEventListener('click', () => { send('r:tcast'); toast('Abrindo o T-Cast na TV'); });

  $('inputs-refresh').addEventListener('click', () => { send('i:list'); toast('Atualizando fontes'); });

  const views = ['remote', 'type', 'inputs', 'apps'];
  document.querySelectorAll('.tab').forEach(tab => tab.addEventListener('click', () => {
    const view = tab.dataset.view;
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t === tab));
    views.forEach(v => $(`view-${v}`).classList.toggle('active', v === view));
    if (view === 'type') $('text').focus();
    if (view === 'inputs') send('i:list');
    if (view === 'apps' && !appsLoaded) loadApps();
  }));

  $('digits-toggle').addEventListener('click', () => $('digits').classList.toggle('show'));

  const text = $('text');
  let pending = null;
  const flushText = () => {
    clearTimeout(pending);
    pending = null;
    send(`t:${text.value.replace(/\n/g, ' ')}`);
  };
  text.addEventListener('input', () => {
    $('count').textContent = `${text.value.length}/100`;
    clearTimeout(pending);
    pending = setTimeout(flushText, 150);
  });
  const submit = () => { if (pending) flushText(); setTimeout(() => sendKey(KEY.enter), 120); };
  text.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault(); submit(); } });
  $('text-enter').addEventListener('click', submit);
  $('text-clear').addEventListener('click', () => {
    text.value = '';
    $('count').textContent = '0/100';
    flushText();
    text.focus();
  });

  $('voice').addEventListener('click', () => {
    const btn = $('voice');
    send('v:claude');
    btn.classList.add('on');
    setTimeout(() => btn.classList.remove('on'), 1000);
    toast('Claude ouvindo pelo microfone da TV');
  });

  $('power').addEventListener('click', () => $('sheet').classList.add('show'));
  $('sheet-cancel').addEventListener('click', () => $('sheet').classList.remove('show'));
  $('sheet').addEventListener('click', e => { if (e.target === $('sheet')) $('sheet').classList.remove('show'); });
  $('sheet-confirm').addEventListener('click', () => {
    $('sheet').classList.remove('show');
    sendKey(KEY.power);
  });

  const pad = $('pad');
  const ripple = $('ripple');
  const STEP = 34;
  let origin = null, moved = false, repeated = false, hold = null, rep = null, zone = null;

  function zoneAt(x, y) {
    const r = pad.getBoundingClientRect();
    const dx = x - (r.left + r.width / 2), dy = y - (r.top + r.height / 2);
    if (Math.hypot(dx, dy) < r.width * 0.19) return 'ok';
    return Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up');
  }

  function fire(name, x, y) {
    sendKey(KEY[name]);
    const el = name === 'ok' ? pad.querySelector('.core') : pad.querySelector(`.chev.${name}`);
    el.classList.add('hit');
    setTimeout(() => el.classList.remove('hit'), 140);
    if (x !== undefined) {
      const r = pad.getBoundingClientRect();
      ripple.style.left = `${x - r.left}px`;
      ripple.style.top = `${y - r.top}px`;
      ripple.classList.remove('go');
      void ripple.offsetWidth;
      ripple.classList.add('go');
    }
  }

  const endPad = () => { clearTimeout(hold); clearInterval(rep); origin = null; };

  pad.addEventListener('pointerdown', e => {
    e.preventDefault();
    pad.setPointerCapture(e.pointerId);
    origin = { x: e.clientX, y: e.clientY };
    moved = false;
    repeated = false;
    zone = zoneAt(e.clientX, e.clientY);
    if (zone !== 'ok') {
      hold = setTimeout(() => {
        repeated = true;
        fire(zone, e.clientX, e.clientY);
        rep = setInterval(() => fire(zone), 110);
      }, 380);
    }
  });
  pad.addEventListener('pointermove', e => {
    if (!origin || repeated) return;
    const dx = e.clientX - origin.x, dy = e.clientY - origin.y;
    if (Math.max(Math.abs(dx), Math.abs(dy)) < STEP) return;
    clearTimeout(hold);
    moved = true;
    fire(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? 'right' : 'left') : (dy > 0 ? 'down' : 'up'), e.clientX, e.clientY);
    origin = { x: e.clientX, y: e.clientY };
  });
  pad.addEventListener('pointerup', e => {
    if (origin && !moved && !repeated) fire(zone, e.clientX, e.clientY);
    endPad();
  });
  pad.addEventListener('pointercancel', endPad);
  pad.addEventListener('contextmenu', e => e.preventDefault());

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') { retry = 300; connect(); }
  });

  connect();
  loadApps();
})();
