# decision: ship a pinned self-contained runtime image

**status:** accepted

**roadmap milestone:** R6: edge demonstrator

## A. context

downloading an unspecified model at startup makes deployment depend on external availability, credentials, mutable tags, and unverified content. Installing training and evaluation packages in the runtime image increases size and attack surface without serving value.

## B. decision

store the approved model in a dedicated Hugging Face repository, pin builds to a full commit SHA, validate the manifest and weight digest during the build, and bake the validated artifact into the image. Keep experiment tracking optional for training and candidate management, never required by runtime. Separate core, serving, training, and development dependency groups.

## C. consequences

the image is a reproducible deployment unit that can start without registry credentials. Promoting a model requires building a new image. Edge and cloud images may optimize differently but must pin the same logical release contracts.

## D. validation or reversal

build from a clean environment, verify artifact integrity, start without registry credentials, and run an end-to-end smoke test. Consider startup download or mounted artifacts only when promotion speed outweighs the added availability and integrity controls.
