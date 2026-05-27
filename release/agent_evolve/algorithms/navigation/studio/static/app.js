"use strict";

// ── State ────────────────────────────────────────────────────────────
//
// ``activities`` mirrors the ``sub_activities`` dict on an Activity plus
// the top-level one.  The top-level is the one we'll emit in /api/export.
// Each Activity object matches spec.Activity.to_json() exactly so save/load
// is a straight pass-through.
const State = {
  schema: null,                 // /api/schema response
  activities: {},               // {name: Activity-JSON}
  topLevel: null,               // name of entry-point Activity
  current: null,                // name of Activity on canvas
  layout: {},                   // {activityName: {nodeId: {x, y}}}
  selection: null,              // {kind: 'node'|'param', id: string} | null
  pending: null,                // in-progress wire source endpoint
};

// ── Boot ─────────────────────────────────────────────────────────────

async function boot() {
  State.schema = await (await fetch("/api/schema")).json();
  buildPalette();
  bindToolbar();

  // Seed the canvas with the Activity behind templates/orchestrated.py
  // (``plan_driven``) as a live example to edit.  Falls back to an empty
  // Activity if the shipped spec can't be fetched.
  let seeded = false;
  try {
    const resp = await fetch("/api/specs/plan_driven");
    if (resp.ok) {
      loadFromJSON(await resp.json());
      setStatus("Loaded plan_driven — the Activity behind templates/orchestrated.py. Edit and re-export.", "ok");
      seeded = true;
    }
  } catch { /* fall through */ }
  if (!seeded) {
    newActivity("my_evolution");
    render();
  }
}

document.addEventListener("DOMContentLoaded", boot);

// ── Palette (right sidebar) ──────────────────────────────────────────

function buildPalette() {
  const root = document.getElementById("palette");
  root.innerHTML = "";

  const groups = [
    { title: "Control Flow",
      items: State.schema.control_nodes.map(n => ({ ...n, _kind: "control" })) },
    { title: "Actions",
      items: State.schema.actions.map(a => ({ ...a, _kind: "action" })) },
  ];

  for (const g of groups) {
    const section = document.createElement("div");
    section.className = "palette-group";
    section.innerHTML = `<h4>${g.title}</h4>`;
    for (const item of g.items) {
      const label = item.action_kind || item.kind;
      const div = document.createElement("div");
      div.className = "palette-item";
      div.title = item.doc || "";
      div.innerHTML = `<div>${item.label || item.kind}</div>` +
                      `<div class="pk">${label}</div>`;
      div.addEventListener("click", () => addNodeFromPalette(item));
      section.appendChild(div);
    }
    root.appendChild(section);
  }
}

function addNodeFromPalette(item) {
  const act = currentActivity();
  const idBase = (item.action_kind || item.kind).replace(/[^a-zA-Z0-9_]+/g, "_");
  let i = 1;
  let id = `${idBase}_${i}`;
  while (act.nodes.some(n => n.id === id)) { i++; id = `${idBase}_${i}`; }

  const config = {};
  if (item._kind === "action") config.action_kind = item.action_kind;

  act.nodes.push({
    id,
    kind: item._kind === "action" ? "Action" : item.kind,
    config,
  });
  ensureLayout(State.current, id);
  render();
}

// ── Toolbar ──────────────────────────────────────────────────────────

function bindToolbar() {
  document.getElementById("btn-validate").addEventListener("click", doValidate);
  document.getElementById("btn-preview").addEventListener("click", doPreview);
  document.getElementById("btn-save").addEventListener("click", doSave);
  document.getElementById("btn-load").addEventListener("click",
    () => document.getElementById("file-picker").click());
  document.getElementById("btn-load-shipped").addEventListener("click", doLoadShipped);
  document.getElementById("btn-export").addEventListener("click", doExport);

  document.getElementById("btn-new-activity").addEventListener("click", () => {
    const name = prompt("New Activity name:", "");
    if (name) newActivity(name);
  });
  document.getElementById("btn-new-param").addEventListener("click", addParameter);

  document.getElementById("top-level-picker").addEventListener("change", (e) => {
    State.topLevel = e.target.value;
  });

  const picker = document.getElementById("file-picker");
  picker.addEventListener("change", async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    try { loadFromJSON(JSON.parse(text)); }
    catch (err) { setStatus(`load failed: ${err.message}`, "err"); }
    picker.value = "";
  });
}

async function doValidate() {
  const spec = topLevelSpec();
  const r = await fetch("/api/validate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ activity: spec }),
  });
  const data = await r.json();
  if (data.ok) setStatus("✔ Activity is valid", "ok");
  else setStatus(`✘ ${data.error}`, "err");
}

function doPreview() {
  const spec = topLevelSpec();
  const mmd = toMermaid(spec);
  showModal("Mermaid preview", `<pre>${escapeHtml(mmd)}</pre>`);
}

function doSave() {
  const spec = topLevelSpec();
  downloadBlob(JSON.stringify(spec, null, 2), `${spec.name}.json`, "application/json");
}

async function doLoadShipped() {
  const list = (await (await fetch("/api/specs")).json()).specs || [];
  if (!list.length) { setStatus("no shipped specs available", "err"); return; }
  const options = list.map(s => `<option value="${escapeHtml(s.name)}">${escapeHtml(s.name)} — ${escapeHtml(s.description || "")}</option>`).join("");
  const body = `<label>Pick a shipped Activity:</label><select id="shipped-sel">${options}</select>`;
  showModalPrompt("Load Shipped", body, async () => {
    const name = document.getElementById("shipped-sel").value;
    const spec = await (await fetch(`/api/specs/${encodeURIComponent(name)}`)).json();
    loadFromJSON(spec);
  });
}

async function doExport() {
  const spec = topLevelSpec();
  const body = `
    <label>Class name (Python identifier):</label>
    <input id="exp-class" value="StudioTemplate">
    <label>Template name (file stem, returned by <code>.name</code>):</label>
    <input id="exp-tmpl" value="studio_template">
    <p class="hint">The generated file must be placed at
      <code>agent_evolve/algorithms/navigation/templates/&lt;template_name&gt;.py</code>
      — relative imports resolve only there.</p>`;
  showModalPrompt("Export .py", body, async () => {
    const className = document.getElementById("exp-class").value.trim();
    const tmplName = document.getElementById("exp-tmpl").value.trim();
    if (!className || !tmplName) { setStatus("class and template name required", "err"); return; }
    const r = await fetch("/api/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ activity: spec, class_name: className, template_name: tmplName }),
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({ error: r.statusText }));
      setStatus(`export failed: ${err.error}`, "err");
      return;
    }
    const src = await r.text();
    downloadBlob(src, `${tmplName}.py`, "text/x-python");
    setStatus(`✔ Exported ${tmplName}.py`, "ok");
  });
}

// ── Activity lifecycle ───────────────────────────────────────────────

function newActivity(name) {
  if (State.activities[name]) {
    setStatus(`Activity "${name}" already exists`, "err");
    return;
  }
  State.activities[name] = {
    name,
    description: "",
    parameters: [],
    nodes: [],
    flows: [],
    sub_activities: {},  // populated on export from other activities
  };
  State.layout[name] = {};
  if (!State.topLevel) State.topLevel = name;
  State.current = name;
  render();
}

function deleteActivity(name) {
  if (Object.keys(State.activities).length <= 1) {
    setStatus("cannot delete last Activity", "err");
    return;
  }
  delete State.activities[name];
  delete State.layout[name];
  if (State.current === name) State.current = Object.keys(State.activities)[0];
  if (State.topLevel === name) State.topLevel = State.current;
  render();
}

function currentActivity() { return State.activities[State.current]; }

/** Build the top-level Activity with sub_activities populated. */
function topLevelSpec() {
  const top = State.activities[State.topLevel];
  if (!top) return null;
  const spec = JSON.parse(JSON.stringify(top));
  spec.sub_activities = {};
  for (const [name, a] of Object.entries(State.activities)) {
    if (name === State.topLevel) continue;
    const copy = JSON.parse(JSON.stringify(a));
    delete copy.sub_activities;
    spec.sub_activities[name] = copy;
  }
  return spec;
}

function loadFromJSON(spec) {
  State.activities = {};
  State.layout = {};
  State.activities[spec.name] = { ...spec, sub_activities: {} };
  State.layout[spec.name] = {};
  autoLayout(spec.name);

  for (const [subName, sub] of Object.entries(spec.sub_activities || {})) {
    State.activities[subName] = { ...sub, sub_activities: {} };
    State.layout[subName] = {};
    autoLayout(subName);
  }
  State.topLevel = spec.name;
  State.current = spec.name;
  State.selection = null;
  State.pending = null;
  render();
  setStatus(`loaded Activity "${spec.name}"`, "ok");
}

// ── Parameters ───────────────────────────────────────────────────────

function addParameter() {
  const name = prompt("Parameter id:", "");
  if (!name) return;
  const act = currentActivity();
  if (act.parameters.some(p => p.id === name)) {
    setStatus(`duplicate parameter id: ${name}`, "err");
    return;
  }
  act.parameters.push({ id: name, type: "Workspace", direction: "in" });
  ensureLayout(State.current, name);
  render();
}

// ── Rendering ────────────────────────────────────────────────────────

function render() {
  renderActivitiesSidebar();
  renderTopLevelPicker();
  renderParametersSidebar();
  renderCanvas();
  renderInspector();
}

function renderActivitiesSidebar() {
  const ul = document.getElementById("activities-list");
  ul.innerHTML = "";
  for (const name of Object.keys(State.activities)) {
    const li = document.createElement("li");
    if (name === State.current) li.classList.add("active");
    const tag = name === State.topLevel ? '<span class="meta">top</span>' : '';
    li.innerHTML = `<span>${escapeHtml(name)} ${tag}</span>`;
    const del = document.createElement("button");
    del.className = "del";
    del.textContent = "✕";
    del.title = "Delete Activity";
    del.addEventListener("click", (e) => { e.stopPropagation(); deleteActivity(name); });
    li.appendChild(del);
    li.addEventListener("click", () => { State.current = name; State.selection = null; render(); });
    ul.appendChild(li);
  }
}

function renderTopLevelPicker() {
  const sel = document.getElementById("top-level-picker");
  sel.innerHTML = "";
  for (const name of Object.keys(State.activities)) {
    const opt = document.createElement("option");
    opt.value = name; opt.textContent = `top: ${name}`;
    if (name === State.topLevel) opt.selected = true;
    sel.appendChild(opt);
  }
}

function renderParametersSidebar() {
  const ul = document.getElementById("parameters-list");
  ul.innerHTML = "";
  const act = currentActivity();
  if (!act) return;
  for (const p of act.parameters) {
    const li = document.createElement("li");
    li.innerHTML = `<span>${escapeHtml(p.id)} <span class="meta">${escapeHtml(p.direction)}:${escapeHtml(p.type)}</span></span>`;
    const del = document.createElement("button");
    del.className = "del"; del.textContent = "✕"; del.title = "Delete parameter";
    del.addEventListener("click", (e) => {
      e.stopPropagation();
      act.parameters = act.parameters.filter(x => x.id !== p.id);
      act.flows = act.flows.filter(f => endpointNode(f.source) !== p.id && endpointNode(f.target) !== p.id);
      render();
    });
    li.appendChild(del);
    li.addEventListener("click", () => { State.selection = { kind: "param", id: p.id }; render(); });
    ul.appendChild(li);
  }
}

function renderCanvas() {
  const svg = document.getElementById("canvas");
  const nodesLayer = document.getElementById("nodes-layer");
  const flowsLayer = document.getElementById("flows-layer");
  nodesLayer.innerHTML = "";
  flowsLayer.innerHTML = "";

  const act = currentActivity();
  if (!act) return;

  // Parameters along the top row — use layout if present, else auto-place.
  let paramX = 40;
  for (const p of act.parameters) {
    const pos = getLayout(State.current, p.id, paramX, 20);
    paramX = Math.max(paramX, pos.x) + 160;
    drawParamNode(nodesLayer, p, pos);
  }

  for (const n of act.nodes) {
    const pos = getLayout(State.current, n.id);
    drawRegularNode(nodesLayer, n, pos);
  }

  for (const f of act.flows) drawFlow(flowsLayer, f);
}

function drawParamNode(parent, p, pos) {
  const g = createSvg("g", { class: "node param", transform: `translate(${pos.x}, ${pos.y})` });
  if (State.selection?.kind === "param" && State.selection.id === p.id) g.classList.add("selected");
  g.dataset.id = p.id;
  g.dataset.kind = "param";
  g.appendChild(createSvg("rect", { class: "bg", width: 140, height: 38 }));
  g.appendChild(textEl(10, 16, p.id, "title"));
  g.appendChild(textEl(10, 30, `${p.direction}:${p.type}`, "subtitle"));

  // Input direction parameters are *sources* for wires (they feed nodes).
  // Out-params are *targets* (node output writes into them).
  const pinY = 19;
  if (p.direction === "in") g.appendChild(pinEl(140, pinY, "out", { nodeId: p.id, pinName: "", type: p.type }));
  else g.appendChild(pinEl(0, pinY, "in", { nodeId: p.id, pinName: "", type: p.type, required: false }));

  attachDrag(g, p.id);
  parent.appendChild(g);
}

function drawRegularNode(parent, node, pos) {
  const { inputs, outputs } = pinsForNode(node);
  const height = Math.max(50, 24 + Math.max(inputs.length, outputs.length) * 16);
  const width = 170;

  const g = createSvg("g", { class: `node kind-${node.kind}`, transform: `translate(${pos.x}, ${pos.y})` });
  if (State.selection?.kind === "node" && State.selection.id === node.id) g.classList.add("selected");
  g.dataset.id = node.id;
  g.dataset.kind = node.kind;

  g.appendChild(createSvg("rect", { class: "bg", width, height }));
  const label = node.kind === "Action" ? (node.config?.action_kind || "Action") : node.kind;
  g.appendChild(textEl(10, 16, node.id, "title"));
  g.appendChild(textEl(10, 30, label, "subtitle"));

  inputs.forEach((pin, i) => {
    g.appendChild(pinEl(0, 50 + i * 16, "in", { nodeId: node.id, pinName: pin.name, type: pin.type, required: pin.required }));
  });
  outputs.forEach((pin, i) => {
    g.appendChild(pinEl(width, 50 + i * 16, "out", { nodeId: node.id, pinName: pin.name, type: pin.type }));
  });

  attachDrag(g, node.id);
  parent.appendChild(g);
}

function drawFlow(parent, flow) {
  const src = endpointCoord(flow.source, "out");
  const tgt = endpointCoord(flow.target, "in");
  if (!src || !tgt) return;
  const mx = (src.x + tgt.x) / 2;
  const d = `M ${src.x} ${src.y} C ${mx} ${src.y}, ${mx} ${tgt.y}, ${tgt.x} ${tgt.y}`;
  const markerId = flow.kind === "ControlFlow" ? "arrow-dashed" : "arrow-solid";
  const path = createSvg("path", { class: `flow ${flow.kind}`, d, "marker-end": `url(#${markerId})` });
  path.addEventListener("click", (e) => {
    e.stopPropagation();
    if (confirm(`Delete flow ${flow.source} → ${flow.target}?`)) {
      const act = currentActivity();
      act.flows = act.flows.filter(x => x !== flow);
      render();
    }
  });
  parent.appendChild(path);
}

// Return actual pin lists for a node, including dynamic CallActivity /
// ExpansionRegion resolution against the referenced sub-Activity.
function pinsForNode(node) {
  // Actions + control nodes with static pins: look up in schema.
  const palette = findPaletteEntry(node);
  if (palette && !palette.dynamic_pins) {
    return {
      inputs: palette.input_pins || [],
      outputs: palette.output_pins || [],
    };
  }
  // CallActivity: mirror sub-Activity parameters.
  const subName = node.config?.activity;
  if (subName && State.activities[subName]) {
    const sub = State.activities[subName];
    if (node.kind === "CallActivity") {
      return {
        inputs: sub.parameters.filter(p => p.direction === "in")
                  .map(p => ({ name: p.id, type: p.type, required: true })),
        outputs: sub.parameters.filter(p => p.direction === "out")
                  .map(p => ({ name: p.id, type: p.type })),
      };
    }
    if (node.kind === "ExpansionRegion") {
      const itemParam = node.config?.item_param || "item";
      const resultParam = node.config?.result_param || "";
      const inputs = [];
      let itemType = null;
      for (const p of sub.parameters) {
        if (p.direction !== "in") continue;
        if (p.id === itemParam) { itemType = p.type; continue; }
        inputs.push({ name: p.id, type: p.type, required: true });
      }
      if (itemType) inputs.unshift({ name: "items", type: listTypeFor(itemType), required: true });
      const outputs = [];
      let resultType = null;
      for (const p of sub.parameters) {
        if (p.direction !== "out") continue;
        if (p.id === resultParam) { resultType = p.type; continue; }
        outputs.push({ name: p.id, type: p.type });
      }
      if (resultType) outputs.unshift({ name: "results", type: listTypeFor(resultType) });
      return { inputs, outputs };
    }
  }
  return { inputs: [], outputs: [] };
}

function listTypeFor(t) {
  if (t === "BranchSpec") return "BranchSpecList";
  if (t === "String") return "StringList";
  return "StringList";  // mirrors control.py fallback
}

function findPaletteEntry(node) {
  if (!State.schema) return null;
  if (node.kind === "Action") {
    return State.schema.actions.find(a => a.action_kind === node.config?.action_kind) || null;
  }
  return State.schema.control_nodes.find(c => c.kind === node.kind) || null;
}

function pinEl(x, y, dir, info) {
  const g = createSvg("g", { class: `pin ${info.required === false ? "optional" : ""}`,
                             transform: `translate(${x}, ${y})` });
  g.appendChild(createSvg("circle", { cx: 0, cy: 0 }));
  const labelX = dir === "in" ? 10 : -10;
  const anchor = dir === "in" ? "start" : "end";
  const t = createSvg("text", { x: labelX, y: 4, "text-anchor": anchor });
  t.textContent = info.pinName ? `${info.pinName}:${info.type}` : info.type;
  g.appendChild(t);
  g.addEventListener("mousedown", (e) => { e.stopPropagation(); onPinMouseDown(dir, info); });
  g.addEventListener("mouseup",   (e) => { e.stopPropagation(); onPinMouseUp(dir, info); });
  return g;
}

// ── Pin interaction: draw a wire ────────────────────────────────────

function onPinMouseDown(dir, info) {
  if (dir !== "out") {
    setStatus("drag from an output pin", "err");
    return;
  }
  State.pending = { dir, info };
  const svg = document.getElementById("canvas");
  svg.addEventListener("mousemove", onPendingMouseMove);
  svg.addEventListener("mouseup", onPendingMouseUp);
}

function onPinMouseUp(dir, info) {
  if (!State.pending) return;
  if (dir !== "in") return;
  const src = State.pending.info;
  const tgt = info;
  State.pending = null;
  document.getElementById("pending-wire").style.display = "none";

  const srcType = src.type, tgtType = tgt.type;
  // Determine flow kind.  If either end is explicitly Void and the *pin name* is empty
  // (bare parameter ref), treat as ObjectFlow — ControlFlow is user-selected via inspector.
  let kind = "ObjectFlow";
  if (srcType === "Void" && tgtType === "Void") kind = "ControlFlow";
  else if (srcType !== tgtType) {
    setStatus(`type mismatch: ${srcType} → ${tgtType}`, "err");
    return;
  }

  const act = currentActivity();
  const srcEndpoint = src.pinName ? `${src.nodeId}.${src.pinName}` : src.nodeId;
  const tgtEndpoint = tgt.pinName ? `${tgt.nodeId}.${tgt.pinName}` : tgt.nodeId;
  if (act.flows.some(f => f.source === srcEndpoint && f.target === tgtEndpoint)) {
    setStatus("wire already exists", "err");
    return;
  }
  act.flows.push({ kind, source: srcEndpoint, target: tgtEndpoint });
  render();
}

function onPendingMouseMove(e) {
  if (!State.pending) return;
  const svg = document.getElementById("canvas");
  const pt = svgPoint(svg, e);
  const anchor = endpointCoord(
    State.pending.info.pinName
      ? `${State.pending.info.nodeId}.${State.pending.info.pinName}`
      : State.pending.info.nodeId,
    "out");
  if (!anchor) return;
  const path = document.getElementById("pending-wire");
  const mx = (anchor.x + pt.x) / 2;
  path.setAttribute("d", `M ${anchor.x} ${anchor.y} C ${mx} ${anchor.y}, ${mx} ${pt.y}, ${pt.x} ${pt.y}`);
  path.style.display = "";
}

function onPendingMouseUp() {
  State.pending = null;
  document.getElementById("pending-wire").style.display = "none";
  const svg = document.getElementById("canvas");
  svg.removeEventListener("mousemove", onPendingMouseMove);
  svg.removeEventListener("mouseup", onPendingMouseUp);
}

// ── Dragging ─────────────────────────────────────────────────────────

function attachDrag(g, id) {
  g.addEventListener("mousedown", (e) => {
    if (e.target.closest(".pin")) return;
    e.stopPropagation();
    const svg = document.getElementById("canvas");
    const start = svgPoint(svg, e);
    const pos = getLayout(State.current, id);
    const startPos = { ...pos };
    const onMove = (ev) => {
      const pt = svgPoint(svg, ev);
      pos.x = startPos.x + (pt.x - start.x);
      pos.y = startPos.y + (pt.y - start.y);
      setLayout(State.current, id, pos);
      // re-render just the transforms: cheap full render is fine for v1.
      render();
    };
    const onUp = () => {
      svg.removeEventListener("mousemove", onMove);
      svg.removeEventListener("mouseup", onUp);
    };
    svg.addEventListener("mousemove", onMove);
    svg.addEventListener("mouseup", onUp);

    // Select the node on mousedown (cheap — render() below will apply class).
    const kind = g.dataset.kind === "param" ? "param" : "node";
    State.selection = { kind, id };
    render();
  });
}

// ── Inspector ────────────────────────────────────────────────────────

function renderInspector() {
  const root = document.getElementById("inspector");
  if (!State.selection) { root.innerHTML = `<p class="hint">Click a node or parameter to edit it.</p>`; return; }

  const act = currentActivity();
  if (State.selection.kind === "param") {
    const p = act.parameters.find(x => x.id === State.selection.id);
    if (!p) { State.selection = null; root.innerHTML = ""; return; }
    root.innerHTML = `
      <h4>Parameter: ${escapeHtml(p.id)}</h4>
      <label>Type</label><select id="p-type">${typeOptions(p.type)}</select>
      <label>Direction</label>
      <select id="p-dir">
        <option value="in" ${p.direction === "in" ? "selected" : ""}>in</option>
        <option value="out" ${p.direction === "out" ? "selected" : ""}>out</option>
      </select>
      <button id="p-del">Delete parameter</button>`;
    document.getElementById("p-type").addEventListener("change", (e) => { p.type = e.target.value; render(); });
    document.getElementById("p-dir").addEventListener("change", (e) => { p.direction = e.target.value; render(); });
    document.getElementById("p-del").addEventListener("click", () => {
      act.parameters = act.parameters.filter(x => x !== p);
      State.selection = null; render();
    });
    return;
  }

  const node = act.nodes.find(n => n.id === State.selection.id);
  if (!node) { State.selection = null; root.innerHTML = ""; return; }
  const palette = findPaletteEntry(node);

  let cfg = `<label>ID</label><input id="n-id" value="${escapeHtml(node.id)}">`;
  const configSchema = (palette && palette.config_schema) || {};
  for (const [key, info] of Object.entries(configSchema)) {
    const val = node.config?.[key] ?? info.default ?? "";
    if (info.enum) {
      const opts = info.enum.map(v => `<option value="${v}" ${v === val ? "selected" : ""}>${v}</option>`).join("");
      cfg += `<label>${escapeHtml(key)}</label><select data-cfg="${escapeHtml(key)}">${opts}</select>`;
    } else if (key === "activity") {
      const opts = Object.keys(State.activities)
        .filter(n => n !== State.current)
        .map(n => `<option value="${escapeHtml(n)}" ${n === val ? "selected" : ""}>${escapeHtml(n)}</option>`).join("");
      cfg += `<label>${escapeHtml(key)} <span class="meta">${escapeHtml(info.hint || "")}</span></label><select data-cfg="${escapeHtml(key)}"><option value="">—</option>${opts}</select>`;
    } else {
      cfg += `<label>${escapeHtml(key)} <span class="meta">${escapeHtml(info.hint || "")}</span></label><input data-cfg="${escapeHtml(key)}" value="${escapeHtml(String(val))}">`;
    }
  }

  // Known action configs that have string templates (e.g. git_commit):
  // expose any top-level string keys already present in the node's config
  // that aren't in the schema, so nothing is lost on round-trip.
  for (const [key, val] of Object.entries(node.config || {})) {
    if (key === "action_kind") continue;
    if (key in configSchema) continue;
    cfg += `<label>${escapeHtml(key)}</label><input data-cfg="${escapeHtml(key)}" value="${escapeHtml(String(val))}">`;
  }

  const pinsHtml = (() => {
    const { inputs, outputs } = pinsForNode(node);
    const fmt = (ps) => ps.map(p => `<li>${escapeHtml(p.name)}: ${escapeHtml(p.type)}${p.required === false ? " (optional)" : ""}</li>`).join("") || "<li class='hint'>none</li>";
    return `<div class="pins"><strong>Inputs</strong><ul>${fmt(inputs)}</ul><strong>Outputs</strong><ul>${fmt(outputs)}</ul></div>`;
  })();

  root.innerHTML = `<h4>${escapeHtml(node.kind)}${node.config?.action_kind ? ` <span class="meta">${escapeHtml(node.config.action_kind)}</span>` : ""}</h4>${cfg}${pinsHtml}<button id="n-del">Delete node</button>`;

  document.getElementById("n-id").addEventListener("change", (e) => {
    const newId = e.target.value.trim();
    if (!newId || act.nodes.some(n => n !== node && n.id === newId)) {
      setStatus("invalid or duplicate id", "err"); render(); return;
    }
    // Rewrite flows that reference the old id.
    for (const f of act.flows) {
      if (endpointNode(f.source) === node.id) f.source = replaceNodeInEndpoint(f.source, newId);
      if (endpointNode(f.target) === node.id) f.target = replaceNodeInEndpoint(f.target, newId);
    }
    const layoutPos = State.layout[State.current][node.id];
    delete State.layout[State.current][node.id];
    if (layoutPos) State.layout[State.current][newId] = layoutPos;
    node.id = newId;
    State.selection = { kind: "node", id: newId };
    render();
  });

  for (const el of root.querySelectorAll("[data-cfg]")) {
    el.addEventListener("change", (e) => {
      const key = e.target.dataset.cfg;
      const v = e.target.value;
      node.config = node.config || {};
      if (v === "" || v === null) delete node.config[key];
      else node.config[key] = v;
      render();
    });
  }

  document.getElementById("n-del").addEventListener("click", () => {
    act.nodes = act.nodes.filter(x => x !== node);
    act.flows = act.flows.filter(f => endpointNode(f.source) !== node.id && endpointNode(f.target) !== node.id);
    delete State.layout[State.current][node.id];
    State.selection = null; render();
  });
}

function typeOptions(selected) {
  return State.schema.types.map(t =>
    `<option value="${t.value}" ${t.value === selected ? "selected" : ""}>${t.value}</option>`
  ).join("");
}

// ── Layout helpers ───────────────────────────────────────────────────

function ensureLayout(activityName, nodeId) {
  const la = State.layout[activityName] || (State.layout[activityName] = {});
  if (!la[nodeId]) {
    const count = Object.keys(la).length;
    la[nodeId] = { x: 60 + (count % 5) * 200, y: 120 + Math.floor(count / 5) * 100 };
  }
}

function getLayout(activityName, nodeId, defaultX = 60, defaultY = 120) {
  ensureLayout(activityName, nodeId);
  return State.layout[activityName][nodeId];
}

function setLayout(activityName, nodeId, pos) {
  State.layout[activityName][nodeId] = pos;
}

function autoLayout(activityName) {
  const a = State.activities[activityName];
  const la = State.layout[activityName] = {};
  let px = 40;
  for (const p of a.parameters) {
    la[p.id] = { x: px, y: 20 }; px += 160;
  }
  a.nodes.forEach((n, i) => {
    la[n.id] = { x: 60 + (i % 5) * 200, y: 120 + Math.floor(i / 5) * 110 };
  });
}

// Coordinate of a pin on the canvas, for drawing flows.
function endpointCoord(endpoint, dir) {
  const [nodeId, pinName] = endpoint.includes(".") ? endpoint.split(".", 2) : [endpoint, null];
  const act = currentActivity();
  const param = act.parameters.find(p => p.id === nodeId);
  if (param) {
    const pos = getLayout(State.current, nodeId);
    return param.direction === "in"
      ? { x: pos.x + 140, y: pos.y + 19 }
      : { x: pos.x,         y: pos.y + 19 };
  }
  const node = act.nodes.find(n => n.id === nodeId);
  if (!node) return null;
  const pos = getLayout(State.current, nodeId);
  const { inputs, outputs } = pinsForNode(node);
  const list = dir === "out" ? outputs : inputs;
  const idx = pinName ? list.findIndex(p => p.name === pinName) : 0;
  const y = 50 + Math.max(0, idx) * 16;
  return dir === "out" ? { x: pos.x + 170, y: pos.y + y } : { x: pos.x, y: pos.y + y };
}

function endpointNode(endpoint) {
  return endpoint.includes(".") ? endpoint.split(".", 1)[0] : endpoint;
}

function replaceNodeInEndpoint(endpoint, newNode) {
  if (!endpoint.includes(".")) return newNode;
  const pin = endpoint.split(".", 2)[1];
  return `${newNode}.${pin}`;
}

// ── Mermaid preview (pure JS, mirrors exporters.to_mermaid) ─────────

function toMermaid(activity) {
  const lines = ["flowchart TD", `    %% ${activity.name}`];
  for (const p of activity.parameters || []) {
    lines.push(p.direction === "in"
      ? `    ${p.id}([${p.id}: ${p.type}])`
      : `    ${p.id}[/${p.id}: ${p.type}/]`);
  }
  const shape = { InitialNode: ["((", "))"], FinalNode: ["(((", ")))"],
                  DecisionNode: ["{", "}"], ForkNode: ["[/", "/]"],
                  JoinNode: ["[\\\\", "\\\\]"], ExpansionRegion: ["[[", "]]"],
                  CallActivity: ["[(", ")]"] };
  for (const n of activity.nodes || []) {
    const label = n.kind === "Action" ? `"${n.id}<br/>${n.config?.action_kind || ""}"` : `"${n.id}<br/>${n.kind}"`;
    const [so, sc] = shape[n.kind] || ["[", "]"];
    lines.push(`    ${n.id}${so}${label}${sc}`);
  }
  for (const f of activity.flows || []) {
    const arrow = f.kind === "ObjectFlow" ? "-->" : "-.->";
    lines.push(`    ${f.source.replace(/\./g, "_")} ${arrow} ${f.target.replace(/\./g, "_")}`);
  }
  return lines.join("\n");
}

// ── Modal helpers ────────────────────────────────────────────────────

function showModal(title, bodyHTML) {
  const dlg = document.getElementById("modal");
  document.getElementById("modal-title").textContent = title;
  document.getElementById("modal-body").innerHTML = bodyHTML;
  const ok = document.getElementById("modal-ok");
  ok.replaceWith(ok.cloneNode(true));   // drop prior click handlers
  dlg.showModal();
}

function showModalPrompt(title, bodyHTML, onOk) {
  const dlg = document.getElementById("modal");
  document.getElementById("modal-title").textContent = title;
  document.getElementById("modal-body").innerHTML = bodyHTML;
  const ok = document.getElementById("modal-ok");
  const fresh = ok.cloneNode(true);
  ok.replaceWith(fresh);
  fresh.addEventListener("click", () => { try { onOk(); } finally { dlg.close(); } });
  dlg.showModal();
}

// ── Utilities ────────────────────────────────────────────────────────

function setStatus(msg, cls = "") {
  const bar = document.getElementById("status-bar");
  bar.textContent = msg;
  bar.className = cls;
}

function createSvg(tag, attrs) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  if (attrs) for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}

function textEl(x, y, text, cls) {
  const t = createSvg("text", { x, y, class: cls });
  t.textContent = text;
  return t;
}

function svgPoint(svg, evt) {
  const pt = svg.createSVGPoint();
  pt.x = evt.clientX; pt.y = evt.clientY;
  return pt.matrixTransform(svg.getScreenCTM().inverse());
}

function downloadBlob(data, filename, mime) {
  const blob = new Blob([data], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, c =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[c]));
}
