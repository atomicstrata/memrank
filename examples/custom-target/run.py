# Copyright 2026 AtomicStrata
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied. See the License for the specific language governing
# permissions and limitations under the License.
"""Run the `recency` engine from a plain script -- no CLI, no config, no setup.

Run from the repo root:

    python examples/custom-target/run.py

This is the same engine `memrank submit recency demo` drives, reached the other way: an
instance handed straight to `memrank.run`, which needs no `adapters.plugins`, no
`targets.path` and no descriptor. It writes nothing and prints nothing but what is below.

WHAT IT DOES NOT PRODUCE, and why that is correct: `result.target` is None. No ref was
given, so memrank declines to invent one -- and without an address there is no variant
digest and no provenance for the build. A number from here is a sanity check, not evidence.
Registering the same engine (see README.md) is what earns the ref, and the receipt with it.
"""

import memrank

from recency_plugin import RecencyAdapter  # isort: skip  -- same directory; see README.md


def main() -> None:
    result = memrank.run(RecencyAdapter(), "demo", repeats=1)

    print(f"composite: {result.composite:.3f}  ({result.adapter} × {result.benchmark})")
    for row in result.per_query:
        print(f"  {row['query_id']}: {'HIT ' if row['hit'] else 'MISS'} "
              f"matched={row['matched_doc_id'] or '-'}")
    print("retrieve p50:", result.latency_metrics["retrieve_p50_ms"], "ms")
    print("target ref:  ", repr(result.target),
          "<- None by design: no ref was given, so none is invented")
    print()
    print("The same engine through the CLI, which does have a ref -- see README.md:")
    print("    memrank submit recency demo --on local")


if __name__ == "__main__":
    main()
