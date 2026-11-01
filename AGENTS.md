# Repository instructions

- The user does not use the SDD approval workflow for this project.
- Work directly on `main`. Commit and push completed work by functional module; do not create branches or pull requests unless explicitly requested later.
- Sync with origin before starting. Never force-push shared history. Preserve unrelated teammate changes.
- The authoritative cleaned data is in `data/processed/`; split definitions are in `data/splits/`. Do not create per-member copies or change statistical/cleaning methods during structural refactors.
- Resolve paths through `cat_arena.common.paths`. Put entry points in `scripts/` and reusable code in `src/cat_arena/`.
- Preserve attribution. Members 4/5 are now delivered; retain their authorship and distinguish historical handoff placeholders from current results.
- Update affected module docs/report references alongside interface changes. Maintain dependencies at the project root.
- Run relevant checks. For shared integration changes use `python scripts/check_project.py --rerun`; full source/image preparation requires actual course images and must not be claimed if absent.
- Follow `CONTRIBUTING.md` for direct-main collaboration and leakage rules.
