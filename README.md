# MRDM Console v1.3.0

A local-first, single-person sleep and rhythm journal. Record sleep with minimal input, see today's observations, and understand movement toward your chosen schedule. The core phase portrait jointly describes target offset and day-to-day drift; it does not claim to measure internal circadian phase or predict drug effects.

## Daily use

- Calendar and sleep entry share the first screen. Select a date; clicking outside or pressing Escape clears the highlight without discarding the draft.
- Enter sleep and wake times. Mark sleep-aid disturbance with one checkbox. Optional awakenings and multiple-interval entry stay out of the main path.
- For an unrecorded no-sleep day, click the no-sleep button and confirm once; no other fields are required.
- Optional medication details use a local name/alias library and journal. Dose, clock time and notes can remain empty. No external lookup is performed.
- The blue phase line connects actual observations from the latest seven days. It is not a forecast or recommended route. Target and movement are explained beside the figure.
- Set only the desired wake time and sleep-duration reference in the sidebar. The app computes derived observations. Internal constants are references, not personalized estimates.

Legacy P/D threshold controls, diagnostic curves, parameter test bench and GP shadow learning have been removed from the app. Jev remains an explicitly invoked optional decision interface over existing candidates. Details are previewed before an external request; medication journals are not included.

## Model and records

Raw sleep records use schema v2 in `data/records.csv`. Version 1 loads compatibly and is backed up before upgrade. Awake duration can be known or explicitly unknown; unknown does not mean zero. Rhythm-day grouping uses the documented 18:00 boundary. Missing dates are not confirmed all-nighters; legacy inferred states must not be treated as measured phase.

The production phase proxy still uses representative wake time and total daily sleep. Alternative main-window and circular-center mappings are research branches. Process S scenarios are supporting context, not a quantity to minimize permanently. Legacy D/H fields remain compatible with stored records, but are not presented as sleep owed or proven health scores.

- [Model specification](docs/MRDM.md)
- [Current roadmap](ROADMAP.md)
- [Single rolling audit](docs/dev/practical_product_audit.md)
- [Phase objective](docs/dev/phase_objective_system.md)
- [Local medication design and implemented subset](docs/dev/local_medication_journal.md)

## Run locally

```sh
mamba env create -f environment.yaml
mamba activate mrdm
bash scripts/start_mrdm.sh
```

The launcher binds localhost. Daily overrides persist in `data/ui_settings.yaml`; do not edit base configuration to change personal goals. Data, backups, medication SQLite files, exports and local research reports are ignored by Git.

An optional TypeSafe key may be supplied through `TYPESAFE_API_KEY` or the ignored `.streamlit/typesafe_api_key` file. Never commit keys.

## Private remote entry

The companion blog has a `/tools/mrdm/` entry for an owner-operated HTTPS Tailscale service. GitHub Pages does not run the Python app. The private service address stays in the accessing browser, not in public source. The computer must remain awake and connected. See [private remote access](docs/dev/private_remote_access.md). Multi-user registration and data isolation are not implemented.

## Development

```sh
PYTHONPATH=. pytest
PYTHONPATH=. python scripts/study_phase_events.py
```

Research outputs are local and must not be committed. Historical tags retain their release dates; intermediate untagged work is consolidated in v1.3.0. See [CHANGELOG](CHANGELOG.md).
