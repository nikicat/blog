---
title: "Battery over WiFi"
date: 2026-07-25
author: Nikolay Bryskin
description: "The mouse lives on another computer, so the laptop cannot see its battery — and UPower has no API to be told. The way in is to become hardware: a virtual Bluetooth mouse the kernel believes."
image: /uploads/battery-over-wifi/cover.png
tags:
  - linux
  - kernel
  - systemd
  - hardware
---

[Part one](/posts/mouse-over-wifi/) ended with a mouse plugged into one computer and
working on another: `netevent` reading `/dev/input/event8` on a little ARM
board, a socket-activated stream over Tailscale, a uinput clone on the
laptop. The cursor moves, the mouse never found out.

It left one thing behind. The G502 is wireless — it has a battery, it knows
how full that battery is, and it tells anyone who asks. On the laptop, the
power panel lists the internal battery, the USB-C sources, a Bluetooth
keyboard. The one power source I actually hold in my hand is the only one
that isn't there.

<!--more-->

<style>
.post-body p, .post-body li { position: relative; }
.post-body img[src$=".svg"] { --w: min(1120px, calc(100% + 20rem), 96vw); display: block; width: var(--w); max-width: none; margin-inline: calc((100% - var(--w)) / 2); }
@media (max-width: 760px) { .post-body p:has(> img[src$=".svg"]) { overflow-x: auto; } .post-body img[src$=".svg"] { width: auto; min-width: 900px; margin-inline: 0; } }
.tgloss { border-bottom: 1px dotted currentColor; cursor: help; outline: none; }
.tgloss > .tgloss-b { display: none; position: absolute; left: 0; margin-top: 1.6em; z-index: 30; width: min(30rem, 100%); padding: .7rem .85rem; border-radius: .5rem; font-size: .85rem; line-height: 1.5; font-weight: 400; font-style: normal; text-align: left; white-space: normal; background: #fff; color: #1e293b; border: 1px solid #cbd5e1; box-shadow: 0 6px 24px rgba(15,23,42,.16); }
.tgloss:hover > .tgloss-b, .tgloss:focus > .tgloss-b, .tgloss:focus-within > .tgloss-b { display: block; }
@media (prefers-color-scheme: dark) { :root:not([data-theme=light]) .tgloss > .tgloss-b { background: #0b1220; color: #e2e8f0; border-color: #3b4a61; box-shadow: 0 6px 24px rgba(0,0,0,.5); } }
:root[data-theme=dark] .tgloss > .tgloss-b { background: #0b1220; color: #e2e8f0; border-color: #3b4a61; box-shadow: 0 6px 24px rgba(0,0,0,.5); }
</style>

Worse, nothing on the desk can see it. The ARM board's vendor kernel is
built without <span class="tgloss" tabindex="0"><code>CONFIG_HID_LOGITECH</code><span class="tgloss-b">Kernel build option that pulls in the Logitech HID drivers. Distributions enable it; vendor board kernels often don't, and the receiver then falls back to <code>hid-generic</code>, which can move a cursor and nothing else. <a href="https://cateee.net/lkddb/web-lkddb/HID_LOGITECH.html">LKDDb entry</a></span></span>:

```console
$ zgrep HID_LOGITECH /proc/config.gz
# CONFIG_HID_LOGITECH is not set
```

So there is no <span class="tgloss" tabindex="0"><code>hidpp</code><span class="tgloss-b">Short for HID++, Logitech's request/response protocol carried inside two vendor-defined HID reports. Features are addressed by 16-bit id — <code>0x1001</code> is battery voltage — which you resolve to a runtime index by asking feature <code>0x0000</code> first. <a href="https://wiki.archlinux.org/title/Logitech_Unifying_Receiver">Arch Wiki</a></span></span> driver there, no <span class="tgloss" tabindex="0"><code>power_supply</code><span class="tgloss-b">The kernel class every battery and charger registers with, surfacing as <code>/sys/class/power_supply/*</code>. The <code>scope=Device</code> attribute marks a peripheral's battery rather than the machine's own. <a href="https://www.kernel.org/doc/html/latest/power/power_supply_class.html">kernel docs</a></span></span> node, nothing for an
applet to read. The receiver is claimed by `hid-generic`, which knows how to
move a cursor and nothing else.

## Asking the mouse directly

Logitech devices speak HID++ — a small request/response protocol carried in
two vendor-defined HID reports, `0x10` (7 bytes) and `0x11` (20 bytes). If
the kernel won't do it for you, <span class="tgloss" tabindex="0"><code>hidraw</code><span class="tgloss-b">Raw access to a HID device's reports, bypassing any driver that claimed it: open <code>/dev/hidraw*</code>, write a report, read the reply. <a href="https://www.kernel.org/doc/html/latest/hid/hidraw.html">kernel docs</a></span></span> will. Write a request, read the
reply:

```python
buf[0], buf[1], buf[2], buf[3] = rid, dev, feature, (fn << 4) | SW_ID
```

That's the whole frame: report id, device index behind the receiver,
feature index, and a byte packing the function with a software id so you can
recognize your own answers. Ask feature `0x0000` (the root feature) for the
index of the feature you want, then call it.

115 lines of that, and the receiver's HID++ endpoint gives up the goods:

```console
$ just battery
{"name": "G502 LIGHTSPEED Wireless Gaming Mouse", "voltage_mv": 4057, "flags": 0}
```

Two details from writing it. First, the only battery feature this mouse
implements is `0x1001`, `BATTERY_VOLTAGE` — millivolts, no percentage.
Remember that, it matters later. Second, my first run returned absolutely
nothing, and the second run worked. A sleeping mouse ignores the first
request; the request is what wakes the link. So the query retries three
times before giving up, and "no answer" genuinely means "off", not "asleep".

## The wall

Now put that number on the laptop's screen. GNOME's power panel renders
<span class="tgloss" tabindex="0">UPower<span class="tgloss-b">The freedesktop daemon that collects batteries — almost entirely from the kernel's <code>power_supply</code> class — and exports them on D-Bus. GNOME's power panel is a view of it, so anything it doesn't know about cannot be displayed. <a href="https://upower.freedesktop.org/">upower.freedesktop.org</a></span></span> devices, so I need UPower to have one.

UPower has no API for that. You can enumerate devices, you can subscribe to
changes, and there is no `AddDevice` anywhere on the bus. Its Linux backend
walks the kernel's `power_supply` class and exports what it finds. (There's
one exception — BlueZ can register a battery provider — and it's no help
unless you're a Bluetooth device.)

That's not a missing feature so much as a boundary. A battery is a hardware
fact; the daemon's job is to report hardware facts, not to accept claims
about them. Which leaves exactly one way in: **the battery has to exist in
the kernel.**

I considered a <span class="tgloss" tabindex="0">DKMS<span class="tgloss-b">Dynamic Kernel Module Support: builds an out-of-tree kernel module automatically against every kernel you install, so it survives upgrades. <a href="https://wiki.archlinux.org/title/Dynamic_Kernel_Module_Support">Arch Wiki</a></span></span> module — thirty lines registering a `power_supply` with
`scope=Device`, fed from userspace. It would work. But the mouse reports
millivolts, so I'd have to invent the voltage-to-percentage curve myself,
and I'd lose the automatic classification that makes UPower call a battery a
*mouse* instead of a nameless cell. More code, worse result.

The other option is stranger and much better: if the only interface is being
hardware, then be hardware.

## Become the mouse

<span class="tgloss" tabindex="0"><code>/dev/uhid</code><span class="tgloss-b">Kernel interface that lets an ordinary userspace process create a HID device: you supply the report descriptor, the kernel binds a driver to it, and every request that driver makes arrives as an event for you to answer. <a href="https://www.kernel.org/doc/html/latest/hid/uhid.html">kernel docs</a></span></span> lets a userspace process create a HID device. You hand the
kernel a report descriptor and some ids, and from that moment the kernel has
a HID device it will happily bind a driver to. Everything the driver asks,
your process answers.

So the laptop grows a virtual Bluetooth-attached Logitech mouse. The daemon that runs it is <span class="tgloss" tabindex="0"><code>uhid-hidpp-battery</code><span class="tgloss-b">The client half of this project: 240 lines of Python that poll zxc-pc for a reading, create the virtual device, answer the driver's HID++ questions out of cache, and push an event when the charge changes. Standard library only.</span></span>.
<span class="tgloss" tabindex="0"><code>hid-logitech-hidpp</code><span class="tgloss-b">The in-tree driver that speaks HID++ to Logitech devices and publishes what it finds — battery, high-resolution scrolling, onboard profiles. It also carries Logitech's voltage-to-percentage curve, which is why this project never has to invent one. <a href="https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/tree/drivers/hid/hid-logitech-hidpp.c">source</a></span></span> binds to it, interrogates it over HID++ exactly as it
would a real one, and publishes what it learns:

![Sequence diagram. On the laptop, uhid-hidpp-battery polls zxc-pc over the tailnet; hidpp-battery-query asks the mouse for feature 0x1001 over hidraw and gets 4057 mV back. Only then does the daemon create the virtual device, which hid-logitech-hidpp interrogates for its name and battery, answering from cache, and publishes as hidpp_battery_N — which UPower shows as a mouse at 88%](/uploads/battery-over-wifi/sequence.svg)

Three parts of the descriptor earn their place. Two vendor collections
declare the HID++ reports — and they must be *exactly* 6 and 19 data bytes,
because `hidpp_validate_device()` measures them and refuses anything else.
The third is a plain mouse collection that never emits a single event. It
exists so udev tags a sibling input device `ID_INPUT_MOUSE=1`, which is what
UPower reads to decide this battery is a mouse. Without it you get a
correct percentage attached to an anonymous battery.

The device id is borrowed. `hid-logitech-hidpp` matches Bluetooth devices by
explicit product id — 39 of them, no wildcard — so the fake claims one from
that list. It doesn't matter which: the name in the panel comes from the
HID++ answer, not the id.

```console
$ dmesg | tail -1
input: G502 LIGHTSPEED Wireless Gaming Mouse as /devices/virtual/misc/uhid/...
```

## What the driver actually asks

Watching the kernel interrogate a device I wrote is the best part of this
whole project. From the first working run, trimmed:

```
SET_REPORT 11ff000100050000…    getFeature 0x0005 -> index 3
SET_REPORT 11ff031100000000…    → "G502 LIGHTSPEED "
SET_REPORT 11ff031110000000…    → "Wireless Gaming "
SET_REPORT 11ff031120000000…    → "Mouse"
SET_REPORT 10ff001100005a       ping -> HID++ 4.2
SET_REPORT 11ff000110000000…    getFeature 0x1000 -> index 0   (not supported)
SET_REPORT 11ff000110040000…    getFeature 0x1004 -> index 0   (not supported)
SET_REPORT 11ff000110010000…    getFeature 0x1001 -> index 4
SET_REPORT 11ff040100000000…    battery voltage -> 4060 mV
SET_REPORT 11ff000121210000…    getFeature 0x2121 -> index 0   (not supported)
SET_REPORT 11ff000121200000…    getFeature 0x2120 -> index 0   (not supported)
```

Note the last two lines. `0x2121` and `0x2120` are high-resolution
scrolling, and the driver doesn't only read — given a device that says yes,
it configures it.

That killed the design I wanted. The elegant version of this program is a
transparent tunnel: forward the kernel's HID++ requests over the network to
the real mouse and forward the answers back. Nothing hardcoded, the name and
features come from the device itself. But the far end of that tunnel is a
mouse being driven by `hid-generic` on the ARM board, and a laptop 30 cm
away deciding to reconfigure its scroll wheel is not a bug I want to debug
six months from now.

So requests are *answered*, not forwarded. The daemon replies out of a cache
it refreshes every five minutes; anything it doesn't serve gets feature
index 0, "not supported", which the driver accepts without complaint. Only
readings cross the network, and nothing is ever written to the mouse.

## The percentage isn't in the mouse

The mouse says 4057 mV. The panel says 88%. Nobody in my code did that
arithmetic — `hid-logitech-hidpp` carries Logitech's discharge curve, and
passing raw millivolts through means never inventing one:

| millivolts | percent |
|---|---|
| 4057 | 88 |
| 3860 | 60 |
| 3660 | 7 |

That curve is *steep* at the bottom: 200 mV covers the last 53 points. It's
the battery being a battery, and it's a good argument for letting the driver
own the mapping.

## What to show when you don't know

A fabricated device that fabricates data is worse than no device. Everything
between the mouse and the pixel breaks independently, and each break needs an
answer that stays honest.

**Nothing yet.** zxc-pc unreachable, or the mouse off, and the daemon exits
before creating anything. `Restart=always` walks a 5 s → 60 s ladder until a
real number arrives — measured on a real outage at +6, +8, +14, +22, +37,
+60, +60 seconds. `StartLimitIntervalSec=0`, because a long outage is an
ordinary state here rather than a fault, and the default start limit would
otherwise declare the unit dead and stop trying.

![Two lanes. The daemon starts, its fetch fails with Errno 111 connection refused, it exits 1, retries on a 5 s to 60 s ladder, and finally fetches 4057 mV and creates the device. Below, the power panel lists no mouse at all until that first successful reading, then shows mouse 88%](/uploads/battery-over-wifi/failure-cold-start.svg)

**A reading, then silence.** After one good number the daemon stays up and
keeps it. A mouse that stopped answering has not changed charge, so the panel
holding its last value is the truthful answer, not a stale one. I stopped the
server socket for five and a half minutes to watch this happen.

![The daemon is publishing 88%, then two polls fail with Errno 111 and log keeping last reading, then the link returns and a poll succeeds with 4057 mV. The daemon never restarts, and the power panel shows mouse 88% unbroken across the whole outage](/uploads/battery-over-wifi/failure-link-lost.svg)

**A number that never moves.** The driver caches too, so a fresh poll changes
nothing by itself. When the reading actually changes the daemon sends an
unsolicited HID++ battery event — the same shape of broadcast a real mouse
sends unprompted — and the driver re-reads and emits a uevent.

![A five-step chain: a poll finds 3860 mV, changed, so the daemon sends an unsolicited HID plus plus event, hid-logitech-hidpp re-reads, a power_supply uevent fires, and UPower updates the panel to 60 percent. An unchanged reading sends nothing](/uploads/battery-over-wifi/failure-push.svg)

**The stream restarts.** The battery service is `BindsTo=` the mouse service,
so a dropped `netevent` stream takes it down with it — and that propagation
happens on an automatic restart, not only an explicit one. The restart job
pulls it back through `Wants=`. Nobody has to reconcile anything.

![Three lanes across two timestamps two seconds apart. At 16:57:50 zxc-mouse.service drops and a restart job is scheduled, and zxc-mouse-battery.service is stopped by BindsTo. At 16:57:52 both are active again, the battery service started by Wants with a new hidpp_battery_N node. The power panel shows mouse 88 percent, then nothing for two seconds, then mouse 88 percent again](/uploads/battery-over-wifi/failure-stream-restart.svg)

I got that one wrong first. Watching a restart loop in the journal I
concluded the design was broken, before noticing I had restarted the daemon
myself, by hand, in the middle of the outage I was inducing. The loop was the
startup path working correctly. Reading your own logs is a skill and I
briefly didn't have it.

## Groups, not root

`/dev/uhid` can create arbitrary HID devices — that is input injection with
extra steps — so it gets its own group rather than being folded into
`input`, and the service reaches it with `DynamicUser=yes` plus
`SupplementaryGroups=uhid`. Same trick as part one, one more group. Ten
minutes after installing that rule I tried to run the daemon by hand:

```
PermissionError: [Errno 13] Permission denied: '/dev/uhid'
```

Correct. My user is not in that group and shouldn't be. The security model
working as designed feels exactly like a bug until you remember writing it.

On the server side the same instinct applies to the receiver: the udev rule
grants the `hidpp` group interface `02` only, because interface `00` is the
receiver's keyboard collection, and a group that can read that is a
keylogging surface the day a keyboard gets paired.

## Was it worth it?

240 lines on the laptop, 115 on the ARM board, three unit files, two udev
rules, no root process on either end, no daemon that knows anything about
Logitech beyond four feature ids.

GNOME shows a mouse at 88% and offers no opinion about where it is. The
kernel believes there's a Bluetooth mouse attached to this laptop. There
isn't — there's a fake device answering questions with numbers that took a
round trip across the room to a receiver in a different computer, over
Tailscale, to a mouse that has never heard of any of this.

The mouse still hasn't found out.
