# feature package: stateful instrument inventory

> defines how tracked observations become a session inventory and a conservative finalized count.

**status:** implemented

**roadmap relationship:** R2: stateful inventory

## A. outcome

the system retains instruments observed during one session, preserves their track evidence, and produces an immutable class-level inventory when the session ends.

## B. sub-features

### B.1 INV-01: append-only observed inventory

**definition:** Records every confirmed track observed during a session even after it leaves the current frame.

**specification:**

- Key mutable entries by track identity and update first seen, last seen, observed-frame count, class, and confidence evidence.
- Reject observations without tracking identities.

**verification:** Inventory tests demonstrate accumulation after items leave view and rejection of untracked detections.

### B.2 INV-02: class and confidence evidence

**definition:** Maintains the current class estimate and its associated confidence for each tracked item.

**specification:**

- Follow the track's current class while retaining the best observed confidence for that class.
- Never combine a class label with confidence evidence belonging to another class.

**verification:** Class-change tests verify that class and confidence remain correctly associated.

### B.3 INV-03: conservative session finalization

**definition:** Converts track-level evidence into an immutable class-level count after capture.

**specification:**

- Estimate each class count as the smaller of distinct tracks and the maximum simultaneously observed count.
- Preserve representative track evidence, time range, observation count, and confidence in the finalized entry.

**verification:** Fragmentation and simultaneous-visibility tests demonstrate the counting rule and immutable result.

### B.4 INV-04: isolated session state

**definition:** Ensures inventory state cannot leak between independent sequences.

**specification:**

- Reset entries, simultaneous counts, and frame position together.
- Keep an already finalized result detached from later mutable inventory changes.

**verification:** Reset and immutable-finalization tests cover new sessions and post-finalization updates.

### B.5 INV-05: inventory evaluation

**definition:** Measures predicted session counts against physical item identities in evaluation data.

**specification:**

- Report count error without allowing errors from different classes or sessions to cancel.
- Require stable ground-truth instance identities and a shared class vocabulary across evaluated sessions.

**verification:** Inventory metric tests cover perfect counts, class errors, session aggregation, absent classes, and invalid identity data.

## C. shared constraints

- Preserve ADR `12` and requirements `FR-005`, `QR-102`, and `AC-003` through `AC-005`.
- Tray finalization uses the conservative class-count heuristic; robot inventory uses incremental resolved-item entries.
- Inventory records observations and does not perform policy evaluation.

## D. package acceptance

- observed tracks remain in inventory after leaving view and repeated frames do not create new entries for the same track.
- simultaneous items remain distinct and finalization produces deterministic immutable counts.
- reset creates empty independent state for the next sequence.
- evaluation reports class-aware and session-aware count error.

## E. non-goals

- guaranteed merging of fragmented tracks into physical identities;
- operator correction of inventory entries;
- durable inventory persistence;
- incremental robot publication, which belongs to the robot workflow package.
