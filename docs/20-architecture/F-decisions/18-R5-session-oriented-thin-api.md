# decision: expose a session-oriented thin API

**status:** accepted

**roadmap milestone:** R5: tray workflow MVP

## A. context

a stateless image endpoint cannot preserve tracking, inventory, or finalization state across frames. Putting model and decision logic directly in HTTP handlers would couple transport behavior to domain implementation and make local execution harder to test.

## B. decision

define stable Python-level runtime and session interfaces first, then expose them through FastAPI as a transport and validation layer. Use explicit operations to create a session, submit ordered frames or a supported video, finalize with context, return the finalized result, and delete the session. Identify sessions with UUIDs and represent requests and responses with versioned typed schemas.

## C. consequences

the API makes sequence boundaries and finalization explicit while leaving domain logic reusable outside HTTP. Clients must preserve frame order and lifecycle rules. Network serialization remains separate from NumPy and internal domain objects.

## D. validation or reversal

test HTTP behavior against the same session contracts used directly in Python. Add streaming transports or result-retrieval endpoints as adapters rather than moving domain logic into transport handlers.
