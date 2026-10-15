# Product Experience

> Defines how the product should orient operators, guide its two core workflows, communicate uncertainty, and remain calm and usable during active work.

## 1. Purpose and Scope

This document governs the shared product experience: user context, experience narrative, information hierarchy, visible states, interaction patterns, accessibility, language, and visual character.

It covers two operator workflows:

- continuous robot operation;
- instrument-tray inventory.

It does not define model behavior, policy logic, technical APIs, confidence thresholds, or the detailed business rules behind a recommendation. Those details may be inspectable when useful, but they must not become the primary interface.

## 2. Decision Status

The following are established experience commitments:

- The primary user is an operator. A more specific role or job title is not yet established.
- Operators need to understand the current state, latest resolved item, inventory, and items requiring review.
- The product provides recommendations only when it has adequate support. Low confidence, missing information, missing policy, and unsupported items remain unresolved and require review.
- `PROTOTYPE` and `NOT FOR CLINICAL USE` remain visible throughout the experience.
- The interface favors calm operation, legibility, and user-friendliness over decoration, novelty, or dense analytics.

This document uses one working assumption: both workflows belong in one coherent operator product, with shared navigation and interaction patterns. The intended device, viewport, input method, operating environment, and relationship between the robot and tray workflows remain open decisions.

## 3. Users and Context

### 3.1 Primary operator

The known user is the person who starts and stops processing, observes item resolution, captures a tray, supplies review context, reviews inventory, and inspects or exports results.

Their core experience needs are:

- immediate orientation after opening or returning to the product;
- an obvious distinction between work in progress, resolved items, and items needing review;
- fast access to the current item and latest outcome;
- confidence that each resolved physical item changes inventory once, and only once;
- a safe, visible way to stop or recover when processing cannot continue;
- optional access to supporting detail without being forced to interpret system internals.

The operator's training, clinical responsibilities, physical environment, stress level, assistive-technology needs, and expected data density have not been established. Designs must not assume expertise or a particular setting until those questions are answered.

### 3.2 Other users

No secondary user is currently defined. Exporting a summary implies that another person may eventually consume an output, but their identity, task, and access needs are unknown. Do not design a separate patient, caregiver, administrator, or reviewer experience without an explicit product decision.

## 4. Core Experience Narrative

The product should feel like a calm operations console: it follows an item from observation to either a supported handling recommendation or an explicit review state, while keeping the overall inventory understandable.

The recurring interaction rhythm is:

1. **Orient:** See what the product is doing now and what happened most recently.
2. **Observe:** Watch items and inventory update as work progresses.
3. **Resolve or route:** Present a supported recommendation, or clearly route the item to review.
4. **Account:** Keep the inventory and final summary consistent with resolved physical items.
5. **Recover:** When work cannot continue, explain the condition and offer a safe stop or restart path.

Before using the product, an operator may be unsure whether processing is active, whether an item has been accounted for, or what needs attention. After interacting with it, the operator should know the current state, the latest outcome, the next available action, and which items still need human judgment.

## 5. Experience Architecture

### 5.1 Shared orientation

Every primary view must make these questions easy to answer at a glance:

- What workflow am I in?
- Is it active, complete, stopped, or unable to proceed?
- What item is being processed now?
- What was resolved most recently?
- What changed in the inventory?
- What requires review?
- What can I do next?

When a question does not apply, the interface should say so through a purposeful empty or inactive state rather than leave an unexplained blank area.

### 5.2 Three-tier information hierarchy

Use a consistent hierarchy across both workflows:

1. **Overview:** A command view summarizes active work, the latest resolved item, inventory totals, and the number of items requiring review.
2. **Workspace:** A focused view supports either continuous robot operation or tray capture and finalization. The current state and primary action dominate this level.
3. **Inspect:** A contextual detail view exposes confidence, explanations, matched rules, and technical JSON without replacing the workspace or interrupting the operator by default.

The overview and exact primary-navigation pattern are a working design direction, not a confirmed form-factor decision. If the product is constrained to a single workflow or a narrow viewport, preserve the hierarchy while adapting its presentation.

### 5.3 Persistent product status

`PROTOTYPE` and `NOT FOR CLINICAL USE` must be visible on every primary view and in exported summaries. They should be readable and persistent without competing with an active blocking condition.

## 6. Core Workflow Experiences

### 6.1 Continuous robot operation

The continuous-operation workspace should support one processing run at a time:

1. **Start:** Make the inactive state and the action to begin a run unmistakable.
2. **Monitor:** Show the current item, its resolution state, and any handling output with minimal delay.
3. **Account:** Update inventory once for each resolved physical item. Keep the latest resolved item visible long enough to verify what changed.
4. **Review:** Keep unresolved items visible as requiring review. Do not present them as recommendations.
5. **Stop or recover:** Keep a safe stop action available and make failures actionable. Present a restart path when restarting is possible.
6. **Conclude:** Allow the operator to inspect the completed run and export its final summary.

The product must not imply that an item is resolved while an outcome is still pending. Exact run-state names, stop semantics, restart behavior, and whether a stopped run can resume are open decisions.

### 6.2 Instrument-tray inventory

The tray-inventory workspace has three operator-visible phases:

1. **Capture:** Choose a live camera or recorded video and scan the full tray. Update overlays and the visible-item list automatically during capture.
2. **Review context:** Confirm procedure stage, item usage, and contamination context.
3. **Finalize:** Review inventory counts grouped by recommended handling or manual review.

Preserve progress and clearly identify the current phase when the operator moves between capture, context review, and finalization. Confidence, explanations, matched rules, and technical JSON belong in optional details, not in the main completion path.

The behavior for changing the capture source, correcting an item, revisiting an earlier phase, or finalizing with unresolved items is not yet defined.

## 7. Visible States and Language

### 7.1 Outcome vocabulary

Use a small, consistent vocabulary in both workflows:

- **Processing:** The product is working on an item and has not produced an outcome.
- **Recommended handling:** A supported handling recommendation is available.
- **Needs review:** The product cannot provide a supported recommendation.
- **Stopped:** Active processing has ended through an operator or system action.
- **Unable to continue:** Processing cannot proceed without intervention.

These labels are proposed interface language. Final terminology should be validated with operators, especially the distinction between a recommendation, a resolution, and a handling output.

### 7.2 Communicating uncertainty

Never convert low confidence, missing information, missing policy, or an unsupported item into a recommendation. Show `Needs review` as a first-class outcome that is visually and semantically distinct from recommended handling.

The primary message should explain what the operator needs to do next. Confidence, explanations, matched rules, and technical JSON may support investigation, but they must remain behind an explicit details control.

### 7.3 Writing style

- Use concise, domain-appropriate operational language.
- Name the current state and next action directly.
- Prefer verbs for controls, such as `Start run`, `Stop run`, `Review item`, `Finalize inventory`, and `Export summary`.
- Avoid model, policy, implementation, or data-format terminology in primary messages.
- Do not use reassuring language to conceal uncertainty or failure.

## 8. Interaction Patterns

### 8.1 Feedback hierarchy

- **Blocking:** A condition that prevents safe continuation stays visible until addressed. It uses an explicit label, explanation, and available next action. Color alone must not communicate severity.
- **Needs attention:** An unresolved item or non-blocking workflow condition remains visible in context and in the review count until handled or the workflow ends.
- **Informational or successful:** Brief feedback may disappear automatically only when the lasting result remains visible in the workspace or inventory. A transient message should remain long enough to be perceived, with three seconds as an initial design baseline rather than a validated timing requirement.

### 8.2 Consequential actions

The safe stop action must be easy to find. Do not add confirmation friction unless stopping would discard or irreversibly change work. If an action will delete data, alter an established status, finalize an irreversible result, or otherwise prevent recovery, explain the consequence and require explicit confirmation.

Whether stopping, restarting, finalizing, or exporting has irreversible effects is not established. Those semantics must be decided before their confirmation behavior is finalized.

### 8.3 Loading, live updates, and empty states

- Never use an unexplained blank panel for loading, waiting, no-result, or failure states.
- Distinguish initial loading from active processing and from inability to continue.
- Preserve the last stable result while a new item is processing, while clearly labeling it as the previous result.
- Announce inventory changes once per resolved physical item and avoid duplicate visual feedback.
- Use motion only to clarify activity or change, not as decoration.

The acceptable delay for current-item, overlay, and inventory updates has not been quantified. `Minimal delay` is the current experience goal and requires a measurable target before acceptance testing.

### 8.4 Interruption recovery

An operator returning after an interruption should be able to recover context from the visible workflow state, current item, latest resolved item, inventory, and review list. Do not rely on a transient notification as the only record of a meaningful outcome.

## 9. Accessibility and Localization

### 9.1 Accessibility baseline

Target WCAG 2.1 AA for the operator interface.

- All actions must be keyboard accessible and have visible focus states.
- Use semantic controls and meaningful accessible names so a screen reader can operate the workflow without a pointer.
- Provide touch targets of at least 44 by 44 points, or the platform-equivalent minimum, when the interface supports touch.
- Do not rely on color, position, motion, or an overlay alone to communicate item or workflow status.
- Associate live status updates with the affected item, and avoid announcements so frequent that they obscure the current task.
- Respect reduced-motion preferences.
- Keep critical labels, counts, and actions legible at supported zoom levels and viewport sizes.

The supported assistive technologies, browsers, devices, and test matrix remain open decisions.

### 9.2 Language and localization

Primary copy should be plain and operational while preserving necessary domain terms. Technical codes and internal terminology belong only in optional detail.

No required languages or locales are defined. Before localization work begins, decide the source language, supported locales, terminology ownership, and how exported summaries represent localized labels.

## 10. Visual Character

The interface should feel calm, legible, and operational rather than futuristic. The visual system should emphasize hierarchy, state, and next action instead of decorative effects or dense analytics.

Apply these principles:

- Reserve the strongest emphasis for the current state, blocking conditions, and primary action.
- Keep recommended handling and `Needs review` clearly distinct without relying only on color.
- Use consistent spacing, typography, icons, and status treatments across both workflows.
- Keep overlays readable without allowing them to obscure the tray or replace the visible-item list.
- Use animation sparingly and only when it helps the operator understand processing or change.

Brand colors, typography, iconography, theme behavior, and support for varied lighting conditions are not established.

## 11. Design System and Component Governance

No component toolkit, design-file source, or token-governance process has been selected. Until that decision is made, product design should use a reusable component vocabulary rather than workflow-specific one-offs.

The minimum shared inventory is:

- persistent prototype-status treatment;
- workflow and phase header;
- start, stop, restart, finalize, and export controls where applicable;
- current-item and latest-result panels;
- capture source selector and capture viewport;
- item overlay and corresponding visible-item row;
- inventory group and count;
- `Needs review` item and review count;
- contextual details disclosure;
- blocking, attention, success, loading, empty, and unable-to-continue states.

Changes to global spacing, color, typography, motion, and status semantics should be made through shared tokens or components once the design-system foundation is chosen. The location and ownership of design source files remain open decisions.

## 12. Experience Review Checklist

A design is consistent with this document when an operator can:

- identify the workflow, current state, and next action without opening technical details;
- distinguish active processing, recommended handling, and `Needs review` without relying on color alone;
- see the current item, latest resolved item, inventory effect, and outstanding review work;
- verify that each resolved physical item is reflected once in inventory;
- stop safely and understand how to recover from a failure;
- complete tray capture, context review, and final inventory review in a clear sequence;
- inspect supporting detail without losing their place;
- operate all actions by keyboard and understand them with a screen reader;
- see `PROTOTYPE` and `NOT FOR CLINICAL USE` throughout the experience and on exports.

## 13. Open Product Decisions

The following decisions require product validation before the experience can be considered complete:

1. Who the operator is, what environment they work in, and whether any secondary user needs a separate experience.
2. Supported devices, viewport sizes, pointer or touch use, and environmental lighting.
3. The primary-navigation model and whether operators may switch workflows while processing is active.
4. Exact run states and the semantics of stopping, restarting, resuming, and finalizing.
5. How operators correct, merge, remove, or otherwise resolve item and inventory mistakes.
6. Whether unresolved items block tray finalization or run completion.
7. The contents, format, destination, and audience of exported summaries.
8. Measurable latency and freshness targets for live item, overlay, and inventory updates.
9. Supported languages, locales, assistive technologies, browsers, and devices.
10. The design-system foundation, visual tokens, design-source location, and governance owner.

