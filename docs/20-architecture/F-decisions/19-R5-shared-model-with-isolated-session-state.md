# decision: share immutable inference objects and isolate session state

**status:** accepted

**roadmap milestone:** R5: tray workflow MVP

## A. context

loading one model per session wastes accelerator memory, while sharing trackers and inventory would leak identity across unrelated videos. Distributed state would support recovery and multiple workers but requires serialization, routing, expiry, and operational infrastructure not needed for the controlled demonstrator.

## B. decision

run one API process with an in-memory, bounded UUID session registry. Share the loaded detector and transform. Give each session its own pipeline tracker, inventory, decision session, and lock. Serialize access to the shared model with one process-wide inference lock and run one server worker.

## C. consequences

session identity remains isolated without duplicating model weights, and concurrency behavior is straightforward to test. Inference throughput is serialized, restart loses sessions, abandoned sessions retain capacity until deletion, and multiple workers are invalid without sticky routing or external state.

## D. validation or reversal

test state isolation, frame/finalize races, session limits, deletion, and load failure. Introduce queues, dynamic batching, replicas, expiry, or durable storage only after measured concurrency, latency, or recovery requirements justify them.
