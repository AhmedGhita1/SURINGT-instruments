# product vision

## A. executive summary and vision statement

### A.1 vision statement

Surgical-instrument processing depends on maintaining a clear chain of accountability for every item. When an instrument is missed, misidentified, counted more than once, or disconnected from the appropriate handling procedure, teams face reconciliation work, workflow disruption, and avoidable safety risk. SURGINT Instruments is a visual workflow assistant that strengthens this chain by maintaining a traceable inventory, providing standardized handling guidance, and directing uncertain cases to human review.

### A.2 strategic goal

The strategic goal is to establish a trustworthy digital backbone for surgical-instrument processing. By bringing instrument identification, inventory, and handling guidance into one coherent and traceable workflow, SURGINT Instruments strengthens instrument accountability, reduces manual reconciliation, and creates the basis for dependable automation under human oversight.

## B. problem space and opportunity

### B.1 core operational problem

Surgical-instrument processing is a continuous accountability task, not a sequence of isolated identifications. Teams must preserve an accurate understanding of each item as instruments enter the workflow, change position, disappear from view, and reappear. When identification, counting, and handling guidance are managed as separate activities, that understanding becomes difficult to maintain and unresolved uncertainty is pushed onto the operator.

### B.2 consequence of the current gap

When instrument accountability breaks down, teams must pause to reconcile counts, confirm identities, and recover missing handling information. This increases workload, delays processing, weakens traceability, and can allow misidentified or incorrectly routed instruments to progress through the workflow. The same uncertainty prevents automated workflows from using results dependably and forces operators to verify information that should already be coherent.

### B.3 opportunity

The opportunity is to make instrument accountability continuous and reviewable throughout processing. A shared operational record of what has been identified, what has been counted, which handling guidance applies, and what remains uncertain can reduce reconciliation and support more dependable automation. SURGINT Instruments addresses this opportunity while preserving human oversight and directing unresolved cases to explicit review.

## C. target audience and ecosystem stakeholders

### C.1 primary users

Robot operators and instrument-tray operators supervise processing runs or capture and finalize tray inventories. They need clear access to workflow state, resolved items, inventory, supported handling outcomes, failures, and items requiring review without having to interpret model or policy internals.

### C.2 secondary stakeholders

Operational supervisors and evaluators review inventory results, handling outcomes, exceptions, and supporting evidence. Integrated instrument-processing workflows consume timely, structured results while retaining independent operational and safety controls.

### C.3 technical stakeholders

Engineering and research teams require reproducible artifacts, stable interfaces, measurable quality, traceable results, and explicit operating limits so they can evaluate and integrate SURGINT Instruments without relying on undocumented model behavior.

The commercial buyer, deployment owner, and regulatory pathway have not yet been established and are not assumed by this prototype.

## D. strategic pillars

### D.1 persistent physical-item state

The product maintains instrument identity and workflow state across repeated observations. A supported physical item is accounted for once even when it appears, moves, leaves view, or reappears.

### D.2 traceable handling outcomes

Instrument observations produce operational value only when connected to validated knowledge, workflow context, and explicit handling policy. Each supported outcome must remain traceable to the evidence, context, model, knowledge, and policy versions that produced it.

### D.3 bounded and reviewable automation

Automation remains limited to demonstrated operating conditions. Unsupported instruments, insufficient evidence, missing information, incompatible policy, and degraded operation produce an explicit review or failure state rather than an unjustified result.

## E. non-goals and boundaries

- **No clinical decision-making:** SURGINT Instruments does not diagnose, recommend patient treatment, or replace accountable clinical judgment.
- **No visual claims of sterility or safety:** Appearance alone is not used to declare an instrument sterile, uncontaminated, safe, or suitable for use.
- **No invented handling outcomes:** Uncertainty, missing context, unsupported items, and absent policy remain visible and do not become recommendations.
- **No replacement for operational safety controls:** SURGINT Instruments supplies instrument understanding and handling outcomes; it does not replace the independent controls required to execute physical operations safely.
- **No safety-critical accounting claim at the prototype stage:** Current inventories and decisions are research outputs until their intended operating conditions have been independently validated.
- **No general hospital or asset-management platform:** The product remains focused on visual understanding, state, and handling support for surgical-instrument processing.

## F. current stage and success criteria

SURGINT Instruments is a product-direction research prototype. Its current purpose is to validate the product assumptions, system boundaries, evidence, and operating profiles required to progress toward an operational product. It is not clinically validated and must not be used for patient care, autonomous safety decisions, or safety-critical instrument accounting.

Product success means that, under declared and independently validated operating conditions, an instrument-processing workflow can use SURGINT Instruments to maintain dependable physical-item identity, inventory, and supported handling procedures; stop or request review when those conditions are not met; and trace every result to the evidence and versioned artifacts that produced it.
