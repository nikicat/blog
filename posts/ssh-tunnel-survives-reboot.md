---
title: "My SSH tunnel survived 3 minutes dead"
date: 2026-07-31
author: Nikolay Bryskin
description: "The process was gone and the socket with it, and three minutes later the far end still had not noticed. How to carry a live SSH session across a reboot with CRIU — and the TCP reset that silently kills it if you skip one step."
image: /uploads/ssh-tunnel-survives-reboot/cover.png
tags:
  - linux
  - ssh
  - networking
  - kernel
---

I killed the process holding an SSH tunnel, waited three minutes, and brought
it back. Same pid, same socket, same encrypted session. The forwards started
carrying traffic again on the first request, and the machine on the other end
never learned that anything had happened.

That should not work. SSH has no session resumption: the keys are negotiated
once per connection and live only in the memory of the two processes. There
is no ticket to present, nothing to reconnect with. And yet the connection
came back, because "lives only in memory" turns out to be a much weaker
statement than it sounds.

<!--more-->

<style>
.post-body img[src$=".svg"] { --w: min(1120px, calc(100% + 20rem), 96vw); display: block; width: var(--w); max-width: none; margin-inline: calc((100% - var(--w)) / 2); }
@media (max-width: 760px) { .post-body p:has(> img[src$=".svg"]) { overflow-x: auto; } .post-body img[src$=".svg"] { width: auto; min-width: 900px; margin-inline: 0; } }
</style>

## Why you would ever want this

Normally you would not. A background SSH tunnel that dies on reboot is a
solved problem: give the machine its own key, write a unit file, let systemd
restart it forever. That fixes reboots, link flaps and far-end restarts all
at once, and it is what you should do.

This is about the case where you cannot. Two versions of it show up in
practice, and both are becoming more common rather than less:

**The credential is a physical object.** The far end authenticates a
hardware-backed key — a FIDO token that must be present and touched. That is
the entire point of the token: no unattended machine can produce that
signature. A tunnel established through it can be *used* forever, but never
re-established without a human and a pocket.

**The session was instantiated remotely, by someone who has since left.** An
operator connects with agent forwarding, sets up forwards on the host, and
logs out. Agent forwarding deliberately leaves nothing behind: the private
key never left the operator's laptop, only signatures crossed the wire. The
running session is now an asset the host itself cannot reproduce.

In both cases the tunnel is not configuration, it is a *capability* — one
that a reboot destroys and no script can recreate. Which reframes the reboot
from routine maintenance into something you schedule around a person's
travel plans. That was worth trying to fix.

## Why it looks impossible

Ask what a live SSH connection actually consists of and you get three piles
of state in two different places.

![Where an SSH session's state lives: the ssh process memory holds session keys and cipher state, the kernel socket holds sequence numbers and queues, and the peer holds its own copy which cannot be touched.](/uploads/ssh-tunnel-survives-reboot/state.svg)

The session keys come out of a Diffie–Hellman exchange at connection setup
and are never transmitted, by design. They sit in the process's heap
alongside the cipher and MAC state, the packet counters, and the bookkeeping
for every channel and forward. Underneath, the kernel holds the TCP socket:
sequence and acknowledgement numbers, the send and receive queues, the
window, the negotiated options.

And the peer holds its own mirror of all of it, which you cannot touch,
cannot ask to resynchronise, and must not alarm.

There is no protocol-level way in. TLS has session tickets and QUIC has
connection IDs that survive a client's address changing; SSH has neither.
Nor does `mosh` help: it survives roaming and sleep because `mosh-server`
keeps running on the far end, but here it is the near end that reboots,
taking the session key with it. `tmux` reattaches a shell, not a connection.

But "the keys are in process memory" is only an obstacle if you think of
memory as private. To the kernel it is a mapping you can read, and to a
checkpointer it is a file.

## The two halves are both capturable

The userspace half has been solvable for years: [CRIU](https://criu.org)
(Checkpoint/Restore In Userspace) stops a process, walks its address space,
open files and mappings, and writes them to disk. Session keys are just bytes
in a page; the checkpointer does not know or care what they mean.

The kernel half is the interesting one, and it exists *because* of CRIU. The
`TCP_REPAIR` socket option — merged in Linux 3.5 — puts a socket into a mode
where you can read out its sequence numbers and queue contents, and later
write them back into a fresh socket, without any of it going on the wire. It
is how container live-migration keeps connections open across a move between
hosts. It is not a hack around the network stack; it is a supported door in
the side of it.

Put the two together and a checkpoint looks like this:

![Time sequence of checkpointing and restoring a live SSH connection: install a packet filter, freeze the process, read socket state via TCP_REPAIR, write images to disk, kill the process, then restore it later while the peer only ever sees an unanswered retransmit.](/uploads/ssh-tunnel-survives-reboot/checkpoint.svg)

The peer's experience of that whole sequence is one segment that went
unacknowledged for a while. TCP is built for exactly that — it retransmits
with exponential backoff and, by default, keeps trying for around fifteen
minutes before giving up. A gap of a minute or three is well inside the
envelope the protocol already tolerates.

Note the first and last steps. Before anything is frozen, the checkpointer
installs a packet filter that drops traffic in both directions between the
two endpoints, and it removes it only after the socket is back. That is not
politeness. It is the difference between this working and not, and it is the
subject of the section after next.

## Doing it

My target was a background `ssh` holding several local forwards, started with
`-N`, orphaned to init: no controlling terminal, `stdin`/`stdout`/`stderr` on
`/dev/null`, one established TCP socket, a few listening sockets and a
control socket. That shape matters, and it is a friendly one. A checkpointer's
hardest problems are terminals and process trees; a forward-only SSH client
has neither.

Find the process and confirm the shape:

```console
$ ls -l /proc/$PID/fd
0 -> /dev/null
1 -> /dev/null
2 -> /dev/null
3 -> socket:[154275]      # the established connection
4 -> socket:[156124]      # a listening forward
...
$ awk '{print $7}' /proc/$PID/stat     # controlling terminal, 0 = none
0
```

If that last number is not zero you have a session with a terminal attached
and you will need `--shell-job` and a good deal more patience.

The dump itself, as root:

```sh
install -d /var/lib/criu/tunnel
criu dump -t $PID -D /var/lib/criu/tunnel --tcp-established --file-locks -v4 -o dump.log
```

`--tcp-established` is what pulls in the socket. The process is gone when
this returns; everything now lives in a few megabytes of image files.

The restore, which can be minutes and a reboot later:

```sh
criu restore -d -D /var/lib/criu/tunnel --tcp-established -v4 -o restore.log
```

Then verify through the tunnel itself — send a real request at a forwarded
port and see whether the service on the far side answers. Do not verify with
`ssh -O check`, for reasons in the gotchas below.

> [!NOTE]
> Two properties make this far less frightening than it sounds. A failed
> *dump* leaves the process running and untouched — I hit several while
> debugging and never lost the connection. And the images persist, so a
> failed *restore* can be retried after fixing whatever broke. Losing the
> tunnel takes both halves failing.

That is the whole mechanism, and within a single boot it worked first try
once the tooling itself was fixed. Across a reboot there is one more thing,
and it is the part I would have got wrong.

## The reset that eats your connection

While the connection is checkpointed there is no socket. The port is not
bound. If a packet arrives from the peer during that window, the kernel does
what it does for any packet to a closed port: it answers with a RST, and the
peer tears the connection down for good. Your images are now a perfect
snapshot of a connection that no longer exists at the other end.

This is why CRIU installs those filter rules. During dump and restore it adds
a mark-based pair covering both directions, which is why the package depends
on a firewall library at all:

```console
# nft list ruleset | grep -A1 'tcp sport 22'
ip saddr 203.0.113.7 ip daddr 198.51.100.4 meta mark != 0x0000c114 tcp sport 22 tcp dport 49731 drop
ip saddr 198.51.100.4 ip daddr 203.0.113.7 meta mark != 0x0000c114 tcp sport 49731 tcp dport 22 drop
```

**Those rules live in the kernel, and a reboot takes them with it.** From the
moment networking comes back until your restore runs, the connection is
completely unprotected — and that is precisely the window in which a machine
that has been offline for a minute is most likely to receive something.

It is not theoretical. I put my own equivalent rule in place before dumping
purely as a belt-and-braces measure, and its counter was non-zero within
seconds. Over a three-minute gap it caught a handful of packets: the far end
retransmitting a small pending segment, backing off as it went. Any one of
those, arriving with no rule in place, would have ended the connection.

![Two time sequences compared across a reboot. Without a filter installed before networking, the first packet from the peer draws a reset and the connection is destroyed. With the filter installed early, the packet is swallowed, the restore runs, the filter is removed, and traffic resumes.](/uploads/ssh-tunnel-survives-reboot/reboot.svg)

So a reboot needs one step a same-boot restore does not: install the drop
rule yourself, *before networking starts*, and remove it only once the
restore has succeeded.

```sh
# before the dump
iptables -I INPUT 1 -s $PEER -p tcp --sport $PEER_PORT -j DROP
# ... dump, reboot, restore ...
iptables -D INPUT   -s $PEER -p tcp --sport $PEER_PORT -j DROP
```

In unit terms the ordering is: rule before the network, restore after the
network (the addresses your forwards bind must exist first), delete after the
restore. Get that sequence wrong in either direction and you either lose the
connection or restore one that can never receive anything.

Two smaller boot-time details in the same family. The source port of the old
connection sits in the ephemeral range, so something else can claim it while
you boot — reserve it with
`sysctl -w net.ipv4.ip_local_reserved_ports=$SRC_PORT` before you dump. And
the pid must be free; in practice it always is right after boot, and CRIU
forces the matter through `ns_last_pid` anyway.

## Three things that bit me

**The distribution's own build could not checkpoint anything.** Every dump
died the same way:

```console
Error (criu/parasite-syscall.c:87): si_code=4 si_pid=… si_status=11
Error (criu/parasite-syscall.c:94): … was stopped by 11 unexpectedly
```

Signal 11 is a segfault, and it is the *parasite* — the small blob CRIU
injects into the target process to make it dump itself — that is dying. It
had nothing to do with SSH: a plain `sleep` failed identically, which is the
test worth running before you blame your workload.

The cause is that the parasite executes inside another process with no libc
and no ordinary stack, so it must be compiled without the hardening a distro
applies to everything else. This one's `PKGBUILD` strips `_FORTIFY_SOURCE`
already — evidence the problem is known — but not
`-fstack-protector-strong` or `-fstack-clash-protection`. Rebuilding the same
version with plain flags fixed it outright:

```sh
# in build(), replacing the existing CFLAGS line
export CFLAGS="-march=armv8-a -O2 -pipe"; export CXXFLAGS="$CFLAGS"; export LDFLAGS=""
```

On aarch64, Arch Linux ARM, kernel 7.1.5, gcc 16.1.1, CRIU 4.2.1. Worth
knowing that a system upgrade will silently put the broken build back, so pin
the package. `criu check --all` is not a useful oracle here either — it
passed with warnings both before and after, and the warnings it does emit
(dirty tracking, userfaultfd, 32-bit compat) are all irrelevant to a
one-shot, same-kernel dump and restore. The one that *is* worth heeding: with
no vDSO-map API it falls back to `mremap()`, so do not change the kernel
between dump and restore.

**The multiplexing control socket does not survive.** The forwards came back
perfectly; `ssh -O check` did not, and the socket file was there but refused
connections. The reason is a neat little impedance mismatch. OpenSSH binds
the control socket at `<path>.XXXXXXXX` and then renames it into place — and
`rename()` does not change the path the kernel recorded at `bind()` time.
Unix sockets are reached through the filesystem inode, so connecting to the
final path works fine for the original process. CRIU faithfully re-binds the
name it was told, the temporary one, and materialises no filesystem entry for
it; the final path still holds the old, now-dead inode. Result: a listening
socket nothing can reach, and `ECONNREFUSED` at the path you would use.

There is no fix — a path cannot be attached to an already-bound Unix socket
after the fact. It is a real limitation with a narrow blast radius: your
forward set is frozen as it was at dump time, since adding one needs the
control channel. Verify through the tunnel, not through `-O check`.

**`--tcp-close` is not the flag you want.** When a dump complains about a
socket in a state other than established, the obviously-named option is a
trap: it means *do not preserve connections, restore them closed*, which
would take the master connection with it. I had picked up a couple of stray
`CLOSE-WAIT` forwarded connections just by probing the tunnel to check it was
alive. They cleared by themselves within seconds. Wait them out.

## What it actually buys, and what it costs

The measured result: a three-minute outage, survived. That covers a real
reboot two to three times over, which was the margin I wanted before trusting
it. The far end's patience is the number you cannot look up — it depends on a
`ClientAlive` setting you may not be able to read — so measure it on the
connection you care about rather than assuming the default.

What survives: the TCP connection, the encrypted session, every forward, the
pid. What does not: the control channel, and any connection that was
travelling *through* a forward at dump time — those endpoints are on the
machine that just went away.

And the honest framing. This is a way to carry an unreproducible capability
across a maintenance window, not a substitute for making it reproducible. If
you can put a key on the box, do that instead and never think about parasites
or repair-mode sockets again. If the credential is a physical object in
someone's pocket, or an agent that logged out last Tuesday, this is a
genuinely good tool — and the failure mode is symmetric with doing nothing,
since a botched restore leaves you exactly where a plain reboot would have.

Which is the part I find quietly satisfying. The received wisdom is that a
reboot ends every session on the machine, and it is true right up until you
notice that "the keys only exist in memory" describes a file you have not
written yet.
