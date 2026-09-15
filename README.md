# SAMCO CTO Standards Hub — Next.js + Python + Excel-Governed Data

This repository is the local/Vercel foundation for the SAMCO CTO corporate standards platform.

## Core rule

The application **must not depend on Historical Data or Live Project Data to stay online**.

Runtime order:

```text
Excel Corporate Baseline
        ↓
Admin Overrides
        ↓
Optional Historical Data
        ↓
Optional Live Project Data
        ↓
Rules / Prediction Router
        ↓
SAMCO App
```

If Historical and Live Project data are both missing, the app runs in `baseline_only` mode using the approved Excel-derived standards, rates and equations.

If the generated JSON itself is temporarily removed by `Clean.bat`, the Next.js app still starts in `empty_safe_mode` and shows zero/empty controlled defaults instead of crashing.

---

## Data folder

The repository contains a root folder named `data`.

```text
data/
├─ Activity lists Final Tuning.xlsx
├─ Tender Bid Calculation & Pricing Workbook - Egypt.xlsx
├─ schema.json
├─ control/
│  └─ admin_overrides.json
├─ generated/
│  ├─ catalog_manifest.json
│  ├─ schema_report.json
│  ├─ master/
│  └─ workbooks/
└─ optional/
   ├─ historical/
   └─ live/
```

### Excel sources currently wired

1. `Activity lists Final Tuning.xlsx`
   - Activity List CSI
   - Resource Unique List
   - material mappings and unique list
   - manpower database, crew rates and productivity
   - equipment mappings, machine cost/rate data and productivity
   - subcontractor mappings and unique list

2. `Tender Bid Calculation & Pricing Workbook - Egypt.xlsx`
   - Fixed Material Prices
   - Concrete Mix Calculator
   - Labor & Equipment Rates
   - Thresholds & Assumptions
   - BOQ Buildings / Roads / Bridges / Tunnels
   - Bid Summary Dashboard

The generated unified baseline currently contains:

- **143 activities**
- **184 unique resources**
- **430 normalized rate records from both workbooks**
- **41 commercial assumptions**

The figures are generated from the supplied workbooks, not manually entered into the app.

---

## SAMCO master ID

Corporate activities receive a stable ID with this format:

```text
SAM-CTO-#########
```

The default ID is deterministically generated from the legacy activity code so rebuilding the JSON does not randomly change identities.

Admin may override any specific ID in `data/control/admin_overrides.json` without modifying the Excel baseline.

Example:

```json
{
  "activities": {
    "02300-01": {
      "SAMCO Master ID": "SAM-CTO-000000001"
    }
  }
}
```

---

# Local workflow

## 1. Put Excel files in `data`

Any `.xlsx` or `.xlsm` file placed directly in `data` is discovered by the converter.

Known SAMCO workbooks are normalized according to `data/schema.json`.
Unknown workbooks are still exported as raw workbook JSON under `data/generated/workbooks`, so adding an unexpected workbook does not stop the pipeline.

## 2. Add GitHub token

Open:

```text
repo_token.txt
```

Replace:

```text
PASTE_GITHUB_TOKEN_HERE
```

with a GitHub Personal Access Token or fine-grained token that has write permission to the target repository.

**Security:** `repo_token.txt` is in `.gitignore`. The PowerShell publishing scripts exclude it from the API snapshot and explicitly delete any previously committed root `repo_token.txt` from GitHub.

Never paste the token into source code, JSON, `.env.example`, Git remote URLs or Vercel frontend variables.

## 3. Build JSON and publish

Double-click:

```text
create_json.bat
```

It opens a PowerShell window and performs:

```text
Discover every Excel in data/
        ↓
Read workbook/sheets
        ↓
Apply data/schema.json
        ↓
Normalize known SAMCO datasets
        ↓
Apply Admin overrides/additions/deletions
        ↓
Build unified rates from BOTH Excel workbooks
        ↓
Create schema/availability manifest
        ↓
Write data/generated/*.json
        ↓
Create GitHub blobs/tree/commit through PowerShell
        ↓
Update GitHub `main` using repo_token.txt
        ↓
Vercel deploy via Git integration
        OR optional VERCEL_DEPLOY_HOOK_URL
```

No local Git repository or Git installation is required. The script uses `repo_token.txt` and the GitHub REST API to update the configured repository's `main` branch directly.

If the configured repository is empty, the first run creates `main` with the local `.gitignore` through GitHub's Contents API, then publishes the remaining workspace snapshot. `repo_token.txt` is never used as that bootstrap file and is never uploaded.

## 4. Clean generated fixed data locally + GitHub

Double-click:

```text
Clean.bat
```

It opens PowerShell and asks you to type `CLEAN`.

It deletes only:

```text
data/generated/**/*.json
```

It does **not** delete:

- Excel source files
- `data/schema.json`
- `data/control/admin_overrides.json`
- application source code
- `repo_token.txt`

Then it creates a GitHub commit through the REST API. Therefore a JSON deleted locally from the generated fixed-data layer is also deleted from GitHub without requiring Git on the computer.

Vercel then redeploys the safe app state. The app does not fail simply because generated JSON is absent.

---

# Admin data control

The source-of-truth model is deliberately layered:

```text
Excel = approved baseline
Admin Override JSON = deliberate corporate changes
Historical/Live = optional evidence
Generated JSON = runtime result
```

Admin can:

### Patch an existing rate

```json
{
  "rates": {
    "CEM-01": {
      "rate": 4100,
      "notes": "Approved supplier quotation 16-Sep-2026"
    }
  }
}
```

### Change a SAMCO activity ID

```json
{
  "activities": {
    "02300-01": {
      "SAMCO Master ID": "SAM-CTO-000000001"
    }
  }
}
```

### Add a new activity

```json
{
  "additions": {
    "activities": [
      {
        "Activity Code": "SAM-NEW-01",
        "Activity description": "New SAMCO standard activity",
        "UOM": "m2"
      }
    ]
  }
}
```

If no SAMCO ID is supplied for a newly added activity, the pipeline creates a `SAM-CTO-#########` ID.

### Add a new rate

```json
{
  "additions": {
    "rates": [
      {
        "rate_id": "SAM-RATE-001",
        "source": "Admin Override",
        "category": "Material",
        "description": "New material",
        "unit": "m2",
        "rate": 350
      }
    ]
  }
}
```

### Suppress a record

```json
{
  "deletions": {
    "rates": ["SAM-RATE-001"],
    "activities": ["02300-01"]
  }
}
```

The baseline Excel file is not destroyed; the governed runtime simply applies the Admin overlay.

The Next.js `/admin` page can write this override file **only in local mode** when:

```text
SAMCO_ALLOW_LOCAL_FILE_WRITES=true
```

and the request includes the correct `SAMCO_ADMIN_KEY`.

On Vercel, filesystem editing is intentionally disabled because the deployment filesystem is not a safe persistent database. Production Admin editing should persist through Supabase, while Git remains the controlled baseline publication mechanism.

---

# Vercel deployment

Recommended:

1. Push this project to GitHub.
2. Connect that GitHub repository to Vercel.
3. Vercel automatically deploys after `create_json.bat` or `Clean.bat` pushes a commit.

Optional: define this only in local `.env.local`:

```text
VERCEL_DEPLOY_HOOK_URL=https://api.vercel.com/v1/integrations/deploy/...
```

The PowerShell scripts will POST the hook after a successful push.

---

# Next.js local run

```powershell
cd SAMCO_CTO_Standards_Hub_Next_Python
copy .env.example .env.local
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

Admin:

```text
http://localhost:3000/admin
```

Before opening the app for the first time, either run:

```text
create_json.bat
```

or:

```powershell
python scripts\excel_to_json.py
```

---

# Runtime fallback / ML routing

The Python Vercel endpoint `api/ml_router.py` and the Next.js data layer apply this rule:

```text
IF Excel baseline is missing:
    empty_safe_mode
    app stays online

ELSE IF Historical OR Live data exists:
    hybrid_predictive
    corporate baseline + available evidence

ELSE:
    baseline_only
    corporate rules + Excel rates/productivity
```

This prevents the ML architecture from becoming a single point of failure.

Historical and live data can improve prediction confidence but never become mandatory dependencies for Tender, Planning, Technical or Cost Control work.

---

# Main generated files

```text
data/generated/catalog_manifest.json
    input workbook hashes, counts, optional-source availability and warnings

data/generated/schema_report.json
    schema validation result

data/generated/master/activity_master.json
    Activity List + SAM-CTO IDs

data/generated/master/resource_master.json
    unique corporate resources

data/generated/master/rates.json
    unified rates from BOTH Excel workbooks + Admin overrides

data/generated/master/commercial_assumptions.json
    risk/overhead/profit/escalation/bond/insurance/VAT/financing assumptions

data/generated/master/fixed_data.bundle.json
    main app-ready baseline bundle

data/generated/workbooks/*.json
    full raw JSON export of every Excel workbook in data/
```

---

# Pricing equations used

The workbook-derived pricing logic is documented in `EQUATIONS.md`. Core formulas include:

```text
Material Cost / Unit
= Material Unit Price × (1 + Wastage %)

Direct Unit Rate
= Material Cost/Unit
+ Labor Cost/Unit
+ Equipment Cost/Unit
+ Subcontractor Rate/Unit

BOQ Amount
= Quantity × Direct Unit Rate

Site Overhead
= Direct Cost × Site Overhead %

Head Office Overhead
= Direct Cost × Head Office Overhead %

Contingency
= Subtotal after Overheads × Risk Contingency %

Escalation
= applicable cost base × Escalation %

Profit
= Subtotal before Profit × Profit Margin %

Bonds & Insurance
= Net Bid Price × applicable bonds/insurance %

Financing Cost
= applicable cost base × Financing Cost %

VAT
= Price before VAT × VAT %

Grand Total Bid Price
= Price before VAT + VAT
```

Concrete mix and machinery equations are also documented in `EQUATIONS.md`.

---

# Schema

See:

- `data/schema.json` — executable Excel-to-JSON mapping
- `SCHEMA.md` — application/domain schema
- `ARCHITECTURE.md` — system pipeline and fallback design
- `SECURITY.md` — Admin, secrets and deployment security
- `EQUATIONS.md` — workbook-derived calculations


---

# Event-driven core — applied in v0.3

The project now includes the recommended PostgreSQL + Orchestration + Redis/Event Broker architecture without sacrificing the existing Excel/JSON fallback.

## New runtime components

```text
lib/db.ts                   PostgreSQL connection + transactions
lib/orchestration.ts        synchronous core / async routing
lib/events.ts               transactional outbox + Redis stream publish
lib/planning.ts             activities/productivity/duration engine
lib/integration-gateway.ts  optional external integration registry
workers/worker.py           Redis/outbox background worker
api/worker.py               Vercel-invokable single worker cycle
```

Database migration:

```text
supabase/migrations/002_event_driven_core.sql
```

This adds durable outbox events, background job history, Planning duration standards and integration endpoint metadata.

## Local setup after npm dependencies are available

```powershell
npm install
pip install -r requirements.txt
```

Apply Supabase migrations, then set `DATABASE_URL`. To load the Excel-derived corporate baseline into PostgreSQL:

```powershell
npm run db:seed
```

Start the web app:

```powershell
npm run dev
```

Optional local background worker:

```powershell
npm run worker
```

The web application does **not** require the worker to calculate Planning durations, display activities/rates, or run deterministic Tender/Cost formulas.

## Environment

Important optional runtime variables:

```text
DATABASE_URL
REDIS_URL
SAMCO_EVENT_STREAM=samco:events
SAMCO_EVENT_GROUP=samco-workers
```

When they are absent, the app continues from the Excel-derived JSON baseline.

## New pages / APIs

- `/planning` — Planning Activity & Duration core
- `/system` — PostgreSQL, broker and Integration Gateway status
- `POST /api/planning/duration` — deterministic duration calculation
- `POST /api/orchestrate` — synchronous/async orchestration entry
- `GET /api/events/status` — DB/broker status
- `GET /api/integrations/status` — optional integration configuration status
- `POST /api/worker.py` — one background worker cycle on Vercel/Python runtime

See `EVENTS.md`, `ARCHITECTURE.md`, `SCHEMA.md`, `SECURITY.md` and `EQUATIONS.md`.

---

# v0.4 — Project documents are now the platform front door

The supplied Construction Drawing AI pipeline has been re-engineered into a generic SAMCO Project Intake & Scope Integration engine. It is no longer bridge-specific and it no longer stores multi-user state in a process-global accumulator.

## What is wired

```text
BOQ + Specs + Contract/ITT + PDF/DXF Drawings
                    ↓
          classify / extract / tables
                    ↓
                   CSI
                    ↓
          SAM-CTO candidate mapping
                    ↓
         controlled scope + evidence
                    ↓
         PostgreSQL + durable outbox
                    ↓
 Technical | Tender | Planning | Cost Control
```

New pages:

- `/intake` — upload documents and build the controlled project scope.
- `/technical` — evidence/completeness/conflict view.
- `/tender` — BOQ/SAM-CTO pricing intake queue.
- `/planning` — now also receives persisted project scope before duration/schedule build-up.
- `/cost-control` — same scope identity ready for budget/CBS/EAC mapping.

New Python engine: `ingestion/`.

New migration: `supabase/migrations/003_project_intake_scope.sql`.

Admin can edit `data/control/document_mappings.json` through `/admin` when `SAMCO_ALLOW_LOCAL_FILE_WRITES=true`.

## Local intake service

```powershell
pip install -r requirements-ingestion.txt
npm run ingestion:dev
```

Then set:

```text
NEXT_PUBLIC_INGESTION_API_URL=http://127.0.0.1:8010/api/intake
```

The intake service is an enrichment/front-door layer, not a single point of failure. If it is offline, the corporate Activity/Resource/Productivity/Rate libraries, Tender calculations and Planning duration engine remain available.

See `DOCUMENT_INTAKE.md` for the complete flow and governance rules.


## GitHub Publishing Target

**Local workspace:** `D:\CTO Standards WorkSpace`

**GitHub repository:** `https://github.com/ahmedlabib33-boop/CTO-Standards-Workspace`

The supplied BAT launchers use this repository explicitly. `repo_token.txt` is local-only and is excluded from Git.

### Windows launchers

- `create_json.bat` — Excel → governed JSON → PowerShell GitHub API commit → update `main`.
- `Clean.bat` — remove generated JSON locally → PowerShell GitHub API commit → update `main`.
- `push_main.bat` — publish the complete main tree through PowerShell and `repo_token.txt`.
- `push_folder.bat` — publish the entire local tree through PowerShell while explicitly excluding `repo_token.txt`.

Paste only the GitHub token into `repo_token.txt`; do not put the token into source code, JSON, or repository files.
