# Real-world validation plan

## Objective

Determine whether source-backed ORCID-to-TAXID evidence improves the speed, consistency, and quality of human customer-screening review without creating false reassurance.

## Questions

1. Does the system retrieve relevant researcher–organism evidence with acceptable precision?
2. How often does it fail because ORCID or PubMed coverage is incomplete?
3. Does it reduce review time compared with the current workflow?
4. Do citations make reviewer conclusions easier to audit?
5. Does the interface cause reviewers to overinterpret publication history?

## Dataset

Build a de-identified, manually adjudicated set of researcher–organism pairs covering:

- strong direct evidence;
- weaker or indirect evidence;
- review-only evidence;
- conflicting or ambiguous evidence;
- legitimate researchers with no machine-retrievable links;
- incorrect identifier matches; and
- organisms absent from the researcher's public record.

At least two qualified annotators should independently label each case. Preserve disagreement rather than forcing consensus prematurely.

## Metrics

- evidence precision and recall at the relationship level;
- coverage across researchers and organism groups;
- citation precision;
- abstention accuracy;
- median review time with and without assistance;
- reviewer agreement;
- false-reassurance rate; and
- frequency and severity of each failure mode.

## Prospective evaluation

Run the tool in shadow mode. Reviewers complete their normal process, then compare it with the tool's retrieved evidence. The application must not affect fulfillment decisions during this stage.

Predefine success criteria with the participating organization. Document workflow changes, reviewer feedback, and cases where the tool would have misled or delayed a reviewer.

## Governance

Before operational use, define data retention, access control, audit logging, incident response, model and rule change control, human escalation, and periodic reevaluation. Treat evidence quality separately from any policy decision about an order.
