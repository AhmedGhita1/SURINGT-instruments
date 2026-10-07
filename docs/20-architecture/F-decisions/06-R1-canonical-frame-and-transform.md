# decision: use one canonical frame and geometry path

**status:** accepted

**roadmap milestone:** R1: perception baseline

## A. context

training begins with images while runtime inference receives camera or decoder frames. Separate preprocessing paths can diverge in channel order, resize behavior, padding, scaling, and box inversion.

## B. decision

use RGB `numpy.uint8` arrays shaped `(H, W, 3)` as the frame boundary. One transform performs aspect-preserving letterbox resize, rescaling, box conversion, clipping, normalization, and inversion. Training and inference use the same transform. Boxes crossing the application boundary use absolute `xyxy` coordinates in the original frame.

## C. consequences

camera and decoder inputs fit the boundary without device semantics. Callers must convert channel order before invoking the transform and must not resize independently. The resize implementation remains part of model parity.

## D. validation or reversal

round-trip known boxes through preprocessing and postprocessing and compare training and inference samples. Replace the implementation only after proving geometric and model-output parity.
