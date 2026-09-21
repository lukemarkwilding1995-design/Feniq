"use strict";
const $ = (id) => document.getElementById(id);
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
let token = localStorage.getItem("feniq_token") || "",
  user = null,
  config = {},
  catalogue = [],
  screen = "dashboard",
  authMode = "login",
  draft = {},
  diagnosis = null,
  editing = null,
  activeJob = null,
  workOrderId = null,
  pageVersion = 0;
let photoUrls = [];
const outcomes = [
  "Adjusted / Resolved",
  "Parts Required",
  "Remake Required",
  "Further Investigation",
  "No Fault Found",
];
const statuses = [
  "New",
  "Scheduled",
  "In Progress",
  "Awaiting Approval",
  "Complete",
  "Cancelled",
];
const money = (n) =>
  new Intl.NumberFormat("en-GB", { style: "currency", currency: "GBP" }).format(
    n / 100,
  );
const date = (v) =>
  v
    ? new Date(v).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "Not scheduled";
const time = (v) =>
  v
    ? new Date(v).toLocaleTimeString("en-GB", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : "—";
const badge = (s) =>
  `<span class="badge ${/Resolved|Complete|Approved/.test(s) ? "good" : /Pending|Parts|Approval|Scheduled/.test(s) ? "warn" : /Reject|Remake|Urgent/.test(s) ? "bad" : "blue"}">${esc(s || "Draft")}</span>`;
const options = (items, value = "", placeholder = "") =>
  (placeholder ? `<option value="">${esc(placeholder)}</option>` : "") +
  items
    .map((x) => {
      let v = typeof x === "object" ? x.id : x,
        n = typeof x === "object" ? x.name : x;
      return `<option value="${esc(v)}" ${String(v) === String(value) ? "selected" : ""}>${esc(n)}</option>`;
    })
    .join("");
const field = (label, name, value = "", type = "text", extra = "") =>
  `<label>${esc(label)}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`;
const area = (label, name, value = "", extra = "") =>
  `<label>${esc(label)}<textarea name="${name}" ${extra}>${esc(value)}</textarea></label>`;
const select = (label, name, items, value = "", placeholder = "") =>
  `<label>${esc(label)}<select name="${name}">${options(items, value, placeholder)}</select></label>`;
const empty = (title, desc) =>
  `<div class="empty"><b>${esc(title)}</b><p>${esc(desc)}</p></div>`;
const head = (eyebrow, title, sub = "", action = "") =>
  `<div class="page-head"><div><div class="eyebrow">${eyebrow}</div><h1>${esc(title)}</h1><p>${esc(sub)}</p></div>${action}</div>`;
const newButton =
  '<button class="primary" data-action="new">+ New inspection</button>';
const stat = (label, value, note) =>
  `<div class="stat"><span>${label}</span><b>${value}</b><small>${note}</small></div>`;
function toast(message, error = false) {
  $("toast").textContent = message;
  $("toast").style.background = error ? "#923b32" : "#163e31";
  $("toast").style.display = "block";
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => ($("toast").style.display = "none"), 6500);
}
async function api(url, opts = {}) {
  let r = await fetch(url, {
    ...opts,
    headers: {
      ...(opts.headers || {}),
      ...(token ? { Authorization: "Bearer " + token } : {}),
    },
  });
  if (!r.ok) {
    let d;
    try {
      d = await r.json();
    } catch {
      d = { detail: "Request failed. Please try again." };
    }
    if (r.status === 401 && user) {
      signOut();
      throw Error("Your session expired. Please sign in again.");
    }
    throw Error(
      Array.isArray(d.detail)
        ? d.detail.map((x) => x.msg).join(". ")
        : d.detail || "Request failed",
    );
  }
  return (r.headers.get("content-type") || "").includes("json") ? r.json() : r;
}
const send = (url, data, method = "POST") =>
  api(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
async function busy(button, fn) {
  if (button?.disabled) return;
  const before = button?.textContent;
  if (button) {
    button.disabled = true;
    button.textContent = "Working…";
  }
  try {
    return await fn();
  } catch (e) {
    toast(e.message, true);
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = before;
    }
  }
}
function openModal(title, html) {
  $("modalBody").innerHTML =
    `<div class="dialog-head"><h2>${esc(title)}</h2><button data-action="close" aria-label="Close dialog">×</button></div>${html}`;
  $("modal").showModal();
}
function signOut() {
  token = "";
  user = null;
  localStorage.removeItem("feniq_token");
  $("shell").classList.add("hidden");
  $("auth").classList.remove("hidden");
  $("modal").close();
  photoUrls.forEach(URL.revokeObjectURL);
  photoUrls = [];
  renderAuth();
}
function renderAuth() {
  document
    .querySelectorAll("[data-auth]")
    .forEach((b) =>
      b.classList.toggle("selected", b.dataset.auth === authMode),
    );
  let html = "";
  if (authMode === "register")
    html += field(
      "Company name",
      "company_name",
      "",
      "text",
      'required maxlength="180"',
    );
  if (authMode === "join")
    html += field("Company invite code", "invite_code", "", "text", "required");
  if (authMode !== "login")
    html += field(
      "Your name",
      authMode === "register" ? "admin_name" : "name",
      "",
      "text",
      'required maxlength="180"',
    );
  html +=
    field(
      "Email address",
      "email",
      "",
      "email",
      'required autocomplete="email"',
    ) +
    field(
      "Password",
      "password",
      "",
      "password",
      `required ${authMode === "login" ? 'autocomplete="current-password"' : 'minlength="8" autocomplete="new-password"'}`,
    );
  $("authFields").innerHTML = html;
  $("authSubmit").textContent = {
    login: "Sign in",
    register: "Create company",
    join: "Join team",
  }[authMode];
  $("authError").textContent = "";
}
async function enter(data) {
  token = data.token;
  user = data.user;
  localStorage.setItem("feniq_token", token);
  catalogue = await api("/api/diagnostics/catalogue");
  $("auth").classList.add("hidden");
  $("shell").classList.remove("hidden");
  $("companyText").textContent = user.company;
  $("userName").textContent = user.name;
  $("roleText").textContent =
    user.role === "admin" ? "Company admin" : "Service engineer";
  $("avatar").textContent = user.name
    .split(" ")
    .map((x) => x[0])
    .slice(0, 2)
    .join("");
  $("demoBanner").classList.toggle(
    "hidden",
    !user.company.startsWith("FenIQ Demo"),
  );
  await go("dashboard");
}
$("authForm").onsubmit = async (e) => {
  e.preventDefault();
  const b = $("authSubmit");
  b.disabled = true;
  $("authError").textContent = "";
  try {
    await enter(
      await send(
        "/api/" +
          {
            login: "login",
            register: "register-company",
            join: "join-company",
          }[authMode],
        Object.fromEntries(new FormData(e.target)),
      ),
    );
  } catch (err) {
    $("authError").textContent = err.message;
  } finally {
    b.disabled = false;
  }
};
$("logout").onclick = signOut;
$("menuToggle").onclick = () =>
  document.querySelector(".sidebar").classList.toggle("open");
$("switchRole").onclick = () =>
  busy($("switchRole"), async () =>
    enter(
      await api(
        "/api/demo?role=" + (user.role === "admin" ? "engineer" : "admin"),
        { method: "POST" },
      ),
    ),
  );
async function go(id) {
  screen = id;
  const version = ++pageVersion;
  document.querySelector(".sidebar").classList.remove("open");
  document
    .querySelectorAll("[data-go]")
    .forEach((b) => b.classList.toggle("active", b.dataset.go === id));
  $("content").innerHTML = '<div class="loading">Loading your workspace…</div>';
  photoUrls.forEach(URL.revokeObjectURL);
  photoUrls = [];
  window.scrollTo(0, 0);
  try {
    let html = await pages[id]();
    if (version !== pageVersion) return;
    $("content").innerHTML = html;
    if (id === "report") await loadPhotos(activeJob);
    await updateNotifications();
  } catch (e) {
    if (version === pageVersion)
      $("content").innerHTML =
        empty("We couldn’t load this page", e.message) +
        '<button data-action="retry">Try again</button>';
  }
}
async function updateNotifications() {
  const ns = await api("/api/notifications");
  $("notificationButton").textContent =
    "Notifications" +
    (ns.filter((n) => !n.read).length
      ? ` (${ns.filter((n) => !n.read).length})`
      : "");
}
function jobTable(jobs) {
  if (!jobs.length)
    return empty(
      "No inspections yet",
      "Start a new inspection to capture your first service visit.",
    );
  return `<div class="table-wrap"><table><thead><tr><th>Site / reference</th><th>Product</th><th>Outcome</th><th>Inspected</th><th></th></tr></thead><tbody>${jobs.map((j) => `<tr><td><b>${esc(j.customer)}</b><small>${esc(j.reference || "No reference")}</small></td><td>${esc(j.product)}<small>${esc(j.engineer.name)}</small></td><td>${badge(j.outcome)}</td><td>${date(j.created_at)}</td><td><button data-report="${j.id}">View ↗</button></td></tr>`).join("")}</tbody></table></div>`;
}
function learningHistoryCards(items) {
  return items
    .map(
      (item) =>
        `<article class="visit"><div class="actions">${badge(item.decision)}${badge(item.status)}${badge("Revision " + item.outcome_version)}</div><p><b>Decision retained ${esc(date(item.created_at))}</b> · Inspection ${esc(item.job_id.slice(0, 8))}</p><p>${esc(item.reason)}</p><small>Outcome checksum ${esc(item.outcome_sha256.slice(0, 16))}… · ${item.source_integrity_valid ? "Source integrity verified" : "Source integrity check failed"}</small></article>`,
    )
    .join("");
}

function datasetCandidateCards(items) {
  return items
    .map(
      (item) =>
        `<article class="visit"><div class="actions">${badge(item.decision?.decision || "Second decision needed")}${badge("Outcome revision " + item.outcome_version)}</div><p class="muted">Prepared field-limited payload · SHA-256 ${esc(item.preview_sha256.slice(0, 16))}…</p><pre class="preview-code">${esc(JSON.stringify(item.preview, null, 2))}</pre>${item.decision ? `<p class="notice">${esc(item.decision.reason)}</p>` : `<form id="learningDatasetForm"><input type="hidden" name="outcome_revision_id" value="${esc(item.outcome_revision_id)}"><input type="hidden" name="outcome_sha256" value="${esc(item.outcome_sha256)}"><input type="hidden" name="preview_sha256" value="${esc(item.preview_sha256)}">${select("Second decision", "decision", ["Reject", "Approve local research"])}${area("Reason for decision", "reason", "", 'required minlength="5" maxlength="2000"')}<p class="error form-error" role="alert"></p><button class="primary">Retain dataset decision</button></form>`}</article>`,
    )
    .join("");
}

function datasetHistoryCards(items) {
  return items
    .map(
      (item) =>
        `<article class="visit"><div class="actions">${badge(item.decision)}${badge(item.status)}</div><p><b>Decision retained ${esc(date(item.created_at))}</b> · Outcome revision ${esc(item.outcome_version ?? "unknown")}</p><p>${esc(item.reason)}</p><small>Prepared checksum ${esc(item.preview_sha256.slice(0, 16))}… · ${item.preview_integrity_valid ? "Payload integrity verified" : "Payload integrity check failed"} · ${item.source_integrity_valid ? "Source integrity verified" : "Source integrity check failed"}</small></article>`,
    )
    .join("");
}

const pages = {
  async dashboard() {
    const [jobs, orders, approvals] = await Promise.all([
      api("/api/jobs"),
      api("/api/work-orders"),
      api("/api/approvals"),
    ]);
    const open = orders
      .filter((w) => !["Complete", "Cancelled"].includes(w.status))
      .sort((a, b) =>
        (a.scheduled_for || "z").localeCompare(b.scheduled_for || "z"),
      );
    return (
      head(
        "YOUR WORKSPACE",
        `Good to see you, ${user.name.split(" ")[0]}.`,
        "Here’s what’s happening across your service visits.",
        newButton,
      ) +
      `<div class="hero"><div><div class="eyebrow">KNOWLEDGE AT THE POINT OF REPAIR</div><h2>Every check brings you closer.</h2><p>Turn observations into a clear diagnosis, a considered repair and a report you can stand behind.</p><button class="primary" data-action="new">Start an inspection ↗</button> <button data-go="library">Explore field guides</button></div><div class="hero-mark" aria-hidden="true">▥</div></div><div class="stats">${stat("Inspections", jobs.length, "Saved service records")}${stat("Visits to complete", open.length, "Scheduled and active work")}${stat("Repairs resolved", jobs.filter((j) => j.outcome === "Adjusted / Resolved").length, "Confirmed in inspection records")}${stat("Awaiting approval", approvals.filter((a) => a.status === "Pending").length, "Commercial decisions")}</div><div class="grid"><section class="panel"><div class="panel-head"><h3>Recent inspections</h3><button data-go="jobs">View all ↗</button></div>${jobTable(jobs.slice(0, 5))}</section><section class="panel"><div class="panel-head"><h3>Upcoming visits</h3><button data-go="schedule">Schedule ↗</button></div>${
        open.length
          ? open
              .slice(0, 3)
              .map(
                (w) =>
                  `<div class="visit"><span class="visit-time">${date(w.scheduled_for)} · ${time(w.scheduled_for)}</span><h4>${esc(w.title)}</h4><small>${esc(w.site_reference || "No reference")}</small><button data-start-order="${w.id}">${w.job_id ? "Open inspection" : "Start inspection"} ↗</button></div>`,
              )
              .join("")
          : empty("All caught up", "Your next assigned visit will appear here.")
      }</section></div>`
    );
  },
  async jobs() {
    const jobs = await api("/api/jobs");
    pages.jobs.cache = jobs;
    return (
      head(
        "SERVICE RECORDS",
        "Inspections",
        "A clear record of every check, repair and outcome.",
        newButton,
      ) +
      `<div class="toolbar"><input id="jobSearch" aria-label="Search inspections" placeholder="Search site, reference or diagnosis…"><select id="jobFilter" aria-label="Filter outcomes">${options(outcomes, "", "All outcomes")}</select></div><div class="panel" id="jobResults">${jobTable(jobs)}</div>`
    );
  },
  async schedule() {
    const [orders, customers] = await Promise.all([
      api("/api/work-orders"),
      api("/api/customers"),
    ]);
    pages.schedule.orders = orders;
    pages.schedule.customers = customers;
    return (
      head(
        "SERVICE OPERATIONS",
        "Schedule",
        user.role === "admin"
          ? "Plan visits, assign your team and follow progress."
          : "Your assigned visits and follow-up work.",
        user.role === "admin"
          ? '<button class="primary" data-action="new-order">+ Schedule a visit</button>'
          : "",
      ) +
      `<div class="cards">${
        orders.length
          ? orders
              .sort((a, b) =>
                (a.scheduled_for || "z").localeCompare(b.scheduled_for || "z"),
              )
              .map(
                (w) =>
                  `<article class="panel"><div class="actions">${badge(w.status)}${badge(w.priority)}</div><h3 style="margin-top:18px">${esc(w.title)}</h3><p>${esc(customers.find((c) => c.id === w.customer_id)?.name || "No customer linked")}</p><div class="visit-time">${date(w.scheduled_for)} · ${time(w.scheduled_for)}</div><p class="muted">${esc(w.notes || "No visit notes")}</p><label>Status<select data-order-status="${w.id}">${options(statuses, w.status)}</select></label><div class="actions"><button class="primary" data-start-order="${w.id}">${w.job_id ? "Open inspection" : "Start inspection"}</button>${user.role === "admin" ? `<button data-edit-order="${w.id}">Edit visit</button>` : ""}</div></article>`,
              )
              .join("")
          : empty(
              "No visits scheduled",
              user.role === "admin"
                ? "Create a visit and assign it to a team member."
                : "Your admin can assign visits to you.",
            )
      }</div>`
    );
  },
  async customers() {
    const cs = await api("/api/customers");
    return (
      head(
        "CUSTOMER DIRECTORY",
        "Customers",
        "Site details close to the work they belong to.",
        '<button class="primary" data-action="new-customer">+ Add customer</button>',
      ) +
      `<div class="cards">${cs.length ? cs.map((c) => `<article class="panel"><div class="eyebrow">CUSTOMER / SITE</div><h3>${esc(c.name)}</h3><p>${esc(c.address || "No address recorded")}</p><p class="muted">${esc(c.contact_name)}<br>${esc(c.email)}<br>${esc(c.phone)}</p><button data-customer-inspect="${esc(c.name)}">New inspection ↗</button></article>`).join("") : empty("Your customer directory starts here", "Add a customer to use them when scheduling visits.")}</div>`
    );
  },
  async approvals() {
    const [as, js] = await Promise.all([
      api("/api/approvals"),
      api("/api/jobs"),
    ]);
    return (
      head(
        "COMMERCIAL DECISIONS",
        "Approvals",
        "Keep replacement parts, remakes and chargeable work accountable.",
      ) +
      `<div class="cards">${as.length ? as.map((a) => `<article class="panel">${badge(a.status)}${a.scope_current === false ? '<p class="notice">Historical or changed findings. This decision does not authorise the current inspection. Reject pending requests and submit a new one.</p>' : ""}<h3 style="margin-top:18px">${esc(a.approval_type)}</h3><small>${esc(js.find((j) => j.id === a.job_id)?.customer || "Inspection")}</small><p>${esc(a.description)}</p><h2>${money(a.estimated_cost_pence)}</h2>${a.decision_note ? `<p class="notice">${esc(a.decision_note)}</p>` : ""}<div class="actions"><button data-report="${a.job_id}">View inspection</button>${user.role === "admin" && a.status === "Pending" ? `<button class="primary" data-decision="${a.id}">Review request</button>` : ""}</div></article>`).join("") : empty("No approval requests", "Open an inspection to request approval for parts or further work.")}</div>`
    );
  },
  async library() {
    const gs = await api("/api/guides");
    pages.library.cache = gs;
    return (
      head(
        "FIELD KNOWLEDGE",
        "Knowledge library",
        "Practical guidance for considered, repeatable repairs.",
      ) +
      `<div class="toolbar"><input id="guideSearch" aria-label="Search guides" placeholder="Search hinges, gasket, locking, sliding…"></div><div class="notice">Field guides support professional judgement. Manufacturer-specific limits remain pending verification unless explicitly marked verified.</div><div class="cards" id="guideResults">${guideCards(gs)}</div>`
    );
  },
  async learning() {
    const [
      m,
      ps,
      a,
      reviewQueue,
      reviewHistory,
      datasetCandidates,
      dataset,
      datasetHistory,
    ] = await Promise.all([
      api("/api/learning/metrics"),
      api("/api/learning/patterns"),
      api("/api/analytics"),
      user.role === "admin" ? api("/api/learning/review-queue") : [],
      user.role === "admin"
        ? api("/api/learning/review-history")
        : { items: [], next_offset: null },
      user.role === "admin" ? api("/api/learning/dataset-candidates") : [],
      user.role === "admin"
        ? api("/api/learning/internal-dataset")
        : { count: 0 },
      user.role === "admin"
        ? api("/api/learning/dataset-history")
        : { items: [], next_offset: null },
    ]);
    return (
      head(
        "LEARN FROM THE WORK",
        "Repair insights",
        "Engineer-confirmed outcomes turn field experience into evidence.",
      ) +
      `<div class="stats">${stat("Confirmed outcomes", m.records, "Engineer feedback records")}${stat("Diagnosis confirmed", m.diagnosis_confirmation_rate + "%", "Matches the initial diagnosis")}${stat("Repair resolution", m.repair_resolution_rate + "%", "Of confirmed outcomes")}${stat("Repeat visits", m.repeat_visit_rate + "%", "Of confirmed outcomes")}</div><div class="grid"><div class="panel"><h3>Patterns from completed repairs</h3>${ps.length ? ps.map((p) => `<div class="visit"><h4>${esc(p.predicted_diagnosis)}</h4><p class="muted">${p.cases} confirmed cases · ${p.confirmation_rate}% diagnosis confirmed · ${p.resolution_rate}% resolved</p></div>`).join("") : empty("More experience, better insight", "Record a repair outcome from an inspection to begin.")}</div><div class="panel"><h3>Workspace snapshot</h3><p>${a.total} total inspections</p><p>${a.resolved} resolved · ${a.remakes} requiring remakes</p><h3>Dataset maturity</h3>${badge(m.learning_status)}<p class="muted">Average usefulness: ${m.average_engineer_rating} / 5</p><div class="notice">Outcomes are collected as evidence. They do not automatically change the diagnostic rules.</div></div></div>${user.role === "admin" ? `<section class="panel" style="margin-top:22px"><h2>Governed outcome review</h2><p class="muted">Only the latest opted-in outcome revision is eligible. A decision is retained against its checksum. “Prepare” means further de-identification work may begin; it does not anonymise the record, train AI, or change diagnostic rules.</p>${reviewQueue.length ? reviewQueue.map((item) => `<article class="visit"><div class="actions">${badge(item.review?.decision || "Awaiting review")}${badge("Revision " + item.outcome_version)}</div><h3>${esc(item.confirmed_diagnosis)}</h3><p>Predicted: ${esc(item.predicted_diagnosis)}</p><p>Actual repair: ${esc(item.actual_repair)}</p><p>${item.resolved ? "Resolved" : "Unresolved"} · Outcome checksum ${esc(item.outcome_sha256.slice(0, 16))}…</p>${item.review ? `<p class="notice">Review reason: ${esc(item.review.reason)}</p>` : `<form id="learningReviewForm"><input type="hidden" name="outcome_revision_id" value="${esc(item.outcome_revision_id)}"><input type="hidden" name="outcome_sha256" value="${esc(item.outcome_sha256)}">${select("Decision", "decision", ["Prepare for de-identification", "Exclude"])}${area("Reason for decision", "reason", "", 'required minlength="5" maxlength="2000"')}<p class="error form-error" role="alert"></p><button class="primary">Record review decision</button></form>`}</article>`).join("") : empty("No opted-in outcomes awaiting review", "Engineers can opt in when recording a repair outcome. Only current revisions appear here.")}</section>` : ""}` +
      (user.role === "admin"
        ? `<section class="panel" style="margin-top:22px"><h2>Field-limited research candidates</h2><p class="muted">${dataset.count} currently approved for local company research. Review the exact prepared fields before a separate decision. Customer/site details, photos, measurements, notes and free-text diagnoses or repairs are excluded. Source linkage remains in this company database; these records are not anonymous or cleared for model training or external sharing.</p>${datasetCandidates.length ? datasetCandidateCards(datasetCandidates) : empty("No prepared candidates", "A current opted-in outcome needs a first-stage “Prepare for de-identification” review and complete provenance.")}</section>`
        : "") +
      (user.role === "admin"
        ? `<section class="panel" style="margin-top:22px"><h2>Review decision history</h2><p class="muted">Retained decisions remain visible after corrections or consent withdrawal. Historical “Prepare” decisions never authorise use of a later revision.</p><div id="learningHistoryList">${reviewHistory.items.length ? learningHistoryCards(reviewHistory.items) : empty("No review decisions yet", "A company admin decision will appear here after it is recorded.")}</div><div class="actions" id="learningHistoryMore">${reviewHistory.next_offset === null ? "" : `<button data-review-history-next="${reviewHistory.next_offset}">Load older decisions</button>`}</div></section>`
        : "") +
      (user.role === "admin"
        ? `<section class="panel" style="margin-top:22px"><h2>Dataset decision history</h2><p class="muted">A later correction or opt-out removes an approved record from the active local dataset, while retaining the decision for audit.</p><div id="datasetHistoryList">${datasetHistory.items.length ? datasetHistoryCards(datasetHistory.items) : empty("No dataset decisions yet", "The separate approval or rejection will appear here.")}</div><div class="actions" id="datasetHistoryMore">${datasetHistory.next_offset === null ? "" : `<button data-dataset-history-next="${datasetHistory.next_offset}">Load older decisions</button>`}</div></section>`
        : "")
    );
  },
  async company() {
    const c = await api("/api/company");
    const us = user.role === "admin" ? await api("/api/company/users") : [];
    const events = user.role === "admin" ? await api("/api/audit") : [];
    return (
      head(
        "YOUR ORGANISATION",
        "Company & team",
        "A shared workspace with individual responsibilities.",
      ) +
      `<div class="grid"><div class="panel"><h3>${esc(c.name)}</h3>${c.invite_code ? `<p class="muted">Share this code with engineers you want to join your company.</p><div class="notice"><b>${esc(c.invite_code)}</b></div>` : "<p>Your administrator manages team invitations.</p>"}<h3>Team members</h3>${us.map((u) => `<div class="visit"><b>${esc(u.name)}</b><p class="muted">${esc(u.email)} · ${esc(u.role)}</p></div>`).join("")}</div><div class="panel"><h3>Recent activity</h3>${
        events.length
          ? events
              .slice(0, 12)
              .map(
                (e) =>
                  `<div class="visit"><b>${esc(e.action.replaceAll(".", " ").replaceAll("_", " "))}</b><small>${date(e.created_at)} · ${time(e.created_at)}</small></div>`,
              )
              .join("")
          : empty(
              "Activity will appear here",
              "Saved changes create an audit record for company admins.",
            )
      }</div></div>`
    );
  },
  async notifications() {
    const ns = await api("/api/notifications");
    return (
      head(
        "STAY IN THE LOOP",
        "Notifications",
        "Assignments and decisions relevant to you.",
      ) +
      `<div class="panel">${ns.length ? ns.map((n) => `<div class="visit"><div class="actions"><h4>${esc(n.title)}</h4>${!n.read ? badge("New") : ""}</div><p>${esc(n.body)}</p><small>${date(n.created_at)}</small>${!n.read ? `<button data-read="${n.id}">Mark as read</button>` : ""}</div>`).join("") : empty("Nothing new", "Updates about visits and approvals will appear here.")}</div>`
    );
  },
  async inspection() {
    return renderDetails();
  },
  async checks() {
    return renderChecks();
  },
  async result() {
    return renderResult();
  },
  async report() {
    const j = activeJob;
    const [snapshot, outcomes] = await Promise.all([
      api(`/api/jobs/${j.id}/diagnostic-snapshot`),
      api(`/api/jobs/${j.id}/outcome-history`),
    ]);
    return (
      head(
        "INSPECTION RECORD",
        j.reference || "Service report",
        j.customer,
        `<div class="actions"><button data-action="edit-job">Edit inspection</button><button class="primary" data-action="pdf">Download PDF ↓</button></div>`,
      ) +
      snapshotPanel(snapshot) +
      outcomeSummary(outcomes) +
      (await citationPanel(j)) +
      `<article class="panel"><div class="panel-head"><h2>FenIQ <small> / SERVICE REPORT</small></h2>${badge(j.approved_by_engineer ? "Engineer approved" : "Review required")}</div><div class="report-meta">${[
        ["Customer / site", j.customer],
        ["Product", j.product],
        ["System", j.system_name],
        ["Engineer", j.engineer.name],
        ["Date", date(j.created_at)],
        ["Outcome", j.outcome],
      ]
        .map(
          ([k, v]) =>
            `<div><small>${k}</small><b>${esc(v || "Not recorded")}</b></div>`,
        )
        .join("")}</div>${[
        ["Reported fault", j.fault],
        ["Diagnosis", j.diagnosis],
        ["Supporting evidence", j.evidence.join("\n")],
        ["Recommended action", j.recommendation],
        ["Work carried out", j.work_done],
        ["Parts / further requirements", j.parts_required],
        ["Engineer notes", j.engineer_notes],
        ["Customer sign-off", j.signature],
      ]
        .map(
          ([k, v]) =>
            `<section class="report-section"><h3>${k}</h3><p>${esc(v || "Not recorded")}</p></section>`,
        )
        .join(
          "",
        )}<div class="notice">${j.confidence}% rule score. Decision support, not a calibrated probability or a manufacturer specification.</div><h3>Photo evidence</h3><div id="reportPhotos" class="photos">${j.photos.length ? "Loading photos…" : "No photos attached yet."}</div><form id="photoForm" style="margin-top:20px"><div class="form-grid">${select("Evidence phase", "phase", ["before", "after"])}<label>JPG, PNG or WEBP<input type="file" name="photo" accept="image/jpeg,image/png,image/webp" required></label></div><button>Add photo</button></form>${config.vision_enabled && j.photos.length ? '<button data-action="analyse">Analyse first photo</button>' : ""}</article><div class="actions"><button class="primary" data-action="learning-form">Record repair outcome</button><button data-action="approval-form">Request commercial approval</button>${!j.approved_by_engineer ? '<button data-action="approve-job">Mark engineer reviewed</button>' : ""}</div>`
    );
  },
};
function outcomeSummary(rows) {
  if (!rows.length)
    return '<section class="panel" style="margin-bottom:20px"><h3>Repair outcome</h3><p>No retained repair outcome yet.</p></section>';
  const row = rows.at(-1);
  const p = row.payload;
  const checks = p.verification_definition
    ? `<p><b>${esc(p.verification_definition.title)} revision ${p.verification_definition.revision}</b></p><ul>${p.verification_definition.checks.map((check) => `<li>${esc(check.label)}: ${esc(p.verification_answers[check.key])}</li>`).join("")}</ul>`
    : '<p class="muted">No structured verification definition was retained for this legacy revision.</p>';
  return `<section class="panel" style="margin-bottom:20px"><div class="panel-head"><h3>Latest repair outcome</h3>${badge(p.resolved ? "Reported resolved" : "Not resolved")}</div><p><b>Actual repair:</b> ${esc(p.actual_repair)}</p><p><b>Final checks:</b> ${esc(p.verification_checks || "Not recorded in legacy feedback")}</p>${checks}<p><b>Confirmed diagnosis:</b> ${esc(p.confirmed_diagnosis)}</p><small>Retained revision ${row.version} of ${rows.length} · ${row.integrity_valid ? "Integrity checked" : "Integrity check failed"}. Earlier revisions remain available from Record repair outcome.</small></section>`;
}
function snapshotPanel(snapshot) {
  if (!snapshot)
    return '<div class="notice">Legacy inspection: no original diagnostic snapshot is available. Its current record will be preserved before the next edit or first repair feedback.</div>';
  const p = snapshot.payload;
  const measurements =
    p.answers === null
      ? "Typed measurements were not available for this record."
      : p.checks
          .filter((c) => Object.hasOwn(p.answers, c.key))
          .map((c) => {
            const value = p.answers[c.key];
            return `${c.label}: ${typeof value === "boolean" ? (value ? "Yes" : "No") : value}${c.unit ? " " + c.unit : ""}`;
          })
          .join("\n");
  const label =
    snapshot.origin === "server_diagnosis"
      ? "Original saved server diagnosis"
      : snapshot.origin === "legacy_capture"
        ? "Legacy record captured before later changes"
        : "Original engineer-entered record";
  return `<details class="panel" style="margin-bottom:20px"><summary><b>${label}</b> · ${snapshot.integrity_valid ? "Integrity checked" : "Integrity check failed"}</summary><p>${esc(p.diagnosis || "No diagnosis recorded")}</p><small>Captured ${esc(date(snapshot.captured_at))}. Later report edits do not change this snapshot.</small><h4>Original fault</h4><p>${esc(p.fault)}</p><h4>Original evidence</h4><p style="white-space:pre-wrap">${esc(p.evidence.join("\n"))}</p><h4>Original measurements and checks</h4><p style="white-space:pre-wrap">${esc(measurements)}</p><p style="overflow-wrap:anywhere"><small>Record SHA-256: ${esc(snapshot.sha256)}<br>Rule file SHA-256: ${esc(p.rules_sha256 || "Not recorded")}</small></p></details>`;
}
function guideCards(gs) {
  return gs.length
    ? gs
        .map(
          (g) =>
            `<article class="panel"><div class="eyebrow">FIELD GUIDE</div><h3>${esc(g.title)}</h3><p class="muted">${esc(g.summary)}</p>${badge(g.source_status.replaceAll("_", " "))}<p><button data-guide="${g.id}">Read guide ↗</button></p></article>`,
        )
        .join("")
    : empty("No matching guides", "Try another product or component name.");
}
function startInspection(customer = "", order = null) {
  draft = {
    customer,
    product: "French Door",
    outcome: "Further Investigation",
  };
  diagnosis = null;
  editing = null;
  workOrderId = order?.id || null;
  if (order) {
    draft.reference = order.site_reference;
    draft.fault = order.notes;
  }
  go("inspection");
}
function renderDetails() {
  return (
    head(
      "NEW INSPECTION",
      "Start with the essentials",
      "Capture the site and reported issue before physical checks.",
    ) +
    `<div class="stepper"><span class="current">1 · Details</span>→<span>2 · Physical checks</span>→<span>3 · Repair & report</span></div><form id="detailsForm" class="panel form-card"><div class="form-grid">${field("Customer / site", "customer", draft.customer, "text", 'required maxlength="255"')}${field("Job reference", "reference", draft.reference, "text", 'maxlength="120"')}${select("Product", "product", ["French Door", "Window", "Residential Door", "Bifold", "Sliding Door", "Tilt & Turn"], draft.product)}${field("System / manufacturer", "system_name", draft.system_name)}<div class="wide">${area("Reported fault", "fault", draft.fault, "required")}</div><div class="wide">${select("Diagnostic module", "module", catalogue, draft.module || catalogue.find((m) => m.products.includes(draft.product))?.id)}</div></div><div class="notice">Select the module that matches your physical investigation. No measurements or test results are assumed.</div><button class="primary">Continue to physical checks →</button></form>`
  );
}
function renderChecks() {
  const m = catalogue.find((x) => x.id === draft.module);
  return (
    head(
      "PHYSICAL EVIDENCE",
      m.name,
      "Record what you have actually checked on site.",
    ) +
    `<div class="stepper"><span>1 · Details</span>→<span class="current">2 · Physical checks</span>→<span>3 · Repair & report</span></div><form id="checksForm" class="panel form-card"><div class="form-grid">${m.checks
      .map((c) => {
        let value = draft.diagnostic_answers?.[c.key];
        let label =
          c.label +
          (c.unit ? " (" + c.unit + ")" : "") +
          (c.required ? " *" : "");
        return c.type === "number"
          ? field(
              label,
              c.key,
              value ?? "",
              "number",
              `step="any" min="0" ${c.required ? "required" : ""}`,
            )
          : `<label>${esc(label)}<select name="${c.key}" ${c.required ? "required" : ""}>${options(
              c.type === "bool"
                ? [
                    { id: "true", name: "Yes" },
                    { id: "false", name: "No" },
                  ]
                : c.options,
              value === undefined ? "" : String(value),
              "Select a finding…",
            )}</select></label>`;
      })
      .join(
        "",
      )}</div><div class="notice">FenIQ working rules support your investigation. Check approved manufacturer documentation before applying system-specific tolerances.</div><div class="actions"><button type="button" data-go="inspection">← Back</button><button class="primary">Run diagnosis →</button></div></form>`
  );
}
function renderResult() {
  const d = diagnosis;
  return (
    head(
      editing ? "UPDATE INSPECTION" : "DIAGNOSIS & REPAIR",
      editing
        ? "Complete the service record"
        : "From findings to a clear action",
      "Review the diagnosis and record what happened on site.",
    ) +
    `<div class="stepper"><span>1 · Details</span>→<span>2 · Physical checks</span>→<span class="current">3 · Repair & report</span></div><div class="grid"><form id="resultForm" class="panel"><h3>Repair record</h3>${editing ? field("Customer / site", "customer", draft.customer, "text", "required") : ""}${area("Work carried out", "work_done", draft.work_done)}${field("Parts / further requirements", "parts_required", draft.parts_required)}${select("Outcome", "outcome", outcomes, draft.outcome || "Further Investigation")}${area("Engineer notes", "engineer_notes", draft.engineer_notes)}${field("Customer sign-off name", "signature", draft.signature)}<label class="check"><input name="approved_by_engineer" type="checkbox" ${draft.approved_by_engineer ? "checked" : ""}>I have reviewed this diagnosis and service record.</label><p class="muted">Commercial approvals for parts, remakes or chargeable work are requested separately from the saved inspection.</p><div class="actions">${!editing ? '<button type="button" data-go="checks">← Back to checks</button>' : ""}<button class="primary">${editing ? "Save changes" : "Save inspection"} →</button></div></form><div><div class="panel"><div class="eyebrow">DIAGNOSTIC FINDING</div><h2>${esc(d.title)}</h2><div class="result-score"><span class="score">${d.confidence}%</span><span class="muted">Rule score<br><small>Not a calibrated probability</small></span></div><div class="bar"><span style="width:${Number(d.confidence)}%"></span></div><ul class="detail-list">${d.evidence.map((x) => `<li>${esc(x)}</li>`).join("")}</ul><h3>Recommended action</h3><p>${esc(d.recommendation)}</p>${d.repair_steps?.length ? `<h3>Repair sequence</h3><ol class="detail-list">${d.repair_steps.map((x) => `<li>${esc(x)}</li>`).join("")}</ol>` : ""}</div><div class="notice">Engineer review is required before acting on findings. Manufacturer values must be verified against approved sources.</div></div></div>`
  );
}
async function loadPhotos(j) {
  const container = $("reportPhotos");
  container.innerHTML = "";
  for (const p of j.photos) {
    try {
      const r = await api(p.url);
      const url = URL.createObjectURL(await r.blob());
      photoUrls.push(url);
      if (screen !== "report" || activeJob.id !== j.id) return;
      const fig = document.createElement("figure");
      fig.innerHTML = `<img alt="${esc(p.phase)} inspection evidence" src="${url}"><figcaption>${esc(p.phase)} · ${esc(p.name)}</figcaption>`;
      container.appendChild(fig);
    } catch (e) {
      container.textContent =
        "Some photo evidence could not be loaded. " + e.message;
    }
  }
  if (!j.photos.length) container.textContent = "No photos attached yet.";
}
async function showReport(id) {
  activeJob = await api("/api/jobs/" + id);
  await go("report");
}
async function orderForm(id = null) {
  const [customers, users, orders] = await Promise.all([
    api("/api/customers"),
    api("/api/company/users"),
    api("/api/work-orders"),
  ]);
  const w = orders.find((x) => x.id === id) || {};
  openModal(
    id ? "Edit service visit" : "Schedule a service visit",
    `<form id="orderForm" data-id="${id || ""}"><div class="form-grid"><div class="wide">${field("Visit title", "title", w.title, "text", 'required maxlength="240"')}</div>${select("Customer", "customer_id", customers, w.customer_id, "Select customer…")}${select("Assign to", "assigned_engineer_id", users, w.assigned_engineer_id, "Unassigned")}${field("Visit date & time", "scheduled_for", w.scheduled_for?.slice(0, 16), "datetime-local")}${select("Priority", "priority", ["Low", "Normal", "High", "Urgent"], w.priority || "Normal")}<div class="wide">${field("Site / job reference", "site_reference", w.site_reference)}${area("Visit notes", "notes", w.notes)}</div></div><input type="hidden" name="job_id" value="${esc(w.job_id || "")}"><p class="error form-error" role="alert"></p><button class="primary">Save visit</button></form>`,
  );
}
async function outcomeForm() {
  const j = activeJob;
  const [l, history, definition] = await Promise.all([
    api(`/api/jobs/${j.id}/learning`),
    api(`/api/jobs/${j.id}/outcome-history`),
    api(`/api/jobs/${j.id}/verification-definition`),
  ]);
  const latest = history.at(-1);
  const previousAnswers = latest?.payload.verification_answers || {};
  const structuredChecks = definition.checks
    .map((check) =>
      select(
        check.label,
        `verification_${check.key}`,
        ["Pass", "Fail", "Not checked"],
        previousAnswers[check.key] || "Not checked",
      ),
    )
    .join("");
  openModal(
    "Record repair outcome",
    `<form id="learningForm"><input type="hidden" name="expected_version" value="${latest?.version || 0}"><input type="hidden" name="verification_definition_id" value="${esc(definition.id)}"><input type="hidden" name="verification_definition_sha256" value="${esc(definition.sha256)}"><h3>${esc(definition.title)} · Revision ${definition.revision}</h3><p class="muted">${esc(definition.source_status)}. Complete every check; every required check must pass before reporting the fault resolved.</p><div class="form-grid">${structuredChecks}</div>${area("Final checks and observed results (required if resolved)", "verification_checks", latest?.payload.verification_checks || "", 'maxlength="10000"')}${area("Reason for correcting the previous outcome", "change_reason", "", latest ? 'required maxlength="2000"' : 'maxlength="2000"')}${field("Engineer-confirmed diagnosis", "confirmed_diagnosis", l?.confirmed_diagnosis || j.diagnosis, "text", "required")}${area("Actual repair carried out", "actual_repair", l?.actual_repair || j.work_done, "required")}<div class="form-grid">${select(
      "Did the repair resolve the fault?",
      "resolved",
      [
        { id: "true", name: "Yes" },
        { id: "false", name: "No" },
      ],
      String(l?.resolved ?? false),
    )}${select(
      "Is another visit required?",
      "repeat_visit_required",
      [
        { id: "false", name: "No" },
        { id: "true", name: "Yes" },
      ],
      String(l?.repeat_visit_required ?? false),
    )}${select("Part / remake correct?", "remake_or_part_correct", ["Not applicable", "Yes", "No"], l?.remake_or_part_correct || "Not applicable")}${select(
      "How useful was FenIQ?",
      "engineer_rating",
      [
        { id: 1, name: "1 · Not useful" },
        { id: 2, name: "2 · Slightly useful" },
        { id: 3, name: "3 · Useful" },
        { id: 4, name: "4 · Very useful" },
        { id: 5, name: "5 · Excellent" },
      ],
      l?.engineer_rating || 3,
    )}</div>${area("Feedback", "engineer_feedback", l?.engineer_feedback)}<label class="check"><input type="checkbox" name="anonymised_for_learning" ${l?.anonymised_for_learning ? "checked" : ""}>Permit consideration for future anonymised learning. This does not anonymise this record or automatically update any rules.</label><p class="error form-error" role="alert"></p><button class="primary">Save outcome</button></form><h3>Retained outcome history</h3>${
      history.length
        ? history
            .slice()
            .reverse()
            .map(
              (r) =>
                `<div class="visit"><strong>Revision ${r.version} - ${esc(new Date(r.created_at).toLocaleString())}</strong><p>${esc(r.payload.actual_repair)}</p><p>Final checks: ${esc(r.payload.verification_checks || "Not recorded in legacy feedback")}</p>${r.payload.verification_definition ? `<p>${esc(r.payload.verification_definition.title)} revision ${r.payload.verification_definition.revision}</p><ul>${r.payload.verification_definition.checks.map((check) => `<li>${esc(check.label)}: ${esc(r.payload.verification_answers[check.key])}</li>`).join("")}</ul>` : '<p class="muted">No structured verification definition was retained for this legacy revision.</p>'}<p>${r.payload.resolved ? "Reported resolved" : "Not resolved"} | ${r.integrity_valid ? "Integrity checked" : "Integrity check failed"}</p><small>${esc(r.payload.change_reason || r.payload.origin)}</small></div>`,
            )
            .join("")
        : "<p>No retained revisions yet. Existing feedback will be preserved on its next correction.</p>"
    }`,
  );
}
document.addEventListener("click", async (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.auth) {
    authMode = b.dataset.auth;
    renderAuth();
    return;
  }
  if (b.dataset.demo) {
    await busy(b, async () =>
      enter(await api("/api/demo?role=" + b.dataset.demo, { method: "POST" })),
    );
    return;
  }
  if (b.dataset.go) {
    await go(b.dataset.go);
    return;
  }
  if (b.dataset.report) {
    await busy(b, () => showReport(b.dataset.report));
    return;
  }
  if (b.dataset.reviewHistoryNext) {
    await busy(b, async () => {
      const page = await api(
        `/api/learning/review-history?offset=${Number(b.dataset.reviewHistoryNext)}`,
      );
      $("learningHistoryList").insertAdjacentHTML(
        "beforeend",
        learningHistoryCards(page.items),
      );
      $("learningHistoryMore").innerHTML =
        page.next_offset === null
          ? ""
          : `<button data-review-history-next="${page.next_offset}">Load older decisions</button>`;
    });
    return;
  }
  if (b.dataset.datasetHistoryNext) {
    await busy(b, async () => {
      const page = await api(
        `/api/learning/dataset-history?offset=${Number(b.dataset.datasetHistoryNext)}`,
      );
      $("datasetHistoryList").insertAdjacentHTML(
        "beforeend",
        datasetHistoryCards(page.items),
      );
      $("datasetHistoryMore").innerHTML =
        page.next_offset === null
          ? ""
          : `<button data-dataset-history-next="${page.next_offset}">Load older decisions</button>`;
    });
    return;
  }
  if (b.dataset.customerInspect) {
    startInspection(b.dataset.customerInspect);
    return;
  }
  if (b.dataset.startOrder) {
    await busy(b, async () => {
      const orders = await api("/api/work-orders"),
        w = orders.find((x) => x.id === b.dataset.startOrder);
      if (w.job_id) {
        await showReport(w.job_id);
        return;
      }
      const cs = await api("/api/customers");
      startInspection(cs.find((c) => c.id === w.customer_id)?.name || "", w);
    });
    return;
  }
  if (b.dataset.editOrder) {
    await busy(b, () => orderForm(b.dataset.editOrder));
    return;
  }
  if (b.dataset.read) {
    await busy(b, async () => {
      await api(`/api/notifications/${b.dataset.read}/read`, {
        method: "POST",
      });
      await go("notifications");
    });
    return;
  }
  if (b.dataset.guide) {
    await busy(b, async () => {
      let g = await api("/api/guides/" + b.dataset.guide);
      openModal(
        g.title,
        `<p>${esc(g.summary)}</p>${badge(g.source_status.replaceAll("_", " "))}<ol class="detail-list">${g.steps.map((s) => `<li>${esc(s)}</li>`).join("")}</ol><div class="notice">${g.warnings.map(esc).join("<br>")}</div>`,
      );
    });
    return;
  }
  if (b.dataset.decision) {
    openModal(
      "Review commercial request",
      `<form id="decisionForm" data-id="${b.dataset.decision}"><p class="muted">Approval requires engineer review and unchanged inspection findings. Rejected requests can be replaced with a new request.</p>${select("Decision", "status", ["Approved", "Rejected"])}${area("Decision note", "decision_note", "", "required")}<p class="error form-error" role="alert"></p><button class="primary">Save decision</button></form>`,
    );
    return;
  }
  const action = b.dataset.action;
  if (!action) return;
  if (action === "close") {
    $("modal").close();
    return;
  }
  if (action === "new") {
    startInspection();
    return;
  }
  if (action === "retry") {
    go(screen);
    return;
  }
  if (action === "new-order") {
    await busy(b, () => orderForm());
    return;
  }
  if (action === "new-customer") {
    openModal(
      "Add a customer",
      `<form id="customerForm"><div class="form-grid">${field("Customer / site name", "name", "", "text", 'required maxlength="200"')}${field("Contact name", "contact_name")}${field("Email", "email", "", "email")}${field("Phone", "phone", "", "tel")}<div class="wide">${area("Site address", "address")}</div></div><p class="error form-error" role="alert"></p><button class="primary">Save customer</button></form>`,
    );
    return;
  }
  if (action === "edit-job") {
    draft = { ...activeJob };
    editing = activeJob.id;
    workOrderId = null;
    diagnosis = {
      title: draft.diagnosis,
      confidence: draft.confidence,
      evidence: draft.evidence,
      recommendation: draft.recommendation,
    };
    await go("result");
    return;
  }
  if (action === "learning-form") {
    await busy(b, outcomeForm);
    return;
  }
  if (action === "approval-form") {
    openModal(
      "Request commercial approval",
      `<form id="approvalForm">${select("Request type", "approval_type", ["Replacement part", "Sash remake", "Full frame remake", "Chargeable repair", "Warranty escalation", "Further investigation"])}${area("Reason and supporting details", "description", "", "required")}${field("Estimated cost (£)", "cost", "", "number", 'required min="0" step="0.01"')}<p class="muted">Your company administrator will receive this request.</p><p class="error form-error" role="alert"></p><button class="primary">Submit request</button></form>`,
    );
    return;
  }
  if (action === "approve-job") {
    await busy(b, async () => {
      await api(`/api/jobs/${activeJob.id}/approve`, { method: "PATCH" });
      await showReport(activeJob.id);
      toast("Inspection marked as engineer reviewed");
    });
    return;
  }
  if (action === "pdf") {
    await busy(b, async () => {
      const r = await api(`/api/jobs/${activeJob.id}/report.pdf`),
        url = URL.createObjectURL(await r.blob()),
        a = document.createElement("a");
      a.href = url;
      a.download = `FenIQ-${activeJob.reference || activeJob.id.slice(0, 8)}.pdf`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 60000);
      toast("Report downloaded");
    });
    return;
  }
  if (action === "analyse") {
    await busy(b, async () => {
      let d = await api(`/api/photos/${activeJob.photos[0].id}/analyse`, {
        method: "POST",
      });
      openModal(
        "Photo observations",
        Object.entries(d)
          .filter(([k, v]) => Array.isArray(v))
          .map(
            ([k, v]) =>
              `<h3>${esc(k.replaceAll("_", " "))}</h3><ul>${v.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`,
          )
          .join(""),
      );
    });
    return;
  }
});
document.addEventListener("submit", async (e) => {
  const form = e.target;
  if (
    form.id === "authForm" ||
    form.id.startsWith("citation") ||
    form.id === "sourceReviewForm" ||
    form.id.startsWith("case") ||
    form.id.startsWith("passport") ||
    form.id === "siteForm"
  )
    return;
  e.preventDefault();
  const b = form.querySelector('button:not([type="button"])');
  if (b?.disabled) return;
  const data = Object.fromEntries(new FormData(form));
  await busy(b, async () => {
    try {
      if (form.id === "detailsForm") {
        draft = { ...draft, ...data };
        await go("checks");
      }
      if (form.id === "checksForm") {
        const checks = catalogue.find((m) => m.id === draft.module).checks;
        draft.diagnostic_answers = {};
        for (const c of checks) {
          if (data[c.key] !== "")
            draft.diagnostic_answers[c.key] =
              c.type === "bool"
                ? data[c.key] === "true"
                : c.type === "number"
                  ? Number(data[c.key])
                  : data[c.key];
        }
        diagnosis = await send("/api/diagnostics/run", {
          module_id: draft.module,
          answers: draft.diagnostic_answers,
        });
        await go("result");
      }
      if (form.id === "resultForm") {
        draft = {
          ...draft,
          ...data,
          approved_by_engineer: form.elements.approved_by_engineer.checked,
          diagnosis: diagnosis.title,
          confidence: diagnosis.confidence,
          evidence: diagnosis.evidence,
          recommendation: diagnosis.recommendation,
          work_order_id: workOrderId,
        };
        activeJob = await send(
          "/api/jobs" + (editing ? "/" + editing : ""),
          draft,
          editing ? "PATCH" : "POST",
        );
        editing = activeJob.id;
        await go("report");
        toast(
          "Inspection saved. Add photos or record the repair outcome below.",
        );
      }
      if (form.id === "customerForm") {
        await send("/api/customers", data);
        $("modal").close();
        await go("customers");
        toast("Customer added");
      }
      if (form.id === "orderForm") {
        data.customer_id = data.customer_id || null;
        data.job_id = data.job_id || null;
        data.assigned_engineer_id = data.assigned_engineer_id
          ? Number(data.assigned_engineer_id)
          : null;
        await send(
          "/api/work-orders" + (form.dataset.id ? "/" + form.dataset.id : ""),
          data,
          form.dataset.id ? "PATCH" : "POST",
        );
        $("modal").close();
        await go("schedule");
        toast("Visit saved");
      }
      if (form.id === "approvalForm") {
        await send("/api/approvals", {
          job_id: activeJob.id,
          approval_type: data.approval_type,
          description: data.description,
          estimated_cost_pence: Math.round(Number(data.cost) * 100),
        });
        $("modal").close();
        await go("approvals");
        toast("Approval requested");
      }
      if (form.id === "decisionForm") {
        await send(`/api/approvals/${form.dataset.id}/decision`, data);
        $("modal").close();
        await go("approvals");
        toast("Decision recorded");
      }
      if (form.id === "learningForm") {
        const verificationAnswers = {};
        for (const [key, value] of Object.entries(data)) {
          if (!key.startsWith("verification_")) continue;
          if (
            key !== "verification_definition_id" &&
            key !== "verification_definition_sha256"
          ) {
            verificationAnswers[key.slice("verification_".length)] = value;
            delete data[key];
          }
        }
        await send(`/api/jobs/${activeJob.id}/learning`, {
          ...data,
          verification_answers: verificationAnswers,
          resolved: data.resolved === "true",
          repeat_visit_required: data.repeat_visit_required === "true",
          engineer_rating: Number(data.engineer_rating),
          anonymised_for_learning:
            form.elements.anonymised_for_learning.checked,
        });
        $("modal").close();
        await go("learning");
        toast("Repair outcome saved");
      }
      if (form.id === "learningReviewForm") {
        await send("/api/learning/reviews", data);
        await go("learning");
        toast("Review decision retained");
      }
      if (form.id === "learningDatasetForm") {
        await send("/api/learning/dataset-decisions", data);
        await go("learning");
        toast("Dataset decision retained");
      }
      if (form.id === "photoForm") {
        const fd = new FormData(form);
        const file = fd.get("photo");
        if (file.size > 10 * 1024 * 1024)
          throw Error("Choose an image smaller than 10 MB.");
        const upload = new FormData();
        upload.append("phase", data.phase);
        upload.append("file", file);
        await api(`/api/jobs/${activeJob.id}/photos`, {
          method: "POST",
          body: upload,
        });
        await showReport(activeJob.id);
        toast("Photo evidence attached");
      }
    } catch (err) {
      const error = form.querySelector(".form-error");
      if (error) error.textContent = err.message;
      throw err;
    }
  });
});
document.addEventListener("change", async (e) => {
  if (e.target.dataset.orderStatus) {
    await busy(null, async () => {
      try {
        await api(
          `/api/work-orders/${e.target.dataset.orderStatus}/status?status=${encodeURIComponent(e.target.value)}`,
          { method: "PATCH" },
        );
        toast("Visit status updated");
      } finally {
        await go("schedule");
      }
    });
  }
  if (e.target.id === "jobFilter") filterJobs();
});
function filterJobs() {
  const q = $("jobSearch").value.toLowerCase(),
    status = $("jobFilter").value;
  $("jobResults").innerHTML = jobTable(
    pages.jobs.cache.filter(
      (j) =>
        (j.customer + " " + j.reference + " " + j.diagnosis + " " + j.product)
          .toLowerCase()
          .includes(q) &&
        (!status || j.outcome === status),
    ),
  );
}
document.addEventListener("input", (e) => {
  if (e.target.id === "jobSearch") filterJobs();
  if (e.target.id === "guideSearch") {
    const q = e.target.value.toLowerCase();
    $("guideResults").innerHTML = guideCards(
      pages.library.cache.filter((g) =>
        (g.title + " " + g.summary).toLowerCase().includes(q),
      ),
    );
  }
});
(async () => {
  renderAuth();
  try {
    config = await api("/api/config");
    $("demoAccess").classList.toggle("hidden", !config.demo_enabled);
    if (token) {
      const u = await api("/api/me");
      await enter({ token, user: u });
    }
  } catch (e) {
    signOut();
    if (!/bearer|token/i.test(e.message)) toast(e.message, true);
  }
})();
// Preserve entered values when moving backwards through the inspection wizard.
document.addEventListener("input", (e) => {
  const f = e.target.form;
  if (!f || !e.target.name) return;
  if (["detailsForm", "resultForm"].includes(f.id))
    draft[e.target.name] =
      e.target.type === "checkbox" ? e.target.checked : e.target.value;
  if (f.id === "checksForm") {
    const c = catalogue
      .find((m) => m.id === draft.module)
      ?.checks.find((c) => c.key === e.target.name);
    if (!c) return;
    draft.diagnostic_answers ??= {};
    if (e.target.value === "") delete draft.diagnostic_answers[c.key];
    else
      draft.diagnostic_answers[c.key] =
        c.type === "bool"
          ? e.target.value === "true"
          : c.type === "number"
            ? Number(e.target.value)
            : e.target.value;
  }
});
document.addEventListener("change", (e) => {
  if (e.target.form?.id === "detailsForm" && e.target.name === "module")
    draft.diagnostic_answers = {};
});
// Private source documents are loaded only through company-authorised endpoints.
pages.library = async function () {
  const [guides, docs] = await Promise.all([
    api("/api/guides"),
    api("/api/documents"),
  ]);
  pages.library.cache = guides;
  pages.library.documents = docs;
  const makers = [...new Set(docs.map((d) => d.manufacturer))].sort();
  const categories = [...new Set(docs.map((d) => d.category))].sort();
  return (
    head(
      "KNOWLEDGE AT THE POINT OF WORK",
      "Technical library",
      "Search your field guides, manufacturer manuals and repair videos.",
    ) +
    `<div class="stats">${stat("Source documents", docs.filter((d) => d.media_type !== "video").length, "Private company library")}${stat("Repair videos", docs.filter((d) => d.media_type === "video").length, "Original training material")}${stat("PDF pages", docs.reduce((n, d) => n + d.page_count, 0).toLocaleString(), "Text search where available")}${stat("Field guides", guides.length, "Practical repair sequences")}</div><div class="toolbar"><input id="documentSearch" aria-label="Search technical documents" placeholder="Search manuals, systems or words inside PDFs…"><select id="manufacturerFilter" aria-label="Manufacturer filter">${options(makers, "", "All manufacturers")}</select><select id="categoryFilter" aria-label="Document category">${options(categories, "", "All categories")}</select></div><div class="notice">Private source library. Issue and system labels come from the supplied filenames. Documents are indexed for reference; their technical values have not been approved as diagnostic rules.</div><div id="documentResults" class="cards">${documentCards(docs)}</div><div class="panel-head" style="margin-top:38px"><h2>Field guides</h2></div><div class="toolbar"><input id="guideSearch" aria-label="Search guides" placeholder="Search field guides…"></div><div class="cards" id="guideResults">${guideCards(guides)}</div>`
  );
};
function documentCards(docs) {
  return docs.length
    ? docs
        .map(
          (d) =>
            `<article class="panel"><div class="eyebrow">${esc(d.manufacturer)} / ${d.media_type === "video" ? "VIDEO" : "PDF"}</div><h3>${esc(d.title)}</h3>${badge(d.source_review?.status || "Pending review")}${d.media_type !== "video" ? `<p><button data-source-review="${d.id}">Source review</button></p>` : ""}<p class="muted">${esc(d.category)}</p><div class="actions">${(d.systems || []).map(badge).join("")}${d.page_count ? badge(d.page_count + " pages") : ""}</div><p><small>${esc(d.revision)} · ${(d.size_bytes / 1048576).toFixed(1)} MB</small></p>${d.media_type !== "video" && !d.text_indexed ? '<p class="muted">Image-only document: browse pages or search its title. Text extraction needs review or OCR.</p>' : ""}${
              d.matches?.length
                ? `<div class="search-matches">${d.matches
                    .slice(0, 3)
                    .map(
                      (m) =>
                        `<p><button data-document="${d.id}" data-page="${m.page}">Page ${m.page} ↗</button><small>${esc(m.excerpt)}…</small></p>`,
                    )
                    .join("")}</div>`
                : ""
            }<button class="primary" data-document="${d.id}">${d.media_type === "video" ? "Watch video" : "Open PDF"} ↗</button></article>`,
        )
        .join("")
    : empty(
        "No matching source documents",
        "Try a broader search or another manufacturer.",
      );
}
let documentRequest = 0;
async function searchDocuments() {
  const request = ++documentRequest;
  const query = new URLSearchParams({
    q: $("documentSearch").value,
    manufacturer: $("manufacturerFilter").value,
    category: $("categoryFilter").value,
  });
  try {
    const docs = await api("/api/documents?" + query);
    if (screen === "library" && request === documentRequest)
      $("documentResults").innerHTML = documentCards(docs);
  } catch (e) {
    toast(e.message, true);
  }
}
document.addEventListener("input", (e) => {
  if (e.target.id === "documentSearch") {
    clearTimeout(searchDocuments.timer);
    searchDocuments.timer = setTimeout(searchDocuments, 250);
  }
});
document.addEventListener("change", (e) => {
  if (["manufacturerFilter", "categoryFilter"].includes(e.target.id))
    searchDocuments();
});

let viewingDocument = null,
  viewingPage = 1,
  viewerRequest = 0;
async function renderDocumentPage(page) {
  const request = ++viewerRequest;
  viewingPage = page;
  $("documentPageLabel").textContent =
    `PDF page ${page} of ${viewingDocument.page_count}`;
  $("documentPage").innerHTML =
    '<div class="loading">Rendering source page…</div>';
  $("previousPage").disabled = page <= 1;
  $("nextPage").disabled = page >= viewingDocument.page_count;
  try {
    const response = await api(
      `/api/documents/${viewingDocument.id}/pages/${page}`,
    );
    const url = URL.createObjectURL(await response.blob());
    photoUrls.push(url);
    if (request !== viewerRequest) return;
    $("documentPage").innerHTML =
      `<img src="${url}" alt="${esc(viewingDocument.title)}, PDF page ${page}" style="display:block;width:100%;height:auto">`;
  } catch (e) {
    $("documentPage").innerHTML = empty(
      "This page could not be rendered",
      e.message,
    );
  }
}
document.addEventListener("click", async (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.document) {
    await busy(b, async () => {
      const d = pages.library.documents.find(
        (x) => x.id === b.dataset.document,
      );
      if (!d) throw Error("Document unavailable. Reload the library.");
      viewingDocument = d;
      if (d.media_type === "video") {
        const r = await api(d.url),
          url = URL.createObjectURL(await r.blob());
        photoUrls.push(url);
        openModal(
          d.title,
          `<p class="muted">${esc(d.manufacturer)} · Private training video</p><video controls playsinline preload="metadata" style="width:100%;max-height:65vh" src="${url}"></video><p><button data-action="download-document">Download original ↓</button></p>`,
        );
      } else {
        openModal(
          d.title,
          `<p class="muted">${esc(d.manufacturer)} · ${esc(d.revision)} · Private source</p><div class="actions"><button id="previousPage" data-action="previous-page">← Previous</button><span id="documentPageLabel"></span><button id="nextPage" data-action="next-page">Next →</button><button data-action="download-document">Original PDF ↓</button></div><div id="documentPage" style="margin-top:16px;min-height:260px"></div><p class="muted">PDF page numbers can differ from printed page/section labels.</p><small>Source integrity: ${esc(d.sha256.slice(0, 16))}…</small>`,
        );
        await renderDocumentPage(Number(b.dataset.page || 1));
      }
    });
    return;
  }
  if (b.dataset.action === "previous-page")
    await renderDocumentPage(Math.max(1, viewingPage - 1));
  if (b.dataset.action === "next-page")
    await renderDocumentPage(
      Math.min(viewingDocument.page_count, viewingPage + 1),
    );
  if (b.dataset.action === "download-document")
    await busy(b, async () => {
      const r = await api(viewingDocument.url),
        url = URL.createObjectURL(await r.blob()),
        a = document.createElement("a");
      photoUrls.push(url);
      a.href = url;
      a.download = viewingDocument.source_filename;
      a.click();
    });
});
