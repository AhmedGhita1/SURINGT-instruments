# decision: begin with a pretrained closed-set RT-DETR detector

**status:** accepted

**roadmap milestone:** R1: perception baseline

## A. context

the first product increment needs measurable localization and classification for a known instrument taxonomy. Training from scratch requires substantially more data, while retrieval-based recognition introduces embedding, gallery, unknown-rejection, and multi-model evaluation problems before the base perception system is proven.

## B. decision

fine-tune the pretrained `PekingU/rtdetr_r18vd_coco_o365` model with a new classifier for the supported SURGINT classes. Keep the detector closed-set for the first validated system. Treat retrieval-based category expansion as a separate feasibility decision.

## C. consequences

transfer learning provides a practical baseline and one artifact produces boxes and class scores. Adding or reordering classes requires a new trained artifact. The system cannot claim open-set recognition. RT-DETR was a pragmatic starting choice, not the result of a complete detector benchmark.

## D. validation or reversal

compare class-level accuracy, latency, memory use, and failure behavior on representative data. Revisit the detector when another architecture materially improves the required deployment profile, or revisit closed-set recognition after retrieval feasibility is demonstrated.
