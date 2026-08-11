(function () {
  const root = document.getElementById("seatmapAdmin");
  if (!root) return;

  const svgUrl = root.dataset.svgUrl;
  const seatsUrl = root.dataset.seatsUrl;
  const mapWrap = document.getElementById("adminMapWrap");
  const mapInner = document.getElementById("adminMapInner");
  const stateText = document.getElementById("seatmapState");
  const searchInput = document.getElementById("seatSearch");
  const openEditorButton = document.getElementById("openSeatEditor");
  const openEditorSideButton = document.getElementById("openSeatEditorSide");
  const clearAllSelectionButton = document.getElementById("clearAllSelection");
  const summary = document.getElementById("statusSummary");
  const empty = document.getElementById("seatEditorEmpty");
  const selectionCard = document.getElementById("seatSelectionCard");
  const dialog = document.getElementById("seatEditorDialog");
  const form = document.getElementById("seatEditorForm");
  const title = document.getElementById("selectedSeatTitle");
  const meta = document.getElementById("selectedSeatMeta");
  const selectedReason = document.getElementById("selectedSeatReason");
  const dialogTitle = document.getElementById("seatDialogTitle");
  const dialogMeta = document.getElementById("seatDialogMeta");
  const dialogReason = document.getElementById("seatDialogReason");
  const lockMessage = document.getElementById("seatLockMessage");
  const errorMessage = document.getElementById("seatErrorMessage");
  const actionLabel = document.getElementById("seatActionLabel");
  const statusSelect = document.getElementById("seatStatus");
  const assigneeInput = document.getElementById("seatAssignee");
  const noteInput = document.getElementById("seatNote");
  const closeDialogButton = document.getElementById("closeSeatEditor");
  const closeButton = document.getElementById("clearSelection");
  const saveButton = form.querySelector('button[type="submit"]');
  const tooltip = document.createElement("div");
  tooltip.className = "seat-hover-tip";
  tooltip.hidden = true;
  document.body.appendChild(tooltip);

  const lockedStatuses = new Set(["vip_assigned", "taken", "public_sold", "closed"]);
  const MIXED_VALUE = "(mixed value)";
  const state = {
    seats: new Map(),
    circles: new Map(),
    statusLabels: {},
    selectedKey: null,
    selectedKeys: new Set(),
    svg: null,
    scale: 1,
    panX: 0,
    panY: 0,
    dragging: false,
    dragMoved: false,
    suppressClick: false,
    activePointerId: null,
    pointers: new Map(),
    pinch: null,
    startX: 0,
    startY: 0,
    baseX: 0,
    baseY: 0,
  };

  function seatKey(floorId, rowId, number) {
    return `${floorId}|${rowId}|${number}`;
  }

  function setStateText(text, tone) {
    stateText.textContent = text;
    stateText.dataset.tone = tone || "";
  }

  function setEditorError(text) {
    if (!errorMessage) return;
    errorMessage.textContent = text || "";
    errorMessage.hidden = !text;
  }

  function seatLabel(seat) {
    return `${seat.floorId} ${seat.rowId}排 ${seat.number}號`;
  }

  function priceLabel(price) {
    if (!price) return "";
    return `NT$${Number(price).toLocaleString("en-US")}`;
  }

  function compactPriceZone(seat) {
    if (!seat.price) return seat.sectionName || "";
    const price = Number(seat.price);
    if (!Number.isFinite(price) || price <= 0) return seat.sectionName || "";
    return `$${price.toLocaleString("en-US")}區`;
  }

  function compactSeatStatus(seat) {
    const zone = compactPriceZone(seat);
    const suffix = zone ? ` ${zone}` : "";
    if (seat.effectiveStatus === "public_sold") return `已在OPENTIX售出${suffix}`;
    if (seat.effectiveStatus === "vip_assigned") return `已調票給${seat.assigneeName || "未填姓名"}${suffix}`;
    if (seat.effectiveStatus === "pulled") return `已調票未指定${suffix}`;
    if (seat.effectiveStatus === "taken") {
      return seat.assigneeName ? `已預訂給${seat.assigneeName}${suffix}` : `已預訂${suffix}`;
    }
    if (seat.effectiveStatus === "closed") return `不開放販售${suffix}`;
    if (seat.effectiveStatus === "vip_available") return `VIP可分配${suffix}`;
    return `OPENTIX販售中${suffix}`;
  }

  function selectedSeats() {
    return Array.from(state.selectedKeys)
      .map((key) => state.seats.get(key))
      .filter(Boolean);
  }

  function selectionArray(selection) {
    return Array.isArray(selection) ? selection : [selection].filter(Boolean);
  }

  function sameSelectionValue(seats, field) {
    if (!seats.length) return "";
    const first = seats[0][field] || "";
    return seats.every((seat) => (seat[field] || "") === first) ? first : "";
  }

  function selectionHasMixedValue(seats, field) {
    if (seats.length < 2) return false;
    const values = new Set(seats.map((seat) => seat[field] || ""));
    return values.size > 1;
  }

  function setMixedField(input, mixed) {
    input.dataset.mixed = mixed ? "true" : "false";
    input.classList.toggle("is-mixed", mixed);
  }

  function setSelectionFieldValue(input, seats, field) {
    const mixed = selectionHasMixedValue(seats, field);
    setMixedField(input, mixed);
    input.value = mixed ? MIXED_VALUE : sameSelectionValue(seats, field);
  }

  function fieldKeepsExisting(input) {
    return input.dataset.mixed === "true";
  }

  function markFieldEdited(input) {
    if (input.dataset.mixed !== "true") return;
    setMixedField(input, false);
  }

  function editButtonText(count, canEdit) {
    if (!count) return "編輯";
    if (!canEdit) return "不可編輯";
    return `編輯${count.toLocaleString("en-US")}個座位`;
  }

  function updateEditButtons(count, canEdit) {
    const disabled = count === 0 || !canEdit;
    [openEditorButton, openEditorSideButton].forEach((button) => {
      if (!button) return;
      button.disabled = disabled;
      button.textContent = editButtonText(count, canEdit);
    });
    if (clearAllSelectionButton) clearAllSelectionButton.disabled = count === 0;
  }

  function statusBreakdown(seats) {
    const counts = {};
    seats.forEach((seat) => {
      counts[seat.effectiveStatus] = (counts[seat.effectiveStatus] || 0) + 1;
    });
    return Object.entries(counts)
      .map(([status, count]) => `${state.statusLabels[status] || status} ${count}`)
      .join(" / ");
  }

  function selectionLockedReason(seats) {
    const lockedSeats = seats.filter((seat) => !seat.editable);
    if (!lockedSeats.length) return "";
    if (lockedSeats.length === 1) return lockedSeats[0].lockedReason || "此座位不可調度";
    const counts = lockedSeats.reduce((bucket, seat) => {
      const reason = seat.lockedReason || "此座位不可調度";
      bucket[reason] = (bucket[reason] || 0) + 1;
      return bucket;
    }, {});
    return Object.entries(counts)
      .map(([reason, count]) => (count > 1 ? `${reason} ${count.toLocaleString("en-US")}個` : reason))
      .join("；");
  }

  function applyTransform() {
    mapInner.style.transform = `translate3d(${state.panX}px, ${state.panY}px, 0) scale(${state.scale})`;
  }

  function clampScale(value) {
    return Math.max(0.12, Math.min(4, value));
  }

  function transformedBox(element) {
    const box = element.getBBox();
    const matrix = element.getCTM();
    if (!matrix) return box;
    const points = [
      new DOMPoint(box.x, box.y).matrixTransform(matrix),
      new DOMPoint(box.x + box.width, box.y).matrixTransform(matrix),
      new DOMPoint(box.x, box.y + box.height).matrixTransform(matrix),
      new DOMPoint(box.x + box.width, box.y + box.height).matrixTransform(matrix),
    ];
    const xs = points.map((point) => point.x);
    const ys = points.map((point) => point.y);
    return {
      x: Math.min(...xs),
      y: Math.min(...ys),
      width: Math.max(...xs) - Math.min(...xs),
      height: Math.max(...ys) - Math.min(...ys),
    };
  }

  function seatBounds() {
    const circles = Array.from(state.circles.values());
    const boxes = circles
      .map((circle) => {
        try {
          return transformedBox(circle);
        } catch (_error) {
          return null;
        }
      })
      .filter(Boolean);
    if (!boxes.length) return null;
    const minX = Math.min(...boxes.map((box) => box.x));
    const minY = Math.min(...boxes.map((box) => box.y));
    const maxX = Math.max(...boxes.map((box) => box.x + box.width));
    const maxY = Math.max(...boxes.map((box) => box.y + box.height));
    return { x: minX, y: minY, width: maxX - minX, height: maxY - minY };
  }

  function resetView() {
    const bounds = seatBounds();
    if (!bounds) return;
    const width = Math.max(320, mapWrap.clientWidth - 48);
    const height = Math.max(320, mapWrap.clientHeight - 48);
    const fitScale = Math.min(width / bounds.width, height / bounds.height);
    state.scale = clampScale(fitScale * 1.22);
    state.panX = 24 - bounds.x * state.scale + Math.max(0, (width - bounds.width * state.scale) / 2);
    state.panY = 24 - bounds.y * state.scale + Math.max(0, (height - bounds.height * state.scale) / 2);
    applyTransform();
  }

  function zoomAt(clientX, clientY, nextScale) {
    const rect = mapWrap.getBoundingClientRect();
    const scale = clampScale(nextScale);
    const originX = (clientX - rect.left - state.panX) / state.scale;
    const originY = (clientY - rect.top - state.panY) / state.scale;
    state.panX = clientX - rect.left - originX * scale;
    state.panY = clientY - rect.top - originY * scale;
    state.scale = scale;
    applyTransform();
  }

  function trackPointer(event) {
    state.pointers.set(event.pointerId, {
      clientX: event.clientX,
      clientY: event.clientY,
    });
  }

  function pointerList() {
    return Array.from(state.pointers.values());
  }

  function pointerCenter(points) {
    return {
      x: (points[0].clientX + points[1].clientX) / 2,
      y: (points[0].clientY + points[1].clientY) / 2,
    };
  }

  function pointerDistance(points) {
    return Math.hypot(points[0].clientX - points[1].clientX, points[0].clientY - points[1].clientY);
  }

  function beginPan(event) {
    state.activePointerId = event.pointerId;
    state.dragging = true;
    state.dragMoved = false;
    state.startX = event.clientX;
    state.startY = event.clientY;
    state.baseX = state.panX;
    state.baseY = state.panY;
    mapWrap.classList.add("is-dragging");
  }

  function beginPinch() {
    const points = pointerList();
    if (points.length < 2) return;
    const distance = pointerDistance(points);
    if (!Number.isFinite(distance) || distance <= 0) return;
    const center = pointerCenter(points);
    const rect = mapWrap.getBoundingClientRect();
    state.pinch = {
      startDistance: distance,
      startScale: state.scale,
      originX: (center.x - rect.left - state.panX) / state.scale,
      originY: (center.y - rect.top - state.panY) / state.scale,
    };
    state.dragging = false;
    state.dragMoved = true;
    state.activePointerId = null;
    hideTooltip();
    mapWrap.classList.add("is-dragging");
  }

  function movePinch() {
    if (!state.pinch) return;
    const points = pointerList();
    if (points.length < 2) return;
    const distance = pointerDistance(points);
    const center = pointerCenter(points);
    if (!Number.isFinite(distance) || distance <= 0) return;
    const rect = mapWrap.getBoundingClientRect();
    const scale = clampScale(state.pinch.startScale * (distance / state.pinch.startDistance));
    state.panX = center.x - rect.left - state.pinch.originX * scale;
    state.panY = center.y - rect.top - state.pinch.originY * scale;
    state.scale = scale;
    applyTransform();
  }

  function finishGesture() {
    const moved = state.dragMoved || Boolean(state.pinch);
    state.dragging = false;
    state.dragMoved = false;
    state.activePointerId = null;
    state.pinch = null;
    if (!state.pointers.size) mapWrap.classList.remove("is-dragging");
    if (!moved) return;
    state.suppressClick = true;
    hideTooltip();
    window.setTimeout(() => {
      state.suppressClick = false;
    }, 120);
  }

  function removeSeatMark(key) {
    mapInner.querySelectorAll("line.admin-seat-taken-mark").forEach((line) => {
      if (line.dataset.adminSeatKey === key) line.remove();
    });
  }

  function addSeatMark(circle, key) {
    const cx = Number(circle.getAttribute("cx"));
    const cy = Number(circle.getAttribute("cy"));
    const radius = Number(circle.getAttribute("r"));
    if (!Number.isFinite(cx) || !Number.isFinite(cy) || !Number.isFinite(radius)) return;

    const delta = radius * 0.8;
    const transform = circle.getAttribute("transform");
    const pairs = [
      [cx - delta, cy - delta, cx + delta, cy + delta],
      [cx - delta, cy + delta, cx + delta, cy - delta],
    ];
    pairs.forEach(([x1, y1, x2, y2]) => {
      const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
      line.setAttribute("class", "admin-seat-taken-mark");
      line.setAttribute("x1", String(x1));
      line.setAttribute("y1", String(y1));
      line.setAttribute("x2", String(x2));
      line.setAttribute("y2", String(y2));
      line.setAttribute("stroke-width", String(Math.max(2.4, radius * 0.32)));
      if (transform) line.setAttribute("transform", transform);
      line.dataset.adminSeatKey = key;
      circle.parentNode.insertBefore(line, circle.nextSibling);
    });
  }

  function renderSeat(circle, seat) {
    const key = seat.key;
    Array.from(circle.classList).forEach((className) => {
      if (className.startsWith("admin-status-")) circle.classList.remove(className);
    });
    circle.classList.add("admin-seat", `admin-status-${seat.effectiveStatus}`);
    circle.classList.toggle("is-override", Boolean(seat.isOverride));
    circle.classList.toggle("has-assignee", Boolean(seat.assigneeName));
    circle.classList.toggle("is-selected", state.selectedKeys.has(key));
    circle.dataset.adminSeatKey = key;
    circle.dataset.effectiveStatus = seat.effectiveStatus;
    circle.setAttribute("role", "button");
    circle.setAttribute("tabindex", "0");
    circle.setAttribute("aria-label", `${seatLabel(seat)} ${compactSeatStatus(seat)}`);
    removeSeatMark(key);
    if (lockedStatuses.has(seat.effectiveStatus)) addSeatMark(circle, key);
  }

  function renderTooltip(seat) {
    tooltip.innerHTML = "";
    const heading = document.createElement("strong");
    heading.textContent = seatLabel(seat);
    const status = document.createElement("span");
    status.className = `tip-status tip-status-${seat.effectiveStatus}`;
    status.textContent = compactSeatStatus(seat);
    tooltip.append(heading, status);
  }

  function moveTooltip(clientX, clientY) {
    const margin = 14;
    const offset = 16;
    const rect = tooltip.getBoundingClientRect();
    let left = clientX + offset;
    let top = clientY + offset;
    if (left + rect.width + margin > window.innerWidth) left = clientX - rect.width - offset;
    if (top + rect.height + margin > window.innerHeight) top = clientY - rect.height - offset;
    tooltip.style.left = `${Math.max(margin, left)}px`;
    tooltip.style.top = `${Math.max(margin, top)}px`;
  }

  function showTooltip(seat, event) {
    if (state.dragging) return;
    renderTooltip(seat);
    tooltip.hidden = false;
    tooltip.dataset.status = seat.effectiveStatus;
    if (event) {
      moveTooltip(event.clientX, event.clientY);
      return;
    }
    const circle = state.circles.get(seat.key);
    if (!circle) return;
    const rect = circle.getBoundingClientRect();
    moveTooltip(rect.left + rect.width / 2, rect.top + rect.height / 2);
  }

  function hideTooltip() {
    tooltip.hidden = true;
  }

  function renderSummary() {
    const counts = {};
    state.seats.forEach((seat) => {
      counts[seat.effectiveStatus] = (counts[seat.effectiveStatus] || 0) + 1;
    });
    const order = ["vip_available", "vip_assigned", "taken", "pulled", "public_sold", "closed", "public_available"];
    summary.innerHTML = order
      .filter((status) => counts[status])
      .map(
        (status) => `
          <div class="summary-row">
            <span class="status-dot status-dot-${status}"></span>
            <span>${state.statusLabels[status] || status}</span>
            <strong>${counts[status]}</strong>
          </div>
        `
      )
      .join("");
  }

  function openEditorDialog() {
    const seats = selectedSeats();
    if (!seats.length || !dialog) return;
    if (!seats.every((seat) => seat.editable)) {
      setStateText(selectionLockedReason(seats), "warn");
      return;
    }
    renderSelected();
    dialog.hidden = false;
    if (typeof dialog.showModal === "function") {
      if (!dialog.open) dialog.showModal();
    } else {
      dialog.hidden = false;
    }
    window.setTimeout(() => statusSelect.focus(), 0);
  }

  function closeEditorDialog() {
    if (!dialog) return;
    if (typeof dialog.close === "function" && dialog.open) {
      dialog.close();
    } else {
      dialog.hidden = true;
    }
  }

  function renderSelected() {
    const seats = selectedSeats();
    const seat = seats.length === 1 ? seats[0] : null;
    const hasSelection = seats.length > 0;
    const allEditable = hasSelection && seats.every((item) => item.editable);
    empty.hidden = hasSelection;
    selectionCard.hidden = !hasSelection;
    form.hidden = !hasSelection;
    updateEditButtons(seats.length, allEditable);
    state.circles.forEach((circle, key) => {
      circle.classList.toggle("is-selected", state.selectedKeys.has(key));
    });
    if (!hasSelection) {
      closeEditorDialog();
      return;
    }

    if (seat) {
      title.textContent = seatLabel(seat);
      dialogTitle.textContent = seatLabel(seat);
      const parts = [seat.sectionName, priceLabel(seat.price), seat.statusLabel].filter(Boolean);
      meta.textContent = `${parts.join(" / ")}${seat.isOverride ? " / 內部標記" : ""}`;
      dialogMeta.textContent = meta.textContent;
      selectedReason.textContent = seat.editable ? seat.statusReason : seat.lockedReason || seat.statusReason;
      dialogReason.textContent = seat.statusReason;
      assigneeInput.value = seat.assigneeName || "";
      noteInput.value = seat.note || "";
      setMixedField(assigneeInput, false);
      setMixedField(noteInput, false);
    } else {
      title.textContent = `已選 ${seats.length.toLocaleString("en-US")} 個座位`;
      dialogTitle.textContent = title.textContent;
      meta.textContent = statusBreakdown(seats);
      dialogMeta.textContent = meta.textContent;
      selectedReason.textContent = seats.every((item) => item.editable)
        ? "批次修改會將同一個狀態、受配者與備註套用到所有已選座位。"
        : "目前選取中包含不可修改座位。";
      dialogReason.textContent = selectedReason.textContent;
      setSelectionFieldValue(assigneeInput, seats, "assigneeName");
      setSelectionFieldValue(noteInput, seats, "note");
    }

    renderActionOptions(seats);
    updateEditorControls(seats);
  }

  function renderActionOptions(selection) {
    const seats = selectionArray(selection);
    const seat = seats[0];
    const allEditable = seats.length > 0 && seats.every((item) => item.editable);
    const statuses = new Set(seats.map((item) => item.effectiveStatus));
    statusSelect.innerHTML = "";
    const actions = allEditable
      ? (seat.allowedActions || []).filter((action) =>
          seats.every((item) => (item.allowedActions || []).some((candidate) => candidate.value === action.value))
        )
      : [];
    if (!allEditable) {
      const option = document.createElement("option");
      option.value = seat ? seat.effectiveStatus : "";
      option.textContent = seats.length > 1 ? "不可批次修改" : seat.statusLabel;
      statusSelect.appendChild(option);
      return;
    }

    const currentIsAction = actions.some((action) => action.value === seat.effectiveStatus);
    if (statuses.size > 1 || !currentIsAction) {
      const placeholder = document.createElement("option");
      placeholder.value = "";
      placeholder.textContent = statuses.size > 1 ? MIXED_VALUE : "選擇動作";
      statusSelect.appendChild(placeholder);
    }
    actions.forEach((action) => {
      const option = document.createElement("option");
      option.value = action.value;
      option.textContent = action.label;
      statusSelect.appendChild(option);
    });
    statusSelect.value = statuses.size === 1 && currentIsAction ? seat.effectiveStatus : "";
  }

  function updateEditorControls(selection) {
    const seats = selectionArray(selection);
    const editable = seats.length > 0 && seats.every((seat) => seat.editable);
    const action = statusSelect.value;
    const assigning = editable && action === "vip_assigned";

    lockMessage.hidden = editable;
    lockMessage.textContent = editable ? "" : selectionLockedReason(seats);
    actionLabel.hidden = !editable;
    statusSelect.disabled = !editable;
    assigneeInput.disabled = !assigning;
    noteInput.disabled = !editable;
    const keepsAssignee = fieldKeepsExisting(assigneeInput);
    saveButton.disabled = !editable || !action || (action === "vip_assigned" && !keepsAssignee && !assigneeInput.value.trim());
    saveButton.textContent = seats.length > 1 ? `儲存 ${seats.length.toLocaleString("en-US")} 個座位` : "儲存座位";

    if (editable && action === "pulled") {
      assigneeInput.value = "";
      setMixedField(assigneeInput, false);
      assigneeInput.placeholder = "釋出後不指定受配者";
    } else {
      assigneeInput.placeholder = "由鉅 / Wayne / 郭阿姨";
    }
  }

  function selectSeat(key) {
    const clickedSeat = state.seats.get(key);
    if (!clickedSeat) return;
    const wasSelected = state.selectedKeys.has(key);
    if (wasSelected) {
      state.selectedKeys.delete(key);
    } else {
      state.selectedKeys.add(key);
    }
    const remainingKeys = Array.from(state.selectedKeys);
    state.selectedKey = state.selectedKeys.has(key) ? key : remainingKeys.pop() || null;
    setEditorError("");
    renderSelected();
    const seats = selectedSeats();
    const allEditable = seats.length > 0 && seats.every((seat) => seat.editable);
    if (!wasSelected && !clickedSeat.editable) {
      setStateText(clickedSeat.lockedReason || selectionLockedReason(seats), "warn");
    } else if (seats.length && !allEditable) {
      setStateText(selectionLockedReason(seats), "warn");
    } else if (state.selectedKeys.size > 1) {
      setStateText(`已選取 ${state.selectedKeys.size.toLocaleString("en-US")} 個座位`, "");
    } else if (state.selectedKey) {
      setStateText(`已選取 ${seatLabel(state.seats.get(state.selectedKey))}`, "");
    } else {
      setStateText("已取消選取", "");
    }
  }

  function wireSeats() {
    mapInner.querySelectorAll("line.seat-taken-mark,line.admin-seat-taken-mark").forEach((line) => line.remove());
    const circles = mapInner.querySelectorAll("circle.seat[data-floor][data-row][data-number]");
    circles.forEach((circle) => {
      const key = seatKey(circle.dataset.floor, circle.dataset.row, circle.dataset.number);
      const seat = state.seats.get(key);
      if (!seat) return;
      state.circles.set(key, circle);
      renderSeat(circle, seat);
      circle.addEventListener("click", (event) => {
        if (state.suppressClick) return;
        event.stopPropagation();
        selectSeat(key);
      });
      circle.addEventListener("pointerenter", (event) => {
        const freshSeat = state.seats.get(key);
        if (freshSeat) showTooltip(freshSeat, event);
      });
      circle.addEventListener("pointermove", (event) => {
        if (!tooltip.hidden) moveTooltip(event.clientX, event.clientY);
      });
      circle.addEventListener("pointerleave", hideTooltip);
      circle.addEventListener("focus", () => {
        const freshSeat = state.seats.get(key);
        if (freshSeat) showTooltip(freshSeat);
      });
      circle.addEventListener("blur", hideTooltip);
      circle.addEventListener("keydown", (event) => {
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        selectSeat(key);
      });
    });
  }

  function applySearch() {
    const query = searchInput.value.trim().toLowerCase();
    let matches = 0;
    state.circles.forEach((circle, key) => {
      const seat = state.seats.get(key);
      const haystack = [
        seatLabel(seat),
        seat.sectionName,
        seat.assigneeName,
        seat.note,
        seat.statusLabel,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      const matched = query && haystack.includes(query);
      if (matched) matches += 1;
      circle.classList.toggle("search-match", Boolean(matched));
      circle.classList.toggle("search-dim", Boolean(query && !matched));
    });
    if (!query) {
      setStateText(`${state.seats.size.toLocaleString("en-US")} 個座位已載入`, "");
    } else {
      setStateText(`${matches.toLocaleString("en-US")} 筆符合`, matches ? "" : "warn");
    }
  }

  async function saveSelected(event) {
    event.preventDefault();
    const seats = selectedSeats();
    if (!seats.length) return;

    setEditorError("");
    setStateText("儲存中...", "");
    try {
      const response = await fetch(seatsUrl, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          seats: seats.map((seat) => ({
            floorId: seat.floorId,
            rowId: seat.rowId,
            number: seat.number,
          })),
          adminStatus: statusSelect.value,
          assigneeName: statusSelect.value === "vip_assigned" && !fieldKeepsExisting(assigneeInput) ? assigneeInput.value : "",
          note: fieldKeepsExisting(noteInput) ? "" : noteInput.value,
          keepExistingAssignee: fieldKeepsExisting(assigneeInput),
          keepExistingNote: fieldKeepsExisting(noteInput),
        }),
      });
      if (!response.ok) {
        let message = "儲存失敗，請重新整理後再試一次。";
        try {
          const payload = await response.json();
          message = payload.detail || message;
        } catch (_error) {
          const text = await response.text();
          if (text) message = text;
        }
        throw new Error(message);
      }
      const data = await response.json();
      const updatedSeats = data.seats || (data.seat ? [data.seat] : []);
      updatedSeats.forEach((updatedSeat) => {
        state.seats.set(updatedSeat.key, updatedSeat);
        const circle = state.circles.get(updatedSeat.key);
        if (circle) renderSeat(circle, updatedSeat);
      });
      if (!tooltip.hidden && state.selectedKey) {
        const activeSeat = state.seats.get(state.selectedKey);
        if (activeSeat) showTooltip(activeSeat);
      }
      renderSummary();
      applySearch();
      const savedMessage = updatedSeats.length > 1
        ? `已儲存 ${updatedSeats.length.toLocaleString("en-US")} 個座位`
        : updatedSeats[0]
          ? `已儲存 ${seatLabel(updatedSeats[0])}`
          : "已儲存";
      closeEditorDialog();
      clearSelection(savedMessage, "success");
    } catch (error) {
      setStateText("儲存失敗", "error");
      setEditorError(error instanceof Error ? error.message : "儲存失敗，請重新整理後再試一次。");
    }
  }

  function wireMapControls() {
    mapWrap.addEventListener("pointerdown", (event) => {
      if (event.button !== 0) return;
      trackPointer(event);
      hideTooltip();
      try {
        mapWrap.setPointerCapture(event.pointerId);
      } catch (_error) {
        // Some touch browsers may already have assigned capture.
      }
      if (state.pointers.size >= 2) {
        beginPinch();
        event.preventDefault();
        return;
      }
      beginPan(event);
    });

    mapWrap.addEventListener("pointermove", (event) => {
      if (!state.pointers.has(event.pointerId)) return;
      trackPointer(event);
      if (state.pinch) {
        movePinch();
        event.preventDefault();
        return;
      }
      if (!state.dragging || state.activePointerId !== event.pointerId) return;
      const dx = event.clientX - state.startX;
      const dy = event.clientY - state.startY;
      if (Math.abs(dx) + Math.abs(dy) > 4) state.dragMoved = true;
      state.panX = state.baseX + dx;
      state.panY = state.baseY + dy;
      applyTransform();
    });

    function endPointer(event) {
      const wasTracked = state.pointers.delete(event.pointerId);
      if (!wasTracked) return;
      try {
        mapWrap.releasePointerCapture(event.pointerId);
      } catch (_error) {
        // Pointer capture may already be released by the browser.
      }
      if (state.pinch) {
        finishGesture();
        return;
      }
      if (state.dragging && state.activePointerId === event.pointerId) {
        finishGesture();
        return;
      }
      if (!state.pointers.size) mapWrap.classList.remove("is-dragging");
    }

    mapWrap.addEventListener("pointerup", endPointer);
    mapWrap.addEventListener("pointercancel", endPointer);
    mapWrap.addEventListener("lostpointercapture", endPointer);

    mapWrap.addEventListener(
      "wheel",
      (event) => {
        event.preventDefault();
        const factor = event.deltaY < 0 ? 1.12 : 0.88;
        zoomAt(event.clientX, event.clientY, state.scale * factor);
      },
      { passive: false }
    );

    root.querySelectorAll("[data-map-action]").forEach((button) => {
      button.addEventListener("click", () => {
        const rect = mapWrap.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        const action = button.dataset.mapAction;
        if (action === "zoom-in") zoomAt(centerX, centerY, state.scale * 1.18);
        if (action === "zoom-out") zoomAt(centerX, centerY, state.scale * 0.84);
      });
    });
  }

  async function init() {
    try {
      const [svgResponse, seatsResponse] = await Promise.all([fetch(svgUrl), fetch(seatsUrl)]);
      if (!svgResponse.ok) throw new Error("座位圖 SVG 載入失敗。");
      if (!seatsResponse.ok) throw new Error("座位資料載入失敗。");
      const svgText = await svgResponse.text();
      const seatData = await seatsResponse.json();

      state.statusLabels = seatData.statusOptions || {};
      seatData.seats.forEach((seat) => state.seats.set(seat.key, seat));
      mapInner.innerHTML = svgText;
      state.svg = mapInner.querySelector("svg");
      if (!state.svg) throw new Error("SVG did not contain a root svg element.");
      state.svg.style.width = `${Number(state.svg.getAttribute("width") || 20000)}px`;
      state.svg.style.height = `${Number(state.svg.getAttribute("height") || 20000)}px`;
      state.svg.setAttribute("aria-label", "OPENTIX 座位圖");
      state.svg.querySelectorAll("text.seat").forEach((text) => {
        text.style.pointerEvents = "none";
      });

      wireSeats();
      renderSummary();
      renderSelected();
      resetView();
      setStateText(`${state.seats.size.toLocaleString("en-US")} 個座位已載入`, "success");
    } catch (error) {
      console.error(error);
      setStateText("座位圖載入失敗", "error");
      mapInner.innerHTML = '<div class="map-loading map-error">座位圖載入失敗。</div>';
    }
  }

  form.addEventListener("submit", saveSelected);
  statusSelect.addEventListener("change", () => {
    const seats = selectedSeats();
    if (seats.length) updateEditorControls(seats);
  });
  assigneeInput.addEventListener("input", () => {
    markFieldEdited(assigneeInput);
    const seats = selectedSeats();
    if (seats.length) updateEditorControls(seats);
  });
  assigneeInput.addEventListener("focus", () => {
    if (assigneeInput.dataset.mixed === "true") assigneeInput.select();
  });
  noteInput.addEventListener("input", () => {
    markFieldEdited(noteInput);
    const seats = selectedSeats();
    if (seats.length) updateEditorControls(seats);
  });
  noteInput.addEventListener("focus", () => {
    if (noteInput.dataset.mixed === "true") noteInput.select();
  });
  if (openEditorButton) openEditorButton.addEventListener("click", openEditorDialog);
  if (openEditorSideButton) openEditorSideButton.addEventListener("click", openEditorDialog);
  if (closeDialogButton) closeDialogButton.addEventListener("click", closeEditorDialog);
  if (dialog) {
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) closeEditorDialog();
    });
  }
  function clearSelection(message = "已清除選擇", tone = "") {
    state.selectedKey = null;
    state.selectedKeys.clear();
    setEditorError("");
    renderSelected();
    setStateText(message, tone);
  }

  closeButton.addEventListener("click", () => clearSelection());
  if (clearAllSelectionButton) clearAllSelectionButton.addEventListener("click", () => clearSelection());
  searchInput.addEventListener("input", applySearch);
  wireMapControls();
  init();
})();
