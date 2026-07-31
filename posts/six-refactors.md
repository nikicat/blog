---
title: "Six refactors that caught real bugs"
date: 2026-08-01
author: Nikolay Bryskin
description: "I spent an hour removing code smells from a working scraper. Every single one turned out to be load-bearing — each refactor either exposed a live bug or made one impossible. Six before-and-after pairs."
image: /uploads/six-refactors/cover.png
tags:
  - python
  - refactoring
  - codequality
  - typing
---

I had a working scraper. A few thousand articles, an embedding model, some analysis scripts. It ran, it produced numbers, and it was riddled with the sort of smells you tell yourself you'll clean up later: a boolean flag here, a bare tuple there, a two-hundred-line `main()`.

So I cleaned them up, expecting a cosmetic hour. Instead, four of the six refactors uncovered a bug that was live in the code at that moment, and the other two made a class of bug unrepresentable. The smells weren't cosmetic. They were the places where the code was vague about what it meant, and the bugs had moved into exactly those places.

<!--more-->

Here are the six, each as a before-and-after, with the bug it turned up.

## 1. A boolean parameter is two functions in a trenchcoat

Loading the corpus could also fetch it, which seemed convenient:

```python
# bad: the flag decides whether this function touches the network
def load_articles(fetch=False):
    raw = fetch_articles() if fetch else json.loads(CACHE.read_text())
    return {u: [clean(b) for b in bodies] for u, bodies in raw.items()}
```

The bug: analysis scripts call `load_articles()` to read the corpus. When I later raised the per-author article cap, that default-`False` path stopped being enough — and one of the analysis scripts started *downloading articles* as a side effect of loading them, in parallel with a real fetch job, competing with itself for the same rate limit. I only noticed because the two jobs began starving each other.

A function named `load` had a network call inside it, gated by an argument most callers never passed.

```python
# good: one name, one job
def load_articles() -> dict[Author, list[Text]]:
    """Pure cache read. Fetching is fetch_articles()' job."""
    records = load_records()
    return {u: [clean(records[i]["body_markdown"]) for i in ids]
            for u, ids in load_index().items() if len(ids) >= MIN_ARTICLES}
```

The caller that wants both says so: `fetch_articles(); data = load_articles()`. **If a boolean parameter switches what a function fundamentally does, it's two functions, and the vaguer of the two names is hiding the dangerous one.**

## 2. Name the tuple

Three parallel lists came back from one call:

```python
# bad: what's in position 1?
def query_set():
    return names, texts, srcs

names, texts, _ = query_set()      # every caller re-remembers the order
```

And a stats helper returned seven floats in a dict, with a separate formatter that had to know all seven keys by string:

```python
# bad
return {"em_dash": dash / per_k, "bullets": bullets / per_k, ...}

def fmt(p):
    return f"em-dash {p['em_dash']:.2f}/1k, bullets {p['bullets']:.1f}/1k, ..."
```

`NamedTuple` fixes both, and the second one absorbs its formatter:

```python
# good
class QuerySet(NamedTuple):
    """The held-out articles of a run, aligned with the saved vectors."""
    names: list[Author]
    texts: list[Text]
    sources: list[Source]

class Typography(NamedTuple):
    em_dash: float          # per 1000 words
    bullets: float
    ...
    def __str__(self) -> str:
        return f"em-dash {self.em_dash:.2f}/1k, bullets {self.bullets:.1f}/1k, ..."
```

The `fmt()` function disappeared — with fields instead of string keys, formatting belongs on the type. And the payoff arrived immediately: the moment the shapes had names, the type checker started reading them, and it flagged this:

```python
class Source(NamedTuple):
    author: Author
    index: int        # ← "index" overrides tuple.index with an incompatible type
```

A field called `index` silently shadows `tuple.index()`. That's the kind of thing you find at 2am six months later. It cost one rename (`article_index`) because the tuple had a name for a checker to talk about.

## 3. Give your strings a type

Everything in this codebase is a string: usernames, article ids, URLs, raw markdown, cleaned prose, forty-word chunks. The signatures said `str` for all of them.

```python
# bad: six different meanings, one type
def clean(md: str) -> str: ...
def load_articles() -> dict[str, list[str]]: ...
```

Python's type aliases are free and they carry the domain:

```python
# good
Author = str        # dev.to username
ArticleId = str
Url = str
Markdown = str      # article body exactly as published
Text = str          # prose after clean()
Chunk = Text        # one CHUNK_WORDS-long slice
Episode = list[Chunk]

def clean(md: Markdown) -> Text: ...
def load_articles() -> dict[Author, list[Text]]: ...
```

These are `str` at runtime — a checker won't stop you passing one for another. That isn't the point. The point is the signature now states a transformation, and the distinction between `Markdown` and `Text` is precisely the one that had already cost me an afternoon: I'd cached `Text` where I needed `Markdown`, discovered later that cleaning had deleted content I wanted back, and had to re-download 1,900 articles to recover it. The types don't enforce that. They *name* it, which is what stops the next person from making it.

> [!NOTE]
> Aliases pay for themselves fastest in code where one primitive type means half a dozen things — scrapers, ETL, anything with ids. If every parameter in a module is `str: str -> str`, the type annotations are decoration; naming the strings turns them back into documentation.

## 4. Split when the function changes subject

`main()` fetched, loaded, split, embedded, saved, and scored. Ninety lines, six subjects, one scope where every intermediate variable stayed live to the end.

```python
# bad (abridged): six jobs, one function
def main():
    rng = random.Random(0)
    data = fetch_and_load()
    ...
    for i, u in enumerate(names):          # embedding, inline
        enroll_vecs.append(embed_episode(model, tok, rng.sample(pool, ...)))
        ...
    np.savez(EMBEDDINGS, E=E, Q=Q, y=y, ...)
    def report(name, sims):                # scoring, nested
        ...
```

```python
# good: the steps have names, and each is separately testable
def main() -> None:
    fetch_articles()
    data = load_articles()
    names = sorted(data)[:N_AUTHORS]
    splits = split_authors(data, names)
    emb = embed_corpus(splits, names)
    save_embeddings(emb, names)
    METRICS.write_text(json.dumps(evaluate(emb, splits, names), indent=1))
```

The same treatment turned a 60-line `describe()` into `group_members`, `print_agreement`, `print_mixed_clusters`, `print_pure_clusters` and `print_author_spread`. Longest function in the repo went from ~90 lines to 36, across 67 functions.

The concrete payoff came an hour later. The embedding phase takes forty minutes and had no checkpointing, so any interruption threw all of it away. Adding checkpoints meant touching `embed_corpus` and nothing else — a resume-from-disk branch and a `save_checkpoint` call. Inside the old `main()`, that same change would have been surgery on a function that also owned the fetch, the scoring and the file writes. **Long functions don't just read badly; they make every later change bigger than it should be.**

## 5. Record facts instead of recomputing them

This one is my favourite, because it looked clever.

Downstream analysis needed to know which articles had been used as queries. The embedding step had shuffled them with a seeded RNG, so I reconstructed the shuffle by replaying it:

```python
# bad: re-derive the state by re-running the randomness
rng = random.Random(0)              # same seed as the embedding run
pairs = list(enumerate(data[u]))
rng.shuffle(pairs)                  # relies on: same-length list, same permutation
per = author_chunks([t for _, t in pairs])
```

It worked. It also meant that adding an author, changing the split, or reordering a loop would silently pair every article with the wrong label — and the analysis would still run and still print plausible numbers.

```python
# good: the producer writes down what it did
class Query(NamedTuple):
    article_index: int
    chunks: Episode

np.savez(EMBEDDINGS, Q=..., 
         src_user=np.array([s.author for s in sources]),
         src_idx=np.array([s.article_index for s in sources]))
```

Two extra arrays replaced a re-derivation that depended on iteration order. And once provenance was recorded rather than replayed, a second bug fell out: the enrollment sample was drawn from one shared RNG, so *which* chunks an author got depended on how many authors had been processed before them. A resumed run would have produced different vectors than an uninterrupted one — an irreproducibility I'd never have noticed, since both runs print equally reasonable numbers. Seeding per author (`random.Random(f"{SEED}:{author}")`) made each author independent of the others' order.

## 6. One source of truth per fact

The article bodies lived in two files: a records cache keyed by id, and a per-author cache of the same bodies. Which existed only because a *third* function needed to map a query back to its record — and did it by matching on the full body text:

```python
# bad: two stores of the same bytes, joined by comparing article bodies
by_body = {r["body_markdown"]: r for r in records.values()}
return [by_body.get(raw[s.author][s.index]) for s in sources]
```

Once the per-author cache stored ids instead of bodies, the join became a lookup:

```python
# good
def records_for(sources: list[Source]) -> list[Record | None]:
    index, records = load_index(), load_records()
    return [records.get(index[s.author][s.article_index]) for s in sources]
```

That deleted 45MB of duplicated bodies, a 180MB dictionary built on every call, and a whole category of "the two caches disagree" bugs. The same principle killed a hardcoded metrics table inside the report generator — the numbers now come from the JSON the scoring run writes, so the report cannot quote a figure the code didn't just produce.

## The pattern

Six smells, six bugs, and the correlation isn't a coincidence. Each smell marked a place where the code was *vague about what it meant*: a flag that blurred loading and fetching, a tuple that blurred three lists, a `str` that blurred markdown and prose, a function that blurred six jobs, a seed that stood in for a fact, two files that both claimed to hold the same bytes. Ambiguity is where bugs live, because ambiguity is precisely what a reviewer's eye slides over.

If you want a Monday-morning version, in the order I'd do it again:

1. Grep for boolean parameters. Each one is probably two functions.
2. Name any tuple you return with more than two elements — then read what your type checker says once it can see the shape.
3. If a module's signatures are all `str -> str`, alias the strings after the things they mean.
4. Find the longest function and cut it where the subject changes.
5. Search for state you re-derive from a seed, a sort order, or an iteration order — record it instead.
6. Find two files that store the same fact, and delete one.

None of that is new advice. What surprised me was the hit rate: I went in expecting to make the code prettier, and came out having fixed a live rate-limit collision, a shadowed method, a reproducibility hole, and a duplicate-cache join. The cleanup *was* the debugging.
