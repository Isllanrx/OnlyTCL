const N = window.XStreamNative;
const Native = window.RTCPeerConnection;
if (!N || !Native || window.__xstreamInstalled) return;
window.__xstreamInstalled = true;

const post = (m) => N.postMessage(JSON.stringify(m));
let active = null;
let seq = 0;

N.addEventListener('message', (e) => {
    let m;
    try { m = JSON.parse(e.data); } catch (err) { return; }
    if (active) active._native(m);
});

class XPeer extends EventTarget {
    constructor(config) {
        super();
        this._config = Object.assign({}, config);
        this._pending = new Map();
        this._channels = new Map();
        this._nextId = 1;
        this._transceivers = [];
        this._senders = [];
        this._streams = null;
        this._remote = null;
        this._last = { at: 0, frames: 0 };
        this._timer = 0;
        this._s = {
            signalingState: 'stable',
            iceGatheringState: 'new',
            iceConnectionState: 'new',
            connectionState: 'new',
            localDescription: null,
            remoteDescription: null,
            currentLocalDescription: null,
            currentRemoteDescription: null,
            pendingLocalDescription: null,
            pendingRemoteDescription: null,
            canTrickleIceCandidates: true
        };
        this._answer = '';
        if (active) active.close();
        active = this;
        post({ t: 'open', config: { iceServers: this._config.iceServers || [] } });
    }

    get sctp() { return null; }

    getConfiguration() { return Object.assign({}, this._config); }

    setConfiguration(config) { this._config = Object.assign({}, this._config, config); }

    _cmd(op) { post({ t: 'cmd', cmd: op }); }

    _request(op) {
        const req = ++seq;
        return new Promise((resolve, reject) => {
            this._pending.set(req, { resolve, reject });
            this._cmd(Object.assign({ req }, op));
        });
    }

    _decoder() {
        const req = ++seq;
        return new Promise((resolve) => {
            this._pending.set('d' + req, { resolve, reject: resolve });
            post({ t: 'decoderStats', req });
        });
    }

    createDataChannel(label, init) {
        init = init || {};
        const id = this._nextId++;
        const ch = new XChannel(this, id, String(label), init);
        this._channels.set(id, ch);
        const spec = { op: 'createDataChannel', id, label: ch.label, ordered: ch.ordered, protocol: ch.protocol };
        if (ch.maxRetransmits !== null) spec.maxRetransmits = ch.maxRetransmits;
        if (ch.maxPacketLifeTime !== null) spec.maxPacketLifeTime = ch.maxPacketLifeTime;
        this._cmd(spec);
        return ch;
    }

    addTransceiver(trackOrKind, init) {
        this._streams = this._streams || syntheticStreams();
        const kind = typeof trackOrKind === 'string' ? trackOrKind : trackOrKind.kind;
        const direction = (init && init.direction) || 'sendrecv';
        this._cmd({ op: 'addTransceiver', kind, direction });
        const pc = this;
        const stream = this._streams[kind];
        const track = kind === 'video' ? (stream ? stream.getVideoTracks()[0] : null) : (stream ? stream.getAudioTracks()[0] : null);
        const receiver = {
            track: track || null,
            transport: null,
            getSynchronizationSources: () => [],
            getContributingSources: () => [],
            getParameters: () => ({ codecs: [], headerExtensions: [] }),
            getStats: () => pc.getStats()
        };
        const sender = this._sender(typeof trackOrKind === 'string' ? null : trackOrKind);
        const t = {
            kind,
            mid: null,
            direction,
            currentDirection: null,
            stopped: false,
            receiver,
            sender,
            setCodecPreferences(codecs) {
                pc._cmd({ op: 'codecPrefs', kind, codecs: (codecs || []).map((c) => ({ mimeType: c.mimeType, sdpFmtpLine: c.sdpFmtpLine })) });
            },
            stop() { this.stopped = true; }
        };
        this._transceivers.push(t);
        return t;
    }

    _sender(track) {
        const sender = {
            track: track || null,
            transport: null,
            dtmf: null,
            replaceTrack(next) { sender.track = next; return Promise.resolve(); },
            getParameters: () => ({ encodings: [{}], codecs: [], headerExtensions: [], rtcp: {} }),
            setParameters: () => Promise.resolve(),
            getStats: () => Promise.resolve(new Map())
        };
        this._senders.push(sender);
        return sender;
    }

    addTrack(track) {
        const t = this._transceivers.find((x) => x.kind === track.kind && !x.sender.track);
        if (t) {
            t.sender.track = track;
            return t.sender;
        }
        return this._sender(track);
    }

    removeTrack(sender) { if (sender) sender.track = null; }

    getSenders() { return this._senders.slice(); }

    getReceivers() { return this._transceivers.map((t) => t.receiver); }

    getTransceivers() { return this._transceivers.slice(); }

    restartIce() {}

    createOffer() {
        return this._request({ op: 'createOffer' }).then((v) => new RTCSessionDescription({ type: v.type, sdp: v.sdp }));
    }

    createAnswer() {
        return Promise.reject(new DOMException('answer role not supported', 'NotSupportedError'));
    }

    setLocalDescription(desc) {
        const sdp = desc && desc.sdp ? desc.sdp : undefined;
        return this._request({ op: 'setLocal', sdp }).then((v) => {
            const d = new RTCSessionDescription({ type: 'offer', sdp: v.sdp });
            this._s.localDescription = this._s.pendingLocalDescription = d;
            this._signaling('have-local-offer');
        });
    }

    setRemoteDescription(desc) {
        const type = desc.type || 'answer';
        this._answer = desc.sdp || '';
        (this._answer.match(/a=candidate:[^\r\n]+/g) || []).forEach((l) => { this._remote = this._remote || candidateOf(l); });
        return this._request({ op: 'setRemote', type, sdp: this._answer }).then(() => {
            const d = new RTCSessionDescription({ type, sdp: this._answer });
            this._s.remoteDescription = this._s.currentRemoteDescription = d;
            this._s.currentLocalDescription = this.localDescription;
            this._s.pendingLocalDescription = this._s.pendingRemoteDescription = null;
            this._signaling('stable');
        });
    }

    addIceCandidate(c) {
        if (!c || !c.candidate) return Promise.resolve();
        this._remote = this._remote || candidateOf(c.candidate);
        const candidate = { candidate: c.candidate, sdpMid: c.sdpMid == null ? null : c.sdpMid, sdpMLineIndex: c.sdpMLineIndex == null ? null : c.sdpMLineIndex };
        if (c.usernameFragment) candidate.usernameFragment = c.usernameFragment;
        return this._request({ op: 'addIce', candidate }).then(() => undefined);
    }

    getStats() {
        const sel = arguments[0];
        if (sel && sel.kind) return Promise.resolve(new Map());
        const within = (p) => Promise.race([p.catch(() => ({})), new Promise((r) => setTimeout(() => r({}), 900))]);
        return Promise.all([within(this._request({ op: 'stats' })), within(this._decoder())]).then(([r, d]) => this._report(r || {}, d || {}));
    }

    _report(r, d) {
        const now = performance.timeOrigin + performance.now();
        const map = new Map();
        const put = (o) => map.set(o.id, Object.assign({ timestamp: now }, o));
        const dv = d.video || {};
        const v = r.video || {};
        const a = r.audio || {};
        const decoded = dv.framesDecoded || 0;
        const dt = (now - this._last.at) / 1000;
        const fps = this._last.at && dt > 0 ? Math.max(0, (decoded - this._last.frames) / dt) : 0;
        this._last = { at: now, frames: decoded };
        const vc = codecOf(this._answer, 'video');
        const ac = codecOf(this._answer, 'audio');
        put(Object.assign({ id: 'CV', type: 'codec', transportId: 'T0' }, vc));
        put(Object.assign({ id: 'CA', type: 'codec', transportId: 'T0' }, ac));
        put({ id: 'T0', type: 'transport', dtlsState: this.connectionState === 'connected' ? 'connected' : 'new', selectedCandidatePairId: 'CP0', bytesReceived: (r.videoBytes || 0) + (r.audioBytes || 0) });
        put({
            id: 'CP0', type: 'candidate-pair', transportId: 'T0', state: this.connectionState === 'connected' ? 'succeeded' : 'in-progress',
            nominated: true, localCandidateId: 'LC0', remoteCandidateId: 'RC0', bytesReceived: (r.videoBytes || 0) + (r.audioBytes || 0),
            currentRoundTripTime: r.rtt || 0, availableIncomingBitrate: r.availableIncomingBitrate || 0
        });
        const rc = this._remote || { address: '', port: 0, protocol: 'udp', candidateType: 'host' };
        put(Object.assign({ id: 'RC0', type: 'remote-candidate', transportId: 'T0' }, rc));
        put({ id: 'LC0', type: 'local-candidate', transportId: 'T0', protocol: 'udp', candidateType: 'host' });
        const vt = this._streams ? this._streams.video.getVideoTracks()[0] : null;
        const at = this._streams ? this._streams.audio.getAudioTracks()[0] : null;
        put({
            id: 'IV', type: 'inbound-rtp', kind: 'video', mediaType: 'video', transportId: 'T0', codecId: 'CV',
            ssrc: v.ssrc || ssrcOf(this._answer, 'video'), trackIdentifier: vt ? vt.id : '', mid: '1',
            packetsReceived: v.packetsReceived || r.videoPackets || 0, packetsLost: v.packetsLost || 0,
            bytesReceived: v.bytesReceived || r.videoBytes || 0, jitter: v.jitter || 0,
            framesReceived: r.frames || 0, framesDecoded: decoded, keyFramesDecoded: r.keyFrames || 0,
            framesDropped: dv.framesDropped || 0, framesPerSecond: fps, totalDecodeTime: dv.totalDecodeTime || 0,
            frameWidth: dv.frameWidth || 0, frameHeight: dv.frameHeight || 0,
            jitterBufferDelay: 0, jitterBufferEmittedCount: decoded, totalAssemblyTime: 0,
            framesAssembledFromMultiplePackets: r.frames || 0,
            nackCount: v.nackCount || 0, pliCount: v.pliCount || r.plis || 0, firCount: v.firCount || 0
        });
        put({
            id: 'IA', type: 'inbound-rtp', kind: 'audio', mediaType: 'audio', transportId: 'T0', codecId: 'CA',
            ssrc: a.ssrc || ssrcOf(this._answer, 'audio'), trackIdentifier: at ? at.id : '', mid: '0',
            packetsReceived: a.packetsReceived || r.audioPackets || 0, packetsLost: a.packetsLost || 0,
            bytesReceived: a.bytesReceived || r.audioBytes || 0, jitter: a.jitter || 0
        });
        put({ id: 'OA', type: 'outbound-rtp', kind: 'audio', mediaType: 'audio', transportId: 'T0', codecId: 'CA', packetsSent: 0, bytesSent: 0 });
        return map;
    }

    close() {
        if (this.signalingState === 'closed') return;
        if (active === this) {
            post({ t: 'close' });
            active = null;
        }
        clearInterval(this._timer);
        this._channels.forEach((ch) => ch._state('closed'));
        this._pending.forEach((p) => p.reject(new DOMException('connection closed', 'InvalidStateError')));
        this._pending.clear();
        this._s.signalingState = 'closed';
        this._s.iceConnectionState = 'closed';
        this._s.connectionState = 'closed';
        if (this._streams && this._streams.audio._ctx) this._streams.audio._ctx.close().catch(() => {});
    }

    _signaling(s) {
        if (this.signalingState === s) return;
        this._s.signalingState = s;
        this.dispatchEvent(new Event('signalingstatechange'));
    }

    _settle(key, m) {
        const p = this._pending.get(key);
        if (!p) return;
        this._pending.delete(key);
        if (m.ok === false) p.reject(new DOMException(String(m.error), 'OperationError'));
        else p.resolve(m.value === undefined ? m : m.value);
    }

    _track(kind) {
        this._streams = this._streams || syntheticStreams();
        const stream = this._streams[kind];
        const track = kind === 'video' ? stream.getVideoTracks()[0] : stream.getAudioTracks()[0];
        const t = this._transceivers.find((x) => x.kind === kind);
        if (t) t.receiver.track = track;
        if (kind === 'video') {
            post({ t: 'surface', on: true });
            clearInterval(this._timer);
            this._timer = setInterval(() => {
                this._streams.paint();
                revealSurface(stream);
            }, 500);
        }
        if (!track) return;
        this.dispatchEvent(event('track', { track, streams: [stream], receiver: t ? t.receiver : {}, transceiver: t || null }));
    }

    _native(m) {
        switch (m.ev) {
            case 'result': return this._settle(m.req, m);
            case 'decoderStats': return this._settle('d' + m.req, { value: { video: m.video, audio: m.audio } });
            case 'ice': {
                const candidate = m.candidate == null ? null : new RTCIceCandidate({
                    candidate: m.candidate, sdpMid: m.sdpMid, sdpMLineIndex: m.sdpMLineIndex, usernameFragment: m.usernameFragment
                });
                return this.dispatchEvent(event('icecandidate', { candidate }));
            }
            case 'gathering':
                this._s.iceGatheringState = m.state;
                return this.dispatchEvent(new Event('icegatheringstatechange'));
            case 'iceState':
                this._s.iceConnectionState = m.state;
                return this.dispatchEvent(new Event('iceconnectionstatechange'));
            case 'state':
                this._s.connectionState = m.state;
                return this.dispatchEvent(new Event('connectionstatechange'));
            case 'dc': {
                const ch = new XChannel(this, m.id, m.label, { protocol: m.protocol });
                this._channels.set(m.id, ch);
                return this.dispatchEvent(event('datachannel', { channel: ch }));
            }
            case 'dcOpen': return this._channel(m.id, (ch) => ch._state('open'));
            case 'dcClose': return this._channel(m.id, (ch) => ch._state('closed'));
            case 'dcError': return this._channel(m.id, (ch) => ch.dispatchEvent(new Event('error')));
            case 'msg': return this._channel(m.id, (ch) => ch._message(m));
            case 'track': return this._track(m.kind);
            case 'fatal':
                this._s.connectionState = 'failed';
                this._s.iceConnectionState = 'failed';
                this.dispatchEvent(new Event('iceconnectionstatechange'));
                return this.dispatchEvent(new Event('connectionstatechange'));
            default:
        }
    }

    _channel(id, fn) {
        const ch = this._channels.get(id);
        if (ch) fn(ch);
    }
}
['signalingState', 'iceGatheringState', 'iceConnectionState', 'connectionState', 'localDescription', 'remoteDescription',
    'currentLocalDescription', 'currentRemoteDescription', 'pendingLocalDescription', 'pendingRemoteDescription',
    'canTrickleIceCandidates'].forEach((name) => {
    Object.defineProperty(XPeer.prototype, name, { configurable: true, enumerable: true, get() { return this._s[name]; } });
});
handlers(XPeer.prototype, ['icecandidate', 'icegatheringstatechange', 'iceconnectionstatechange', 'connectionstatechange',
    'signalingstatechange', 'track', 'datachannel', 'negotiationneeded', 'icecandidateerror']);

function isCloudPeer(config) {
    if (!config || typeof config !== 'object') return false;
    if (Object.keys(config).length === 0) return false;
    return true;
}

function RTCPeerConnection(config, constraints) {
    if (isCloudPeer(config)) {
        try {
            return new XPeer(config);
        } catch (err) {
            post({ t: 'error', where: 'XPeer', error: String((err && err.stack) || err) });
        }
    }
    return new Native(config, constraints);
}
RTCPeerConnection.prototype = XPeer.prototype;
Object.defineProperty(RTCPeerConnection, Symbol.hasInstance, { value: (o) => o instanceof XPeer || o instanceof Native });
if (Native.generateCertificate) RTCPeerConnection.generateCertificate = Native.generateCertificate.bind(Native);
window.RTCPeerConnection = RTCPeerConnection;
if (window.webkitRTCPeerConnection) window.webkitRTCPeerConnection = RTCPeerConnection;
