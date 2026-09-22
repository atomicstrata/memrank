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
"""An engine memrank does not ship, registered into its catalog from outside the tree.

Importing this module registers `recency` as an adapter. Point memrank at it and a
descriptor naming `adapter: recency` resolves like any built-in -- `memrank targets ls`,
`memrank submit recency demo`, a receipt, a row in a sweep:

    export PYTHONPATH=$PWD/examples/more/custom-target
    memrank config set adapters.plugins recency_plugin
    memrank config set targets.path $PWD/examples/more/custom-target/targets

See README.md for what that buys over handing `memrank.run` an instance directly.

THE ENGINE IS DELIBERATELY THE DUMBEST THING THAT STILL RETRIEVES: it returns the k most
recently ingested documents and never looks at the query. That is a real baseline -- memory
systems are measured against recency precisely because it is hard to beat on conversational
data -- and it makes the point that the harness scores what an engine DOES. Nothing here
declares an intent to be relevant; the score is what it is.
"""

from datetime import datetime

from memrank import Document, Memory, Recall
from memrank.instrumentation import TokenCollector
from memrank.plugins import AdapterRegistration, register_adapter
from memrank.secrets.requirements import EngineRequirements


class Recency(Memory):
    """Return the most recently ingested documents, newest first.

    The whole engine contract is the six methods below. `transport = "in-process"` is what
    says memrank drives this in its own process -- there is nothing to launch, nothing
    listening on a port, and no image to pin.
    """

    name = "recency"
    version = "0.1.0"
    #: The engine and the adapter are the same object here, so they share a version. A wrapper
    #: around someone else's engine reports THAT engine's version, which is what a receipt
    #: needs in order to say what ran.
    engine_version = "0.1.0"
    transport = "in-process"

    def __init__(self) -> None:
        self._store: list[Document] = []
        self._tokens = TokenCollector()

    def prepare(self, isolation_unit: str) -> None:
        """Start this unit from empty.

        THE MOST CONSEQUENTIAL METHOD. Leaked state does not raise -- it inflates every score
        after the first, because documents from an earlier conversation are still there to be
        retrieved. An engine that cannot isolate cannot be measured.
        """
        self._store = []

    def ingest(self, documents: list[Document]) -> None:
        # Untimed on purpose: memrank times this call at its own boundary, so an engine
        # neither has to report latency nor can flatter it.
        self._store.extend(documents)

    def retrieve(self, query: str, k: int, user_id: str,
                 query_timestamp: datetime | str | None = None) -> Recall:
        """The k newest documents, ignoring the query entirely.

        Returned in ranked order, newest first, because `recall@k` reads the order. An engine
        that returns its matches unordered scores worse than one that ranks badly.
        """
        newest = list(reversed(self._store))[:k]
        return Recall(documents=newest,
                      declared={"strategy": "recency", "considered": len(self._store)})

    def cleanup(self) -> None:
        self._store = []

    def token_metrics(self) -> dict[str, float | None]:
        """No tokens are spent: nothing is embedded and no model is called.

        The collector reports `None` rather than `0.0`, and the difference matters -- zero is a
        measurement, absent is the absence of one, and a leaderboard that averages them together
        is reporting a number nobody produced.
        """
        return self._tokens.as_metrics()


register_adapter(AdapterRegistration.in_process(
    Recency,
    # What launching this engine costs in credentials. Nothing: no provider is called, so there
    # is no key to preflight. Saying so is the point -- an engine with no declared requirements
    # cannot be preflighted at all, and the run would fail at launch instead of at submission.
    requirements=EngineRequirements("recency"),
    # What the receipt should say about the artifact that ran. `type: application` is the
    # in-process shape -- there is no container to digest and no repository memrank built this
    # from, so it claims neither.
    provenance={
        "prefix": None,
        "type": "application",
        "image_name": None,
        "manufacturer": "example",
        "supplier": "example",
        "source_repo": None,
        "ancestors": [],
        "patches": [],
        "properties": {"memrank:distribution": "in-process"},
    },
))
