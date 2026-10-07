# decision: use an explicit PyTorch fine-tuning loop

**status:** accepted

**roadmap milestone:** R1: perception baseline

## A. context

fine-tuning requires separate learning rates for pretrained and new parameters, warmup, gradient clipping, validation mAP, checkpoint selection, and reproducible resume state. General training frameworks provide these features but also own lifecycle behavior that is central to understanding this system.

small synthetic batches also produced measured divergence between training and evaluation when BatchNorm running statistics were updated.

## B. decision

use a small explicit PyTorch loop. Apply a lower learning rate to pretrained features, a higher rate to the new head, linear warmup followed by cosine decay, and gradient clipping. Freeze BatchNorm running statistics while allowing trainable scale and bias parameters to update.

## C. consequences

optimization behavior remains visible and testable. The project owns resume wiring, precision features, distributed training, and framework edge cases. Batch size becomes primarily a throughput choice rather than a source of normalization drift.

## D. validation or reversal

verify train and evaluation parity on an overfit subset and track validation mAP across runs. Adopt a higher-level framework only when required capabilities exceed the clarity and maintainability of the local loop.
