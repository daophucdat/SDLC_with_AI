/* Prototype tương tác cho màn hình làm việc. Dữ liệu là dữ liệu mẫu; mọi độ trễ chỉ để mô phỏng.
   Truy vết: Blueprint_SDD.md §3.4 (F2, F3, F4), §3.5 (UI state model), §3.7 (state machines). */
(function () {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const el = (tag, attrs = {}, ...kids) => {
    const n = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs)) {
      if (v == null || v === false) continue;
      if (k === "class") n.className = v;
      else if (k === "text") n.textContent = v;
      else if (k.startsWith("on")) n.addEventListener(k.slice(2), v);
      else n.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat()) if (kid != null) n.append(kid.nodeType ? kid : document.createTextNode(kid));
    return n;
  };

  // ---------------- Mock data ----------------
  const ME = "Trần Thu Hà";
  const baseDocs = () => [
    { id: "d1", name: "Hop_dong_KhachHang_X_2025.pdf", pages: 32, status: "ready", by: "Nguyễn Minh Anh", date: "12/09/2026" },
    { id: "d2", name: "Phu_luc_02_HopDong_X.pdf", pages: 6, status: "ready", by: ME, date: "14/09/2026" },
    { id: "d3", name: "Bao_gia_Q3_2026.pdf", pages: 12, status: "ready", by: "Lê Quốc Bảo", date: "01/10/2026" },
    { id: "d4", name: "Bien_ban_hop_15-09-2026.pdf", pages: null, status: "processing", by: ME, date: "19/10/2026", autoReady: 9000 },
    { id: "d5", name: "Scan_hop_dong_2019.pdf", pages: 18, status: "no_text", by: ME, date: "18/10/2026" },
    { id: "d6", name: "Ke_hoach_trien_khai_2027.pdf", pages: null, status: "error", by: "Lê Quốc Bảo", date: "18/10/2026",
      error: "File có mật khẩu. Hãy bỏ mật khẩu rồi tải lại." },
  ];

  const ANSWERS = {
    payment: {
      text: "Theo hợp đồng với khách hàng X, việc thanh toán chia làm hai đợt: 30% giá trị hợp đồng trong vòng 07 ngày kể từ ngày ký [1], và 70% còn lại sau khi hai bên ký biên bản nghiệm thu [2].\n\nPhụ lục 02 bổ sung: nếu thanh toán chậm quá 15 ngày, khách hàng chịu phí 0,05% mỗi ngày trên số tiền chậm trả [3].",
      cites: [
        { docId: "d1", page: 4, excerpt: "Bên B thanh toán cho Bên A 30% giá trị hợp đồng trong vòng 07 (bảy) ngày kể từ ngày ký hợp đồng." },
        { docId: "d1", page: 5, excerpt: "70% giá trị còn lại được thanh toán sau khi hai bên ký biên bản nghiệm thu." },
        { docId: "d2", page: 2, excerpt: "Trường hợp chậm thanh toán quá 15 ngày, Bên B chịu phí 0,05%/ngày trên số tiền chậm trả." },
      ],
    },
    quote: {
      text: "Báo giá quý 3/2026 gồm ba hạng mục: bản quyền phần mềm cho 50 người dùng [1], gói triển khai và đào tạo 20 ngày công [1], và hỗ trợ vận hành 12 tháng [2]. Báo giá có hiệu lực đến hết ngày 31/12/2026 [2].",
      cites: [
        { docId: "d3", page: 2, excerpt: "Hạng mục 1: bản quyền phần mềm cho 50 người dùng. Hạng mục 2: triển khai và đào tạo, 20 ngày công." },
        { docId: "d3", page: 5, excerpt: "Hạng mục 3: hỗ trợ vận hành 12 tháng. Báo giá có hiệu lực đến hết ngày 31/12/2026." },
      ],
    },
    uncited: { text: "Thời hạn bảo hành thường là 12 tháng kể từ ngày nghiệm thu, áp dụng cho lỗi phần mềm", cites: [] },
  };
  const SUGGESTIONS = [
    "Tóm tắt các điều khoản thanh toán của khách hàng X",
    "Báo giá quý 3 gồm những hạng mục nào?",
    "Thời hạn bảo hành trong hợp đồng X là bao lâu?",
  ];

  // ---------------- State (§3.5) ----------------
  const S = {
    role: "member", docs: baseDocs(), uploads: 0, turns: [], streaming: null, failNext: false,
    online: true, aiDown: false, session: false, filter: "", source: null, openMenu: null,
  };
  const docById = (id) => S.docs.find((d) => d.id === id);
  const readyDocs = () => S.docs.filter((d) => d.status === "ready");
  const canRemove = (d) => S.role === "lead" || d.by === ME;

  // ---------------- Toasts, SR status ----------------
  const srStatus = el("div", { class: "sr-only", "aria-live": "polite", id: "sr-status" });
  document.body.append(srStatus);
  const announce = (msg) => { srStatus.textContent = ""; setTimeout(() => (srStatus.textContent = msg), 50); };
  function toast(message, kind = "info") {
    const t = el("div", { class: `toast ${kind}` }, el("span", { text: message }),
      el("button", { class: "btn btn-ghost btn-icon", "aria-label": "Đóng thông báo", style: "color:inherit;margin-left:auto", onclick: () => t.remove() }, "✕"));
    $("#toasts").append(t);
    setTimeout(() => t.remove(), 5000);
  }

  // ---------------- Dialog (focus trap) ----------------
  let dialogConfirm = null, lastFocus = null;
  function openDialog({ title, body, confirmLabel, danger = true, onConfirm }) {
    lastFocus = document.activeElement;
    $("#dialog-title").textContent = title;
    $("#dialog-body").textContent = body;
    const c = $("#dialog-confirm");
    c.textContent = confirmLabel;
    c.className = `btn ${danger ? "btn-danger" : "btn-primary"}`;
    dialogConfirm = onConfirm;
    $("#dialog").hidden = false;
    $("#dialog-cancel").focus();
  }
  function closeDialog() { $("#dialog").hidden = true; dialogConfirm = null; lastFocus && lastFocus.focus(); }
  $("#dialog-cancel").addEventListener("click", closeDialog);
  $("#dialog-confirm").addEventListener("click", () => { const f = dialogConfirm; closeDialog(); f && f(); });
  $("#dialog").addEventListener("keydown", (e) => {
    if (e.key === "Tab") {
      const a = $("#dialog-cancel"), b = $("#dialog-confirm");
      if (e.shiftKey && document.activeElement === a) { e.preventDefault(); b.focus(); }
      else if (!e.shiftKey && document.activeElement === b) { e.preventDefault(); a.focus(); }
    }
  });

  // ---------------- Library (§3.6.2 LibraryPanel, DocumentItem) ----------------
  const STATUS = {
    ready: { icon: "📄", badge: "badge-ready", label: "Sẵn sàng" },
    processing: { icon: "⏳", badge: "badge-processing", label: "Đang xử lý" },
    uploading: { icon: "⬆️", badge: "badge-processing", label: "Đang tải lên" },
    paused: { icon: "📶", badge: "badge-warning", label: "Tạm dừng — mất kết nối" },
    upload_failed: { icon: "⛔", badge: "badge-error", label: "Tải lên thất bại" },
    no_text: { icon: "⚠️", badge: "badge-warning", label: "Không đọc được chữ" },
    error: { icon: "⛔", badge: "badge-error", label: "Lỗi" },
  };

  function renderLibrary() {
    const list = $("#doc-list");
    list.replaceChildren();
    const q = S.filter.trim().toLowerCase();
    const docs = q.length >= 2 ? S.docs.filter((d) => d.name.toLowerCase().includes(q)) : S.docs;
    $("#doc-count").textContent = `(${S.docs.length})`;
    if (!S.docs.length) {
      list.append(el("li", { class: "empty small" }, el("div", { class: "empty-icon", "aria-hidden": "true" }, "🗂️"),
        el("p", { text: "Kho chưa có tài liệu." }), el("p", { class: "xs", text: "Kéo-thả file PDF vào đây hoặc bấm “Tải tài liệu”." })));
      return;
    }
    if (!docs.length) {
      list.append(el("li", { class: "empty small" }, el("p", { text: `Không có tài liệu nào khớp “${S.filter}”.` }),
        el("button", { class: "btn btn-secondary", onclick: () => { S.filter = ""; $("#doc-filter").value = ""; renderLibrary(); } }, "Xoá bộ lọc")));
      return;
    }
    for (const d of docs) list.append(docItem(d));
  }

  function docItem(d) {
    const st = STATUS[d.status];
    const meta = el("div", { class: "doc-meta" },
      el("span", { class: `badge ${st.badge}` }, d.status === "uploading" ? `${st.label} ${Math.round(d.progress)}%` : st.label),
      d.pages ? el("span", { text: `${d.pages} trang` }) : null,
      el("span", { text: `${d.by === ME ? "Bạn" : d.by} · ${d.date}` }));
    const body = el("div", { style: "min-width:0" }, el("div", { class: "doc-name", title: d.name, text: d.name }), meta);
    if (d.status === "uploading") body.append(el("div", { class: "progress", role: "progressbar", "aria-valuenow": Math.round(d.progress), "aria-valuemin": 0, "aria-valuemax": 100, "aria-label": `Tiến độ tải ${d.name}` }, el("span", { style: `width:${d.progress}%` })));
    if (d.status === "no_text") body.append(el("div", { class: "doc-msg warning", text: "File dạng ảnh scan, không được dùng để trả lời (BR-006)." }));
    if (d.status === "error" || d.status === "upload_failed") body.append(el("div", { class: "doc-msg error", text: d.error || "Không tải lên được. Kiểm tra kết nối rồi thử lại." }));
    if (d.status === "processing") body.append(el("div", { class: "doc-msg muted", text: "Có thể hỏi khi tài liệu sẵn sàng." }));

    const items = [];
    if (d.status === "error" || d.status === "upload_failed") items.push(el("button", { role: "menuitem", onclick: () => retryDoc(d) }, "Thử lại"));
    if (canRemove(d) && d.status !== "uploading") items.push(el("button", { role: "menuitem", class: "danger", onclick: () => confirmRemove(d) }, "Gỡ khỏi kho"));
    let menuWrap = el("span");
    if (items.length) {
      const menu = el("div", { class: "menu", role: "menu", hidden: S.openMenu !== d.id }, items);
      const btn = el("button", { class: "btn btn-ghost btn-icon", "aria-label": `Tuỳ chọn cho ${d.name}`, "aria-haspopup": "menu", "aria-expanded": S.openMenu === d.id ? "true" : "false",
        onclick: (e) => { e.stopPropagation(); S.openMenu = S.openMenu === d.id ? null : d.id; renderLibrary(); if (S.openMenu) setTimeout(() => $(`#doc-${d.id} .menu button`)?.focus(), 0); } }, "⋯");
      menuWrap = el("div", { class: "menu-wrap" }, btn, menu);
    }
    return el("li", { class: "doc", id: `doc-${d.id}`, title: d.name }, el("span", { class: "doc-icon", "aria-hidden": "true" }, st.icon), body, menuWrap);
  }

  function confirmRemove(d) {
    S.openMenu = null; renderLibrary();
    openDialog({
      title: "Gỡ tài liệu?",
      body: `“${d.name}” sẽ không còn được dùng cho câu trả lời mới của cả đội. Thao tác này không hoàn tác được.`,
      confirmLabel: "Gỡ tài liệu",
      onConfirm: () => {
        S.docs = S.docs.filter((x) => x !== d);
        d.removed = true;
        if (S.source && S.source.docId === d.id) renderSource();
        renderAll();
        toast(`Đã gỡ “${d.name}”.`, "success");
      },
    });
  }
  function retryDoc(d) { S.openMenu = null; d.error = null; if (d.status === "upload_failed") startUpload(d); else { d.status = "processing"; finishProcessing(d, 2500); } renderAll(); }

  // Upload simulation (F2)
  function handleFiles(files) {
    if (!S.online) { toast("Đang mất kết nối. Hãy thử lại khi có mạng.", "error"); return; }
    for (const f of files) {
      const isPdf = /\.pdf$/i.test(f.name) || f.type === "application/pdf";
      if (!isPdf) { toast(`“${f.name}”: chỉ hỗ trợ file PDF.`, "error"); continue; }
      if (f.size > 50 * 1024 * 1024) { toast(`“${f.name}”: file vượt 50 MB. Hãy tách file hoặc liên hệ trưởng nhóm.`, "error"); continue; }
      const dup = S.docs.find((d) => d.name === f.name);
      const add = () => {
        const d = { id: "u" + Date.now() + Math.random().toString(16).slice(2, 6), name: f.name, pages: null, status: "uploading", progress: 0, by: ME, date: new Date().toLocaleDateString("vi-VN") };
        S.docs.unshift(d); startUpload(d); renderAll();
      };
      if (dup) openDialog({ title: "File này đã có trong kho", body: `“${f.name}” đã được tải lên ngày ${dup.date}. Tải thêm bản trùng có thể làm câu trả lời bị lặp.`, confirmLabel: "Vẫn tải", danger: false, onConfirm: add });
      else add();
    }
  }
  function startUpload(d) {
    d.status = "uploading"; d.progress = d.progress || 0; d.attempt = 0;
    const tick = () => {
      if (!S.docs.includes(d)) return;
      if (!S.online) {
        d.attempt++; d.status = d.attempt > 3 ? "upload_failed" : "paused"; renderLibrary();
        if (d.status === "paused") setTimeout(tick, 2000);
        return;
      }
      d.status = "uploading";
      d.progress = Math.min(100, d.progress + 7 + Math.random() * 10);
      renderLibrary();
      if (d.progress < 100) setTimeout(tick, 180);
      else { d.status = "processing"; renderAll(); finishProcessing(d, 2600); }
    };
    setTimeout(tick, 150);
  }
  function finishProcessing(d, ms) {
    setTimeout(() => {
      if (!S.docs.includes(d) || d.status !== "processing" || S.holdProcessing) return;
      d.pages = d.pages || 8 + Math.floor(Math.random() * 30);
      if (/scan/i.test(d.name)) { d.status = "no_text"; toast(`“${d.name}” không có chữ đọc được (file scan), nên không được dùng để trả lời.`, "error"); }
      else { d.status = "ready"; toast(`“${d.name}” đã sẵn sàng để hỏi.`, "success"); }
      renderAll();
    }, ms);
  }

  // ---------------- Thread (§3.6.2 ChatThread, AnswerCard) ----------------
  function renderThread() {
    const root = $("#thread-inner");
    root.replaceChildren();
    const ready = readyDocs().length;
    if (!S.docs.length) {
      const drop = el("div", { class: "hero-drop", id: "hero-drop" },
        el("div", { class: "empty-icon", "aria-hidden": "true" }, "📥"),
        el("h2", { text: "Tải tài liệu PDF đầu tiên để bắt đầu hỏi" }),
        el("p", { class: "muted", text: "Kéo-thả file vào đây. Chỉ hỗ trợ PDF dạng văn bản, tối đa 50 MB mỗi file. Kho dùng chung cho cả đội BD." }),
        el("button", { class: "btn btn-primary btn-lg", onclick: () => $("#file-input").click() }, "Chọn file PDF"));
      bindDrop(drop);
      root.append(drop);
      return;
    }
    if (!S.turns.length) {
      root.append(el("div", { class: "empty" },
        el("div", { class: "empty-icon", "aria-hidden": "true" }, "💬"),
        el("h2", { text: ready ? `Hỏi bất cứ điều gì về ${ready} tài liệu trong kho` : "Đang chuẩn bị tài liệu…" }),
        el("p", { text: ready ? "Mỗi câu trả lời đều ghi rõ tài liệu và trang nguồn. Bấm vào [1], [2]… để mở đúng trang." : "Bạn có thể hỏi khi có ít nhất 1 tài liệu sẵn sàng." }),
        ready ? el("div", { class: "suggestions" }, SUGGESTIONS.map((s) => el("button", { class: "suggestion", disabled: !!composerDisabledReason(), onclick: () => ask(s) }, s))) : null));
      return;
    }
    S.turns.forEach((t, i) => root.append(el("div", { class: "q-bubble", text: t.q }), answerCard(t, i)));
  }

  function richText(text, turnIdx, cites, streaming) {
    const p = el("div", { class: `answer-text${streaming ? " streaming" : ""}` });
    text.split(/(\[\d+\])/).forEach((part) => {
      const m = part.match(/^\[(\d+)\]$/);
      if (!m) { p.append(part); return; }
      const idx = +m[1], c = cites[idx - 1];
      if (!c) { p.append(part); return; }
      const removed = !docById(c.docId);
      const active = S.source && S.source.turn === turnIdx && S.source.idx === idx;
      p.append(el("button", { class: `cite${removed ? " removed" : ""}`, "aria-pressed": active ? "true" : "false",
        "aria-label": `Nguồn ${idx}: ${c.file}, trang ${c.page}${removed ? " (tài liệu đã được gỡ)" : ""}`,
        title: removed ? "Tài liệu đã được gỡ" : `${c.file} — trang ${c.page}`,
        onclick: () => openSource(turnIdx, idx) }, String(idx)));
    });
    return p;
  }

  function answerCard(t, i) {
    const a = t.a, n = readyDocs().length;
    const card = el("article", { class: "answer", "aria-label": "Câu trả lời" });
    if (a.status === "searching") {
      card.append(el("div", { class: "answer-status" }, el("span", { class: "spinner", "aria-hidden": "true" }), `Đang tìm trong ${n} tài liệu…`));
      return card;
    }
    if (a.status === "not_found") {
      card.classList.add("not-found");
      card.append(el("h3", { style: "font-size:var(--text-base)" }, "🔎 Không tìm thấy thông tin này trong ", String(n), " tài liệu hiện có"),
        el("p", { class: "small", text: a.replaced ? "Câu trả lời vừa soạn không có trích dẫn hợp lệ nên đã được thay bằng thông báo này (EC-14). Bạn không nên dùng phần nội dung vừa hiện." : "Thử diễn đạt lại câu hỏi cụ thể hơn, hoặc tải thêm tài liệu liên quan." }),
        el("div", { class: "row" },
          el("button", { class: "btn btn-secondary", onclick: () => { const ta = $("#composer-input"); ta.value = t.q; ta.focus(); updateComposer(); } }, "Diễn đạt lại"),
          el("button", { class: "btn btn-ghost", onclick: () => $("#file-input").click() }, "Tải thêm tài liệu")));
      return card;
    }
    if (a.status === "failed") {
      card.classList.add("failed");
      card.append(el("p", { style: "margin:0 0 var(--space-3)" }, "⚠️ Chưa trả lời được lúc này. Vui lòng thử lại."),
        el("button", { class: "btn btn-primary", onclick: () => { S.turns.splice(i, 1); ask(t.q); } }, "Thử lại"));
      return card;
    }
    if (a.pendingNote) card.append(el("p", { class: "xs muted", text: a.pendingNote }));
    card.append(richText(a.shown, i, a.cites, a.status === "streaming"));
    if (a.status === "stopped") card.append(el("span", { class: "answer-tag", text: "⏹ Đã dừng — câu trả lời chưa đầy đủ" }));
    if (a.status === "incomplete") {
      card.classList.add("incomplete");
      card.append(el("span", { class: "answer-tag", text: "📶 Câu trả lời chưa hoàn chỉnh do mất kết nối" }),
        el("div", { class: "answer-actions" }, el("button", { class: "btn btn-secondary", onclick: () => { S.turns.splice(i, 1); ask(t.q); } }, "Hỏi lại")));
    }
    if (a.status === "completed") {
      const used = [...new Set((a.shown.match(/\[(\d+)\]/g) || []).map((x) => +x.slice(1, -1)))];
      card.append(el("div", { class: "sources" }, el("h4", { text: "Nguồn" }),
        el("ol", {}, used.map((idx) => {
          const c = a.cites[idx - 1], removed = !docById(c.docId);
          return el("li", {}, el("button", { class: "source-link", onclick: () => openSource(i, idx), "aria-label": `Mở nguồn ${idx}: ${c.file}, trang ${c.page}` },
            el("span", { class: `cite${removed ? " removed" : ""}`, "aria-hidden": "true" }, String(idx)),
            el("span", { style: removed ? "text-decoration:line-through;color:var(--color-text-muted)" : "" }, `${c.file} — trang ${c.page}`),
            removed ? el("span", { class: "xs muted", text: "(đã gỡ)" }) : null));
        }))));
      card.append(feedbackRow(t, i));
    }
    return card;
  }

  function feedbackRow(t) {
    const a = t.a;
    const row = el("div", { class: "answer-actions" });
    if (a.feedback === "sent") row.append(el("span", { class: "xs muted", text: "✓ Cảm ơn phản hồi của bạn" }));
    else {
      row.append(
        el("button", { class: "btn btn-ghost", "aria-pressed": a.feedback === "helpful" ? "true" : "false", onclick: () => { a.feedback = "sent"; toast("Cảm ơn! Phản hồi giúp đội cải thiện chất lượng câu trả lời.", "success"); renderThread(); } }, "👍 Hữu ích"),
        el("button", { class: "btn btn-ghost", "aria-pressed": a.feedback === "nothelpful" ? "true" : "false", "aria-expanded": a.feedback === "nothelpful" ? "true" : "false", onclick: () => { a.feedback = "nothelpful"; renderThread(); } }, "👎 Chưa tốt"));
    }
    row.append(el("button", { class: "btn btn-ghost", onclick: () => copyAnswer(a) }, "⧉ Sao chép kèm nguồn"));
    const wrap = el("div", {}, row);
    if (a.feedback === "nothelpful") {
      wrap.append(el("div", { class: "feedback-reasons", role: "group", "aria-label": "Lý do" },
        el("span", { class: "xs muted", text: "Vì sao?" }),
        ["Sai thông tin", "Thiếu ý", "Sai nguồn", "Khác"].map((r) => el("button", { class: "chip", onclick: () => { a.feedback = "sent"; toast(`Đã ghi nhận: “${r}”.`, "success"); renderThread(); } }, r))));
    }
    return wrap;
  }

  async function copyAnswer(a) {
    const used = [...new Set((a.shown.match(/\[(\d+)\]/g) || []).map((x) => +x.slice(1, -1)))];
    const txt = a.shown + "\n\nNguồn:\n" + used.map((i) => `[${i}] ${a.cites[i - 1].file} — trang ${a.cites[i - 1].page}`).join("\n");
    try { await navigator.clipboard.writeText(txt); toast("Đã sao chép câu trả lời kèm danh sách nguồn.", "success"); }
    catch { toast("Trình duyệt chặn sao chép tự động. Hãy chọn và sao chép thủ công.", "error"); }
  }

  // Q&A simulation (F3)
  function ask(text) {
    const q = text.trim();
    if (!q || S.streaming || composerDisabledReason()) return;
    const ready = readyDocs();
    const processing = S.docs.filter((d) => d.status === "processing").length;
    const turn = { q, a: { status: "searching", shown: "", cites: [], pendingNote: processing ? `${processing} tài liệu đang được xử lý, chưa được dùng cho câu trả lời này.` : "" } };
    S.turns.push(turn);
    $("#composer-input").value = ""; try { sessionStorage.removeItem("draft"); } catch {}
    S.streaming = { turn, timer: null };
    renderThread(); updateComposer(); scrollThread();
    announce(`Đang tìm trong ${ready.length} tài liệu`);

    const fail = S.failNext; S.failNext = false; $("#rv-fail").checked = false;
    setTimeout(() => {
      if (S.streaming?.turn !== turn) return;
      if (fail) return endStream(turn, "failed", 1200);
      if (/thời tiết|weather|giá vàng|bóng đá/i.test(q)) return endStream(turn, "not_found", 300);
      const key = /bảo hành/i.test(q) ? "uncited" : /báo giá|quý 3|hạng mục/i.test(q) ? "quote" : "payment";
      const src = ANSWERS[key];
      turn.a.cites = src.cites.map((c, i) => ({ ...c, idx: i + 1, file: docById(c.docId)?.name || "Tài liệu đã gỡ" }));
      turn.a.status = "streaming";
      let pos = 0;
      const step = () => {
        if (S.streaming?.turn !== turn) return;
        if (!S.online) { turn.a.status = "incomplete"; S.streaming = null; renderThread(); updateComposer(); return; }
        pos = Math.min(src.text.length, pos + 2 + Math.floor(Math.random() * 4));
        turn.a.shown = src.text.slice(0, pos);
        renderThread(); scrollThread();
        if (pos < src.text.length) S.streaming.timer = setTimeout(step, 35);
        else if (!turn.a.cites.length) { turn.a.replaced = true; endStream(turn, "not_found", 400); }
        else { endStream(turn, "completed", 150); }
      };
      step();
    }, 800);
  }
  function endStream(turn, status, delay) {
    setTimeout(() => {
      if (S.streaming?.turn !== turn) return;
      turn.a.status = status; S.streaming = null;
      renderThread(); updateComposer(); scrollThread();
      announce({ completed: `Câu trả lời đã xong, có ${turn.a.cites.length} nguồn`, not_found: "Không tìm thấy thông tin trong tài liệu", failed: "Chưa trả lời được, có nút thử lại" }[status] || "");
    }, delay);
  }
  function stopStream() {
    if (!S.streaming) return;
    clearTimeout(S.streaming.timer);
    const t = S.streaming.turn;
    t.a.status = t.a.shown ? "stopped" : "failed";
    S.streaming = null; renderThread(); updateComposer(); $("#composer-input").focus();
    announce("Đã dừng câu trả lời");
  }
  const scrollThread = () => { const th = $("#thread"); th.scrollTop = th.scrollHeight; };

  // ---------------- Source panel (US-305, EC-15, EC-16) ----------------
  function openSource(turnIdx, idx) {
    const c = S.turns[turnIdx]?.a.cites[idx - 1];
    if (!c) return;
    if (!docById(c.docId)) { toast("Tài liệu này đã được gỡ khỏi kho nên không mở được trang nguồn.", "error"); return; }
    S.source = { turn: turnIdx, idx, docId: c.docId, page: c.page, citePage: c.page, excerpt: c.excerpt };
    renderAll();
    $("#source-close").focus();
  }
  function renderSource() {
    const panel = $("#source-panel"), body = $("#ws-body");
    if (!S.source) { panel.hidden = true; body.classList.remove("source-open"); return; }
    panel.hidden = false; body.classList.add("source-open");
    const d = docById(S.source.docId);
    const content = $("#source-body");
    content.replaceChildren();
    if (!d) {
      $("#source-file").textContent = "Tài liệu đã được gỡ";
      $("#source-page").textContent = "";
      content.append(el("div", { class: "empty" }, el("div", { class: "empty-icon", "aria-hidden": "true" }, "🗑️"), el("h3", { text: "Tài liệu này vừa được gỡ khỏi kho" }), el("p", { text: "Trích dẫn vẫn hiển thị trong câu trả lời nhưng không còn mở được." })));
      return;
    }
    $("#source-file").textContent = d.name;
    $("#source-page").textContent = `Trang ${S.source.page} / ${d.pages}`;
    const filler = "Hai bên thống nhất các điều khoản dưới đây trên cơ sở bình đẳng, tự nguyện và cùng có lợi. Mọi sửa đổi, bổ sung phải được lập thành văn bản và có chữ ký của đại diện hợp pháp hai bên.";
    const page = el("div", { class: "pdf-page", role: "document", "aria-label": `Nội dung trang ${S.source.page}` },
      el("h5", { text: d.name.replace(/_/g, " ").replace(/\.pdf$/i, "").toUpperCase() }),
      el("p", { text: `Điều ${S.source.page + 2}. ${filler}` }));
    if (S.source.page === S.source.citePage) page.append(el("p", {}, "Theo đó, ", el("mark", { text: S.source.excerpt }), " " + filler));
    page.append(el("p", { text: filler }), el("p", { text: filler }));
    content.append(page);
    $("#page-prev").disabled = S.source.page <= 1;
    $("#page-next").disabled = S.source.page >= d.pages;
  }
  $("#source-close").addEventListener("click", () => { S.source = null; renderAll(); });
  $("#page-prev").addEventListener("click", () => { S.source.page--; renderSource(); });
  $("#page-next").addEventListener("click", () => { S.source.page++; renderSource(); });
  $("#open-full").addEventListener("click", () => toast("Trong sản phẩm: mở toàn bộ file trong vùng nguồn (PDF.js)."));

  // ---------------- Composer (§3.7 QuestionComposer) ----------------
  function composerDisabledReason() {
    if (S.session) return "Phiên đã hết hạn — đăng nhập lại để tiếp tục.";
    if (!S.online) return "Đang mất kết nối.";
    if (S.aiDown) return "Hỏi đáp tạm gián đoạn.";
    if (!S.docs.length) return "Tải tài liệu PDF đầu tiên để bắt đầu hỏi.";
    if (!readyDocs().length) return `Đang xử lý ${S.docs.filter((d) => d.status === "processing" || d.status === "uploading").length} tài liệu — bạn có thể hỏi khi có ít nhất 1 tài liệu sẵn sàng.`;
    return "";
  }
  function updateComposer() {
    const ta = $("#composer-input"), btn = $("#send-btn"), form = $("#composer");
    const reason = composerDisabledReason();
    ta.disabled = !readyDocs().length;
    form.classList.toggle("disabled", !!reason);
    $("#composer-hint").replaceChildren(...(reason ? [reason] : [el("kbd", {}, "Enter"), " gửi · ", el("kbd", {}, "Shift"), "+", el("kbd", {}, "Enter"), " xuống dòng"]));
    const len = ta.value.length, counter = $("#composer-counter");
    counter.textContent = `${len}/2000`;
    counter.className = "counter" + (len > 2000 ? " over" : len > 1800 ? " near" : "");
    ta.style.height = "auto"; ta.style.height = Math.min(ta.scrollHeight, 160) + "px";
    if (S.streaming) { btn.textContent = "⏹ Dừng"; btn.className = "btn btn-secondary"; btn.disabled = false; btn.setAttribute("aria-label", "Dừng câu trả lời đang soạn"); }
    else { btn.textContent = "Gửi"; btn.className = "btn btn-primary"; btn.disabled = !!reason || !ta.value.trim() || len > 2000; btn.removeAttribute("aria-label"); }
  }
  const ta = $("#composer-input");
  try { ta.value = sessionStorage.getItem("draft") || ""; } catch {}
  ta.addEventListener("input", () => { try { sessionStorage.setItem("draft", ta.value); } catch {} updateComposer(); });
  ta.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey && !e.isComposing) { e.preventDefault(); if (!S.streaming && ta.value.length <= 2000) ask(ta.value); } });
  $("#composer").addEventListener("submit", (e) => { e.preventDefault(); if (S.streaming) stopStream(); else if (ta.value.length <= 2000) ask(ta.value); });

  // ---------------- Drag & drop, inputs ----------------
  function bindDrop(target) {
    target.addEventListener("dragover", (e) => { e.preventDefault(); target.classList.add("drag-over"); });
    target.addEventListener("dragleave", () => target.classList.remove("drag-over"));
    target.addEventListener("drop", (e) => { e.preventDefault(); target.classList.remove("drag-over"); handleFiles([...e.dataTransfer.files]); });
  }
  bindDrop($("#doc-list"));
  window.addEventListener("dragover", (e) => e.preventDefault());
  window.addEventListener("drop", (e) => e.preventDefault());
  $("#upload-btn").addEventListener("click", () => $("#file-input").click());
  $("#file-input").addEventListener("change", (e) => { handleFiles([...e.target.files]); e.target.value = ""; });
  $("#doc-filter").addEventListener("input", (e) => { S.filter = e.target.value; renderLibrary(); });
  document.addEventListener("click", () => { if (S.openMenu) { S.openMenu = null; renderLibrary(); } });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    if (!$("#dialog").hidden) closeDialog();
    else if (S.openMenu) { S.openMenu = null; renderLibrary(); }
    else if (S.source) { S.source = null; renderAll(); }
    else if ($("#library").classList.contains("expanded")) toggleRail(false);
  });
  function toggleRail(force) {
    const lib = $("#library"), on = force ?? !lib.classList.contains("expanded");
    lib.classList.toggle("expanded", on);
    $("#rail-toggle").setAttribute("aria-expanded", String(on));
  }
  $("#rail-toggle").addEventListener("click", (e) => { e.stopPropagation(); toggleRail(); });
  $("#ai-retry").addEventListener("click", () => { S.aiDown = false; $("#rv-scenario").value = "normal"; renderAll(); toast("Hỏi đáp đã hoạt động trở lại.", "success"); });

  // ---------------- Review toolbar ----------------
  $("#rv-scenario").addEventListener("change", (e) => applyScenario(e.target.value));
  $("#rv-role").addEventListener("change", (e) => { S.role = e.target.value; renderAll(); });
  $("#rv-fail").addEventListener("change", (e) => (S.failNext = e.target.checked));
  $("#rv-min").addEventListener("click", (e) => { const bar = $("#review-bar"); bar.classList.toggle("min"); document.body.classList.toggle("review-min", bar.classList.contains("min")); e.target.textContent = bar.classList.contains("min") ? "Duyệt thiết kế" : "Thu gọn"; e.target.setAttribute("aria-expanded", String(!bar.classList.contains("min"))); });
  function applyScenario(v) {
    S.online = v !== "offline"; S.aiDown = v === "ai-down"; S.session = v === "session"; S.holdProcessing = v === "processing";
    if (v === "empty") { S.docs = []; S.turns = []; S.source = null; }
    else if (v === "processing") { S.docs = baseDocs().map((d) => ({ ...d, status: "processing", pages: null })); S.turns = []; S.source = null; }
    else if (!S.docs.length || S.docs.every((d) => d.status === "processing")) { S.docs = baseDocs(); scheduleAuto(); }
    renderAll();
  }
  function scheduleAuto() { S.docs.filter((d) => d.autoReady).forEach((d) => finishProcessing(d, d.autoReady)); }

  // ---------------- Render all ----------------
  function renderAll() {
    $("#banner-offline").hidden = S.online;
    $("#banner-ai").hidden = !S.aiDown;
    $("#banner-session").hidden = !S.session;
    $("#user-role").textContent = { member: "Thành viên BD", lead: "Trưởng nhóm BD", manager: "Quản lý" }[S.role];
    $("#nav-metrics").hidden = S.role === "member";
    $("#upload-btn").disabled = !S.online || S.session;
    renderLibrary(); renderThread(); renderSource(); updateComposer();
  }
  window.addEventListener("online", () => { if ($("#rv-scenario").value !== "offline") { S.online = true; renderAll(); } });
  window.addEventListener("offline", () => { S.online = false; renderAll(); });

  scheduleAuto();
  renderAll();

  // Liên kết trực tiếp tới một trạng thái: ?scenario=empty|processing|offline|ai-down|session · ?role=member|lead|manager · ?demo=answer|notfound|replaced|stopped|failed
  const params = new URLSearchParams(location.search);
  const sc = params.get("scenario"), rl = params.get("role"), demo = params.get("demo");
  if (rl && ["member", "lead", "manager"].includes(rl)) { $("#rv-role").value = rl; S.role = rl; renderAll(); }
  if (sc && [...$("#rv-scenario").options].some((o) => o.value === sc)) { $("#rv-scenario").value = sc; applyScenario(sc); }
  if (demo === "answer") { ask(SUGGESTIONS[0]); setTimeout(() => openSource(0, 1), 6500); }
  if (demo === "notfound") ask("Thời tiết hôm nay thế nào?");
  if (demo === "replaced") ask(SUGGESTIONS[2]);
  if (demo === "failed") { S.failNext = true; ask(SUGGESTIONS[0]); }
  if (demo === "stopped") { ask(SUGGESTIONS[0]); setTimeout(stopStream, 2200); }
})();
