# Product and UX specification

## Experience goals

1. A prospective client understands what information is required and why.
2. A reviewer understands why the system assigned a score and can override it responsibly.
3. A potential freelance client can understand the complete workflow in under two minutes.

## Public intake form

### Information hierarchy

- concise outcome-oriented headline;
- statement that the firm will review the request;
- company/contact details;
- operating scale and service needs;
- free-text context;
- separate privacy and marketing choices;
- explicit warning against real sensitive data in the demo.

### Validation behavior

- errors appear close to the form and preserve a clear next action;
- required fields have labels, not placeholder-only instructions;
- numeric fields use reasonable minimums;
- the success state exposes a lead ID but no sensitive data;
- the API responds asynchronously so users are not held by AI/email latency.

## Reviewer dashboard

### First screen

- total leads, recent volume, qualified, review required, awaiting information and high priority;
- pipeline chart;
- searchable/filterable lead table;
- visible score, priority, status and next action.

### Review panel

- concise AI summary;
- requested services;
- missing information;
- risk flags;
- complete score breakdown;
- document count;
- human decision control;
- mandatory audit reason and reviewer assignment.

### Design principles

- AI confidence is context, not an authority indicator;
- risk flags are readable labels, not hidden technical codes;
- score breakdown is always available before a decision;
- destructive/reject decisions should require confirmation in production;
- raw sensitive documents should not be previewed by default;
- accessibility target is WCAG 2.2 AA for a production UI.

## Portfolio presentation

A 60–90 second demo should show:

1. submit the ecommerce lead;
2. show the 202 response and lead ID;
3. open n8n execution;
4. show structured extraction and score breakdown;
5. inspect Mailpit email;
6. open Streamlit and record a human onboarding decision;
7. show the audit trail through an API or SQL view.

Use synthetic data overlays and avoid showing local secrets, browser password managers, API keys or full `.env` files.
