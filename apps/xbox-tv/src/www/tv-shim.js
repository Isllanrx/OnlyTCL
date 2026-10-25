(function () {
    if (window.__xboxTvShim) return;
    window.__xboxTvShim = true;

    var BRAZIL = /brazil/i;
    var CLOUD_PLAY = /\/v\d+\/sessions\/cloud\/play\/?$/i;
    var LOGIN_USER = /\/v\d+\/login\/user\/?$/i;
    var OS_NAME = 'android';
    var DEVICE_INFO = 'x-ms-device-info';

    function preferBrazil(data) {
        if (!data || !data.offeringSettings) return false;
        var regions = data.offeringSettings.regions || [];
        var brIdx = -1;
        for (var i = 0; i < regions.length; i++) {
            if (BRAZIL.test(regions[i].name)) {
                brIdx = i;
                break;
            }
        }
        var br;
        if (brIdx >= 0) {
            br = regions.splice(brIdx, 1)[0];
        } else {
            br = {
                name: 'BrazilSouth',
                baseUri: 'https://brs.core.gssv-play-prod.xboxlive.com',
                networkTestHostname: 'brs.gssv-fastlane-prod.xboxlive.com',
                systemUpdateGroups: null
            };
        }
        br.isDefault = true;
        br.fallbackPriority = 0;
        for (var j = 0; j < regions.length; j++) {
            regions[j].isDefault = false;
            regions[j].fallbackPriority = j + 1;
        }
        regions.unshift(br);
        data.offeringSettings.regions = regions;
        data.offeringSettings.allowRegionSelection = true;
        return true;
    }

    function withOsName(json) {
        try {
            var info = JSON.parse(json);
            if (!info.dev || !info.dev.os) return json;
            info.dev.os.name = OS_NAME;
            return JSON.stringify(info);
        } catch (e) {
            return json;
        }
    }

    function patchPlay(init) {
        var body = JSON.parse(init.body);
        if (!body.settings) return init;
        body.settings.osName = OS_NAME;
        body.settings.locale = 'pt-BR';
        var headers = new Headers(init.headers);
        var info = headers.get(DEVICE_INFO);
        if (info) headers.set(DEVICE_INFO, withOsName(info));
        return Object.assign({}, init, { body: JSON.stringify(body), headers: headers });
    }

    function patchLogin(res) {
        if (!res.ok) return res;
        return res.clone().json().then(function (data) {
            if (!preferBrazil(data)) return res;
            var headers = new Headers(res.headers);
            headers.delete('content-length');
            return new Response(JSON.stringify(data), { status: res.status, statusText: res.statusText, headers: headers });
        }, function () { return res; });
    }

    var fetch = window.fetch;
    window.fetch = function (input, init) {
        var url = (typeof input === 'string' ? input : (input && input.url) || '').split('?')[0];
        if (CLOUD_PLAY.test(url) && init && typeof init.body === 'string') {
            try {
                init = patchPlay(init);
            } catch (e) {
                console.warn('[XboxTvShim] play request not patched', e);
            }
        }
        var pending = fetch.call(this, input, init);
        return LOGIN_USER.test(url) ? pending.then(patchLogin) : pending;
    };

    var BUTTONS = 17;
    var done = function () { return Promise.resolve('complete'); };
    var pad = {
        id: 'Xbox Wireless Controller (STANDARD GAMEPAD Vendor: 045e Product: 0b13)',
        index: 0,
        connected: false,
        timestamp: 0,
        mapping: 'standard',
        axes: [0, 0, 0, 0],
        buttons: [],
        vibrationActuator: { type: 'dual-rumble', effects: ['dual-rumble'], playEffect: done, reset: done }
    };
    for (var i = 0; i < BUTTONS; i++) pad.buttons.push({ pressed: false, touched: false, value: 0 });
    var pads = [pad, null, null, null];
    var nativeGetGamepads = navigator.getGamepads && navigator.getGamepads.bind(navigator);
    var last = '';
    var lastPoll = -Infinity;
    var announced = false;

    function setButton(btn, value) {
        btn.value = value;
        btn.pressed = value > 0.15;
        btn.touched = value > 0;
    }

    function poll() {
        var now = performance.now();
        if (now - lastPoll < 4) return;
        lastPoll = now;
        var fire = window.FireOS;
        if (!fire || !fire.getGamepadState) return;
        var raw = fire.getGamepadState();
        if (raw === last) return;
        last = raw;
        var s = raw.split(',');
        pad.connected = s[1] === '1';
        if (s.length === 9) {
            var mask = +s[2];
            for (var b = 0; b < BUTTONS; b++) setButton(pad.buttons[b], (mask >> b) & 1);
            setButton(pad.buttons[6], Math.max(mask >> 6 & 1, s[3] / 1000));
            setButton(pad.buttons[7], Math.max(mask >> 7 & 1, s[4] / 1000));
            for (var a = 0; a < 4; a++) pad.axes[a] = s[5 + a] / 1000;
            pad.timestamp = now;
        }
        if (pad.connected !== announced) {
            announced = pad.connected;
            var ev = new Event(announced ? 'gamepadconnected' : 'gamepaddisconnected');
            ev.gamepad = pad;
            window.dispatchEvent(ev);
        }
    }

    navigator.getGamepads = function () {
        poll();
        if (pad.connected) return pads;
        return nativeGetGamepads ? nativeGetGamepads() : [];
    };

    var inGame = false;
    setInterval(function () {
        if (!announced) poll();
        var video = document.querySelector('video');
        var now = location.pathname.indexOf('/launch/') !== -1 || !!(video && video.readyState >= 2);
        if (now === inGame) return;
        inGame = now;
        if (window.FireOS && window.FireOS.setInGame) window.FireOS.setInGame(inGame);
    }, 500);
})();
