Seva Setu Portal — Investigation and Fix Plan
im working on an existing government old-age pension portal called Seva Setu. Inspect the current repository and understand the existing architecture before changing code. Do not assume the root cause of any issue. First investigate, document evidence, then implement the smallest safe fix that fits the existing project.
Context and business rules

The scheme is for eligible residents aged 60 or older on the application date. Confirm how the current code calculates age.
There must be one application per person. Check backend enforcement, not only frontend validation.
The department has 15 days to decide an application under the stated RTPS workflow.
Where the applicable rules require deemed approval, an untouched overdue application must be marked Approved and the citizen-facing status must reflect that.
The application window closes at midnight India Standard Time (IST).
Do not invent additional scheme eligibility rules. Identify assumptions and flag any rule that needs confirmation.
Work method
Inspect the project structure, README, dependency files, environment configuration examples, models, migrations, views/API endpoints, serializers/forms, frontend components, scheduled jobs, deployment configuration, and tests.
Trace each reported problem from user interface to backend, database, background jobs, and generated documents as applicable.
Before editing, summarize the likely cause with the code/log/test evidence that supports it.
Implement focused fixes consistent with the existing stack. Avoid unnecessary rewrites or introducing new infrastructure before checking what already exists.
Add or update automated tests for each fix and run the relevant test suite.
Never expose secrets, applicant personal data, or production data in logs, screenshots, test fixtures, or the final summary.
If the repository does not contain enough evidence to verify a cause, state exactly what logs, configuration, or access would be needed. Do not claim an issue is fixed unless it was tested.
Issue 1 — Assamese names render as ???? or are truncated
Investigate:
Whether the original Assamese text is correct in the browser before submission.
Whether the API request/response preserves Unicode correctly.
Database column type, database encoding/collation, connection encoding, and any lossy conversion or sanitization.
Whether the stored value is already corrupted or only becomes corrupted in the UI, acknowledgement slip, PDF, export, or print view.
Whether the chosen fonts support Assamese glyphs and whether PDF generation embeds or uses a suitable font.
Whether name fields have restrictive length limits, substring operations, incorrect validation, or truncation in serializers/templates.
Fix the actual point of corruption. Internationalization (i18n) may help language support, but it does not by itself repair Unicode storage or font-rendering defects.
Tests:

Round-trip representative Assamese Unicode text through validation, API, database/model, and acknowledgement/PDF output where supported.
Confirm the full name is preserved and not truncated.
Keep existing English names working.
Issue 2 — Applicants cannot correct a submitted application
Investigate:
Existing application status/workflow and whether any edit, correction, withdrawal, or resubmission mechanism already exists.
Which fields may legally be corrected and at which statuses.
How the backend checks applicant identity and application ownership.
Whether the one-application-per-person rule is enforced by validation and/or database constraints.
Whether editing could overwrite an approved decision or erase audit history.
Implement an appropriate correction flow using the existing architecture (for example, a restricted update/PATCH endpoint and UI form) only after confirming workflow rules. Do not allow users to edit another person's application or silently alter an approved record. Record changes in an audit trail where appropriate. Ensure hidden/omitted fields do not cause incorrect validation and prevent duplicate applications.
Tests:

Applicant can correct permitted fields in allowed statuses.
Unauthorized users cannot edit an application.
Disallowed status transitions are rejected.
Duplicate applications remain blocked.
Audit history and existing data are preserved.
Issue 3 — RTPS deemed auto-approval stopped working
Investigate:
Existing scheduled task/cron/Celery Beat configuration, workers, broker, task registration, and deployment/startup commands.
Task execution history, exceptions, retries, timezone configuration, and recent changes around when the issue began.
Query filters for overdue and untouched applications, status names, date arithmetic, and boundary conditions.
Whether the task runs but fails to update records, or updates the database while the citizen-facing status remains stale.
Idempotency, concurrent execution, transaction handling, and duplicate processing.
Do not add Celery blindly. First determine whether the project already uses Celery or another scheduler and repair the existing mechanism where possible. If a background task is needed, implement it using the project's established approach.
Requirements:

Follow the confirmed 15-day RTPS rule and the correct legal/time calculation.
Ensure qualifying untouched applications are marked Approved and the citizen-facing status agrees.
Make processing safe to retry and prevent conflicting updates.
Add useful operational logging and failure visibility without logging personal data.
Tests:
Application just before the deadline is not approved early.
Application that has crossed the applicable deadline qualifies as expected.
Re-running the task does not corrupt or duplicate processing.
The citizen-facing status reflects deemed approval.
Boundary and timezone cases are covered.
Issue 4 — Portal slows or stalls before pension disbursement deadlines
Investigate first; do not guess or add caching without evidence.
Check:

Request latency, error rates, CPU, memory, worker saturation, connection pools, and server/container limits, if metrics or logs are available.
Slow database queries, query plans, missing indexes, N+1 queries, table scans, locks, long transactions, and connection exhaustion.
Endpoints and pages used most heavily during the deadline period.
Expensive reports/exports, synchronous jobs, file/PDF generation, external API calls, and large payloads.
Whether scheduled tasks run at the same time as peak traffic.
Static assets and frontend requests only if evidence points there.
Use available local tooling, query inspection, profiling, and tests. If production metrics are unavailable, create a reproducible local load/performance test and clearly label it as a simulation rather than production evidence.
After identifying the bottleneck, apply a measured fix such as query optimization, an appropriate index, pagination, batching, caching, or worker configuration. Do not introduce caching where it could show stale or incorrect application/approval statuses.

Tests/verification:

Record a baseline and compare after the change where feasible.
Check correctness under concurrent requests.
Confirm application status and eligibility data are not stale.
Document any production metrics or access still needed.
Issue 5 — Reports of sales calls after applicants submit personal information
Treat this as a potential privacy/security incident, not as a confirmed breach. Do not contact suspected parties or expose applicant data.
Investigate:

Authentication and authorization for applicant records and APIs.
Public or guessable endpoints, insecure direct object references, excessive data returned by APIs, and bulk export/download features.
Admin/staff permissions, account activity, audit logs, unusual access patterns, and data exports.
Third-party integrations, analytics, SMS/email vendors, webhooks, shared spreadsheets, and vendor/contractor access.
Secrets in the repository, unsafe debug settings, exposed backups, logs containing personal data, and deployment configuration.
Whether access logs can establish evidence of unauthorized access, while preserving evidence and following the responsible incident process.
Do not assert that a breach occurred unless evidence confirms it. If a credible exposure is found, document the evidence safely and escalate to the designated government/security/privacy owner for incident response.
Fix verified vulnerabilities with least-privilege access, server-side authorization, data minimization, safe configuration, and appropriate audit logging. Do not put personal data or secrets into logs or test output.

Tests:

Unauthenticated users cannot access private application data.
Applicants can access only their own records.
Unauthorized staff/actions and bulk exports are blocked as required.
API responses expose only necessary fields.
Issue 6 — Application form is confusing or inaccessible
Inspect the full six-step application flow, not just one screenshot.
Investigate:

Labels, instructions, required-field indicators, validation messages, and whether errors explain how to fix the problem.
Mobile layout, text size, keyboard navigation, focus states, screen-reader labels, contrast, and language support.
Whether the form asks for fields irrelevant to the applicant's selected answers.
Whether conditional fields update when gender, marital status, or other relevant answers change.
Whether the application can be reviewed before submission and whether users receive a clear confirmation/acknowledgement.
Whether fields and validation match confirmed scheme rules.
For example, if “Husband's Name” and “Husband's Current Employer” appear for a male, unmarried applicant, trace the field configuration and conditional-rendering logic. Verify the scheme rules before deciding which applicant categories should see these fields. Do not rely on gender alone if the actual scheme requires a different rule.
Implement accessible, responsive, plain-language improvements without changing eligibility rules. Ensure backend validation matches the actual requirements.

Tests:

Conditional fields appear only when relevant under confirmed rules.
Changing answers updates the form without a page reload where appropriate.
Keyboard navigation and error messages work.
Existing valid applications can still be submitted.
Final deliverables
When finished, provide:
A short diagnosis for each issue, with file paths and evidence.
A list of files changed and why.
The fixes implemented, separated from issues that could only be investigated.
Tests added/run and their actual results.
For performance and security, the evidence gathered and any remaining production checks needed.
Any assumptions or scheme/legal rules requiring confirmation.
A prioritized summary suitable for a 2–3 minute screen-recorded walkthrough.
Do not fabricate test results, production measurements, logs, or successful fixes. If something cannot be verified in this repository, say so explicitly.