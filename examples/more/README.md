# more

Material that does not belong to the numbered walk, kept because it still works and is still
the answer to a real question. Everything here either drives memrank's **previous** run loop --
the one the command line and the cloud call, with its older vocabulary of *target* for a named
system and *benchmark* for the class a named evaluation is built from -- or needs something the
numbered folders deliberately avoid: a live engine, or Docker. The seven words the numbered
folders teach need none of it.

| | What it is | Needs |
| --- | --- | --- |
| [`explore-benchmark.py`](explore-benchmark.py) | Load one evaluation's source benchmark and look at it. No runs, nothing written. | nothing |
| [`run-existing-target.py`](run-existing-target.py) | Drive a catalog target through the previous run loop, resolving the ref exactly as `memrank submit` does. | nothing |
| [`custom-target/`](custom-target/README.md) | Register a system memrank does not ship, so `memrank submit` drives it like any other target. | nothing |
| [`native-adapter/`](native-adapter/README.md) | A translator: the contract over HTTP, in any language, without touching memrank. | nothing |
| [`3-line-example.py`](3-line-example.py) | The smallest run against a real engine: one adapter, one benchmark, smoke slice. | a live engine |
| [`supermemory-image/`](supermemory-image/README.md) | Build the engine image the `supermemory` target names. No registry serves it, so the recipe ships instead. | Docker |
| `compare-am-mem0.py` | Kept as a record of the earlier comparison script. It does not run: it imports `memrank.adapters.baseline`, which no longer exists. | does not run |

`3-line-example.py` reads `ATOMICMEMORY_API_URL` (default `http://localhost:3070`),
`MEM0_HTTP_URL` (`http://localhost:8888`) or `HINDSIGHT_API_URL` (`http://localhost:7000`)
depending on the adapter it is given. An unreachable backend fails with a connection error;
memrank does not silently fall back.
