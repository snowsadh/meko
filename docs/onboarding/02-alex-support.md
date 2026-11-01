---
document_id: ATLAS-SUPPORT-001
company: Atlas
audience: Alex, customer support
classification: Support internal
data_type: Synthetic demo
as_of: 2026-11-01
---

# Alex's support playbook

This is fictional support data for a demonstration. Use it alongside the Atlas
company handbook. The cases below are seeded examples, not evidence of a live
ticketing connection or actions performed by Alex.

## Login triage

Before suggesting a fix, identify the customer's plan and sign-in method. Collect
the error code, workspace name and approximate failure time. Do not ask for their
password, one-time login code or API key.

### Enterprise error AMBER-217

AMBER-217 means the customer's identity-provider claims need an Access Ops review.
The confirmed escalation owner is **Isha in Access Ops**. Ask Isha to refresh the
SSO claims. Include the workspace, error code and approximate failure time in the
handoff. **Never reset an Enterprise customer's password as a workaround.**

Customer-facing wording: acknowledge the sign-in problem, explain that the identity
configuration needs review, and collect the required details. Do not promise that
Isha has been contacted unless a message was actually sent. There is no confirmed
resolution time.

### Starter password account

A Starter customer who forgot their password should use the self-service reset
link on the Atlas sign-in page. This guidance applies to password accounts, not
Enterprise SSO accounts. No public Atlas website URL is provided in this demo;
do not invent a reset URL.

### Expired invitation

Atlas workspace invitations expire after **7 calendar days**. A workspace
administrator must issue a fresh invitation. Alex can explain the steps and draft
a request to the administrator; this playbook does not give Alex an invitation
creation tool.

## Billing questions

An unused first subscription payment is eligible for refund review if requested
within **7 calendar days of payment**. A request after that window or a payment
above **₹5,000** requires an explicit exception review. **Omar must approve every
refund before it is issued**, including eligible requests below ₹5,000.

Ask for the payment date, amount, workspace and whether the subscription was used.
Do not request full card details. Alex can assess the supplied facts and draft a
billing handoff. This dataset does not contain a connected refund-processing tool.

## Seeded customer cases

| Case | Customer | Facts | Current recorded state |
| --- | --- | --- | --- |
| SUP-101 | Northstar Design | Enterprise; workspace `northstar-design`; AMBER-217 at 10:15 Asia/Kolkata on 30 October 2026 | Customer reported the issue; Access Ops review has not been confirmed |
| SUP-102 | Cedar Studio | Starter; workspace `cedar-studio`; invitation sent 20 October 2026 and still unused on 29 October | Invitation expired; a fresh administrator-issued invitation is needed |
| SUP-103 | Kite Labs | Starter; first payment ₹2,400 on 28 October 2026; subscription unused; refund requested 30 October | Eligible for refund review; Omar's approval is pending |

These states are snapshots. Do not say a case was fixed, a refund was issued or a
handoff was sent without a newer confirmed result.

## Support report data

These are synthetic **new tickets received during 26–30 October 2026**. They are
not counts of currently open tickets or response-time measurements.

| Category | New tickets |
| --- | ---: |
| Login | 12 |
| Billing | 8 |
| Invitations | 5 |
| Total | 25 |

Login represents 48% of the 25 new tickets. Use the category rows, without the
total row, when producing a chart. A support onboarding presentation can cover
login triage, the AMBER-217 escalation, invitation expiry and billing approval.

## Information outside this role

This support playbook contains no employee leave records, salaries or HR approvals.
The company handbook's general leave allowance does not reveal Snow's individual
balance. Ask HR for private HR questions rather than guessing.
