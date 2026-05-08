/* Fiction Pipeline Dashboard — app.js */

const POLL_MS = 3000;
let currentProject = "";
let selectedStage = null;
let pollTimer = null;
let dagNodes = [];

// ── API helpers ──

async function api(path) {
  const r = await fetch(path);
  return r.json();
}

// ── Init ──

document.addEventListener("DOMContentLoaded", () => {
  loadProjects();
  document.getElementById("projectSelect").addEventListener("change", onProjectChange);
  initDagCanvas();
});

async function loadProjects() {
  const data = await api("/api/projects");
  const sel = document.getElementById("projectSelect");
  sel.innerHTML = '<option value="">-- 选择项目 --</option>';
  for (const p of data.projects) {
    const opt = document.createElement("option");
    opt.value = p;
    opt.textContent = p;
    sel.appendChild(opt);
  }
  if (data.projects.length === 1) {
    sel.value = data.projects[0];
    onProjectChange();
  }
}

function onProjectChange() {
  const sel = document.getElementById("projectSelect");
  currentProject = sel.value;
  selectedStage = null;
  if (pollTimer) clearInterval(pollTimer);
  if (!currentProject) {
    clearAll();
    return;
  }
  refresh();
  pollTimer = setInterval(refresh, POLL_MS);
}

function clearAll() {
  document.getElementById("summaryCards").innerHTML = "";
  document.getElementById("stageTableBody").innerHTML = "";
  document.getElementById("logContent").innerHTML = "";
  document.getElementById("fileList").innerHTML = "";
  document.getElementById("fileContent").innerHTML = '<div class="placeholder">点击 stage 或文件查看内容</div>';
  document.getElementById("filePanelTitle").textContent = "文件浏览 — 选择一个 stage";
  document.getElementById("statusBadge").style.display = "none";
  document.getElementById("currentInfo").textContent = "";
  dagNodes = [];
  drawDag();
}

// ── Refresh ──

async function refresh() {
  if (!currentProject) return;
  const [state, manifest, locks, log] = await Promise.all([
    api(`/api/project/${currentProject}/state`),
    api(`/api/project/${currentProject}/manifest`),
    api(`/api/project/${currentProject}/locks`),
    api(`/api/project/${currentProject}/log`),
  ]);
  renderSummary(state);
  renderStageTable(manifest, locks, state);
  renderLog(log.log);
  renderDag(manifest, locks, state);
  if (selectedStage) renderFileList(manifest, selectedStage);
}

// ── Summary cards ──

function renderSummary(state) {
  if (!state) return;
  const el = document.getElementById("summaryCards");
  const badge = document.getElementById("statusBadge");
  const info = document.getElementById("currentInfo");

  const statusMap = {
    initialized: "pending",
    running: "running",
    paused: "blocked",
    completed: "completed",
  };
  const cls = statusMap[state.status] || "pending";
  badge.textContent = state.status;
  badge.className = "status-badge " + cls;
  badge.style.display = "inline";

  info.textContent = `当前: ${state.current_stage || "-"} · 第 ${state.current_chapter || "-"} 章`;

  el.innerHTML = [
    card("项目", state.story_name || "-"),
    card("状态", state.status || "-"),
    card("当前阶段", state.current_stage || "-"),
    card("当前章节", state.current_chapter || "-"),
    card("冻结章节", (state.frozen_chapters || []).length),
    card("已完成", (state.completed_stages || []).length),
  ].join("");
}

function card(label, value) {
  return `<div class="summary-card"><div class="label">${label}</div><div class="value">${value}</div></div>`;
}

// ── Stage table ──

function renderStageTable(manifest, locks, state) {
  if (!manifest) return;
  const tbody = document.getElementById("stageTableBody");
  const completed = new Set(state?.completed_stages || []);
  const approved = state?.approved || {};
  const currentStage = state?.current_stage || "";

  tbody.innerHTML = manifest.stages.map(s => {
    const lockKey = `lock_${s.id}`;
    const lock = locks?.locks?.[lockKey];
    let status = "pending";
    if (completed.has(s.id) || lock?.status === "completed") status = "completed";
    else if (lock?.status === "running" || currentStage === s.id) status = "running";
    else if (s.depends_on?.length && !s.depends_on.every(d => completed.has(d))) status = "blocked";

    const sel = selectedStage === s.id ? " selected" : "";
    return `<tr class="${sel}" data-stage="${s.id}">
      <td class="stage-id" onclick="selectStage('${s.id}')">${s.id}</td>
      <td>${s.model_profile}</td>
      <td><span class="status-badge ${status}">${status}</span></td>
      <td class="dep-list">${(s.depends_on || []).join(", ") || "—"}</td>
      <td class="dep-list">${(s.parallel_with || []).join(", ") || "—"}</td>
    </tr>`;
  }).join("");
}

// ── Stage selection → file list ──

function selectStage(stageId) {
  selectedStage = stageId;
  document.querySelectorAll(".stage-table tr").forEach(r => {
    r.classList.toggle("selected", r.dataset.stage === stageId);
  });
  fetch(`/api/project/${currentProject}/manifest`)
    .then(r => r.json())
    .then(manifest => renderFileList(manifest, stageId));
  drawDag();
}

function renderFileList(manifest, stageId) {
  const stage = manifest?.stages?.find(s => s.id === stageId);
  if (!stage) return;
  const el = document.getElementById("fileList");
  document.getElementById("filePanelTitle").textContent = `文件浏览 — ${stageId}`;

  let html = "";
  for (const f of stage.reads || []) {
    html += `<span class="file-item reads" onclick="loadFile('${esc(f)}')" title="reads">R: ${f}</span>`;
  }
  for (const f of stage.writes || []) {
    html += `<span class="file-item writes" onclick="loadFile('${esc(f)}')" title="writes">W: ${f}</span>`;
  }
  el.innerHTML = html;
}

function esc(s) {
  return s.replace(/'/g, "\\'");
}

async function loadFile(path) {
  document.querySelectorAll(".file-item").forEach(el => {
    el.classList.toggle("active", el.textContent.includes(path));
  });
  const data = await api(`/api/project/${currentProject}/file?path=${encodeURIComponent(path)}`);
  const el = document.getElementById("fileContent");
  if (data.error) {
    el.textContent = data.error;
    return;
  }
  if (data.ext === "json") {
    try {
      el.textContent = JSON.stringify(JSON.parse(data.content), null, 2);
    } catch {
      el.textContent = data.content;
    }
  } else {
    el.textContent = data.content;
  }
}

// ── Log ──

function renderLog(text) {
  const el = document.getElementById("logContent");
  if (!text) {
    el.innerHTML = '<div style="color:var(--text2)">暂无日志</div>';
    return;
  }
  const wasAtBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 20;
  const lines = text.split("\n").filter(l => l.trim());
  el.innerHTML = lines.map(l => {
    const m = l.match(/^\[([^\]]+)\]\s+(\S+)\s*-\s*(.+?)\s*-\s*(.+)$/);
    if (m) {
      const resultCls = m[4].toLowerCase().includes("fail") ? "result-fail" : "result-ok";
      return `<div class="log-line"><span class="ts">[${m[1]}]</span> <span class="role">${m[2]}</span> - ${m[3]} - <span class="${resultCls}">${m[4]}</span></div>`;
    }
    return `<div class="log-line">${escHtml(l)}</div>`;
  }).join("");
  if (wasAtBottom) el.scrollTop = el.scrollHeight;
}

function escHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// ── DAG ──

let dagCanvas, dagCtx;

function initDagCanvas() {
  dagCanvas = document.getElementById("dagCanvas");
  dagCtx = dagCanvas.getContext("2d");
  const ro = new ResizeObserver(() => {
    const rect = dagCanvas.parentElement.getBoundingClientRect();
    dagCanvas.width = rect.width * devicePixelRatio;
    dagCanvas.height = rect.height * devicePixelRatio;
    dagCtx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);
    drawDag();
  });
  ro.observe(dagCanvas.parentElement);
}

function renderDag(manifest, locks, state) {
  if (!manifest) return;
  const completed = new Set(state?.completed_stages || []);
  const currentStage = state?.current_stage || "";

  dagNodes = manifest.stages.map(s => {
    const lockKey = `lock_${s.id}`;
    const lock = locks?.locks?.[lockKey];
    let status = "pending";
    if (completed.has(s.id) || lock?.status === "completed") status = "completed";
    else if (lock?.status === "running" || currentStage === s.id) status = "running";
    else if (s.depends_on?.length && !s.depends_on.every(d => completed.has(d))) status = "blocked";
    return { ...s, status };
  });
  drawDag();
}

function drawDag() {
  if (!dagCtx) return;
  const w = dagCanvas.width / devicePixelRatio;
  const h = dagCanvas.height / devicePixelRatio;
  dagCtx.clearRect(0, 0, w, h);

  if (!dagNodes.length) {
    dagCtx.fillStyle = "#8b92a8";
    dagCtx.font = "14px sans-serif";
    dagCtx.textAlign = "center";
    dagCtx.fillText("选择项目以查看依赖图", w / 2, h / 2);
    return;
  }

  // Layout: compute layers by dependency depth
  const layers = computeLayers(dagNodes);
  const layerCount = layers.length;
  const nodeW = 110;
  const nodeH = 36;
  const gapX = 40;
  const gapY = 16;
  const totalW = layerCount * nodeW + (layerCount - 1) * gapX;
  const startX = Math.max(20, (w - totalW) / 2);

  // Position nodes
  const pos = {};
  for (let li = 0; li < layers.length; li++) {
    const layer = layers[li];
    const totalH = layer.length * nodeH + (layer.length - 1) * gapY;
    const startY = Math.max(20, (h - totalH) / 2);
    for (let ni = 0; ni < layer.length; ni++) {
      const node = layer[ni];
      pos[node.id] = {
        x: startX + li * (nodeW + gapX),
        y: startY + ni * (nodeH + gapY),
        node,
      };
    }
  }

  // Draw edges
  for (const node of dagNodes) {
    const from = pos[node.id];
    if (!from) continue;
    for (const dep of node.depends_on || []) {
      const to = pos[dep];
      if (!to) continue;
      drawEdge(
        to.x + nodeW, to.y + nodeH / 2,
        from.x, from.y + nodeH / 2,
        "normal"
      );
    }
    for (const par of node.parallel_with || []) {
      const other = pos[par];
      if (!other) continue;
      // draw parallel edge (lighter, dashed)
      const fromY = from.y + nodeH / 2;
      const otherY = other.y + nodeH / 2;
      const midX = Math.max(from.x, other.x) + nodeW + 20;
      drawCurve(from.x + nodeW, fromY, midX, fromY, midX, otherY, other.x + nodeW, otherY, true);
    }
  }

  // Draw nodes
  for (const id in pos) {
    const { x, y, node } = pos[id];
    drawNode(x, y, nodeW, nodeH, node);
  }
}

function computeLayers(nodes) {
  const nodeMap = {};
  for (const n of nodes) nodeMap[n.id] = n;
  const depth = {};
  function getDepth(id) {
    if (depth[id] !== undefined) return depth[id];
    const n = nodeMap[id];
    if (!n || !n.depends_on?.length) return (depth[id] = 0);
    return (depth[id] = 1 + Math.max(...n.depends_on.map(getDepth)));
  }
  for (const n of nodes) getDepth(n.id);
  const maxD = Math.max(...Object.values(depth), 0);
  const layers = Array.from({ length: maxD + 1 }, () => []);
  for (const n of nodes) layers[depth[n.id]].push(n);
  return layers;
}

function drawEdge(x1, y1, x2, y2, type) {
  dagCtx.beginPath();
  dagCtx.strokeStyle = "#3a3f55";
  dagCtx.lineWidth = 1.5;
  const cx = (x1 + x2) / 2;
  dagCtx.moveTo(x1, y1);
  dagCtx.bezierCurveTo(cx, y1, cx, y2, x2, y2);
  dagCtx.stroke();
  // arrowhead
  const angle = Math.atan2(y2 - y1, x2 - cx);
  dagCtx.beginPath();
  dagCtx.fillStyle = "#3a3f55";
  dagCtx.moveTo(x2, y2);
  dagCtx.lineTo(x2 - 8 * Math.cos(angle - 0.4), y2 - 8 * Math.sin(angle - 0.4));
  dagCtx.lineTo(x2 - 8 * Math.cos(angle + 0.4), y2 - 8 * Math.sin(angle + 0.4));
  dagCtx.fill();
}

function drawCurve(x1, y1, cx1, cy1, cx2, cy2, x2, y2, dashed) {
  dagCtx.beginPath();
  dagCtx.strokeStyle = "#4a4f65";
  dagCtx.lineWidth = 1;
  if (dashed) dagCtx.setLineDash([4, 4]);
  dagCtx.moveTo(x1, y1);
  dagCtx.bezierCurveTo(cx1, cy1, cx2, cy2, x2, y2);
  dagCtx.stroke();
  dagCtx.setLineDash([]);
}

function drawNode(x, y, w, h, node) {
  const colors = {
    pending: { bg: "#242836", border: "#6b7280", text: "#8b92a8" },
    running: { bg: "#1a2744", border: "#5b8def", text: "#5b8def" },
    completed: { bg: "#1a2e24", border: "#4caf7d", text: "#4caf7d" },
    blocked: { bg: "#2e2618", border: "#e8a44a", text: "#e8a44a" },
  };
  const c = colors[node.status] || colors.pending;
  const isSelected = selectedStage === node.id;

  // glow for selected
  if (isSelected) {
    dagCtx.shadowColor = c.border;
    dagCtx.shadowBlur = 10;
  }

  // rounded rect
  const r = 6;
  dagCtx.beginPath();
  dagCtx.moveTo(x + r, y);
  dagCtx.lineTo(x + w - r, y);
  dagCtx.arcTo(x + w, y, x + w, y + r, r);
  dagCtx.lineTo(x + w, y + h - r);
  dagCtx.arcTo(x + w, y + h, x + w - r, y + h, r);
  dagCtx.lineTo(x + r, y + h);
  dagCtx.arcTo(x, y + h, x, y + h - r, r);
  dagCtx.lineTo(x, y + r);
  dagCtx.arcTo(x, y, x + r, y, r);
  dagCtx.closePath();
  dagCtx.fillStyle = c.bg;
  dagCtx.fill();
  dagCtx.strokeStyle = isSelected ? c.text : c.border;
  dagCtx.lineWidth = isSelected ? 2 : 1;
  dagCtx.stroke();

  dagCtx.shadowColor = "transparent";
  dagCtx.shadowBlur = 0;

  // text
  dagCtx.fillStyle = c.text;
  dagCtx.font = `${isSelected ? "600" : "500"} 12px sans-serif`;
  dagCtx.textAlign = "center";
  dagCtx.textBaseline = "middle";
  dagCtx.fillText(node.id, x + w / 2, y + h / 2);

  // clickable area
  node._hitBox = { x, y, w, h };
}

// Canvas click → select stage
document.addEventListener("click", e => {
  if (!dagCanvas) return;
  const rect = dagCanvas.getBoundingClientRect();
  const mx = e.clientX - rect.left;
  const my = e.clientY - rect.top;
  for (const node of dagNodes) {
    const hb = node._hitBox;
    if (hb && mx >= hb.x && mx <= hb.x + hb.w && my >= hb.y && my <= hb.y + hb.h) {
      selectStage(node.id);
      return;
    }
  }
});
