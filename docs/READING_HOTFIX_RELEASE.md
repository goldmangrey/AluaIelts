# Reading confirmed hotfix isolated release

Base: 97a70d3. Includes only the six Reading exams, metadata, source-bound repairs, retained-asset support, two renderer fixes and targeted regression evidence. Results V2, Review V2 and all pending Listening edits are excluded.

Production frontend is the existing Cloudflare Worker alua-ielts (the owner explicitly confirmed Workers after inspection found no Pages projects). The deployed Reading CSS from 0f81eb4 is preserved exactly; its different HEAD modal rule is intentionally excluded. Immutable rollback version: 2a752cce-890a-4860-9350-01741f5877bc, deployment 44cf4940-0c27-4b0f-9524-efe8177fe82b.

Backend clones source-fidelity-20261107-9689a3afffa3, retains its untouched original release and creates a rollback-compatible clone with additive lookup for the new image ID. No migrations, environment edits, key changes, grading changes or real user attempt/result changes. Production smoke uses only the existing guarded ALUA QA Release profile through normal authenticated endpoints.

The narrow V1 test fixture contains exactly 41 unchanged confirmed records; the unrelated whole-corpus audit is not part of this release. Isolated preflight: 62 short regressions PASS; production webpack build PASS. Runtime source hashes and all 72 Oracle answer keys match the expected baseline before staging.
