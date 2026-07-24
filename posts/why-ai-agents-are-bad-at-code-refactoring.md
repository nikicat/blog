---
title: "AI agents are bad at code refactoring"
date: 2026-07-23
author: Nikolay Bryskin
description: "Agents ace greenfield work because training data runs requirements→design→code. Refactoring runs that pipeline backwards — and maybe rewrites win."
image: /uploads/why-ai-agents-are-bad-at-code-refactoring/cover-lis3cjixcg02u0l36n8n.jpg
tags:
  - ai
  - refactoring
  - programming
  - softwareengineering
---

Give an AI agent an empty directory and a page of requirements, and it will impress you. Give the same agent an existing codebase and a one-line feature request, and there's a good chance it will leave the project slightly worse while fully satisfying the request.

<!--more-->

And "existing" no longer means old. In the agentic era a codebase can reach that state — drifted design, blurred patterns, obsolete docs — in a matter of weeks, sometimes days, often with an agent as the original author. The archaeology now has to happen on sites that are still under construction.

I want to walk through why I think this happens, and why I suspect it's not a temporary weakness.

## Two forward passes

When an agent builds a project from scratch, the pipeline is:

**requirements → design → code**

The user states what is needed. The agent converts requirements into a software design, picking patterns that fit — it has seen thousands. Then it converts the design into code, step by step.

Both arrows point the same way, and both are *forward passes* — and humanity has documented them exhaustively. Every architecture book, every pattern catalog, every tutorial, every open-source project is a record of someone moving in this direction. A model trained on public text has effectively watched this pipeline run millions of times. It's not surprising that agents are good at it. It would be surprising if they weren't.

## Refactoring runs the pipeline backwards

![Mental Gymnastics meme: "Writing new code" over gymnasts calmly standing on a mat; "Refactoring an existing codebase" over athletes doing extreme acrobatics off a burning van](/uploads/why-ai-agents-are-bad-at-code-refactoring/a6wju0m2pyp8fc2yixfx.jpg)

Now the opposite situation. The agent is dropped into an existing project. What it holds is the pipeline's *output* — the code. The inputs are exactly what's missing:

- The design has drifted; the code no longer matches any design that was ever drawn.
- The patterns are blurred by local, not-so-clean fixes and workarounds.
- The documentation and comments describe a system that no longer exists.

The engineer's task — human or AI — becomes:

1. Recover the *actual* current requirements (they've drifted from whatever the docs claim).
2. Discern the real patterns inside the noisy code.
3. For each anomaly, figure out *why* it exists: legacy? An unfinished plan? A past mistake? A requirement that moved?
4. Correct the requirements picture based on what the code investigation revealed.
5. Decide what design would be ideal for the corrected requirements.
6. Plan a path from the current code state to the target state.
7. Write the code.

Look at the direction of these steps. Steps 1–4 run backwards: from code to design, from design to requirements. Steps 5 and 7 are the familiar forward passes — the easy, well-trained part. Step 6 is neither: it's plotting a route through a live system that has to keep working at every intermediate state — changing the tires while the car is moving.

And the backward direction has a problem the forward one doesn't: it is *underdetermined*. Many different pairs of (requirements, design) could have produced the code in front of you. The forward pass loses information; running it backwards means guessing what was lost. The only thing that disambiguates the guesses is history. And while git preserves the *what* perfectly — it's all there in the repo — the *why* mostly isn't: it lived in review comments, chat threads, and the heads of people who have moved on.

## Step zero: the smell

Worse, you rarely know in advance that refactoring is needed. It is almost never a ticket. You sit down to add a feature or fix a bug, and every implementation you sketch *smells*: each one fights the current design, each needs two workarounds to fit. The decision to refactor is the recognition of that smell — noticing a mismatch between the design you have and the requirement that just arrived.

This is a background process, not a step. A human engineer runs it constantly, motivated by their own future suffering: the person who will maintain this mess is them. An agent's episode ends when the diff lands. Nothing in its loop rewards stopping to question the design; if anything, the training signal runs the other way — "sure, here's your feature" reads as helpful, "we should restructure first" reads as evasive. The agent never has to live in the house it builds.

## Refactoring is a compression task

Strip it down and refactoring is, first of all, *compression*. Given tens of thousands of lines of code, extract the internal structure. And not only the current structure — also the historical one, because step 3 (*why is this here?*) is a question about time, not about code.

Two compressions, then. The first — what the design currently is — is hard, but at least the input fits in a context window. The second is harder in principle: the rationale was never written down, or was written down and has rotted along with the docs. If the code was written by an agent, the problem inverts rather than disappears: the *why* is on record in exhausting detail — but uncompressed, too voluminous to load, and impossible to tell which of it is still true. The agent is asked to decompress a lossy archive with the dictionary thrown away.

What a good human engineer brings here is a *prior* — and note what the prior is over. Not over patterns, but over *decay*. Having watched hundreds of codebases evolve, they can look at a warped shape and reconstruct the erosion: this was once a clean separation, then a deadline happened, then a hotfix happened. Their mental library includes the degraded versions of every pattern, because they have personally watched the degradation happen.

Models are trained mostly on snapshots — final states, clean tutorials, curated open source. Their library holds the pristine versions. So faced with drifted code, a model does what it was trained to do: it matches the mess to the nearest clean shape and confidently describes the codebase as the textbook version of whatever it most resembles. But *which* clean shape, if any, this mess descended from is precisely the question that was supposed to be investigated, not assumed away. Pattern-matching the noise to a pristine archetype is guessing at the story instead of recovering it.

## What agents do instead

![Drake meme: disapproving at "Refactor the workaround", approving at "Wrap it in an abstraction layer"](/uploads/why-ai-agents-are-bad-at-code-refactoring/y2wrftm3gcxbqhqh6nxe.jpg)

Deprived of the story, agents default to greenfield style: take the existing code as ground truth, assume everything in it is intentional, and build the new thing on top. A new abstraction here, a new entity there. Nothing is ever deleted; each session adds a stratum. The result is geological: layers on layers, each written as if everything below it were load-bearing.

If you've watched an agent work on a mature project, you've seen this: it doesn't refactor the workaround — it *respects* it. Wraps it, generalizes it, builds on it. The workaround becomes architecture.

One clarification, because it causes a lot of confusion: agents are quite good at the *mechanics* of refactoring. Tell one "extract this logic into a module, keep behavior identical, update all call sites" and it will do a decent job. This fools people. Fowler's catalog — extract method, move field, rename — is the last mile of refactoring. The hard part was never executing the moves; it's deciding that moves are needed, which ones, and toward what design. Judgment, not mechanics. Agents pass the mechanics test, and it tells us nothing about the judgment.

## The economics flip

![Vince McMahon reaction meme, escalating excitement: ship a hotfix / fix it properly / refactor the codebase / rewrite from scratch](/uploads/why-ai-agents-are-bad-at-code-refactoring/xzr5i8inse89tciscjl1.jpg)

So here is my suspicion: maybe with AI it is simply cheaper to throw the code away and regenerate it. Look at what a rewrite actually involves:

1. Extract the requirements — explicit and implicit.
2. Design against them.
3. Write the code.

That's the greenfield pipeline with one pre-step attached. No smell detection, no archaeology, no step-6 migration plan — most of the seven-step backward pipeline simply disappears. Mass production killed the repair shop for exactly this reason: when manufacturing a new unit costs less than diagnosing the old one, nobody fixes anything. Code generation is heading toward free. Code *diagnosis* is not.
