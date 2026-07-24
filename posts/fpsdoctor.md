---
title: "The 30-hour Yak Shave: Reading One CPU Counter on Windows in 2026"
date: 2026-07-05
author: Nikolay Bryskin
description: "Overwatch framerates fell off a cliff in teamfights, and my i7-7700K swore it wasn't overheating. Proving what actually stalled it took a custom profiler, a forked kernel driver signed in CI — and the fix was a graphics slider."
image: /uploads/fpsdoctor/cover.jpg
tags:
  - windows
  - performance
  - gaming
  - profiling
---

When I play Overwatch, the framerate occasionally falls off a cliff. My monitor runs at 144 Hz; during close-range teamfights—when you either know where the enemy is or you don't—it drops to 100, 90, sometimes 80. The number bothered me, but the sudden disorientation was the real cost. I run a classic esports setup: an NVIDIA GTX 1080 paired with an Intel i7-7700K. Aging, but capable.

I assumed the CPU was thermal throttling. I'd chased a similar issue on my Linux laptop a year prior, where heat was the culprit. I usually develop on Linux, where performance questions take one command, but I refused to not know what was throttling this machine. I was going to measure it, prove it was heat, and fix it.

<!--more-->

## The thermal dead end

Claude Code helped me write a lightweight CLI diagnostic tool. A full overlay was unnecessary; a simple terminal table would do. We called it `fpsdoctor.py`. Claude wired up the Windows PDH (Performance Data Helper) counters for CPU load and queried `nvidia-smi` for GPU status.

To prove the theory, we pulled in LibreHardwareMonitor via Pythonnet to read the CPU sensors. Once I booted up the game and waited for a teamfight, the log came alive. With live metrics streaming into the terminal, all I had to do was watch the temperature column spike.

![The early fpsdoctor output showing the basic loop before PMU metrics were added.](/uploads/fpsdoctor/early-output.png)

But the CPU temperature read 71 °C. The clock ratio was 105%—turbo boost active and healthy. The throttle flags were clear.

The thermal theory died instantly.

If the CPU wasn't melting, what was failing?

## The 78% lie and the compositor trap

My next guess was the GPU. But the tool's verdict column stubbornly read `[OTHER-LIMIT]`. Neither processor was maxed out. GPU utilization hovered around 78%.

A 78% busy GPU shouldn't be the bottleneck; esports titles don't need to peg the card to 100% to be GPU-bound.

> **Excursus: Coarse utilization vs frame-timing**
> A GPU reading 78% utilization in `nvidia-smi` does not mean it has 22% headroom. Utilization only measures the percentage of sampled time the GPU had *any* work queued. In esports titles, a genuinely bottlenecked GPU often reads 70–85%. To find the true limit, measure the per-frame `GPUBusy` time against total frame time. If the GPU is busy for 15ms of a 16ms frame, it is the bottleneck, regardless of the utilization gauge.

The diagnostic logic was flawed because it relied on the coarse `nvidia-smi` metric. Claude integrated Intel's PresentMon via ETW (Event Tracing for Windows) to capture per-frame timing. We changed the logic: compare average `GPUBusy` per frame against `CPUBusy`. Whichever dominates is the limiter.

When I tested again, `fpsdoctor` named a culprit: `[CPU-LIMIT]`. But the numbers looked ridiculous. The game was running at 30 to 45 fps, with massive 500ms hitches.

The tool was measuring `dwm.exe`, the Windows desktop compositor. I play Overwatch in borderless windowed mode at 2.5K. Because of this, the desktop compositor was lazily refreshing in the background. We added a foreground window check to filter out alt-tabbed rows and lock onto the game's Process ID.

Finally, clean data arrived. At 110 fps, the GPU was busy 80% of the frame, but the CPU was busy 98% of the time. The 7700K was the bottleneck. But why was it struggling when it wasn't fully utilized?

## Why an 80% core is saturated

A lingering contradiction: the busiest single logical core sat at only 80% utilization. If the CPU was the limit, why wasn't a core pegged at 100%?

> **Excursus: CPU Thread Migration**
> Windows rarely leaves a hot thread on a single core for a full second. The OS scheduler migrates the heavy game thread across different physical cores every few milliseconds to distribute heat. When a monitoring tool samples core utilization over a one-second window, it sees the workload smeared across three or four cores. An 80% reading on the busiest logical core often hides a single thread that is completely saturated.

The frame timing proved it. The GPU sat idle for 20% of the frame waiting to be fed, while the CPU worked the entire time. A starved GPU and an exhausted CPU defines a CPU-bound game.

But *what* in the architecture was limiting performance? The base clock was 4.2 GHz, boosting to 4.4 GHz perfectly. Was it IPC (instructions per cycle)? Memory latency? The 7700K's small 8 MB L3 cache?

I wanted to measure the percentage of cycles the CPU spent idle, waiting on RAM. On Linux, this is a trivial `perf stat` call. On Windows, it meant reading the hardware Performance Monitoring Unit (PMU) via Model Specific Registers (MSRs). And Windows does not let user-space programs read MSRs.

## The restricted "unrestricted" driver

To read the PMU on Windows, you need a kernel driver. Every clean path failed. Intel's official profilers failed me: Intel PCM required test-signing the OS and rebooting, and the latest Intel VTune dropped support for Kaby Lake. Older VTune versions were hidden behind registration walls and broken download links.

Eventually, we found a Microsoft-signed, allow-listed driver called PawnIO. It was exactly what we needed. We hooked it up, but it was strictly read-only; we couldn't arm the PMU counters.

Then we spotted a lifeline in the PawnIO documentation: an installer option for an "unrestricted (FOR DEVELOPERS)" build.

I installed it. I ran the script. Access denied.

Claude told me the driver was still blocking custom module loads due to driver signature enforcement. "Stop stopping me claude," I typed. "Tell me exactly what to install to build the driver." I thought the AI's safety guardrails were just overly cautious about a documented developer mode.

Claude read the PawnIO source code and proved me wrong. It disassembled the installer payload and compared the digital signatures. The signed release driver used an RSA-4096 certificate; the "unrestricted" build used an RSA-2048 test certificate. Crucially, neither binary carried the `PAWNIO_UNRESTRICTED` compiler flag required to allow custom counter-reading modules. The developer mode was broken upstream.

Because Microsoft maintains a vulnerable-driver blocklist in Windows 11 to prevent malware from gaining root access, developers can't just distribute a signed kernel driver that allows arbitrary MSR reads. You either test-sign your OS—which disables anti-cheat—or you build and self-sign a compliant driver locally.

Since the signed driver was broken, we bypassed the distribution problem. We forked the PawnIO repository and configured a GitHub Actions CI pipeline to compile the truly unrestricted driver from source, signing it with a temporary certificate.

I downloaded my custom artifact, loaded it, and ran `fpsdoctor.py`.

"Omg, it's working!" I typed. Time to test it in Overwatch and see what the PMU actually had to say.

## The memory wall

The live PMU numbers streamed in, and they were undeniable.

During the chaotic teamfights where my framerate dropped, the 7700K spent 36% to 59% of its cycles stalled, waiting on DRAM. The instructions-per-cycle (IPC) collapsed to roughly 0.5. The L3 misses per thousand instructions (MPKI) spiked between 16 and 28.

The Overwatch working set was spilling out of the 7700K's tiny 8 MB L3 cache and fetching from slow DDR4-2400 system memory. The CPU spent half its time standing still.

![How the 8MB L3 cache spills into slow DDR4-2400 memory during a teamfight, stalling the CPU while IPC drops to roughly 0.5.](/uploads/fpsdoctor/memory-wall.svg)

The signature was identical whether the game was capped at 60 fps or uncapped at 122 fps. The framerate wasn't pushing the CPU. The sheer memory footprint of the scene was.

> **Excursus: Memory-stall-bound execution**
> A CPU limit is rarely about clock speed. In gaming, it is often a memory limit. When a frame requires more data than the L3 cache can hold, the CPU must fetch from RAM, taking hundreds of cycles per miss. During these cycles, the processor halts execution (a memory stall). Overclocking the CPU core frequency does nothing to solve this; the cores simply wait faster.
> To test your own rig for memory stalls using PresentMon, run `PresentMon.exe --output_stdout` and monitor the `CPUBusy` metric during a framerate drop. If `CPUBusy` is high but overall CPU package utilization is low, cache spilling is the likely culprit.

But if the cache was overflowing, was there any way to stop it without buying a new processor?

## The hidden win

I had proven my bottleneck, but I still wanted those frames back. A common belief among gamers is that lowering graphics settings only helps if you are GPU bound. If the CPU is choking on memory latency, how could a graphics slider fix it?

I spent the next two hours quietly tweaking Overwatch settings while `fpsdoctor` logged every frame. I changed the "Lighting Quality" setting from Medium to Low.

The CSV logs captured a sharp regime change. My 95th-percentile framerate in heavy fights jumped from 142 to 174 fps. My session peak climbed from 171 to 238 fps. As the framerate rose, my GPU utilization actually increased from 69% to 84%.

Lowering Lighting Quality relieved the CPU. My hypothesis is that complex lighting effects consume a significant amount of the L3 cache. Turning them down reduced the cache pressure, lowered the memory stalls, and gave the CPU the breathing room it needed to feed the GPU faster.

I started the weekend annoyed by a framerate drop and ended it by writing a custom profiler to measure the limits of the Kaby Lake architecture. Diagnosing hardware bottlenecks on Windows requires navigating a hostile driver security model. But the truth is worth the effort—especially when it proves your graphics settings can actually fix your CPU bottlenecks.
