# decision: resolve handling outcomes through ordered typed gates

**status:** accepted

**roadmap milestone:** R3: handling decision support

## A. context

low confidence, unsupported labels, missing facts, missing context, absent policy, conflicting information, and internal failures require different remediation. A single generic error loses meaning, while best-effort defaults can produce unsupported recommendations.

## B. decision

use typed immutable inputs and outputs and evaluate them in a fixed order: validate input, map the perception label, apply the confidence gate, extract instrument facts, merge supplied context, evaluate policy, then attach provenance. Preserve distinct internal outcomes for `invalid_input`, `unsupported_item`, `low_confidence`, `missing_info`, `missing_policy`, `human_review`, and `recommendation`. Operator interfaces may group every non-recommendation under `Needs review` while retaining the reason.

conflicting facts and unexpected resolution exceptions fail to review rather than selecting an arbitrary source or action.

## C. consequences

precedence is explicit and testable, and operators can see what information or governance is missing. The resolver owns more outcome semantics and must keep internal detail compatible with simpler external presentation.

## D. validation or reversal

cover every outcome and precedence edge with tests using real ontology and policy artifacts. Change the order only when approved domain authority rules justify a different result.
