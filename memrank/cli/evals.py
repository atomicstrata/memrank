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
"""``memrank evals`` -- the catalog of goals.

An *eval* is a task definition: dataset, metrics, slices, tiers, judge requirements. A *run* is
one execution of one against a target. The industry is sloppy about this ("my eval finished"
means their run); the tool's nouns stay crisp, which is why the catalog is `evals` and not
`benchmarks` -- and why `evals ls` reads beside `targets ls` rather than as a third grammar.

``show`` renders DECLARED metadata (each benchmark's ``EvalInfo`` plus its class attributes):
constructing the benchmark is I/O-free by contract, and only ``load()`` may ever download --
the catalog answers "what would I be running?" without spending a byte of dataset traffic.
"""
from __future__ import annotations

import json

import typer

from memrank.application.catalogs import get_eval
from memrank.benchmarks.refs import list_eval_refs
from memrank.term import detail, style, table

evals_app = typer.Typer(help="Inspect the catalog of evaluation goals.")


@evals_app.command("ls")
def cli_evals_ls() -> None:
    """Print every runnable evaluation (one per line).

    Every VARIANT, not every benchmark: `beam:100k-smoke` and `beam:1m` are different
    evaluations with different question counts and non-comparable scores, so listing them as one
    line called "beam" answered a question nobody asked.

    A pipe still gets one bare ref per line -- the refs ARE the answer here, and a caller feeding
    them into a loop should not have to strip a heading off the front. A terminal gets the same
    refs in a box, where a heading costs nothing.
    """
    refs = list_eval_refs()
    if not style.supports_boxes():
        for ref in refs:
            style.out(ref)
        return
    table.emit((table.Column("REF", styler=style.accent),), [[ref] for ref in refs],
               title="Evals")


@evals_app.command("show")
def cli_evals_show(
    ref: str = typer.Argument(..., help="eval ref (from `memrank evals ls`)"),
    json_out: bool = typer.Option(False, "--json", help="machine-readable JSON output"),
) -> None:
    """Show one eval's units, slices, tiers, metrics, and judge requirements."""
    try:
        described = get_eval(ref)
    except ValueError as exc:
        style.error(str(exc))
        raise typer.Exit(1) from exc
    if json_out:
        style.out(json.dumps(described, indent=2, sort_keys=True))
        return
    _render(described)



def _render(info: dict) -> None:
    """The human view: a titled panel of label/value pairs.

    The labels used to be padded by hand in every f-string, which meant the block realigned only
    if someone remembered to retype every line; `detail` sizes them from the labels themselves.
    """
    fields = [
        ("unit", f"{info['unit']} -- {info['units_declared']}"),
        ("slices", ", ".join([*info["slices"], "full"])),
    ]
    if info["tiers"]:
        fields.append(("tiers", f"{', '.join(info['tiers'])} (default {info['tiers'][0]})"))
    fields.append(("metric", f"{info['quality_label']} -- {info['quality_description']}"))
    # A fact about the eval, not an instruction to the reader: judging is DERIVED from this, so a
    # judge-required eval judges without being asked and there is no flag left to name here. What
    # is worth saying is what `--no-judge` costs you, since that is the only remaining choice.
    if info["judge"] == "required":
        fields.append(("judge", f"{style.caution('required')} -- judged by default; `--no-judge` "
                                "measures latency and cost with no quality score"))
    else:
        fields.append(("judge", "optional -- scores itself; `--judge` adds LLM-judged answer "
                                "correctness beside it"))
    # Stated, not gated. `--ack-egress` used to be required here and is retired: `--judge` already
    # names the provider, so a second flag confirming it was ceremony the browser never asked for.
    if info["is_synthetic"]:
        fields.append(("egress", "synthetic data -- judging sends nothing real to the provider"))
    else:
        fields.append(("egress", "--judge sends this benchmark's content to the judge provider"))
    if info["requires_graph"]:
        fields.append(("graph", style.caution("requires a graph-capable target")))
    title = (f"{info.get('ref', info['name'])}  "
             f"({info['dataset_version']}, task v{info['task_version']})")
    detail.emit(detail.panel(title, fields))
