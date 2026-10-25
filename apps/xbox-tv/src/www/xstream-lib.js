function toBase64(bytes) {
    let s = '';
    for (let i = 0; i < bytes.length; i += 0x8000) {
        s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    }
    return btoa(s);
}

function fromBase64(b64) {
    const s = atob(b64);
    const out = new Uint8Array(s.length);
    for (let i = 0; i < s.length; i++) out[i] = s.charCodeAt(i);
    return out.buffer;
}

function bytesOf(data) {
    if (data instanceof ArrayBuffer) return new Uint8Array(data);
    if (ArrayBuffer.isView(data)) return new Uint8Array(data.buffer, data.byteOffset, data.byteLength);
    throw new TypeError('unsupported data channel payload');
}

function event(type, props) {
    const e = new Event(type);
    for (const k in props) Object.defineProperty(e, k, { value: props[k], enumerable: true });
    return e;
}

function handlers(proto, names) {
    names.forEach((name) => {
        Object.defineProperty(proto, 'on' + name, {
            configurable: true,
            enumerable: true,
            get() { return (this._on && this._on[name]) || null; },
            set(fn) {
                this._on = this._on || {};
                if (this._on[name]) this.removeEventListener(name, this._on[name]);
                this._on[name] = typeof fn === 'function' ? fn : null;
                if (this._on[name]) this.addEventListener(name, this._on[name]);
            }
        });
    });
}

class XChannel extends EventTarget {
    constructor(pc, id, label, init) {
        super();
        this._pc = pc;
        this._id = id;
        this.label = label;
        this.protocol = init.protocol || '';
        this.ordered = init.ordered !== false;
        this.maxRetransmits = init.maxRetransmits == null ? null : init.maxRetransmits;
        this.maxPacketLifeTime = init.maxPacketLifeTime == null ? null : init.maxPacketLifeTime;
        this.negotiated = false;
        this.id = null;
        this.readyState = 'connecting';
        this.binaryType = 'arraybuffer';
        this.bufferedAmount = 0;
        this.bufferedAmountLowThreshold = 0;
    }

    send(data) {
        if (this.readyState !== 'open') throw new DOMException('channel not open', 'InvalidStateError');
        if (typeof data === 'string') {
            post({ t: 'send', id: this._id, text: true, data });
        } else {
            post({ t: 'send', id: this._id, text: false, data: toBase64(bytesOf(data)) });
        }
    }

    close() {
        if (this.readyState === 'closed') return;
        this._state('closed');
    }

    _state(s) {
        if (this.readyState === s) return;
        this.readyState = s;
        if (s === 'open') this.id = this._id;
        this.dispatchEvent(new Event(s === 'open' ? 'open' : 'close'));
    }

    _message(m) {
        const data = m.text ? m.data : fromBase64(m.data);
        const payload = !m.text && this.binaryType === 'blob' ? new Blob([data]) : data;
        this.dispatchEvent(new MessageEvent('message', { data: payload }));
    }
}
handlers(XChannel.prototype, ['open', 'close', 'message', 'error', 'bufferedamountlow', 'closing']);

function syntheticStreams() {
    const canvas = document.createElement('canvas');
    canvas.width = 1280;
    canvas.height = 720;
    const g = canvas.getContext('2d');
    const paint = () => {
        g.fillStyle = '#000';
        g.fillRect(0, 0, canvas.width, canvas.height);
    };
    const video = canvas.captureStream(1);
    paint();
    let audio;
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        audio = ctx.createMediaStreamDestination().stream;
        audio._ctx = ctx;
    } catch (err) {
        audio = new MediaStream();
    }
    return { video, audio, paint };
}

function revealSurface(stream) {
    document.querySelectorAll('video').forEach((v) => {
        if (v.srcObject !== stream || v.__xstream) return;
        v.__xstream = true;
        v.style.setProperty('opacity', '0', 'important');
        for (let el = v; el; el = el.parentElement) {
            el.style.setProperty('background', 'transparent', 'important');
        }
    });
}

function sdpSection(sdp, kind) {
    return (sdp || '').split(/\r?\nm=/).find((s) => s.startsWith(kind + ' ') || s.startsWith('m=' + kind + ' ')) || '';
}

function codecOf(sdp, kind) {
    const section = sdpSection(sdp, kind);
    const pt = ((section.split(/\r?\n/)[0] || '').split(' ')[3]) || '';
    const map = new RegExp('a=rtpmap:' + pt + ' ([^/\\r\\n]+)/(\\d+)').exec(section);
    const fmtp = new RegExp('a=fmtp:' + pt + ' ([^\\r\\n]+)').exec(section);
    return {
        payloadType: Number(pt) || 0,
        mimeType: kind + '/' + (map ? map[1] : ''),
        clockRate: map ? Number(map[2]) : 0,
        sdpFmtpLine: fmtp ? fmtp[1] : ''
    };
}

function ssrcOf(sdp, kind) {
    const m = /a=ssrc:(\d+)/.exec(sdpSection(sdp, kind));
    return m ? Number(m[1]) : 0;
}

function candidateOf(line) {
    const p = String(line || '').replace(/^a=/, '').split(' ');
    return p.length > 7 ? { address: p[4], port: Number(p[5]), protocol: p[2].toLowerCase(), candidateType: p[7] } : null;
}
