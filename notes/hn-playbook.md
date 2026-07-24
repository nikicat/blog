# Maximizing your odds on Hacker News

A playbook derived from all 59,711 stories submitted to HN between May 25 and
July 24, 2026 (Algolia HN Search API). Definitions used throughout: a post
**drowns** if it never gets past 2 points (never escapes /newest); a **hit**
reaches 100+ points. Baseline odds: **40.7% of posts drown, 4.4% hit, median
score is 3.** Everything below is about moving those odds — the measured spread
between doing everything wrong and everything right is roughly 10×.

## The game you're actually playing

~995 stories are submitted per day. 84.8% never reach 10 points. The only gate
that matters is the first hour on /newest: a handful of early upvotes puts you
on the front page, where outcomes spread wide (more posts land at 100–499 than
at 50–99 — posts that escape the gate tend to keep climbing). Every rule below
is really about surviving that first hour.

## 1. Post from your own domain

**73.8% of all front-page hits are personal blogs and independent project
sites** — not media, not GitHub, not corporate blogs. HN's crowd actively
prefers a bare personal domain, and platforms carry a measurable penalty:

| Venue | hit rate | drown rate |
|---|---|---|
| Personal blog / own site | 5.1% | — |
| arXiv | 3.9% | 50% |
| GitHub repo link | 2.8% | 53% |
| Self post (text) | 2.0% | 44% |
| Substack | 1.9% | 47% |
| Medium | 0.85% | 56% |
| YouTube | 0.48% | 52% |

Practical consequences:

- Same essay on Medium vs. your own domain ≈ **3× worse odds**. Never submit
  the Medium/Substack mirror of your own post.
- **Don't submit a bare GitHub repo.** Write the story of the project — what
  problem, what numbers, what went wrong — on your blog, and submit that. Code
  needs a narrative wrapped around it.
- Video effectively doesn't work on HN. `[video]` posts hit 0.6% of the time,
  YouTube links 0.48%. If the content is a video, write it up instead.

## 2. Pick the uncrowded topic — and be wary of AI framing

Hit rate is nearly the inverse of how crowded a topic is:

| Topic | share of submissions | hit rate |
|---|---|---|
| Retro-computing | 0.4% | 9.4% |
| Programming languages | 2.8% | 6.2% |
| Databases | 1.3% | 6.2% |
| Policy / law / EU | 2.5% | 5.8% |
| Linux / open source | 3.5% | 5.2% |
| Hardware / chips | 1.9% | 4.9% |
| Security | 2.1% | 4.5% |
| **Site average** | | **4.4%** |
| Web / browser | 3.0% | 3.3% |
| **AI / LLM** | **25.3%** | **3.2%** |

AI is a quarter of all submissions and converts worst. It still dominates the
top of the leaderboard — but only for lab releases, incidents, benchmark-moving
open models, and well-written skepticism ("I'm Tired of Talking to AI": 2,013
points). An ordinary AI link converts at 3.6% vs 5.3% for non-AI links.

**Rule of thumb: if your post has a non-AI angle, lead with it.** "How I made
Postgres 10× faster" beats "How AI helped me make Postgres 10× faster" — the
second framing costs you roughly a third of your odds and buries you in the
most crowded queue on the site.

## 3. Title: concrete, short, first-person; never a question

Measured lift on the 4.4% baseline hit rate:

| Title feature | lift |
|---|---|
| Year in parens — "(1998)" repost of a classic | 1.92× |
| Contains a concrete number | 1.42× |
| Short (≤6 words) | 1.24× |
| First-person (I / my / we) | 1.17× |
| Starts with why/how | 0.95× |
| Long (≥12 words) | 0.83× |
| **Ends with "?"** | **0.67×** |
| **[video]** | **0.14×** |

The #2 post of the entire window is the formula in one line:
*"Show HN: I replaced a $120k bowling center system with $1,600 in ESP32s"* —
first-person, two concrete numbers, David-vs-Goliath economics, zero hype.

Specifics read as substance; questions and hedges read as content marketing.
(Correlation, not causation — a "?" doesn't kill the post, it marks the kind of
post that dies. But when you have both framings available, pick the concrete
declarative one.)

## 4. Time it: weekend or US evening; never the UTC dead zone

Worst-to-best posting window is a **3.3× swing** in hit rate:

- **Best single window: Saturday evening US (Sun 00:00–04:00 UTC) — 7.3% hit,
  only 21% drown.** Big awake audience, near-empty /newest.
- Sunday afternoon/evening (12:00–24:00 UTC): 5.5–6.2%.
- Monday morning US (12:00–16:00 UTC): 5.8% — the audience is back before the
  PR machine is.
- Weekends beat weekdays overall: 5.4% vs 4.2%.
- **Dead zone: weekday 04:00–12:00 UTC** (midnight–8am US Eastern): 2.2–3.6%
  hit, roughly half of everything drowns.

Exception — **Show HN wants the opposite**: launches need voters more than a
thin /newest. Show HN converts best 12:00–20:00 UTC on working days (1.9–2.1%)
and worst 04:00–08:00 UTC (0.9% hit, 61% drown).

## 5. Show HN: the harshest room

Show HN overall: 51.8% drown, 1.7% hit — worse than a plain link. The deadest
combination in the entire dataset is **Show HN + AI in the title: 0.99%** (half
the rate of non-AI Show HN).

**When to add the tag.** Both of HN's official criteria must hold: you made it,
and people can try it right now. Not eligible: blog posts, announcements,
landing pages, waitlists, "feedback on my idea". What the tag buys you: the
`/show` feed (a slower second audience, from which moderators pull good ones to
the front page), kinder comment rules (the guidelines tell commenters not to be
gratuitously negative), and social license to be first-person. The convention
is a first comment telling the story — why you built it, the hard parts, the
numbers; that comment does the work a blog post would.

**Tool link vs. write-up.** A personal-blog post converts at ~5.1%, a Show HN
at 1.7% — so when the strongest artifact is the story of building the thing,
the write-up on your own domain is the higher-ceiling play. If the project
matters, do both, separated by weeks, story first. Never both at once.

What the winning Show HNs share:

- Concrete economics or numbers in the title (the $120k bowling system).
- A recognizable name shipping a major version (Homebrew 6.0.0 — 1,481 pts).
- Something the reader can try in 10 seconds in the browser.
- Cleverness/whimsy that demonstrates skill (a PowerPoint clone in one HTML
  file — 1,002 pts).

What drowns: yet another AI wrapper, agent framework, or productivity tool —
the audience has seen thirty that week.

**Niche-runnable (Linux, a specific DE, terminal tools): higher floor, lower
ceiling.** Cut of 390 Show HNs with linux/DE/terminal keywords: they drown
slightly *less* than average (49.5%) and reach 50+ at the same rate (3.85%) —
HN's audience is disproportionately these people, so the niche finds you on
/newest — but they cross 100+ only half as often (1.03% vs 2.18% for non-niche
non-AI). Winners cluster at 70–230 points: once the sub-audience that runs
your platform has voted, the ceiling arrives. Calibrate expectations (a KDE
widget at 150 points is a success), and compensate for the can't-run-it
majority: a GIF or asciinema cast at the top of the README, a WASM/browser
version if remotely feasible (the bucket's best performer shipped CLI *and*
browser-WASM), and the platform named honestly in the title — "for Hyprland"
filters in the passionate voters and heads off "doesn't work on my Mac"
comments. Meanwhile plain links *about* this niche convert at 7.6% — among the
best segments on the site — because everyone can read about a thing even when
only some can run it. That asymmetry is why the write-up usually wins.

## 6. What the biggest stories have in common

Archetypes from the window's top 50, in rough order of frequency:

1. **David vs. Goliath economics** — cheap hardware/simple code beating
   expensive systems.
2. **Corporate misbehavior and policy fights** — Android developer
   verification, Chat Control, platform lock-in. Lowest drown rates of any
   topic: outrage always finds voters.
3. **AI-lab news** — releases and incidents, not products.
4. **The contrarian essay against the current hype** — best-written skepticism
   of AI outperformed nearly every AI product launch.
5. **Technical detective stories** — decoding the bash script on a Uniqlo
   t-shirt, a backdoor in a LinkedIn job offer.
6. **Preservation / retro wins** — reading a Herculaneum scroll, anything with
   a "(1998)" on it. Retro-computing converts at 2× site average.

## 7. Don't get flagged, don't get ring-detected

Users with ≥30 karma can flag; a handful of weighted flags first buries a
story's rank, then kills it ([flagged][dead] — invisible, and absent from the
API, which is why this doc's drown rates are slight undercounts). Flags
outweigh upvotes: a story at 150 points can die to a dozen flags. Software
penalties run alongside: a flamewar detector (comments outpacing votes),
title-bait detection, domain/user bans. What draws flags:

- **Politics without a tech nexus.** The flip side of the policy topic's
  strong hit rate — Chat Control and Android developer verification survive
  because they're about technology; general politics and culture war get
  flagged within minutes regardless of votes. The outrage archetypes above are
  higher-variance than their hit rates suggest: the data only sees survivors.
- Ragebait and editorialized headlines (mods rewrite or penalize titles too —
  keep them factual).
- Dupes of recent discussions; thin content-marketing posts; low-substance
  AI-generated articles, which the community now flags aggressively.

Worse than flags: **never solicit upvotes.** Asking friends or colleagues to
upvote trips the voting-ring detector, which silently buries the post and can
penalize your account and domain. Share the bare link; let people find the
vote arrow themselves. If a post is unfairly flagged, email
hn@ycombinator.com — moderators do restore things. Technical first-person
writing on your own domain is the least-flagged genre on the site.

## Caveats

- One 60-day window (May 25 – Jul 24, 2026); seasonal effects unknown.
- Flagged/dead posts aren't in the API — true drown rates are slightly worse.
- Topic buckets are title-keyword regexes; scores were a snapshot at
  collection time.
- All of it is correlation. The consistent story across every cut — venue,
  topic, title, timing — is that HN rewards **specific, first-person,
  technical substance on your own domain, posted when /newest is quiet**, and
  punishes anything that smells like marketing, platforms, or the crowded
  topic of the moment.

---

*Method: full fetch of `tags=story` from the Algolia HN Search API via
cursor-walk on `created_at_i`, then stdlib-Python cuts by score bands, story
type, title regex topics, domain, title features, and UTC submission time.
Interactive version with charts:
<https://claude.ai/code/artifact/a79bfc88-a4f9-4493-b874-6e00bbf77c09>*
