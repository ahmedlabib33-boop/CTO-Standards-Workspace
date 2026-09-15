# SAMCO CTO Hub — Security Rules

1. `repo_token.txt`, database credentials, Redis credentials and API secrets must never be committed.
2. Use Supabase/PostgreSQL RLS for department/page data access; hiding UI elements is not security.
3. Admin-only mutation APIs require server-side authorization. The prototype uses `SAMCO_ADMIN_KEY`; production should use authenticated admin roles/session claims.
4. Redis is not a source of truth. Durable events live in PostgreSQL outbox records.
5. Do not place secrets in Redis event payloads, browser state, generated JSON or audit display text.
6. External integrations are optional and isolated through the Integration Gateway.
7. The LLM/ML workers cannot directly approve or silently overwrite corporate rates, activities, duration standards or tender values.
8. Corporate master changes require auditable before/after values.
9. Vercel filesystem writes are not used as production persistence. Use PostgreSQL/Supabase; use the local JSON/Git workflow for controlled baseline publishing.
10. Rate updates, corporate ID changes and access changes are privileged operations.

# v0.4 Project Intake security controls

- Intake accepts only `.pdf` and `.dxf` and enforces per-file and per-batch limits.
- Uploaded filenames are reduced to basenames before processing.
- Structured extraction is project/ingestion scoped; the previous process-global accumulator pattern is not used.
- Raw document bytes are not inserted into PostgreSQL. Production should store them in controlled object storage and keep only metadata/storage paths in `project_documents`.
- SAM-CTO matching is advisory/project-working data until the governed mapping status is approved. It cannot modify the corporate `activities` master automatically.
- Admin document-mapping writes require `SAMCO_ADMIN_KEY` in the local workflow and are disabled unless `SAMCO_ALLOW_LOCAL_FILE_WRITES=true`. Production mapping rules should use authenticated database/RLS control.
- OCR is optional and last-resort. If it is unavailable, the document is flagged rather than silently treated as fully extracted.
- Department access to persisted intake data is governed by RLS and `project_scope_feeds`; Top Management/Admin can see consolidated scope.
