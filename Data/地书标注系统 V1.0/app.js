(function () {
  "use strict";

  const UI_CONFIG = {
    storageKey: "dishu_group_label_session_v5", // 升级以防旧缓存冲突
    zoomMin: 0.5, zoomMax: 2.0, zoomStep: 0.1,
    atomicGapPx: 3, atomicPaddingX: 0, atomicPaddingY: 0,
    atomicMinWidthPx: 10, atomicDisplayHeightPx: 60, atomicMinHeightPx: 24,
    atomicSummaryRowHeightPx: 20, atomicSummaryCharWidthPx: 7,
    levelRowHeightPx: 30, groupBoxHeightPx: 28, groupBoxPaddingX: 4, groupBoxMinWidthPx: 8,
    summaryCharWidthPx: 10,
    selectionAlertNonContinuous: "所选对象不连续，已撤销本次选择。"
  };

  const manifestRoot = window.SEGMENTS_MANIFEST;
  const configRoot = window.ANNOTATION_CONFIG;

  if (!manifestRoot || !Array.isArray(manifestRoot.segments)) return alert("未检测到有效的 data/segments_manifest.js");
  if (!configRoot || !Array.isArray(configRoot.tasks)) return alert("未检测到有效的 data/config.js");

  const allSegmentsRaw = manifestRoot.segments.slice();
  const allNormalizedSegments = allSegmentsRaw
    .map(normalizeSegment)
    .sort((a, b) => a.global_order - b.global_order);

  const taskById = new Map(configRoot.tasks.map(t => [t.task_id, t]));
  let uniquePages = []; // 存储包含 L/R 的复合页面信息

  const state = {
    session: { studentId: "", studentName: "", pageStartKey: null, pageEndKey: null },
    zoom: 1.0,
    mode: "grouping",
    currentTaskId: configRoot.tasks[0]?.task_id || null,
    visibleSegments: [], visibleSegmentById: new Map(), lineMap: new Map(), lineOrder: [],
    groups: [], annotations: [],
    selectionRange: null, currentTargetId: null,
    dragSelection: { active: false, startOrder: null, currentOrder: null, moved: false, justFinished: false }
  };

  const dom = {
    loginScreen: document.getElementById("loginScreen"), mainScreen: document.getElementById("mainScreen"),
    studentIdInput: document.getElementById("studentIdInput"), studentNameInput: document.getElementById("studentNameInput"),
    pageStartInput: document.getElementById("pageStartInput"), pageEndInput: document.getElementById("pageEndInput"),
    startBtn: document.getElementById("startBtn"), restoreSessionBtn: document.getElementById("restoreSessionBtn"),
    studentIdLabel: document.getElementById("studentIdLabel"), studentNameLabel: document.getElementById("studentNameLabel"),
    pageRangeLabel: document.getElementById("pageRangeLabel"), currentPageLabel: document.getElementById("currentPageLabel"),
    modeGroupingBtn: document.getElementById("modeGroupingBtn"), modeLabelingBtn: document.getElementById("modeLabelingBtn"),
    labelingTools: document.getElementById("labelingTools"), taskSelect: document.getElementById("taskSelect"),
    zoomOutBtn: document.getElementById("zoomOutBtn"), zoomInBtn: document.getElementById("zoomInBtn"), zoomLabel: document.getElementById("zoomLabel"),
    exportJsonBtn: document.getElementById("exportJsonBtn"), importFileInput: document.getElementById("importFileInput"),
    modeHelpText: document.getElementById("modeHelpText"), rowsRoot: document.getElementById("rowsRoot"),
    selectionInfo: document.getElementById("selectionInfo"), labelingPanel: document.getElementById("labelingPanel"),
    taskMeta: document.getElementById("taskMeta"), taskEditorRoot: document.getElementById("taskEditorRoot"),
    clearCurrentLabelBtn: document.getElementById("clearCurrentLabelBtn"), progressOverlay: document.getElementById("progressOverlay")
  };

  init();

  function init() {
    initPageSelects();
    initTaskSelect();
    bindEvents();
  }

  // 1. 重构页码生成逻辑：将L和R剥离成独立选项
  function initPageSelects() {
    const pageMap = new Map();
    allNormalizedSegments.forEach(s => {
        const key = `${s.page_no}_${s.side}`;
        if (!pageMap.has(key)) {
            pageMap.set(key, { page_no: s.page_no, side: s.side, key });
        }
    });
    uniquePages = Array.from(pageMap.values()).sort((a, b) => {
        if (a.page_no !== b.page_no) return a.page_no - b.page_no;
        return String(a.side).localeCompare(String(b.side)); // 保证 L 在 R 之前
    });

    dom.pageStartInput.innerHTML = ""; dom.pageEndInput.innerHTML = "";
    uniquePages.forEach(p => {
        const text = `第 ${p.page_no} 页 - ${p.side === 'L' ? '左' : '右'} (${p.side})`;
        dom.pageStartInput.appendChild(new Option(text, p.key));
        dom.pageEndInput.appendChild(new Option(text, p.key));
    });
    if (uniquePages.length > 0) {
        dom.pageStartInput.value = uniquePages[0].key;
        dom.pageEndInput.value = uniquePages[uniquePages.length - 1].key;
    }
  }

  function bindEvents() {
    dom.startBtn.addEventListener("click", startSessionFromInputs);
    dom.restoreSessionBtn.addEventListener("click", restoreSessionAndEnter);
    dom.modeGroupingBtn.addEventListener("click", () => setMode("grouping"));
    dom.modeLabelingBtn.addEventListener("click", () => setMode("labeling"));

    dom.taskSelect.addEventListener("change", () => {
      state.currentTaskId = dom.taskSelect.value;
      persistState(); refreshSidePanel(); rerenderAll();
    });

    dom.zoomInBtn.addEventListener("click", () => { state.zoom = clamp(round2(state.zoom + UI_CONFIG.zoomStep), UI_CONFIG.zoomMin, UI_CONFIG.zoomMax); persistState(); rerenderAll(); });
    dom.zoomOutBtn.addEventListener("click", () => { state.zoom = clamp(round2(state.zoom - UI_CONFIG.zoomStep), UI_CONFIG.zoomMin, UI_CONFIG.zoomMax); persistState(); rerenderAll(); });
    
    dom.exportJsonBtn.addEventListener("click", exportJson);
    dom.importFileInput.addEventListener("change", onImportJson);
    dom.clearCurrentLabelBtn.addEventListener("click", clearCurrentLabelValue);

    document.addEventListener("mouseup", onDocumentMouseUp);
    document.addEventListener("mouseleave", onDocumentMouseUp);
    document.addEventListener("click", (ev) => {
        if (!ev.target.closest('.atomic-item') && !ev.target.closest('.group-fragment') && !ev.target.closest('.floating-toolbar')) {
            if (state.mode === 'grouping' && (state.selectionRange || state.currentTargetId)) clearSelection();
        }
    });
  }

  function initTaskSelect() {
    dom.taskSelect.innerHTML = "";
    for (const task of configRoot.tasks) {
      const opt = document.createElement("option"); opt.value = task.task_id; opt.textContent = task.task_name;
      dom.taskSelect.appendChild(opt);
    }
  }

  function normalizeImagePath(p) {
    const s = String(p || "").replace(/\\/g, "/"); if (!s) return "";
    if (s.startsWith("images/")) return s; if (s.startsWith("auto_cut_segments/")) return `images/${s}`; return s;
  }

  function normalizeSegment(raw) {
    const id = raw.id || `seg_${String(raw.global_index || raw.id_str || "").padStart(6, "0")}`;
    const globalOrderRaw = raw.global_order != null ? raw.global_order : (raw.global_index != null ? raw.global_index : raw.id_str);
    return { ...raw, id, global_order: Number(globalOrderRaw), page_no: Number(raw.page_no), line_no: Number(raw.line_no),
             segment_index_in_line: Number(raw.segment_index_in_line), side: raw.side, width: Number(raw.width) || 1, height: Number(raw.height) || 1,
             rel_file_path: normalizeImagePath(raw.rel_file_path || raw.file_path || raw.file_name || "") };
  }

  function buildLineKey(seg) { return `${seg.page_no}_${seg.side}_${seg.line_no}`; }

  function buildVisibleData() {
    const startIndex = uniquePages.findIndex(p => p.key === state.session.pageStartKey);
    const endIndex = uniquePages.findIndex(p => p.key === state.session.pageEndKey);
    const validKeys = new Set(uniquePages.slice(startIndex, endIndex + 1).map(p => p.key));

    state.visibleSegments = allNormalizedSegments.filter(seg => validKeys.has(`${seg.page_no}_${seg.side}`));
    state.visibleSegmentById = new Map(state.visibleSegments.map(seg => [seg.id, seg]));
    state.lineMap = new Map(); state.lineOrder = [];
    
    for (const seg of state.visibleSegments) {
      const lineKey = buildLineKey(seg);
      if (!state.lineMap.has(lineKey)) { state.lineMap.set(lineKey, { lineKey, page_no: seg.page_no, side: seg.side, line_no: seg.line_no, segmentIds: [] }); state.lineOrder.push(lineKey); }
      state.lineMap.get(lineKey).segmentIds.push(seg.id);
    }
    state.lineOrder.sort((a, b) => {
      const la = state.lineMap.get(a), lb = state.lineMap.get(b);
      if (la.page_no !== lb.page_no) return la.page_no - lb.page_no;
      if (la.side !== lb.side) return String(la.side).localeCompare(String(lb.side));
      return la.line_no - lb.line_no;
    });
  }

  function startSessionFromInputs() {
    const studentId = dom.studentIdInput.value.trim(), studentName = dom.studentNameInput.value.trim();
    const startKey = dom.pageStartInput.value, endKey = dom.pageEndInput.value;
    if (!studentId || !studentName) return alert("请输入学号和姓名。");

    const startIndex = uniquePages.findIndex(p => p.key === startKey);
    const endIndex = uniquePages.findIndex(p => p.key === endKey);
    if (startIndex < 0 || endIndex < 0 || startIndex > endIndex) return alert("请输入有效页码范围。");

    state.session = { studentId, studentName, pageStartKey: startKey, pageEndKey: endKey };
    buildVisibleData(); switchToMain(); persistState(); rerenderAll();
  }

  function restoreSessionAndEnter() {
    const raw = localStorage.getItem(UI_CONFIG.storageKey); if (!raw) return alert("未找到本地缓存。");
    try {
      const data = JSON.parse(raw); if (!data.session) return alert("缓存数据缺少 session 信息。");
      state.session = data.session; state.zoom = data.zoom || 1.0; state.mode = data.mode || "grouping";
      state.currentTaskId = data.currentTaskId || configRoot.tasks[0]?.task_id || null;
      state.groups = Array.isArray(data.groups) ? data.groups : []; state.annotations = Array.isArray(data.annotations) ? data.annotations : [];
      state.selectionRange = data.selectionRange || null; state.currentTargetId = data.currentTargetId || null;
      dom.studentIdInput.value = state.session.studentId || ""; dom.studentNameInput.value = state.session.studentName || "";
      
      const fallbackStartKey = data.session.pageStartKey || uniquePages[0]?.key || "";
      const fallbackEndKey = data.session.pageEndKey || uniquePages[uniquePages.length - 1]?.key || "";
      dom.pageStartInput.value = state.session.pageStartKey = fallbackStartKey;
      dom.pageEndInput.value = state.session.pageEndKey = fallbackEndKey;

      buildVisibleData(); switchToMain(); rerenderAll();
    } catch (err) { alert("恢复缓存失败。"); }
  }

  function switchToMain() { dom.loginScreen.classList.remove("screen-active"); dom.mainScreen.classList.add("screen-active"); }

  function setMode(mode) { state.mode = mode; clearDragSelectionPreview(); clearSelection(); persistState(); rerenderAll(); }

  function getAtomicDisplayHeight() { return Math.round(UI_CONFIG.atomicDisplayHeightPx * state.zoom); }
  function getAtomicDisplayWidth(seg) { return Math.max(UI_CONFIG.atomicMinWidthPx, Math.round((Number(seg.width) || 1) * (getAtomicDisplayHeight() / (Number(seg.height) || 1)))); }
  function getAtomicOuterWidth(seg) { return getAtomicDisplayWidth(seg) + UI_CONFIG.atomicPaddingX * 2; }

  function getLineAtomicGeometry(line) {
    const segs = line.segmentIds.map(id => state.visibleSegmentById.get(id)).filter(Boolean);
    const xMap = new Map(); let cursorX = 0;
    for (let i = 0; i < segs.length; i++) {
      const outerWidth = getAtomicOuterWidth(segs[i]);
      xMap.set(segs[i].global_order, { left: cursorX, width: outerWidth, right: cursorX + outerWidth });
      cursorX += outerWidth; if (i < segs.length - 1) cursorX += UI_CONFIG.atomicGapPx;
    }
    return { segs, xMap, totalWidth: cursorX };
  }

  function getNodeSpan(nodeId) {
    const seg = state.visibleSegmentById.get(nodeId); if (seg) return { start: seg.global_order, end: seg.global_order };
    const grp = state.groups.find(g => g.id === nodeId); if (grp) return { start: grp.leaf_start, end: grp.leaf_end };
    return null;
  }

  function isNodeSelectedByRange(nodeId) {
    if (!state.selectionRange) return false;
    const span = getNodeSpan(nodeId); return span && span.start >= state.selectionRange.start && span.end <= state.selectionRange.end;
  }

  function isNodeUnderCurrentTarget(nodeId) {
    if (!state.currentTargetId) return false;
    if (state.currentTargetId === nodeId) return true;
    const targetSpan = getNodeSpan(state.currentTargetId), nodeSpan = getNodeSpan(nodeId);
    if (targetSpan && nodeSpan) return nodeSpan.start >= targetSpan.start && nodeSpan.end <= targetSpan.end;
    return false;
  }

  function isAdjacentOrOverlapping(rangeA, rangeB) { return rangeA && rangeB && !(rangeB.end < rangeA.start - 1 || rangeB.start > rangeA.end + 1); }
  function mergeRanges(rangeA, rangeB) { return { start: Math.min(rangeA.start, rangeB.start), end: Math.max(rangeA.end, rangeB.end) }; }
  
  function getTopLevelNodesInRange(start, end) {
    const result = [], covered = new Set();
    const candidateGroups = state.groups.filter(g => g.leaf_start >= start && g.leaf_end <= end)
      .sort((a, b) => (b.leaf_end - b.leaf_start) - (a.leaf_end - a.leaf_start) || (b.level || 0) - (a.level || 0));
    
    for (const g of candidateGroups) {
      let canUse = true;
      for (let x = g.leaf_start; x <= g.leaf_end; x++) { if (covered.has(x)) { canUse = false; break; } }
      if (!canUse) continue;
      result.push(g.id);
      for (let x = g.leaf_start; x <= g.leaf_end; x++) covered.add(x);
    }
    state.visibleSegments.filter(seg => seg.global_order >= start && seg.global_order <= end).forEach(seg => {
      if (!covered.has(seg.global_order)) { result.push(seg.id); covered.add(seg.global_order); }
    });
    return result.sort((a, b) => getNodeSpan(a).start - getNodeSpan(b).start);
  }

  function isTopLevelGroup(groupId) { return !state.groups.some(g => g.children && g.children.includes(groupId)); }

  function startDragSelection(globalOrder) {
    state.dragSelection.active = true; state.dragSelection.startOrder = globalOrder;
    state.dragSelection.currentOrder = globalOrder; state.dragSelection.justFinished = false; rerenderAll();
  }
  function updateDragSelection(globalOrder) {
    if (state.dragSelection.active && state.dragSelection.currentOrder !== globalOrder) { state.dragSelection.currentOrder = globalOrder; rerenderAll(); }
  }
  function getDragRange() {
    if (!state.dragSelection.active) return null;
    return { start: Math.min(state.dragSelection.startOrder, state.dragSelection.currentOrder), end: Math.max(state.dragSelection.startOrder, state.dragSelection.currentOrder) };
  }
  function finishDragSelection() {
    if (!state.dragSelection.active) return;
    const dragRange = getDragRange(); state.dragSelection.justFinished = true;
    if (dragRange) applyRangeSelection(dragRange);
    clearDragSelectionPreview(false); rerenderAll();
    setTimeout(() => { state.dragSelection.justFinished = false; }, 0);
  }
  function clearDragSelectionPreview(shouldRender = true) { state.dragSelection.active = false; if (shouldRender) rerenderAll(); }
  function onDocumentMouseUp() { if (state.dragSelection.active) finishDragSelection(); }

  function applyRangeSelection(range) {
    if (!range) return;
    state.currentTargetId = null; 
    if (!state.selectionRange) state.selectionRange = { start: range.start, end: range.end };
    else if (isAdjacentOrOverlapping(state.selectionRange, range)) state.selectionRange = mergeRanges(state.selectionRange, range);
    else return alert(UI_CONFIG.selectionAlertNonContinuous);
    persistState(); refreshSidePanel();
  }

  function rerenderAll() {
    updateTopUI(); renderRows(); refreshSidePanel(); refreshProgressOverlay();
  }

  function updateTopUI() {
    document.body.classList.toggle("mode-grouping", state.mode === "grouping");
    document.body.classList.toggle("mode-labeling", state.mode === "labeling");
    dom.studentIdLabel.textContent = state.session.studentId || "-"; dom.studentNameLabel.textContent = state.session.studentName || "-";
    dom.pageRangeLabel.textContent = state.session.pageStartKey ? `${state.session.pageStartKey} 至 ${state.session.pageEndKey}` : "-";
    dom.currentPageLabel.textContent = state.lineOrder.length > 0 ? String(state.lineMap.get(state.lineOrder[0])?.page_no || "-") : "-";
    dom.zoomLabel.textContent = `${Math.round(state.zoom * 100)}%`;
    dom.modeGroupingBtn.classList.toggle("active", state.mode === "grouping"); dom.modeLabelingBtn.classList.toggle("active", state.mode === "labeling");
    dom.labelingTools.classList.toggle("hidden", state.mode !== "labeling");
    dom.labelingPanel.classList.toggle("hidden", state.mode !== "labeling");
    dom.taskSelect.value = state.currentTaskId || "";
  }

  function renderRows() {
    dom.rowsRoot.innerHTML = "";
    let popupRendered = false; 

    for (const lineKey of state.lineOrder) {
      const line = state.lineMap.get(lineKey);
      const rowEl = document.createElement("div"); rowEl.className = "row-block";
      
      const header = document.createElement("div"); header.className = "row-header";
      header.textContent = `页 ${line.page_no} | ${line.side} | 行 ${line.line_no}`;
      rowEl.appendChild(header);

      const atomicStrip = document.createElement("div"); atomicStrip.className = "atomic-strip";
      const atomicSummaryStrip = document.createElement("div"); atomicSummaryStrip.className = "atomic-summary-strip";
      const levelArea = document.createElement("div"); levelArea.className = "levels-area";

      const { segs, xMap } = getLineAtomicGeometry(line);

      segs.forEach((seg, idx) => {
        const outerW = getAtomicOuterWidth(seg);
        const item = document.createElement("div"); item.className = "atomic-item";
        item.style.width = `${outerW}px`; item.style.height = `${getAtomicDisplayHeight() + UI_CONFIG.atomicPaddingY * 2}px`;
        const img = document.createElement("img"); img.src = seg.rel_file_path;
        img.style.width = `${getAtomicDisplayWidth(seg)}px`; img.style.height = `${getAtomicDisplayHeight()}px`;
        item.appendChild(img);

        const dragSelecting = state.dragSelection.active && (() => {
          const r = getDragRange(); return r && seg.global_order >= r.start && seg.global_order <= r.end;
        })();
        
        item.classList.toggle("selecting", dragSelecting);
        item.classList.toggle("selected", (state.mode === "grouping" && isNodeSelectedByRange(seg.id)) || (state.mode === "labeling" && isNodeUnderCurrentTarget(seg.id)));
        item.classList.toggle("has-annotation", nodeHasAnnotationForCurrentTask(seg.id));

        item.addEventListener("mousedown", (ev) => { if (ev.button === 0 && state.mode === "grouping") { ev.preventDefault(); startDragSelection(seg.global_order); } });
        item.addEventListener("mouseenter", () => { if (state.mode === "grouping") updateDragSelection(seg.global_order); });
        item.addEventListener("click", (ev) => { ev.stopPropagation(); if (!state.dragSelection.justFinished) onNodeClick(seg.id); });

        atomicStrip.appendChild(item);

        if (!popupRendered && state.mode === "grouping" && state.selectionRange && seg.global_order === state.selectionRange.start) {
            const ft = createFloatingToolbar();
            ft.style.left = `${xMap.get(seg.global_order).left}px`;
            ft.style.top = `-42px`; 
            atomicStrip.appendChild(ft);
            popupRendered = true;
        }

        const summary = document.createElement("div"); summary.className = "atomic-summary-item";
        summary.dataset.nodeId = seg.id; // 为局部刷新注入标记
        summary.style.width = `${outerW}px`; summary.textContent = getAtomicSummary(seg.id, outerW);
        summary.classList.toggle("has-annotation", nodeHasAnnotationForCurrentTask(seg.id));
        summary.classList.toggle("current-target", state.mode === "labeling" && state.currentTargetId === seg.id);
        if (idx < segs.length - 1) {
          atomicStrip.appendChild(Object.assign(document.createElement("div"), { className: "atomic-gap", style: `width:${UI_CONFIG.atomicGapPx}px` }));
          atomicSummaryStrip.appendChild(Object.assign(document.createElement("div"), { className: "atomic-gap", style: `width:${UI_CONFIG.atomicGapPx}px` }));
        }
        atomicSummaryStrip.appendChild(summary);
      });

      if (state.mode === "labeling") { rowEl.appendChild(atomicStrip); rowEl.appendChild(atomicSummaryStrip); } 
      else { rowEl.appendChild(atomicStrip); }

      buildLineGroupFragments(line, xMap).forEach(({ level, fragments }) => {
        const levelRow = document.createElement("div"); levelRow.className = "level-row";
        fragments.forEach(frag => {
          const fragEl = document.createElement("div"); fragEl.className = "group-fragment";
          fragEl.dataset.nodeId = frag.group.id; // 为局部刷新注入标记
          fragEl.style.left = `${frag.left}px`; fragEl.style.width = `${frag.width}px`;
          fragEl.style.borderColor = frag.color; fragEl.style.background = frag.background;
          
          fragEl.classList.toggle("selected", (state.mode === "grouping" && isNodeSelectedByRange(frag.group.id)) || (state.mode === "labeling" && state.currentTargetId === frag.group.id));
          fragEl.classList.toggle("has-annotation", nodeHasAnnotationForCurrentTask(frag.group.id));

          const label = document.createElement("div"); label.className = "fragment-label"; label.style.color = frag.color;
          label.textContent = getFragmentSummary(frag.group.id, frag.width);
          fragEl.appendChild(label);

          if (state.mode === "grouping" && isTopLevelGroup(frag.group.id)) {
             const xBtn = document.createElement("button");
             xBtn.className = "group-close-btn";
             xBtn.innerHTML = "&times;";
             xBtn.onclick = (ev) => { ev.stopPropagation(); tryUngroup(frag.group.id); };
             fragEl.appendChild(xBtn);
          }

          fragEl.addEventListener("click", (ev) => { ev.stopPropagation(); onNodeClick(frag.group.id); });
          levelRow.appendChild(fragEl);
        });
        levelArea.appendChild(levelRow);
      });

      rowEl.appendChild(levelArea); dom.rowsRoot.appendChild(rowEl);
    }
  }

  function createFloatingToolbar() {
    const ft = document.createElement("div"); ft.className = "floating-toolbar";
    const len = state.selectionRange.end - state.selectionRange.start + 1;
    if (len >= 2) {
      const btnGrp = document.createElement("button"); btnGrp.className = "ft-btn primary"; btnGrp.textContent = "Group";
      btnGrp.onclick = (ev) => { ev.stopPropagation(); applyGroup(); }; ft.appendChild(btnGrp);
    }
    const btnCancel = document.createElement("button"); btnCancel.className = "ft-btn"; btnCancel.textContent = "取消选择";
    btnCancel.onclick = (ev) => { ev.stopPropagation(); clearSelection(); }; ft.appendChild(btnCancel);
    return ft;
  }

  function buildLineGroupFragments(line, xMap) {
    if (line.segmentIds.length === 0) return [];
    const levelMap = new Map(), lineStart = line.segmentIds[0], lineEndId = line.segmentIds[line.segmentIds.length - 1];
    const lineStartOrder = state.visibleSegmentById.get(lineStart).global_order;
    const lineEndOrder = state.visibleSegmentById.get(lineEndId).global_order;

    for (const group of state.groups) {
      const overlapStart = Math.max(group.leaf_start, lineStartOrder), overlapEnd = Math.min(group.leaf_end, lineEndOrder);
      if (overlapStart > overlapEnd) continue;
      const startBox = xMap.get(overlapStart), endBox = xMap.get(overlapEnd);
      if (!startBox || !endBox) continue;
      if (!levelMap.has(group.level)) levelMap.set(group.level, []);
      levelMap.get(group.level).push({ group, left: startBox.left, width: Math.max(UI_CONFIG.groupBoxMinWidthPx, endBox.right - startBox.left),
        color: colorFromLevel(group.level), background: colorBgFromLevel(group.level) });
    }
    return Array.from(levelMap.entries()).sort((a, b) => a[0] - b[0]).map(([level, fragments]) => ({ level, fragments }));
  }

  function getAtomicSummary(nodeId, boxWidth) {
    const task = taskById.get(state.currentTaskId); if (!task) return "";
    const ann = state.annotations.find(a => a.target_id === nodeId && a.task_id === task.task_id);
    return ann ? summarizeAnnotationValue(task, ann.value, Math.max(1, Math.floor((boxWidth - 4) / UI_CONFIG.atomicSummaryCharWidthPx))) : "";
  }
  function getFragmentSummary(nodeId, boxWidth) {
    const maxChars = Math.max(2, Math.floor((boxWidth - 8) / UI_CONFIG.summaryCharWidthPx));
    if (state.mode === "grouping") return summarizeText(nodeId, maxChars);
    const task = taskById.get(state.currentTaskId), ann = task && state.annotations.find(a => a.target_id === nodeId && a.task_id === task.task_id);
    return ann ? summarizeAnnotationValue(task, ann.value, maxChars) || summarizeText(nodeId, maxChars) : summarizeText(nodeId, maxChars);
  }
  function summarizeAnnotationValue(task, value, maxChars) {
    if (task.mode === "text" || task.mode === "single") return summarizeText(String(value || ""), maxChars);
    if (task.mode === "multi" || task.mode === "multi_text") return summarizeText(Array.isArray(value) ? value.join(",") : "", maxChars);
    if (task.mode === "scale") return value ? summarizeText(Object.entries(value).map(([k, v]) => `${k}:${v}`).join("|"), maxChars) : "";
    return "";
  }

  function nodeHasAnnotationForCurrentTask(nodeId) {
    const task = taskById.get(state.currentTaskId), ann = state.annotations.find(a => a.target_id === nodeId && a.task_id === state.currentTaskId);
    if (!ann || !task) return false;
    if (task.mode === "multi" || task.mode === "multi_text") return Array.isArray(ann.value) && ann.value.length > 0;
    if (task.mode === "scale") return !!ann.value && Object.keys(ann.value).length > 0;
    return ann.value != null && String(ann.value).trim() !== "";
  }

  function onNodeClick(nodeId) {
    if (state.mode === "grouping") {
        state.currentTargetId = null; 
        toggleSelection(nodeId);
    } else {
      state.currentTargetId = nodeId; persistState(); refreshSidePanel(); rerenderAll();
    }
  }

  function toggleSelection(nodeId) {
    const span = getNodeSpan(nodeId); if (!span) return;
    if (isNodeSelectedByRange(nodeId)) return;
    if (!state.selectionRange) state.selectionRange = { start: span.start, end: span.end };
    else if (isAdjacentOrOverlapping(state.selectionRange, span)) state.selectionRange = mergeRanges(state.selectionRange, span);
    else return alert(UI_CONFIG.selectionAlertNonContinuous);
    persistState(); refreshSidePanel(); rerenderAll();
  }

  function clearSelection() { state.selectionRange = null; state.currentTargetId = null; persistState(); refreshSidePanel(); rerenderAll(); }

  function applyGroup() {
    if (!state.selectionRange) return;
    const { start, end } = state.selectionRange; if (end <= start) return alert("至少选择两个连续对象才能组合。");
    const children = getTopLevelNodesInRange(start, end); if (children.length < 2) return alert("当前选择不足以形成新分组。");
    
    const newGroup = { id: `grp_${String(Date.now()).slice(-6)}_${Math.floor(Math.random()*100)}`,
                       level: Math.max(0, ...children.map(id => state.groups.find(g => g.id === id)?.level || 0)) + 1,
                       children, leaf_start: start, leaf_end: end };
    state.groups.push(newGroup); state.selectionRange = null; state.currentTargetId = null; 
    persistState(); refreshSidePanel(); rerenderAll();
  }

  function tryUngroup(nodeId) {
    const idx = state.groups.findIndex(g => g.id === nodeId); if (idx < 0) return;
    state.groups.splice(idx, 1); state.currentTargetId = null; state.selectionRange = null;
    persistState(); refreshSidePanel(); rerenderAll();
  }

  function refreshSidePanel() {
    if (!state.currentTargetId && !state.selectionRange) { dom.selectionInfo.textContent = "尚未选中对象"; }
    else if (state.selectionRange) {
       dom.selectionInfo.innerHTML = `<div>选区：<strong>${state.selectionRange.start} - ${state.selectionRange.end}</strong></div>`;
    }
    else if (state.currentTargetId) dom.selectionInfo.innerHTML = `<div>当前对象：<strong>${state.currentTargetId}</strong></div>`;
    refreshTaskEditor();
  }

  // 3. 解决失去焦点重绘问题：局部静默更新算法
  function updateSummaryDOM(nodeId) {
    dom.rowsRoot.querySelectorAll(`.atomic-summary-item[data-node-id="${nodeId}"]`).forEach(el => {
        el.textContent = getAtomicSummary(nodeId, parseFloat(el.style.width));
        el.classList.toggle("has-annotation", nodeHasAnnotationForCurrentTask(nodeId));
    });
    dom.rowsRoot.querySelectorAll(`.group-fragment[data-node-id="${nodeId}"]`).forEach(el => {
        const label = el.querySelector(".fragment-label");
        if (label) label.textContent = getFragmentSummary(nodeId, parseFloat(el.style.width));
        el.classList.toggle("has-annotation", nodeHasAnnotationForCurrentTask(nodeId));
    });
    refreshProgressOverlay();
    persistState(); 
  }

  function refreshTaskEditor() {
    dom.taskEditorRoot.innerHTML = ""; if (state.mode !== "labeling") return;
    const task = taskById.get(state.currentTaskId); if (!task) return dom.taskMeta.textContent = "未选择任务。";
    if (!state.currentTargetId) return dom.taskMeta.textContent = `当前任务：${task.task_name}。请点击左侧对象。`;
    
    dom.taskMeta.textContent = `对象：${state.currentTargetId}`;
    const ann = state.annotations.find(a => a.target_id === state.currentTargetId && a.task_id === task.task_id);
    const value = ann ? ann.value : getDefaultTaskValue(task);
    
    if(task.help_text) dom.taskEditorRoot.appendChild(Object.assign(document.createElement("div"), { className: "task-help", textContent: task.help_text }));
    
    const sec = document.createElement("div"); sec.className = "editor-section";
    const label = document.createElement("label"); label.textContent = task.task_name; sec.appendChild(label);

    const triggerSave = (newVal, silent = false) => {
        setAnnotationValue(state.currentTargetId, task.task_id, newVal);
        if (silent) updateSummaryDOM(state.currentTargetId); else { persistState(); rerenderAll(); }
    };

    if (task.mode === "text") {
      const textarea = document.createElement("textarea"); textarea.value = value || ""; textarea.placeholder = task.placeholder || "";
      // 核心修正：监听 input 事件静默更新 DOM，这样焦点不会丢失，也不影响对图形的点击拦截
      textarea.addEventListener("input", () => triggerSave(textarea.value, true)); 
      sec.appendChild(textarea);
    } 
    else if (task.mode === "single") {
      const list = document.createElement("div"); list.className = "task-option-list";
      (task.options || []).forEach(opt => {
        const item = document.createElement("label"); item.className = "task-option-item";
        const radio = document.createElement("input"); radio.type = "radio"; radio.name = "singleOpt"; radio.value = opt; radio.checked = value === opt;
        radio.addEventListener("change", () => { if(radio.checked) triggerSave(opt); });
        item.append(radio, document.createTextNode(" " + opt)); list.appendChild(item);
      });
      sec.appendChild(list);
    }
    else if (task.mode === "multi") {
      const list = document.createElement("div"); list.className = "task-option-list"; const valArr = Array.isArray(value) ? value : [];
      (task.options || []).forEach(opt => {
        const item = document.createElement("label"); item.className = "task-option-item";
        const chk = document.createElement("input"); chk.type = "checkbox"; chk.value = opt; chk.checked = valArr.includes(opt);
        chk.addEventListener("change", () => triggerSave(chk.checked ? [...valArr, opt] : valArr.filter(x => x !== opt)));
        item.append(chk, document.createTextNode(" " + opt)); list.appendChild(item);
      });
      sec.appendChild(list);
    }
    else if (task.mode === "multi_text") {
       const wrap = document.createElement("div"); wrap.className = "multi-text-tags";
       const arr = Array.isArray(value) ? value : [];
       arr.forEach((t, i) => {
         const tag = document.createElement("div"); tag.className = "multi-text-tag"; tag.textContent = t;
         const del = document.createElement("button"); del.textContent = "×";
         del.onclick = () => { const next = arr.slice(); next.splice(i, 1); triggerSave(next); };
         tag.appendChild(del); wrap.appendChild(tag);
       });
       const input = document.createElement("input"); input.type = "text"; input.placeholder = "输入后回车";
       input.addEventListener("keydown", (ev) => {
         if (ev.key === "Enter" && input.value.trim()) triggerSave([...arr, input.value.trim()]);
       });
       sec.append(wrap, input);
    }
    else if (task.mode === "scale") {
       const vObj = (value && typeof value === "object") ? value : {};
       (task.items || []).forEach(itemDef => {
         const box = document.createElement("div"); box.className = "scale-item";
         box.innerHTML = `<div class="scale-item-title">${itemDef.label}</div>`;
         if (itemDef.ui === "discrete") {
           const row = document.createElement("div"); row.className = "scale-discrete-options";
           for (let v = Number(itemDef.min||1); v <= Number(itemDef.max||5); v += Number(itemDef.step||1)) {
              const btn = document.createElement("button"); btn.textContent = v; btn.classList.toggle("active", Number(vObj[itemDef.item_id]) === v);
              btn.onclick = () => triggerSave({ ...vObj, [itemDef.item_id]: v });
              row.appendChild(btn);
           }
           box.appendChild(row);
         } else {
            const row = document.createElement("div"); row.className = "scale-range-row";
            const inp = document.createElement("input"); inp.type = "range"; inp.min = itemDef.min||0; inp.max = itemDef.max||100; inp.step = itemDef.step||1;
            inp.value = vObj[itemDef.item_id] != null ? vObj[itemDef.item_id] : inp.min;
            const badge = document.createElement("div"); badge.className="scale-value-badge"; badge.textContent = inp.value;
            // Range 拖动过程中静默保存更新标记，不让其丢失焦点
            inp.addEventListener("input", () => { badge.textContent = inp.value; triggerSave({ ...vObj, [itemDef.item_id]: Number(inp.value) }, true); });
            row.append(Object.assign(document.createElement("span"),{textContent:inp.min}), inp, badge); box.appendChild(row);
         }
         sec.appendChild(box);
       });
    }
    dom.taskEditorRoot.appendChild(sec);
  }

  function clearCurrentLabelValue() {
    if (!state.currentTargetId || !state.currentTaskId) return;
    state.annotations = state.annotations.filter(a => !(a.target_id === state.currentTargetId && a.task_id === state.currentTaskId));
    persistState(); rerenderAll();
  }

  function setAnnotationValue(targetId, taskId, value) {
    const idx = state.annotations.findIndex(a => a.target_id === targetId && a.task_id === taskId);
    const item = { target_id: targetId, task_id: taskId, value, updated_at: new Date().toISOString() };
    if (idx >= 0) state.annotations[idx] = item; else state.annotations.push(item);
  }

  function getDefaultTaskValue(task) { return task.mode === "scale" ? {} : (task.mode === "multi" || task.mode === "multi_text" ? [] : ""); }

  function refreshProgressOverlay() {
      const overlay = dom.progressOverlay;
      if (state.mode === "grouping") {
          const totalAtoms = state.visibleSegments.length;
          const groupedAtoms = new Set();
          let maxLevel = 0; const levelCounts = {};
          state.groups.forEach(g => {
              for(let i=g.leaf_start; i<=g.leaf_end; i++) groupedAtoms.add(i);
              levelCounts[g.level] = (levelCounts[g.level] || 0) + 1;
              if (g.level > maxLevel) maxLevel = g.level;
          });
          const pct = totalAtoms ? Math.round((groupedAtoms.size / totalAtoms) * 100) : 0;
          
          let html = `<div class="progress-title">Grouping 统计信息</div>
                      <div class="progress-row"><span>单元覆盖率：</span><strong>${groupedAtoms.size} / ${totalAtoms} (${pct}%)</strong></div>
                      <div class="progress-row"><span>总编组数：</span><strong>${state.groups.length}</strong></div>`;
          for(let i=1; i<=maxLevel; i++) {
              html += `<div class="progress-row"><span>${i} 级组数量：</span><strong>${levelCounts[i]||0}</strong></div>`;
          }
          if (maxLevel > 0) html += `<div class="progress-row" style="color:#2563eb; margin-top:4px;"><span>当前最大层级：</span><strong>${maxLevel}</strong></div>`;
          overlay.innerHTML = html;
      } else {
          const task = taskById.get(state.currentTaskId);
          if (!task) { overlay.innerHTML = "请选择标注任务"; return; }
          const totalAtoms = state.visibleSegments.length, totalGroups = state.groups.length;
          let labeledAtoms = 0, labeledGroups = 0;
          
          state.visibleSegments.forEach(seg => {
              const ann = state.annotations.find(a => a.target_id === seg.id && a.task_id === task.task_id);
              if (ann && hasAnnotationValue(task, ann.value)) labeledAtoms++;
          });
          state.groups.forEach(grp => {
              const ann = state.annotations.find(a => a.target_id === grp.id && a.task_id === task.task_id);
              if (ann && hasAnnotationValue(task, ann.value)) labeledGroups++;
          });

          overlay.innerHTML = `<div class="progress-title">Labeling - [${task.task_name}]</div>
                               <div class="progress-row"><span>图形被标注：</span><strong>${labeledAtoms} / ${totalAtoms}</strong></div>
                               <div class="progress-row"><span>组别被标注：</span><strong>${labeledGroups} / ${totalGroups}</strong></div>`;
      }
  }
  function hasAnnotationValue(task, v) {
      if (task.mode === "multi" || task.mode === "multi_text") return Array.isArray(v) && v.length > 0;
      if (task.mode === "scale") return v && Object.keys(v).length > 0;
      return v != null && String(v).trim() !== "";
  }

  // 2. 增强的数据导入/导出：包括 config_snapshot 和校验逻辑
  function exportJson() {
    const filename = `${state.session.studentId}_${state.session.studentName}_${Date.now()}.json`;
    const payload = { 
        project: configRoot.project, 
        config_snapshot: JSON.parse(JSON.stringify(configRoot)), // 写入快照
        session: state.session, 
        groups: state.groups, 
        annotations: state.annotations 
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = filename; a.click();
  }

  function onImportJson(ev) {
    const file = ev.target.files && ev.target.files[0]; if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const data = JSON.parse(String(reader.result || "{}"));
        const warnings = [];
        
        // 校验 config_snapshot 是否一致
        if (data.config_snapshot && data.config_snapshot.tasks) {
            const curTaskIds = configRoot.tasks.map(t => t.task_id).sort().join(",");
            const impTaskIds = data.config_snapshot.tasks.map(t => t.task_id).sort().join(",");
            if (curTaskIds !== impTaskIds) {
                warnings.push("⚠️ 导入文件的任务配置（config.js）与当前系统存在差异！\n这可能导致部分标注数据无法正常显示。");
            }
        } else {
            warnings.push("⚠️ 导入文件缺失配置快照，无法验证标注任务匹配度。");
        }

        // 校验页码范围是否一致
        if (data.session && state.session && state.session.pageStartKey) {
            if (data.session.pageStartKey !== state.session.pageStartKey || data.session.pageEndKey !== state.session.pageEndKey) {
                warnings.push(`⚠️ 导入文件的工作范围（${data.session.pageStartKey} 至 ${data.session.pageEndKey}）与您当前所在的范围不同。\n导入后将自动为您跳转到文件指定的工作范围。`);
            }
        }

        // 如果有异常，则出具确认警告框
        if (warnings.length > 0) {
            if (!confirm(warnings.join("\n\n") + "\n\n是否继续导入数据？")) {
                ev.target.value = ""; return;
            }
        }

        if (data.session) {
            state.session = data.session; 
            // 自动修正 UI 上的范围显示
            dom.pageStartInput.value = state.session.pageStartKey || uniquePages[0].key;
            dom.pageEndInput.value = state.session.pageEndKey || uniquePages[uniquePages.length-1].key;
            buildVisibleData(); // 强制刷新可见数据
        }
        if (data.groups) state.groups = data.groups; if (data.annotations) state.annotations = data.annotations;
        persistState(); rerenderAll();
      } catch (err) { alert("导入失败：" + err.message); } finally { ev.target.value = ""; }
    }; reader.readAsText(file);
  }
  
  function persistState() { localStorage.setItem(UI_CONFIG.storageKey, JSON.stringify(state)); }
  function colorFromLevel(level) { return ["#8b5cf6", "#ef4444", "#2563eb", "#10b981", "#f59e0b", "#ec4899"][(level - 1) % 6]; }
  function colorBgFromLevel(level) { return ["rgba(139,92,246,0.08)", "rgba(239,68,68,0.08)", "rgba(37,99,235,0.08)", "rgba(16,185,129,0.08)", "rgba(245,158,11,0.08)", "rgba(236,72,153,0.08)"][(level - 1) % 6]; }
  function summarizeText(s, n) { const str = String(s || ""); return str.length <= n ? str : `${str.slice(0, n)}...`; }
  function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }
  function round2(v) { return Math.round(v * 100) / 100; }
})();