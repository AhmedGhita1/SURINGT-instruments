# UC-002: capture an instrument tray

**User:** Demonstration operator or evaluator.

**Situation:** The user has a tray available through a live camera or recorded video and wants the system to observe its contents.

**Outcome:** A session contains tracked observations suitable for inventory finalization.

## A. main flow

1. The user starts a live camera or opens a supported video.
2. The system creates a session and shows the source with detection overlays.
3. The user moves slowly across the full tray while the system updates the visible-item list.
4. The user finishes the scan when coverage is sufficient.

## B. exceptions

- Camera permission, video decoding, or session creation fails: explain the problem and allow retry.
- No item remains tracked long enough: allow finalization but state that the inventory is empty.
- The user discards the session: stop capture and remove its state.
