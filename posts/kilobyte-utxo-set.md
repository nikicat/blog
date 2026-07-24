---
title: "The Kilobyte UTXO Set: Utreexo, SwiftSync, and Bitcoin's state problem"
date: 2026-07-16
author: Nikolay Bryskin
description: "Interactive version: this article has a live playground edition where you can add coins, inspect..."
image: /uploads/kilobyte-utxo-set/cover-bfjad0ppv1wiq78l2c2p.png
tags:
  - bitcoin
  - cryptography
  - datastructures
---

> **Interactive version:** this article has a [live playground edition](https://nikicat.github.io/kilobyte-utxo-set/) where you can add coins, inspect Merkle proofs, and spend them yourself. The GIF below is a recording of it.

Every Bitcoin node drags a **12 GB database** through its whole life just to answer one question: *does this coin exist?* Cryptographic accumulators — Utreexo above all — compress that answer into **about thirty hashes**. Here's why that matters, how it works, and what it costs.

<!--more-->

## 1 · Validation is cheap. State is not.

To validate a transaction, a node must check each input against a record of every coin that exists and hasn't been spent — the *UTXO set* (unspent transaction outputs). Each check needs a handful of facts: the coin **exists**, its **amount**, its **spending condition** (script), plus its **creation height and coinbase flag** (for coinbase maturity and BIP 68 relative timelocks). Then the spent coins are deleted and the new outputs inserted.

| ~170 M | ~12 GB | ~3 B | **~0.9 kB** |
|---|---|---|---|
| unspent coins tracked by every node | UTXO database on disk | random lookups during one full sync | the same state, as a Utreexo accumulator |

Signatures can be skipped below a reviewable checkpoint (`assumevalid`), bandwidth can be bought, but the UTXO set is different: it's **random-access state touched by every single input**. If it fits in RAM, lookups are ~100 ns; if it doesn't, they become disk seeks and a full sync degrades from hours to days. State is the term that decides whether a Raspberry Pi and a workstation live in the same universe.

<details>
<summary>How Bitcoin Core actually stores it — LevelDB, dbcache, and the flush spiral</summary>


Core keeps the UTXO set in a LevelDB database (`chainstate/`, ~48 bytes per coin plus index overhead) fronted by an in-memory cache (`-dbcache`, default 450 MiB). While the working set fits in the cache, coin lookups and updates are memory-speed. When the cache fills during sync, Core writes it out and *empties it* — so the next few million lookups all miss and go to disk.

With ~170M coins needing north of 10 GB of cache, a default-sized cache overflows constantly. Every miss is a random read; every flush rewrites overlapping LevelDB files (compaction). On a machine with 2–4 GB of RAM this — not hashing, not signatures — is where initial sync goes to die. The standard advice "raise your dbcache" is a workaround for exactly the cost accumulators remove.

</details>

<details>
<summary>Why snapshots don't solve this — assumeutxo still ships the state</summary>


`assumeutxo` lets a node start from a UTXO snapshot and validate history in the background — a big usability win. But the snapshot *is* the 12 GB state: you still have to download it, hash it, store it, and random-access it forever after. It moves the state problem around the timeline; it doesn't shrink the state. An accumulator shrinks the thing itself, which is why the two compose nicely: an accumulator checkpoint is a kilobyte you can read in a code review.

</details>

## 2 · Flip who carries the data

An *accumulator* is a compact commitment to a set. It supports four operations: **add** an element, **delete** one, **prove** membership, and **verify** a proof. The trick is a change of responsibility: the verifier keeps only the tiny commitment, and whoever wants to *spend* a coin must present a proof that it's in the set.

```text
Today — the node carries the set
  tx input “spend coin X”
    → look up X in a 12 GB database   (random read, per input, forever)
    → exists? get amount + script → validate

Accumulator — the spender carries a proof
  input + ~1 kB proof (“X is in the set, here's the path”)
    → check proof against ~28 hashes  (pure hashing, no database)
    → amount + script are inside the proven leaf → validate
```

The database becomes a receipt check. Nothing about Bitcoin's consensus rules changes — only *how a node represents what it already verifies*.

## 3 · Utreexo: a forest that counts in binary

Utreexo (Dryja, 2019) arranges the UTXO set as a **forest of perfect Merkle trees** — every leaf is the hash of one coin (its outpoint, amount, script, creation height, and coinbase flag). The forest's shape is forced by one rule: *tree sizes are the binary digits of the coin count*. 6 coins = `110₂` = one 4-tree and one 2-tree. The node stores only the tree **roots** and the count. That's the entire database.

![Playground recording: two coins are added (watch equal-height trees carry-merge like a binary counter, 6 → 8 coins collapse into one 8-tree), then coin c's Merkle proof is highlighted and it is spent — the proof hashes become the new roots in place.](/uploads/kilobyte-utxo-set/playground.gif)

*(Recording of the [interactive playground](https://nikicat.github.io/kilobyte-utxo-set/) — try it yourself.)*

Three things to notice:

**Adding is a carry.** A new coin starts as a lone 1-tree. If a 1-tree already exists, the two combine under a new parent; if that collides with a 2-tree, they combine again — exactly like incrementing a binary counter. Adds need *no data at all* beyond the roots.

**A proof is a path.** To spend a coin, you present the coin plus its sibling hashes up to a root — about `log₂(n)` hashes, ~28 for the real UTXO set. The amount and script are inside the leaf hash, so a proof can't lie about them: the hashes wouldn't land on the node's stored root.

**The proof is also the update.** This is Utreexo's quiet elegance: when a coin is deleted, the new roots of the leftover pieces are *literally the hashes from the proof you just verified*. Verification and the state update consume the same bytes — the node never needs data it doesn't already hold in its hand.

<details>
<summary>The delete, step by step — worked example with 4 coins</summary>


Say the forest holds one 4-tree over coins `a b c d`: root `R = H(H(a,b), H(c,d))`. A transaction spends `c`, attaching the proof `{d, H(a,b)}`.

**Verify:** the node computes `H(c,d)` from the claimed coin and its sibling, then `H(H(a,b), H(c,d))`, and checks the result equals its stored root `R`. It does — the coin exists, and its amount/script (inside `c`'s leaf hash) are authentic.

**Delete:** remove the 4-tree's root from state. Three coins remain, and 3 = `11₂`, so the forest must become a 2-tree plus a 1-tree. Their roots are `H(a,b)` and `d` — *both are items from the proof*. No lookup, no recomputation from leaves the node doesn't have.

In general, deleting a leaf makes its sibling "move up" one level, and the proof always contains exactly the hashes needed to rebuild every affected root.

*A footnote for the precise:* this tree-splitting is how the 2019 paper presents deletion. The implementations that shipped (utreexod, Floresta's rustreexo) use a newer *swapless* scheme — the leaf counter never decreases, the deleted slot simply goes empty, and `d` moves up into its parent's position, so the example would end as the single root `H(H(a,b), d)` rather than two roots. The property that matters is identical in both designs: the verified proof contains exactly the bytes needed to write the new roots.

</details>

<details>
<summary>What does the node trust? — nothing but its own hashes</summary>


Where do the roots come from? **The node computes them itself, from genesis** — it starts with an empty forest and applies every add and delete with its own hands as it validates each block. The accumulator state at any height is a pure function of the chain, exactly like today's UTXO set, only smaller. Nobody hands you roots.

Given that, proofs are self-authenticating: a proof either hashes up to *your own* stored roots or it doesn't, and forging one — wrong amount, wrong script, a coin that never existed — requires a SHA-2 collision (implementations hash with SHA-512/256). Whoever supplies proofs (a peer, a bridge) is exactly as untrusted as a peer supplying blocks today: garbage fails validation and the block is rejected.

Bridges are therefore a **liveness** dependency, never a safety one — with no proof you can't validate a spend, so you can be starved, but you cannot be fooled. The one optional trust-flavored piece is a hardcoded checkpoint (starting from baked-in roots instead of genesis), and that sits in the same trust class as `assumevalid`: a reviewable constant in the source, auditable by anyone who syncs without it.

</details>

<details>
<summary>Where do proofs come from? — bridge nodes and stale proofs</summary>


Somebody has to generate proofs for spenders, and today's wallets don't track them. **Bridge nodes** fill the gap: they maintain the *entire* forest (every internal hash — larger than a plain UTXO database) and attach proofs to transactions and blocks on behalf of the legacy ecosystem.

There's a subtler cost: **proofs go stale**. Every block adds and deletes leaves, which restructures the forest, so a proof valid at height *H* may be wrong at *H+1*. Wallets that hold their own proofs must refresh them as blocks arrive (cheap per block, but a standing obligation), or lean on a bridge to prove on demand. This dynamic-proof property is the main engineering difference from textbook Merkle trees, and the main reason adoption needs infrastructure, not just code.

</details>

## 4 · What Utreexo trades away

Accumulators don't create efficiency from nothing — they move costs to where they're cheaper to pay. The honest ledger:

- **Deleted: state & random I/O.** Node state: 12 GB → ~1 kB. No database, no cache tuning, no flush stalls. Validation speed becomes independent of RAM — a Pi validates like a workstation.
- **Added: bandwidth.** Blocks travel with proofs: about ×1.7 the bytes as utreexod ships today (worst case ×4 for per-transaction relay). Caching cuts most of it — most coins are spent soon after creation, proofs for cached coins are omitted, and the paper's simulation with a 500 MB leaf cache lands near ×1.25.
- **Added: prover burden.** Spenders (or bridge nodes on their behalf) must generate and refresh proofs. Bridges store *more* than a normal node — the asymmetry is the point, but someone must run them.
- **Added: CPU, slightly.** ~log n hashes per input is *more* raw compute than a RAM hash-map hit. On a big-RAM machine Utreexo doesn't win time — it wins footprint. The speedup is real only where state was the bottleneck.

<details>
<summary>Why the bandwidth hit is smaller than it looks — coins die young</summary>


Empirically, a large share of outputs are spent within hours or days of creation (change outputs, exchange churn, batching flows). Utreexo exploits this: nodes keep recently added leaves cached, and peers skip sending proofs for anything the receiver is known to cache. Since most spends hit young coins, most proofs shrink to nearly nothing. The published numbers span exactly this effect: proofs roughly double a block uncached, utreexod ships at about ×1.7, and the paper's simulated 500 MB leaf cache brings the whole download down to about ×1.25. The long tail — old coins waking up — pays full ~28-hash fare.

</details>

<details>
<summary>What it means for initial sync — which bottleneck it removes, in numbers</summary>


A full sync is bounded below by `max(network, disk, cpu)`. On mid-2026 mainnet (~753 GB of blocks, ~3B inputs): a 1 Gbps line needs ~1h40m for the download no matter what; hashing and parsing cost tens of minutes of CPU; signatures below `assumevalid` are skipped. On big-RAM hardware the UTXO term is small — so Utreexo barely moves the bound there, and the extra proof bytes actually *raise* the network term.

The transformation is on *constrained* hardware: with 2 GB of RAM, a stock node's UTXO term explodes into billions of disk seeks (days), while a Utreexo node's stays exactly where the big-RAM one is. Accumulators don't lower the floor — they make the floor reachable on hardware that used to sit 10× above it.

</details>

## 5 · SwiftSync: never build the database at all

Utreexo shrinks the UTXO set by making spenders carry proofs. [SwiftSync](https://gist.github.com/RubenSomsen/a61a37d14182ccd78760e477c78133cd) (Somsen, 2025) goes further for the special case of syncing: it needs **no proofs, no forest, no lookups**. You download a *hint file* — literally one bit per output ever created, saying whether that output will still be unspent when you reach the tip (~100 MB compressed for all of Bitcoin's history). Then validation becomes bookkeeping:

```text
output created, hint = 1  →  append to the final UTXO set    (write-once, never read during sync)
output created, hint = 0  →  aggregate += H(outpoint)        (never stored anywhere)
input spends a coin       →  aggregate -= H(outpoint)        (no existence check — just subtract)
───────────────────────────────────────────────────────────
end of sync:   aggregate == 0  →  set is consistent ✓
               aggregate != 0  →  bad hints or invalid spend → abort, fail closed ✗
```

The fail-closed property is why the hint file needs no trust in the safety sense: anyone can publish hints, and lying is self-defeating — wrong hints can waste your time, never corrupt your state.

The second consequence is the deeper one. Adding and subtracting from an aggregate **commutes** — order doesn't matter. So blocks no longer have to be validated one after another:

```text
today:      b₁ → b₂ → b₃ → b₄        each block needs the state the previous one left
SwiftSync:  b₃, b₁, b₄, b₂  →  Σ     any order, every core at once
```

This attacks the *serial* bottleneck of sync — the one cost no amount of bandwidth or disk can buy back. The trade: spent coins are never materialized, so their scripts can't be individually checked (nor coinbase maturity, which needs the same per-coin metadata) — SwiftSync inherits the same `assumevalid` stance a default node already takes for old signatures. It's a sync-time trick only: when it finishes you're a stock node with a stock database. A proof-of-concept measured a [5.28× sync speedup](https://delvingbitcoin.org/t/swiftsync-speeding-up-ibd-with-pre-generated-hints-poc/1562) before parallel validation is even exploited.

<details>
<summary>Why a sum can prove set-consistency — the accountant's argument</summary>


Think of the aggregate as a ledger that must balance. Every hint-0 output deposits `H(outpoint)` exactly once when it's created; every input withdraws `H(outpoint)` exactly once when it spends. If history is honest, deposits and withdrawals pair off perfectly and the balance is zero.

Now try to cheat. Spend a coin that never existed: a withdrawal with no matching deposit — non-zero. Spend the same coin twice: two withdrawals, one deposit — non-zero. Mark a doomed output as "unspent" in the hints: its deposit never happens but its withdrawal does — non-zero. Mark a surviving output as "doomed": a deposit nobody withdraws — non-zero. The hash makes collisions infeasible, so entries can't be forged to cancel accidentally — and each node **salts the hash with its own random secret**, so an adversary who authors both hints and transactions can't precompute entries engineered to cancel. One equality at the end certifies billions of set operations that were never performed individually.

Hints are also **deterministic** given the chain and target height — anyone can regenerate the file and compare, so a published hint file is reproducible, not bespoke. Fuller designs fold amounts into the aggregated data to tighten the money-supply check; the [gist](https://gist.github.com/RubenSomsen/a61a37d14182ccd78760e477c78133cd) walks the exact accounting.

</details>

<details>
<summary>SwiftSync vs Utreexo, head to head — they solve different problems</summary>


| | Utreexo | SwiftSync |
|---|---|---|
| Scope | node architecture, forever | initial sync only |
| State while running | ~1 kB of roots | hint bits + one aggregate |
| Network cost | ×1.2–1.7 blocks, ongoing | ~100 MB hints, once |
| Parallel validation | no — forest updates are ordered | yes — fully commutative |
| Trust added | none | none for safety; pairs with assumevalid |
| Needs ecosystem | bridges, proof relay, wallet support | nothing — one hint file |
| After sync | stays a kilobyte node | becomes a stock node |

They compose, too: a Utreexo node can use SwiftSync-style hints to skip proof verification for coins that die during sync — the ideas attack orthogonal costs (state vs. seriality).

</details>

## 6 · Utreexo isn't the only answer

| Approach | Deletes which cost | Pays with | Trust change | Status |
|---|---|---|---|---|
| Utreexo | UTXO state, forever (~1 kB node) | ×1.2–1.7 block bandwidth; bridge infra; dynamic proofs | none | utreexod, Floresta |
| SwiftSync | UTXO state *during sync* + parallel block validation | ~100 MB hint file (fail-closed if wrong) | pairs with assumevalid | PoC, ~5× sync |
| assumeutxo | waiting: start at a snapshot, validate history behind | obtain + verify a 12 GB snapshot; state unchanged | reviewable snapshot hash in code | shipped in Core |
| UHS (Fields) | ~half of state: store coin *hashes* only | peers attach coin data to relayed txs | none | proposal |
| TXO bitfield (Cohen) | most of state: one spentness bit per historical output | separate index to locate coin data | none | proposal |
| UTXO commitments | trust in any snapshot: miners commit the set's hash | a consensus change — the hard part | reduces trust | never activated |
| RSA / class-group accumulators | proof staleness & log-size proofs (constant-size instead) | trusted setup (RSA) or slow group math | setup ceremony (RSA) | research |
| ZeroSync | sync itself: verify a succinct proof of the whole chain | enormous proving cost; young cryptography | soundness of the proof system | research |

<details>
<summary>Why not RSA accumulators? — constant-size proofs exist, with a catch</summary>


RSA accumulators (Boneh–Bünz–Fisch, 2019) commit a set into a single group element; membership proofs are constant-size and don't go stale the way Merkle paths do, and thousands of proofs aggregate into one. The catch: you need a modulus nobody can factor — a *trusted setup ceremony*, anathema to Bitcoin's assumptions. Class groups avoid the ceremony but make every operation orders of magnitude slower. Merkle forests won in practice because they're plain SHA-2 hashing (SHA-512/256 in the shipped code): no new assumptions, fast on any CPU, auditable by anyone who can read forty lines of code.

</details>

## 7 · Applicability: pick by deployment, not by elegance

None of these designs dominates — they spend different budgets (RAM, bandwidth, latency, sync time), so the right one depends on what the machine is *for*:

| Deployment | Pain today | Best fit | Why |
|---|---|---|---|
| Desktop / workstation node | little — a few hours of sync | assumeutxo now; SwiftSync when it lands | the UTXO set already fits in RAM; Utreexo would only add bandwidth |
| Home server / Raspberry Pi | cache thrashing: days of sync, dbcache tuning | **Utreexo** (utreexod, Floresta) + SwiftSync | validation becomes RAM-independent — the death-spiral mode disappears |
| Phone / mobile wallet | light wallets verify PoW + inclusion but can't check rule-validity; Electrum-style ones also reveal addresses | **Utreexo** from a checkpoint (embedded Floresta) | ~1 kB state and forward-only validation are phone-sized; a wallet that enforces the rules itself |
| Exchange / explorer / heavy infra | none of the above — they need rich indexes anyway | stock node, big dbcache; **run bridges** as a service | address/history indexes dwarf the UTXO set |
| Miner / pool | validation latency is money | stock node, everything in RAM | proof bytes in the hot path are pure cost |
| Ephemeral nodes — CI, fleet spin-up | every fresh instance pays a full IBD | **SwiftSync** (+ assumeutxo today) | reproducible hints turn provisioning into a parallel batch job |

<details>
<summary>What a phone full node actually looks like — the Utreexo endgame</summary>


The pieces: an embeddable compact-state node (Floresta ships as a library with bindings for exactly this), a **hardcoded accumulator checkpoint** — a kilobyte of roots, reviewable in the source like `assumevalid` — and forward-only validation from that checkpoint. Wallet discovery uses compact block filters (BIP 158) checked locally, so no server ever learns your addresses.

The honest costs: proof-carrying blocks are ~×1.7 bytes on a possibly metered connection, and sustained hashing costs battery — so the realistic mode is "validate on Wi-Fi and charge, serve the wallet locally all day."

To be precise about what this improves on: today's light wallets are *not* "no validation." An SPV client verifies the header chain (proof-of-work, difficulty) and Merkle inclusion of its transactions, so a server cannot forge a payment to it — and Neutrino (BIP 157/158) already fixed the privacy leak that Electrum-style and bloom-filter wallets have. What no light client can do is check **rule-validity**: scripts, signatures, inflation, double-spends elsewhere. It follows the most-work chain unconditionally, trusting the hashrate majority to enforce the rules, and it can be lied to by omission. That specific gap — enforcing consensus rules yourself — is the one a checkpointed Utreexo node closes; privacy it merely matches.

</details>

<details>
<summary>Why the heavyweights keep fat nodes — and why that's the design working</summary>


**Miners** race the network: every millisecond spent validating a fresh block delays mining on top of it, which costs real revenue in stale and empty blocks. They keep the whole UTXO set pinned in RAM and want the block-relay hot path as thin as possible.

**Exchanges, explorers, and API providers** need address indexes, transaction history, and mempool analytics — orders of magnitude more state than the UTXO set — so shrinking it saves them approximately nothing. But they own the beefy hardware anyway, which makes them the natural **bridge operators**.

This split isn't a failure of adoption — it's the intended shape: *few fat provers, many thin verifiers*. The asymmetry between a data-center bridge and a phone verifying against 28 hashes is precisely what the accumulator was designed to create.

</details>

## 8 · Further reading

- [Utreexo: a dynamic hash-based accumulator](https://eprint.iacr.org/2019/611.pdf) — Dryja's original paper; sections 1–4 are unusually readable, and the coin-lifetime data behind proof caching lives here.
- [Utreexo in Context](https://lukechampine.com/utreexo-talk.html) — where accumulators sit among stateless-client designs.
- [Floresta docs](https://getfloresta.github.io/floresta-docs/ch00-00-introduction.html) — a working Rust compact-state node, documented as a book.
- [utreexod](https://github.com/utreexo/utreexod) — full node with Utreexo support (beta), including kilobyte-checkpoint bootstrap.
- [SwiftSync gist](https://gist.github.com/RubenSomsen/a61a37d14182ccd78760e477c78133cd) and the [Delving Bitcoin PoC thread](https://delvingbitcoin.org/t/swiftsync-speeding-up-ibd-with-pre-generated-hints-poc/1562).
- [Bitcoin Optech: Utreexo topic](https://bitcoinops.org/en/topics/utreexo/) — the maintained index of everything since the paper.

---

*Figures are mid-2026 mainnet approximations. The [interactive edition](https://nikicat.github.io/kilobyte-utxo-set/) simplifies Utreexo's position bookkeeping (noted inline there); the root arithmetic is faithful. Corrections welcome via [GitHub](https://github.com/nikicat/kilobyte-utxo-set).*