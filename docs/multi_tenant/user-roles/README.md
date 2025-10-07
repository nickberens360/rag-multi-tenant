# Minimal RBAC for Multi‑Tenant (v1)

Purpose: define a minimal, scalable RBAC that works now and can expand later without schema churn or breaking changes. Optimized for AI agent ingestion with a machine‑readable catalog and implementation plan.

Quick Links
- Catalog (machine‑readable): `rbac_catalog.yaml`
- Implementation Plan: `implementation_plan.yaml` (JSON: `implementation_plan.json`)
- Test Matrix: `rbac_test_matrix.yaml`
- Human Overview: `minimal_rbac.md`

Scope and Goals
- Minimal roles: SuperAdmin, TenantOwner, TenantAdmin, Member
- Minimal permissions: platform:admin, tenant:manage, user:manage, data:read, data:write
- Enforced tenant scoping; default deny; least privilege


Deliverables in this folder
- A minimal, explicit permission catalog for roles
- A stepwise plan to implement authorization gates in FastAPI
- A small test matrix to validate policy decisions

Future Extensions (non‑breaking)
- Add `Viewer`, `BillingAdmin`, or custom tenant roles by appending rows to the catalog and enabling `enable_custom_roles` feature flag.
