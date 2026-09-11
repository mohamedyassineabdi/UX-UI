# Contributing to UX/UI Auditor

Read the [README](README.md), [Checkpoint](docs/CHECKPOINT.md), [Product Specification](docs/PRODUCT-SPECIFICATION.md), [Technical Specification](docs/TECHNICAL-SPECIFICATION.md), [Architecture](docs/ARCHITECTURE.md), and the engineering document relevant to your change before editing.

AI-assisted contributors must also follow [AI Instructions](AI-INSTRUCTIONS.md), use the task routing in [Reading Map](READING-MAP.md), and apply [Execution Rules](EXECUTION-RULES.md).

## Local work

Follow [Environment](docs/ENVIRONMENT.md) and [Configuration](docs/CONFIGURATION.md), then use the checks in [Testing](docs/TESTING.md). Work in a focused feature, fix, or documentation branch. Do not pull, rebase, reset, or clean over unrelated dirty work; use a separate worktree when integration is risky.

## Change workflow

Inspect the existing implementation and tests, make the smallest coherent change, add/update focused tests, update affected documentation, and run the minimum validation matrix. Changes to public behavior may require updates to the Product/Technical Specifications, Architecture, Data Model, API/Database/Configuration documents, and Checkpoint. Architectural decisions deserve an ADR; routine fixes do not.

## Pull requests

Before requesting review, confirm scope is clear, relevant tests/builds pass, security implications are considered, documentation is current, credentials/generated outputs are absent, and unrelated changes are excluded. Existing history uses concise scoped messages (for example, `docs: ...`); follow that observed style without treating it as a formal Conventional Commits requirement.

For security architecture see [Security](docs/SECURITY.md); for operational/release handling see [Security Operations](docs/SECURITY_OPERATIONS.md). Do not publish a private vulnerability contact that the repository does not provide.
