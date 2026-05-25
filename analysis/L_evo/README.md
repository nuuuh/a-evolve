# L_evo — empirical evidence for the evolution-loss barrier

This folder contains the working files for the §4.2 subsection that empirically demonstrates $\Levo > 0$ on each of the three benchmarks via benchmark-specific capability bottlenecks.

The design is locked in `../barrier_exp_design.md` (see §2 for the three stair-step tables).

This folder lives at `a-evolve/analysis/L_evo/`, sibling to `a-evolve/evaluations/` (the source analysis folders) and `a-evolve/results/` (the raw run outputs).

## What this folder produces

For each benchmark, one stair-step table showing performance vs. capability level:
- **PolyBench**: confidence calibration / coverage stair-step.
- **FutureX**: search-API breadth stair-step.
- **CTF-Dojo**: per-category specialised-toolkit stair-step.

All numbers come from existing analysis folders — no new runs.

## Folder layout

```
L_evo/
├── README.md                    (this file)
├── data/                        (extracted numbers, raw)
│   ├── polybench_stairstep.json
│   ├── futurex_stairstep.json
│   └── ctf_dojo_stairstep.json
├── scripts/                     (extraction + figure / table generation)
│   ├── extract_polybench.py
│   ├── extract_futurex.py
│   ├── extract_ctf_dojo.py
│   ├── generate_tex_table.py    (single combined LaTeX table)
│   └── generate_figure.py       (optional matplotlib figure)
├── output/
│   ├── stairstep_table.tex      (final LaTeX for §4.2)
│   └── stairstep_figure.pdf     (optional combined figure)
└── notes.md                     (per-benchmark sourcing notes)
```

## Source data references

| Benchmark | Source file |
|---|---|
| PolyBench | `evaluations/analysis_poly/{report.md, h1_vs_h4_investigation.md, glimpse.md}` (Tables 2, 12) |
| FutureX | `evaluations/analysis_futurex/{leaderboard_comparison.md, l3_l4_performance_progression.md, evolver_api_exploration.md}` |
| CTF-Dojo | `evaluations/analysis_ctf_dojo/{report.md §4.2, infrastructure_failures.md}` |

Both `evaluations/analysis_*/` paths exist under `/home/ec2-user/A-EVOLVE-V2/a-evolve/evaluations/` and the older sibling tree at `/home/ec2-user/A-EVOLVE-V2/evaluations/`.

## Workflow

1. **Extract** stair-step numbers per benchmark into `data/*.json` from the cited analysis files. One row per capability level; columns include the benchmark's headline metric (Coverage / CWR / Pass / Accuracy).
2. **Verify** numbers against the source by spot-check (do not invent numbers; cite each row's analysis-file location in the JSON).
3. **Generate** a single combined LaTeX table (`generate_tex_table.py`) with three sub-tables (one per benchmark). Output to `output/stairstep_table.tex`.
4. **Optionally generate** a matplotlib figure (`generate_figure.py`) showing the three stair-steps side-by-side as bar charts. Output to `output/stairstep_figure.pdf`.
5. **Drop into §4.2** by including the figure: `\includegraphics[width=\linewidth]{../../analysis/L_evo/output/stairstep_figure.pdf}` from `paper/EMNLP26/sections/experiment.tex`. The combined LaTeX table is also available at `output/stairstep_table.tex`.

## Notes on what is *not* needed

- No new evolution runs.
- No new LLM-judge calls.
- No per-cycle saturation curves (discarded design — see `../barrier_exp_design.md` §6).
- No cross-baseline ablation (that lives in RQ2).

## Status

- [x] Extract PolyBench stair-step (`data/polybench_stairstep.json`)
- [x] Extract FutureX stair-step (`data/futurex_stairstep.json`)
- [x] Extract CTF-Dojo stair-step (`data/ctf_dojo_stairstep.json`)
- [x] Generate combined LaTeX table (`output/stairstep_table.tex`)
- [x] Generate combined figure (`output/stairstep_figure.{pdf,png}`)
- [ ] Wire into §4.2 of `paper/EMNLP26/sections/experiment.tex`
