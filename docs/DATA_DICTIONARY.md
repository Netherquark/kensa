# Dataset and feature dictionary

## Raw schema

**Record:** [Zenodo 5046428](https://zenodo.org/records/5046428), `background_for_training.h5`. Published compressed file size: 646.4 MB; published event count: 4,000,000; expected MD5 `08cb4801229f9d480567f8d3f5cac134`.

| HDF5 key | Intended content | Project treatment |
|---|---|---|
| `Particles` | `(N, 19, 4)` numerical tensor | Full-row chunk scan; schema gate requires 19 slots and 4 values per slot |
| `Particles_Names` | Feature-name metadata | Captured in inventory and checked for pT field |
| `Particles_Classes` | Particle-type metadata | Captured in inventory |

Published slot order: MET, four electrons, four muons, ten jets. Feature values: transverse momentum `pT`, pseudorapidity `eta`, azimuth `phi`, particle type code. Published type coding: `0` = padding; `1` = MET; `2` = electron; `3` = muon; `4` = jet. Angular convention: `phi` in radians within `[-pi, pi]`. Momentum values are in GeV under the paper's natural-unit convention. The audit retains actual metadata values so the local source file can be checked.

The article reports the event-generation and filtering requirements: simulated 13 TeV proton-proton collisions; at least one selected electron or muon; electron threshold `pT > 23 GeV`, `|eta| < 3`; muon threshold `pT > 23 GeV`, `|eta| < 2.1`. Selected objects include jets and up to four electrons, four muons, ten jets, plus MET, following published cuts. Full selection detail is in the paper.

## Derived event table

One Parquet row per source row, with stable source ordinal `event_row_id`. No physical event ID is inferred from row ordinal.

| Column | Type | Definition |
|---|---|---|
| `event_row_id` | int64 | Zero-based row ordinal in source tensor |
| `met_pt`, `met_phi` | float32 | Fields from fixed MET slot 0; verify metadata and data-quality flags |
| `n_electrons` | int16 | Count of type-code 2 slots |
| `n_muons` | int16 | Count of type-code 3 slots |
| `n_jets` | int16 | Count of type-code 4 slots |
| `n_objects` | int16 | Electron + muon + jet slot count |
| `leading_electron_pt` | float32 | Maximum `pT` among type-code 2 slots; zero if none |
| `leading_muon_pt` | float32 | Maximum `pT` among type-code 3 slots; zero if none |
| `leading_jet_pt` | float32 | Maximum `pT` among type-code 4 slots; zero if none |
| `ht_jets` | float32 | Sum of jet `pT` values, `Σ pT(jet)` |
| `sum_lepton_pt` | float32 | Sum of electron and muon `pT` values |
| `max_abs_eta` | float32 | Maximum `|eta|` across electron, muon and jet slots; zero when empty |
| `has_nonfinite` | bool | Event contains any NaN or infinity in raw tensor values |
| `invalid_type_count` | int16 | Event slot count with non-finite / out-of-vocabulary type value |
| `negative_pt_count` | int16 | Occupied slots with `pT < 0` |
| `inconsistent_padding_count` | int16 | Type-zero slots with any nonzero kinematic coordinate |

`pT` field name and physical units come from source documentation and must be validated against HDF5 metadata. When the ETL builds aggregate features, non-finite numeric inputs contribute zero to derived aggregate arithmetic and remain marked by quality columns. The raw HDF5 source remains unchanged. Any nonzero quality-flag count must be investigated before scientific interpretation.

## Research guardrails

- Type zero is structural padding under the published schema. Treating it as a measured zero-pT particle biases occupancy and kinematic calculations.
- `Particles_Classes` describes particle categories; it is not evidence of per-event signal/background ground truth.
- The main training file is a Standard Model cocktail after lepton selection. Hidden black-box truth data belong to a separate challenge record.
- The `40 MHz` phrase describes the intended Level-1 trigger use case. File itself is a finite offline simulated dataset.
