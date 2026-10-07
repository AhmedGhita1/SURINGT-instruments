# decision: finalize tray inventory and decisions exactly once

**status:** accepted

**roadmap milestone:** R5: tray workflow MVP

## A. context

tracking identities and counts may change while tray frames continue arriving. Live handling decisions could flicker, duplicate actions, or appear authoritative before the operator has supplied the required context.

## B. decision

separate tray capture from decision finalization. While open, the session accepts ordered observations and maintains draft inventory. Finalization validates context, freezes inventory, resolves one handling outcome per published class-level entry, and stores one immutable result. After successful finalization, reject further frame or context mutation.

## C. consequences

tray results come from a stable evidence set and concurrent frame/finalize behavior is unambiguous. Class-level summaries collapse fragmented tracks but cannot represent different context for two physical items of the same class. Correction requires a new session unless a separately designed reopen workflow is introduced.

## D. validation or reversal

test empty, uncertain, invalid-context, successful, repeated, and concurrent finalization paths. Move to per-instance or revisable results only after physical identity and revision semantics are explicitly supported.
