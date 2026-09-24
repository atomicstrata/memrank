# Contributing and getting help

To use Memrank in your own work, start with [installation](install.md) and the
[task guides](README.md). This page is for feedback and changes to Memrank itself.

## Get help

Use the [GitHub issue tracker](https://github.com/atomicstrata/memrank/issues) for bugs,
methodology questions and disagreements. Include the Memrank and Python versions, the system
and evaluation you used, a minimal reproduction, the result you expected and the actual error
or behavior. Remove keys and private task content before posting. For other questions, contact
hello@atomicstrata.ai.

Feedback about a comparison is useful even without a code change: describe the question you were
trying to answer, what you measured and which part of the result was hard to interpret.

## Work on the project

[Local development](local-development.md) covers the environment, commands and checks. Use that
checkout setup before running the [examples](../examples/README.md) or tests.

| Change | Guide |
|---|---|
| Add a memory integration | [Adding a system](systems.md) and the [system contract](system-contract.md) |
| Add tasks or a dataset loader | [Adding an evaluation](evaluations.md) |
| Add a measurement rule | [Measures](measures.md) |
| Change documentation | [Documentation index](README.md) and [documentation checks](local-development.md#tests-and-checks) |
| Add tests | [Test tree](../tests/README.md) |

You can pass a system or evaluation from your own project without contributing it to the package.
A contribution makes it available to other users. Keep changes scoped, include the checks you ran,
and explain any effect on measurement or reproducibility. A scoring change requires a matching
update to [methodology](methodology.md).

Memrank's code is [Apache-2.0](../LICENSE). Preserve dataset notices and attribution when changing
bundled material. The [vendor-neutral charter](SPEC.md#7-governance----the-vendor-neutral-charter)
states the project's governance commitments.
