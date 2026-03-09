# Orbital Credit Dashboard (`OC-0601`)

This is the Sprint 6 scaffold for `dashboard/web-app` using Next.js (App Router).

## Prerequisites
- Node.js `>=18.18` (current workspace uses Node `20.5.1`)
- npm

## Run
```powershell
# first time setup:
Copy-Item .env.example .env

npm run dev
```

Open `http://localhost:3000`.

## Scaffolded Routes
- `/` : OC-0601 landing and route jump page
- `/login` : banker login shell
- `/applications` : queue shell
- `/applications/[applicationId]` : risk analysis shell
- `/system-status` : system monitoring shell

## Design Mapping
All scaffold routes are mapped to files in:
- `../../updated_stitch_designs`

Reference manifest:
- `../../updated_stitch_designs/manifest.csv`
- `../../updated_stitch_designs/manifest.json`

Detailed mapping for implementation handoff:
- `docs/DESIGN_REFERENCES.md`

## Next Tasks
- OC-0602: Build queue UI + data integration
- OC-0603: Build detail/rationale UI
- OC-0604: Add decision confirmation and action flow
- OC-0605: Add auth guard placeholder
