# decision: separate offline development from runtime execution

**status:** accepted

**roadmap milestone:** R1: perception baseline

## A. context

training and evaluation are batch-oriented, throughput-focused, and depend on datasets and metric tooling. Runtime inference is latency-focused, stateful across frames, and must remain deployable without the training environment.

## B. decision

separate dataset, training, and evaluation code from runtime tracking, inventory, and serving code. Keep model inference contracts shared. The versioned model artifact is the supported bridge from offline development to runtime execution.

## C. consequences

serving installations do not require dataset tooling, training frameworks, or experiment tracking. Runtime behavior cannot depend on a training configuration or workspace path. Shared model code must remain compatible with both environments.

## D. validation or reversal

verify that the serving package and container load a promoted artifact and execute inference without offline dependencies. Merge layers only if the separation creates more coupling than it removes.
