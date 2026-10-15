# product principles

> defines the stable product and system-design constraints used to resolve ambiguity, evaluate proposals, and prevent scope or safety drift.

## A. evidence-supported claims

every capability and reliability claim must be supported by documented evaluation evidence. Unsupported conditions, weak performance, and known limitations must remain explicit.

## B. explicit human authority and uncertainty handling

the system provides decision support without replacing accountable human judgment. Ambiguous, unsupported, low-confidence, or incomplete cases must transition to an explicit review state rather than produce an authoritative recommendation.

## C. separation of concerns

distinct concerns must remain clearly bounded, with explicit relationships between them. Each concern must be understandable, evaluable, and changeable without silently redefining another.

## D. verification-gated scope expansion

new capabilities, supported conditions, and product claims must define measurable acceptance evidence. Known data, evaluation, and failure-mode gaps take priority over unsupported scope expansion.

## E. minimal sufficient architecture

introduce components, abstractions, and infrastructure only when required by a demonstrated product, quality, or operational constraint. Prefer the simplest design that preserves correctness, traceability, and maintainability.
