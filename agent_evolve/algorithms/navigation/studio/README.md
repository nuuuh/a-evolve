# Navigation Studio

A browser-based visual designer for evolution systems. Drag nodes onto a
canvas, wire them together, validate, and export a ready-to-use
`EvolutionTemplate` Python file that drops into
`agent_evolve/algorithms/navigation/templates/`.

Built on top of the [`navigation/activity/`](../activity/) metamodel — the
studio is a thin skin over its `Activity`, `ActivityRuntime`, validator, and
registry. No new dependencies (stdlib `http.server` + vanilla JS).

## Launch

```bash
python -m agent_evolve.algorithms.navigation.studio
# serving at http://127.0.0.1:8765/
```

Flags:
- `--port N` (default 8765)
- `--host ADDR` (default 127.0.0.1)

## Workflow

1. Open `http://127.0.0.1:8765/` in a browser. The canvas boots with the
   `plan_driven` Activity already loaded — the same graph backing
   `templates/orchestrated.py`, including its `analyst` and
   `evolve_one_branch` sub-activities — so you have a working example to
   edit immediately.
2. Click **Load Shipped…** to switch to `inline`, or **Load JSON** to
   open a previously saved graph. (Or delete everything and start fresh.)
3. Add parameters (left sidebar ➕), then drop nodes from the **Palette**
   on the right. Click a node to edit its config in the **Inspector**.
4. Drag from an **output pin** (right edge) to an **input pin** (left
   edge) to draw a wire. Types must match; `Void → Void` becomes a
   `ControlFlow` automatically.
5. Click **Validate** anytime — the server runs the real
   `activity.validator.validate()` and reports the exact node/pin
   failure.
6. Click **Export .py** → pick a class name (e.g. `MyTemplate`) and
   template name (e.g. `my_template`). The file downloads.
7. Move the file to
   `agent_evolve/algorithms/navigation/templates/my_template.py`.
   The relative imports (`from ..activity...`, `from .base import …`)
   resolve only there.
8. Use it:

```python
from agent_evolve.algorithms.navigation.templates.my_template import MyTemplate
from agent_evolve.algorithms.navigation.engine import NavigationEngine

engine = NavigationEngine(config, template=MyTemplate(engine=None))
```

`NavigationEngine` accepts any `EvolutionTemplate` via the `template=`
kwarg. No edits to `templates/__init__.py` required.

## Generated file shape

- Embeds the Activity as a module-level `ACTIVITY_SPEC` dict literal.
- `__init__` does `Activity.from_json(ACTIVITY_SPEC)` once and stashes
  the `default_registry()`.
- `execute()` builds bindings for whichever engine-provided values the
  Activity declares as `in`-parameters (one of `workspace`, `git`,
  `batch`, `cfg`, `evo_number`, `routing_log`), runs the shared
  `ActivityRuntime`, and returns the standard
  `{evo_number, mutated, plan, branches, trajectory}` contract.
- `_pick(outputs, name, default)` mirrors the helper in
  `activity/adapters.py` so templates can read their outputs by
  out-parameter name *or* by a trailing `.name` pin reference.

## Sub-activities

The studio keeps all Activities flat in a left-sidebar list. `CallActivity`
and `ExpansionRegion` nodes reference a *sibling* Activity from the same
list via the **Inspector**'s `activity` dropdown. On export, the chosen
top-level Activity is emitted with every other Activity embedded under
`sub_activities`.

This matches how `plan_driven.json` is structured (sub-activities are dict
values, not nested graphs). No drill-down canvas is needed.

## Limitations (v1)

- No nested sub-activity canvas (flat sidebar only).
- No in-browser Activity execution / dry-run; use `Validate` for checks.
- No editing of the `Type` enum or registry — only already-registered
  actions and types can be used.
- The studio writes no files on the server: all saves are browser
  downloads. Load state via **Load JSON** or **Load Shipped…**.
- Session state lives in the open tab. Save to JSON before closing.

## Files

```
studio/
├── __init__.py           # launch()
├── __main__.py           # python -m … .studio
├── server.py             # stdlib HTTP routes + static serving
├── schema.py             # default_registry() + Type → JSON palette
├── codegen.py            # Activity JSON → template .py source
├── static/
│   ├── index.html
│   ├── app.js            # vanilla JS + SVG canvas
│   └── styles.css
└── README.md
```

Nothing outside `studio/` is modified by this package. The generated
template is the only artifact that leaves.
