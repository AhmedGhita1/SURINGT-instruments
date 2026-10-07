# decision: use append-only inventory with conservative tray counting

**status:** accepted

**roadmap milestone:** R2: stateful inventory

## A. context

the product needs an inventory of items observed during a run, not only items visible in the current frame. For tray capture, a camera leaving an item does not mean the item left the tray. Counting distinct tracks directly also overcounts when one physical item is fragmented into several identities.

## B. decision

retain an item after it has been observed and do not remove it because it leaves the camera view. Add a resolved physical item to inventory once. For finalized tray counts, estimate each class as the smaller of its distinct-track count and maximum simultaneous observed count.

## C. consequences

inventory answers "what was observed during this run" rather than "what is visible now." The tray heuristic resists sequential fragmentation without another learned model, but it can undercount items that never appear simultaneously and cannot repair every identity error. Robot inventory uses incremental resolved-item additions rather than the tray count heuristic.

## D. validation or reversal

evaluate count error against physical item identities and report duplicate and unresolved rates. Replace the heuristic when tracklet merging, appearance evidence, or operator confirmation provides measurably better counts.
