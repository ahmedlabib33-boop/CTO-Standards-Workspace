# data folder

Drop `.xlsx` or `.xlsm` corporate source workbooks directly in this folder.

- `schema.json` tells the converter how known SAMCO sheets are normalized.
- `control/admin_overrides.json` contains Admin changes, additions and suppressions.
- `generated/` is disposable and may be deleted/rebuilt at any time.
- `optional/historical/` and `optional/live/` are optional enrichment layers only.

Do not put GitHub tokens in this folder. The local token belongs in root `repo_token.txt`, which is ignored by Git.

## Project intake control data

`control/document_mappings.json` is preserved by the generated-data clean workflow. It contains Admin-governed document classification keywords, CSI inference mappings, contract-term rules and SAM-CTO matching thresholds. Generated Excel JSON remains under `generated/`; these two layers must not be mixed.
