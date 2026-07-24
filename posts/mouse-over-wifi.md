---
title: "Mouse over WiFi"
date: 2026-07-24
author: Nikolay Bryskin
description: "Both USB-C ports were taken — so the mouse got plugged into the ARM board nearby and forwarded to the laptop as input events: netevent, systemd socket activation, and a Tailscale-only port."
image: /uploads/mouse-over-wifi/cover.jpg
tags:
  - linux
  - systemd
  - networking
  - tailscale
---

Today I found that I needed to connect a USB mouse to my laptop — and both
USB-C ports were occupied, one by the monitor, one by power. Turns out it's
not a huge deal on Linux if you have another PC nearby.

The reasonable fix is a €3 USB-C adapter. But the adapter is three days of
shipping away, and the other PC — a little Rockchip ARM board that lives on
my desk — was right there, with free USB-A ports and a network connection to
my laptop. On Linux, "the mouse is plugged into the wrong computer" is not
really a hardware problem. It's a routing problem.

<!--more-->

## Pick your layer

There are two ways to ship a USB device across a network:

**Forward the USB device itself** — that's `usbip`, which is in the mainline
kernel. The remote host sees a real USB device, URBs get shuttled over TCP,
and everything that could talk to the physical device can talk to the remote
one. That's the right tool when something needs the *device* — firmware
flashers, smartcard readers, license dongles.

**Forward the input events** — a mouse is not an interesting USB device. By
the time applications see it, it's just a stream of tiny `input_event`
structs coming out of `/dev/input/eventN`: relative X, relative Y, button,
sync. The kernel will happily accept the same structs back through
`/dev/uinput` and synthesize a new input device out of them. So instead of
tunneling USB, you can read events on one machine and replay them on the
other. Less protocol, less latency sensitivity, and it works regardless of
what's on the other end — Wayland, X11, a bare console.

For a mouse, events win. The tool for this is
[netevent](https://github.com/Blub/netevent) — a ~130 KB binary with two
relevant subcommands: `cat` (open an event device, dump its events to
stdout) and `create` (read events from stdin, create a uinput clone). It's
`netevent-git` in the AUR.

## The five-minute version

Find the mouse on the machine it's plugged into. `/dev/input/by-id/` gives
you stable names, unlike `eventN` which reshuffles on replug:

```console
$ ls -l /dev/input/by-id/
lrwxrwxrwx 1 root root  9 platform-noserial-if01-event-mouse -> ../event8
lrwxrwxrwx 1 root root 13 usb-Logitech_USB_Receiver-hidraw -> ../../hidraw0
```

Then, from the laptop, one pipe:

```console
$ ssh zxc-pc 'sudo netevent cat /dev/input/by-id/platform-noserial-if01-event-mouse' \
    | netevent create
```

That's genuinely all of it. `netevent cat` grabs the device exclusively
(`EVIOCGRAB` — the server machine stops seeing the mouse), streams events
over the SSH connection, and `netevent create` conjures a virtual "Logitech
USB Receiver Mouse" on the laptop that the desktop picks up like any
hotplugged device. The cursor moves. SSH gives you encryption and auth for
free.

I used exactly this for about an hour. Then the sysadmin brain kicked in,
because the pipe has problems:

- it needs `sudo` on the server (`/dev/input/*` is root:input),
- it dies silently on suspend, roaming, or a Wi-Fi blip, and takes the
  mouse with it,
- it drags my interactive SSH config — agent forwarding, a GPG socket
  RemoteForward — into what should be a dumb transport,
- and it plants a landmine that I would step on two hours later. We'll get
  there.

## The grown-up version: socket activation

What I actually want is an appliance: the server *exports* the mouse,
permanently and cheaply; the laptop *attaches* when it wants to; the grab —
the mouse going dead on the server — should last exactly as long as the
attachment. That maps one-to-one onto systemd socket activation:

![Events flow down through zxc-pc — receiver, /dev/input/event8, netevent cat — across a Tailscale-only TCP link on port 8763, then up through the laptop — socat, netevent create, /dev/uinput — into a virtual mouse](/uploads/mouse-over-wifi/architecture.svg)

Two unit files on the server. The socket:

```ini
# /etc/systemd/system/zxc-mouse.socket
[Unit]
Description=Export Logitech mouse over Tailscale (netevent)

[Socket]
ListenStream=8763
BindToDevice=tailscale0
Accept=yes
MaxConnections=1

[Install]
WantedBy=sockets.target
```

And the per-connection service it spawns:

```ini
# /etc/systemd/system/zxc-mouse@.service
[Unit]
Description=netevent mouse stream to %i

[Service]
ExecStart=/usr/bin/netevent cat /dev/input/by-id/platform-noserial-if01-event-mouse
StandardInput=socket
StandardOutput=socket
StandardError=journal
DynamicUser=yes
SupplementaryGroups=input
```

Almost every line here is doing security or lifecycle work:

- **`Accept=yes`** is inetd mode: each TCP connection spawns a fresh
  instance with the connection as stdin/stdout. `netevent cat` doesn't know
  the network exists — it writes to "stdout" and systemd has already wired
  that to the socket.
- **`BindToDevice=tailscale0`** scopes the listener with `SO_BINDTODEVICE`:
  connections arriving via any other interface never reach it. The mouse is
  reachable over the tailnet and nothing else — no LAN exposure, and
  Tailscale brings the encryption and authentication that raw TCP doesn't.
- **`MaxConnections=1`** — a second client gets refused instead of fighting
  over the grab.
- **`DynamicUser=yes` + `SupplementaryGroups=input`** is my favorite part.
  The prototype needed `sudo` for exactly one reason: reading
  `/dev/input/event8`, which is `root:input 0660`. But that's not a *root*
  problem, it's a *group* problem — so let systemd mint a throwaway user
  that exists only for the lifetime of the connection and holds exactly one
  privilege: the `input` group. No sudo rules, no long-lived root process,
  no real user to keep in the group forever (permanent `input` membership
  is a standing keylogger license — every process you run can read every
  keystroke).

The lifecycle falls out of the socket activation for free:

![Sequence diagram: laptop connects over the tailnet to port 8763, zxc-pc spawns an instance which grabs the mouse; events stream into the uinput clone; on disconnect the instance exits and the grab is released](/uploads/mouse-over-wifi/sequence.svg)

Nobody is grabbing anything while no one is attached. The mouse is a shared
resource with connection-scoped ownership, which is exactly the semantics
you'd want and exactly what an always-running daemon wouldn't give you.

On the laptop, the attaching end is one more unit:

```ini
# /etc/systemd/system/zxc-mouse.service
[Unit]
Description=Attach Logitech mouse exported by zxc-pc

[Service]
ExecStart=/bin/sh -c 'socat -u TCP:zxc-pc:8763,keepalive,keepidle=5,keepintvl=5,keepcnt=2 STDOUT | netevent create --duplicates=resume'
Restart=always
RestartSec=2
RestartSteps=8
RestartMaxDelaySec=60
DynamicUser=yes
SupplementaryGroups=input
```

Same trick on this side — `netevent create` needs `/dev/uinput`, which is
also `root:input 0660`, so the same throwaway-user-plus-one-group pattern
covers it. `socat` instead of `nc` because of the keepalive knobs: a mouse
stream is silent when the mouse is idle, so without keepalives a dead peer
looks identical to a boring evening. With `keepidle=5,keepintvl=5,keepcnt=2`
a vanished server is detected in ~15 seconds, the pipe exits, and
`Restart=always` walks the backoff (2 s → 60 s) until the server is back.

One deliberate omission: this unit has **no `[Install]` section**. It cannot
be enabled at boot, even by accident. `systemctl start zxc-mouse` is the new
"plug in the mouse"; `systemctl stop zxc-mouse` is unplugging it — and
handing it back to the machine it's physically attached to.

Did the interface scoping actually work? Two checks:

```console
$ ssh zxc-pc ss -tln | grep 8763
LISTEN 0  4096  *%tailscale0:8763  *:*        # the % is SO_BINDTODEVICE

$ nc -z -w3 192.168.88.247 8763               # via LAN: refused
$ systemctl start zxc-mouse && systemctl is-active zxc-mouse
active                                         # via tailnet: streaming
```

## The landmine

I promised a landmine. First start of the polished new service:

```
sh[1510469]: error: error while expecting hello packet: Success
```

The client connects, expects netevent's protocol hello, and gets EOF —
reported with errno 0, the error message equivalent of a shrug. The server
journal has the real story:

```
netevent[61925]: error: failed to grab input device: Device or resource busy
```

Something already held the exclusive grab. It was the prototype — the SSH
pipe from two hours earlier. I had killed my end of it, but the remote
`netevent cat` had no idea: it only touches its dead socket when the mouse
*moves*, and the mouse, grabbed and therefore inert, had not moved. A
process whose only job is to report motion, kept alive by the absence of
motion, holding the grab forever. The new service died against it on every
retry.

One `pkill` on the server later, the service came up and stayed up.

## Was it worth it?

Latency over the LAN (Tailscale negotiates a direct path between machines
on the same network) is imperceptible — mouse events are a few dozen bytes
each, and the event clock is carried in the protocol. The whole thing cost
three unit files and one 130 KB tool, runs with no root process and no sudo
rule on either machine, exposes one port on one virtual interface, and
gives the mouse back the moment I stop the service.

The dongle is still not here. The mouse never found out it's being
forwarded.
