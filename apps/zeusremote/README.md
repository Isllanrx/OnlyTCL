# ZeusRemote (T-Cast Local Network Remote Control)

Smartphone remote control application communicating directly with the TCL TV background network service (`nScreen_srv`).

---

## Protocol Architecture

Interfacing with TCL proprietary TCP ports (4202/8888):
* `TcastLink`: Socket manager with automatic exponential backoff reconnection.
* `HostWatch`: Local subnet service discovery.
* `TcastReviver`: Persistent connection watchdog.

Binary releases are hosted at:
https://github.com/Isllanrx/OnlyTCL/releases/tag/v1.0.0
