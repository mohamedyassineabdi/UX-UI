# Reading Map

**Status:** Task-dependent document routing
**Repository baseline:** `main @ b49d8ac0ca9b89da97629c734fa50d5245b5420b`
**Last updated:** 2026-09-11
**Audience:** AI/code agents and contributors
**Scope:** What to read before non-trivial work; inspect corresponding source/tests after reading.
**Related documents:** [AI Instructions](AI-INSTRUCTIONS.md), [Project Context](PROJECT-CONTEXT.md), [Execution Rules](EXECUTION-RULES.md), [Contributing](CONTRIBUTING.md).

## Universal starting set

Read [README](README.md), [Project Context](PROJECT-CONTEXT.md), [Checkpoint](docs/CHECKPOINT.md), the relevant row below, and the owning source/tests before a non-trivial change.

| Task | Read first | Then inspect | Update if behavior changes |
| --- | --- | --- | --- |
| Product behavior | [Requirements](docs/PRODUCT-REQUIREMENTS.md), [Product Spec](docs/PRODUCT-SPECIFICATION.md), [UX](docs/UX-SPECIFICATION.md) | relevant pipeline/UI/tests | Product Spec; UX if applicable |
| Backend/API | [Technical](docs/TECHNICAL-SPECIFICATION.md), [Architecture](docs/ARCHITECTURE.md), [API](docs/API-SPECIFICATION.md), [Security](docs/SECURITY.md) | server, auth, tests | API; Product Spec if observable; Security |
| Database | [Data Model](docs/DATA-MODEL.md), [Database](docs/DATABASE-SPECIFICATION.md), [Decisions](docs/DECISIONS.md) | job store/migrations/tests | Database, Data Model, ADR if architectural |
| Frontend | [UX](docs/UX-SPECIFICATION.md), [Design](docs/DESIGN-SYSTEM.md), [Content](docs/CONTENT-GUIDELINES.md), [Accessibility](docs/ACCESSIBILITY.md), [API](docs/API-SPECIFICATION.md) | React source/build/tests | affected UX/design/content/accessibility/API docs |
| Security | [Security](docs/SECURITY.md), [Security Operations](docs/SECURITY_OPERATIONS.md), [Quality Gates](docs/QUALITY-GATES.md), [Decisions](docs/DECISIONS.md) | trust-boundary source/tests/config | Security; Security Operations if operational |
| Scoring/measurement | [Product Spec](docs/PRODUCT-SPECIFICATION.md), [Technical](docs/TECHNICAL-SPECIFICATION.md), [Decisions](docs/DECISIONS.md), [Testing](docs/TESTING.md) | semantics, measurement, scoring/tests | Product/Technical Spec; ADR if architectural |
| Deployment/configuration | [Deployment](docs/DEPLOYMENT.md), [Environment](docs/ENVIRONMENT.md), [Configuration](docs/CONFIGURATION.md), [Release Process](docs/RELEASE-PROCESS.md) | deployment/config/CI | Deployment/Environment/Configuration/Release Process |
| Testing | [Testing](docs/TESTING.md), [Quality Gates](docs/QUALITY-GATES.md) | affected tests and CI | Testing if contract/guidance changes |
| Project status | [Project Plan](docs/PROJECT-PLAN.md), [Roadmap](docs/ROADMAP.md), [Implementation Plan](docs/IMPLEMENTATION-PLAN.md), [Milestones](docs/MILESTONES.md), [Risk Register](docs/RISK-REGISTER.md) | history and current checkpoint | status document supported by evidence |
| UX/content/accessibility | [UX](docs/UX-SPECIFICATION.md), [Design](docs/DESIGN-SYSTEM.md), [Content](docs/CONTENT-GUIDELINES.md), [Accessibility](docs/ACCESSIBILITY.md) | UI/report source and tests | the affected UX documents |
| Analytics | [Analytics](docs/ANALYTICS.md), [Data Model](docs/DATA-MODEL.md), [Security](docs/SECURITY.md) | actual telemetry/storage | Analytics; product/privacy documents if introduced |
| Documentation only | [Styleguide](docs/STYLEGUIDE.md), [Contributing](CONTRIBUTING.md), [Checkpoint](docs/CHECKPOINT.md) | affected authoritative document | only relevant documentation |
| Architecture | [Architecture](docs/ARCHITECTURE.md), [Decisions](docs/DECISIONS.md), [Technical](docs/TECHNICAL-SPECIFICATION.md), [Data Model](docs/DATA-MODEL.md), [Security](docs/SECURITY.md) | source, migrations, tests | Architecture, ADR, relevant contracts |

## Do not substitute planning for implementation

Do not read the [Roadmap](docs/ROADMAP.md) as current behavior, design/accessibility recommendations as implemented components or compliance, analytics proposals as telemetry, or the risk register as approved scope.
