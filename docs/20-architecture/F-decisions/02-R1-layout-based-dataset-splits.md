# decision: split synthetic data by scene layout

**status:** accepted

**roadmap milestone:** R1: perception baseline

## A. context

synthetic frames generated from one settled layout show the same instruments in the same positions while camera pose and lighting vary. A random frame split would place views of the same arrangement in both training and validation and inflate measured generalization.

## B. decision

assign complete scene layouts to exactly one of training, validation, or evaluation. No layout may contribute frames to more than one split.

## C. consequences

validation measures performance on unseen arrangements rather than memorized geometry. The number of independent layouts, not the number of rendered frames, limits confidence in the estimate. Split membership becomes part of the dataset version.

## D. validation or reversal

verify split construction by layout identity. Preserve group-based splitting for future real sequences whenever several frames share one physical scene or capture session.
