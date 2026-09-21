# 07 -- against a known engine

`uv run python examples/07-against-a-known-engine/run.py`

Your system -- the memory written in the script -- against one you did not write, on identical
tasks and measures. **Prints** one paired reading: means, gap, flips. The stand-in is
`WordOverlap`, which memrank ships, so this runs offline. Swap that one class for a real engine:
`Mem0` needs Mem0 at `MEM0_HTTP_URL` (default `http://localhost:8888`) or the `mem0ai` SDK, and
`AtomicMemory` needs AtomicMemory at `ATOMICMEMORY_API_URL` (`http://localhost:3070`). Both are
in `memrank.systems`, and `memrank.catalog()` prints the rest with what each one needs. An
unreachable backend fails loudly; memrank does not fall back.
