# decision: define application-owned detection postprocessing and output

**status:** accepted

**roadmap milestone:** R1: perception baseline

## A. context

RT-DETR emits class scores for every query. Flattened query-by-class top-k can return one query and box under several labels, which can create duplicate tracks. Exposing Torch or Transformers outputs would also couple tracking, evaluation, and APIs to model-specific coordinates and device semantics.

## B. decision

select at most one class per query using per-query argmax. Apply the same decoding path in evaluation and runtime. Publish immutable `Detections` containing NumPy boxes, scores, class IDs, and optional track IDs. Boxes use absolute original-frame `xyxy` coordinates; label names resolve through the artifact manifest.

## C. consequences

downstream components remain independent of RT-DETR, Torch devices, and normalized model coordinates. Serialization is explicit because NumPy arrays are not JSON-native. Reported detection metrics describe the postprocessing that the application actually uses.

## D. validation or reversal

test empty and populated shapes, coordinate inversion, class ranges, and duplicate-query behavior. A detector replacement must reproduce this contract or introduce an explicitly versioned successor.
