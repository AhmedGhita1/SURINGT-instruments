# decision: separate model selection from training recovery

**status:** accepted

**roadmap milestone:** R1: perception baseline

## A. context

a deployable model and a resumable training checkpoint serve different purposes. Shipping optimizer and scheduler state wastes space, while using only the best model for recovery can lose the latest training progress.

## B. decision

write two checkpoint roles. `best` contains the model and deployable manifest selected by validation evidence. `latest` additionally contains epoch, optimizer, scheduler, and best-score state required to resume the run. Select `best` by validation mAP rather than training loss.

## C. consequences

deployment artifacts remain smaller and do not expose irrelevant optimizer state. Training recovery remains explicit. Model selection and crash recovery may point to different epochs and must not be treated as interchangeable.

## D. validation or reversal

test restoration from `latest` and independent loading of `best`. Revisit only if an artifact system can preserve both roles without obscuring their different semantics.
