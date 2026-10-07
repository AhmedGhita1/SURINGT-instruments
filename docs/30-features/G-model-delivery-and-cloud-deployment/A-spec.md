# feature package: model delivery and cloud deployment

> defines how a validated model and serving application become a reproducible containerized research deployment.

**status:** implemented

**roadmap relationship:** R5 serving foundation; does not complete R6 robot-edge validation

## A. outcome

engineers can build, test, publish, and run a versioned container containing the serving application and one integrity-checked model artifact.

## B. sub-features

### B.1 DEL-01: separated dependency profiles

**definition:** Keeps serving dependencies smaller than the combined training and development environment.

**specification:**

- Declare core, serving, training, and development dependency groups explicitly.
- Ensure runtime imports do not depend on undeclared training packages.

**verification:** Packaging tests compare source imports with declared dependencies across supported Python versions.

### B.2 DEL-02: candidate-model registration

**definition:** Optionally logs training runs and validated candidate artifacts to W&B without making runtime depend on W&B.

**specification:**

- Validate a candidate checkpoint before upload and preserve the selected project, entity, artifact name, and alias.
- Keep local training and serving functional when W&B is not configured.

**verification:** W&B and registration tests cover run metadata, epoch logging, candidate validation, upload targeting, and missing-SDK errors.

### B.3 DEL-03: immutable release-model input

**definition:** Retrieves the selected public model repository at one full commit SHA during the production image build.

**specification:**

- Accept only a full model revision SHA and copy only the required weights, configuration, and manifest.
- Validate the copied manifest and weight digest before completing the image.

**verification:** Manifest tests and production Docker stages enforce revision shape, required files, and integrity loading.

### B.4 DEL-04: self-contained serving image

**definition:** Packages the installed application, API, static console, ontology, policy, and validated model into one GPU-capable image.

**specification:**

- Run as a non-root user with one API worker and declared runtime limits.
- Expose a readiness-based health check and require no model download during container startup.

**verification:** CI builds the image, starts it with a generated checkpoint, checks installed-package paths, and runs the API smoke test.

### B.5 DEL-05: tested release publication

**definition:** Gates versioned container publication on source tests and container validation.

**specification:**

- Run lint, unit, integration, model, image, and smoke checks before release publication.
- On a matching version tag, publish versioned and `latest` images to the configured container registry.

**verification:** The CI workflow defines the test, image, and tag-gated publication jobs and verifies tag-to-package version agreement.

## C. shared constraints

- Preserve ADR `20` and requirements `OR-002` through `OR-004`, `QR-205`, and `QR-302`.
- Runtime success must not depend on W&B availability.
- The deployed artifact set remains fixed for the lifetime of the image.

## D. package acceptance

- source and packaging checks pass on supported Python versions.
- the CI image starts, becomes ready, imports only installed packages, and passes its smoke test.
- the production build rejects a missing or non-SHA model revision and a corrupt model artifact.
- a release tag matching the package version produces immutable versioned and convenience image tags.

## E. non-goals

- robot-edge hardware packaging or performance validation;
- Kubernetes or distributed serving;
- automatic model promotion;
- production secrets, authentication, or public-network hardening;
- persistent runtime monitoring.
