# Architecture decision records

Numbered records of decisions that shape the project. Each ADR gives context, the decision, alternatives considered, and consequences.

## Numbering

`ADR-NNN`, three digits, assigned in order and never reused. Numbers are not renumbered when a record is superseded.

## Lifecycle

Proposed, then Active (adopted), then Superseded (replaced by a later ADR, which it links to).

## Layout

The existing records sit in lifecycle folders: `Proposed/`, `Active/`, and `Superseded/`. [`list-adr.md`](list-adr.md) is the generated index from the earlier tooling and is not updated automatically. When you add an ADR, create it as `(ADR-NNN)-Title.md` in the folder for its status (or as a folder of the same name when it has attachments), and move it when its status changes.

Cite ADRs with their title, for example ADR-001 (Sidecars as Completion Contract).
