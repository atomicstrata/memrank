---
status: active
last_reviewed: 2026-09-02
---

# Engine images: what you can obtain

> **Not core.** This page is about the targets [the command line](command-line.md) knows by
> name in its catalog, each of which is a container. A system you pass to an evaluation from
> Python -- the interface [the README](../../README.md) describes -- needs none of it.

A target names an engine, and an engine is a container. This page answers the question that decides
whether a published number is evidence to you or a claim about us: **can you get that container,
and if not, what do you run instead?**

It is stated per target because the answer differs per target, and two of the four are not "yes".

| Target | Image | Can you obtain it | What you run |
|---|---|---|---|
| `hindsight`, `hindsight:matched` | `ghcr.io/vectorize-io/hindsight:0.6.2` | **Yes** -- the vendor's own published image, anonymous pull | the same bytes we measured |
| `atomicmemory` | `ghcr.io/atomicstrata/atomicmemory-core:latest` | **Yes** -- public package, anonymous pull | the same bytes we measured |
| `supermemory` | built from a recipe; no registry serves it | **You build it** -- [`examples/more/supermemory-image/`](../../examples/more/supermemory-image/README.md) | the same recipe, your own build |
| `mem0` | a patched fork, built privately | **No** | mem0's own server, run by you |

The control arms -- `no-context`, `fixed-context`, `full-context` -- and the in-process memory
floors `tfidf`, `bm25` and `word-overlap` carry no image and no credential. They run in-process on a fresh machine with nothing
installed, which is why every comparison here can be reproduced at least in part by anyone.

Both anonymous pulls in the table were re-checked on 2026-09-02.

## hindsight

The vendor's own published build, pulled by public reference and unmodified. Measuring what the
vendor ships is what makes a neutral benchmark neutral, and it means a hindsight result is fully
reproducible: the manifest, the compose graph and the image are all obtainable, and the image is
pinned to a released version rather than to `latest`.

## atomicmemory

Our engine, published to `ghcr.io` as a public package and named by its public reference like any
other vendor's. Whose engine it is does not change how a target says what it runs, and it does not
change what you can pull: the anonymous pull succeeds with no credential.

The engine's *source* is not public. The image is, which is what reproducing a run requires.

## mem0

**The `mem0` target runs a private fork, and you cannot obtain its image.** This is the one place
where the catalog's shape and its reproducibility diverge, so it is stated flatly rather than
implied.

The image is built from a fork of `mem0ai/mem0` at upstream `v2.0.1` carrying **ten unofficial
patches**. That lineage is not hidden: every receipt records it as CycloneDX pedigree -- the
upstream ancestor `pkg:github/mem0ai/mem0@v2.0.1`, the patch count, and the image digest that ran
-- so a reader can see what the number was produced by even though the fork itself is not
published.

What the patches do, from what this repository can establish: they add a **native Voyage embedder**
that upstream has no registry entry for, **pgvector dimension handling** so an embedder swap does
not corrupt the store, and **extraction fallbacks** that change what is retained when fact
extraction returns nothing. Those three are load-bearing for the configurations the fork exists to
serve. The itemised list of all ten lives in the fork's own repository and is not derivable from
this one; this page will not guess at the remainder.

The target's manifest says it is "mem0 as mem0 ships and evaluates it" -- transcribed components,
the vendor's own retrieval depth. That is true of the *configuration* and not of the *binary*, and
a `mem0` row should be read with that qualifier attached.

**To benchmark mem0 yourself, run mem0 yourself.** memrank's mem0 adapter speaks to any mem0 OSS
server over HTTP:

```bash
# your own mem0 server, from mem0's published instructions
export MEM0_HTTP_URL=http://localhost:8888
```

Then either drive the system directly (see
[`examples/02-your-own-system/`](../../examples/02-your-own-system/README.md) for the shape) or write a target manifest of your own and point `targets.path` at it, exactly as
[`examples/more/custom-target/`](../../examples/more/custom-target/README.md) does. What you will be measuring
is upstream mem0, which is not the same system as our fork -- and that difference is the honest
reason this page exists rather than a caveat at the bottom of a leaderboard.

Publishing the fork is a decision about the fork, not a documentation change, and it has not been
taken.

## supermemory

**The image is not published; the recipe is.** supermemory has no published server image and no
plain open-source server -- the open repository is Cloudflare Workers plus the hosted SaaS. The
only self-hostable artifact that speaks the adapter's API is the prebuilt `supermemory local`
binary, and that binary is **closed-source**. We may not hand it on, so the container we built is
not distributed.

What ships instead is the build: [`examples/more/supermemory-image/`](../../examples/more/supermemory-image/README.md)
is the Dockerfile our own image was built from. It fetches the binary at *your* build time from the
vendor's own public installer, so nothing is redistributed and what lands on your machine comes
from supermemory.

Two limits, stated because they bound what "the same container" means:

- **The version is pinned to `0.0.3`.** 0.0.6 ships a bundle missing `@rivetkit/rivetkit-wasm`
  whose document-processing workflow never finalises, so ingests hang rather than fail. The pin is
  a working-version pin, not a preference.
- **The installer is mutable.** The vendor serves it from an unversioned URL with no published
  digest, so two builds of `0.0.3` on two days are not guaranteed to be the same bytes. Pin the
  image you build by digest and record it; `0.0.3` alone does not identify a build. This is a real
  ceiling on reproducing a supermemory number and it is not one we can raise from here.

A previous version of the `supermemory` compose file claimed the opposite of all this -- that
nothing about the image had to stay private because it was "their open source, built by us". That
was wrong, and correcting it is what produced this page.

## What the published package ships

The published package ships the manifest and compose graph for every target whose engine an
outsider can actually obtain. A target whose image resolves only inside our own infrastructure
would name a host that resolves for nobody, which is worse than not offering it -- so `mem0` and
`supermemory` are described here rather than shipped as runnable refs, and the sections above say
what to run in their place.

The adapters for both are public, and so is everything the run loop does with them. What is
withheld is an address, not a capability.
