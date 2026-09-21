let activePassport = null;
pages.passports = async function () {
  const [products, sites] = await Promise.all([
    api("/api/passports"),
    api("/api/sites"),
  ]);
  return (
    head(
      "PRODUCT LIFECYCLE",
      "Product passports",
      "A persistent identity for each installed window or door.",
      user.role === "admin"
        ? '<div class="actions"><button data-passport-action="site">Add site</button><button class="primary" data-passport-action="create">Create passport</button></div>'
        : "",
    ) +
    '<div class="notice">Product details are supplied by your team. They are not verified manufacturer specifications. Lifecycle notes are shared within your company; linked inspection reports retain their existing access restrictions.</div>' +
    `<div class="cards">${products.length ? products.map((p) => `<article class="panel"><div class="eyebrow">${esc(p.product)}</div><h3>${esc(p.label)}</h3><p>${esc(sites.find((s) => s.id === p.site_id)?.name || "Site")}</p><p class="muted">${esc(p.manufacturer)} ${esc(p.system_name)}</p><p><small>Serial: ${esc(p.serial_number || "Not recorded")}</small></p><button data-passport-id="${p.id}">Open passport →</button></article>`).join("") : empty("No products registered yet", "An administrator can add a site and register the first product.")}</div>` +
    `<section class="panel" style="margin-top:24px"><h3>Registered sites</h3>${sites.length ? sites.map((s) => `<div class="visit"><b>${esc(s.name)}</b><p>${esc(s.address || "Address not recorded")}</p></div>`).join("") : "<p>No sites registered. Existing customers remain available when adding a site.</p>"}</section>`
  );
};
pages.passport = async function () {
  const d = await api("/api/passports/" + activePassport);
  const p = d.passport;
  const analysis = d.failure_analysis;
  const patterns = analysis.patterns
    .map(
      (item) =>
        `<div class="visit"><div class="actions"><h4>${esc(item.diagnosis)}</h4>${badge(item.signal)}</div><p>${item.cases} linked inspection${item.cases === 1 ? "" : "s"} · ${item.resolved} resolved · ${item.not_resolved} not resolved · ${item.outcome_not_recorded} without retained outcome</p><p>${item.original_snapshot_cases} based on immutable original diagnosis · ${item.repeat_visit_required} requiring another visit</p>${item.requires_review ? '<p class="notice">Repeated diagnosis with an unresolved or follow-up outcome. Engineer review recommended.</p>' : ""}</div>`,
    )
    .join("");
  return (
    head(
      "PRODUCT PASSPORT",
      p.label,
      d.site.name,
      '<button data-go="passports">All passports</button>',
    ) +
    `<section class="panel"><div class="report-meta">${[
      ["Product", p.product],
      ["Manufacturer", p.manufacturer],
      ["System", p.system_name],
      ["Serial number", p.serial_number],
      ["Site address", d.site.address],
      ["Passport ID", p.id],
    ]
      .map(
        ([k, v]) =>
          `<div><small>${k}</small><b style="overflow-wrap:anywhere">${esc(v || "Not recorded")}</b></div>`,
      )
      .join(
        "",
      )}</div><p class="muted">Team-supplied identification. Verify product applicability against controlled manufacturer evidence.</p><div class="actions"><button data-passport-action="event">Add lifecycle note</button><button data-passport-action="link">Link inspection</button></div></section>` +
    `<section class="panel" style="margin-top:24px"><div class="panel-head"><h3>Repeat-failure intelligence</h3>${badge(`${analysis.visible_linked_inspections} visible inspections`)}</div><p class="muted">${esc(analysis.method)}</p><p>${analysis.original_snapshot_cases} immutable original diagnoses · ${analysis.latest_outcomes} latest retained outcomes · ${analysis.omitted_without_diagnosis} records omitted without a diagnosis</p>${patterns || "<p>No diagnosis patterns are available yet.</p>"}</section>` +
    `<div class="grid" style="margin-top:24px"><section class="panel"><h3>Lifecycle history</h3><p class="muted">Entries are retained. Add a correction note to clarify an earlier entry.</p>${d.events.map((e) => `<div class="visit"><small>${esc(e.occurred_on)} · Recorded ${date(e.created_at)}</small><h4>${esc(e.kind)}</h4><p style="white-space:pre-wrap">${esc(e.note)}</p></div>`).join("")}</section><section class="panel"><h3>Linked inspections</h3>${d.inspections.length ? d.inspections.map((j) => `<div class="visit"><b>${esc(j.reference || "Inspection")}</b><p>${esc(j.outcome || "Outcome not recorded")}</p>${j.repair_outcome ? `<p><b>Latest repair:</b> ${esc(j.repair_outcome.payload.actual_repair)}</p><p><b>Final checks:</b> ${esc(j.repair_outcome.payload.verification_checks || "Not recorded in legacy feedback")}</p><small>Outcome revision ${j.repair_outcome.version} of ${j.outcome_revision_count} · ${j.repair_outcome.integrity_valid ? "Integrity checked" : "Integrity check failed"}</small>` : "<small>No retained repair outcome.</small>"}<p><button data-report="${j.id}">View report →</button></p></div>`).join("") : "<p>No linked reports available to your account.</p>"}</section></div>`
  );
};
document.addEventListener("click", async (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.passportId) {
    activePassport = b.dataset.passportId;
    await go("passport");
    return;
  }
  const action = b.dataset.passportAction;
  if (!action) return;
  await busy(b, async () => {
    if (action === "site") {
      const customers = await api("/api/customers");
      if (!customers.length) {
        toast("Add a customer before registering its site.", true);
        return;
      }
      openModal(
        "Add site",
        `<form id="siteForm">${select("Customer", "customer_id", customers, "", "Select customer…")}${field("Site name", "name", "", "text", 'required maxlength="200"')}${area("Site address", "address")}<p class="error form-error" role="alert"></p><button class="primary">Save site</button></form>`,
      );
    }
    if (action === "create") {
      const sites = await api("/api/sites");
      if (!sites.length) {
        toast("Add a site before registering its products.", true);
        return;
      }
      openModal(
        "Create product passport",
        `<form id="passportCreate">${select("Site", "site_id", sites, "", "Select site…")}${field("Product location / label", "label", "", "text", 'required maxlength="200"')}${select("Product", "product", ["Window", "French Door", "Residential Door", "Bifold", "Sliding Door", "Tilt & Turn"])}${field("Manufacturer", "manufacturer")}${field("System", "system_name")}${field("Serial number", "serial_number")}<p class="error form-error" role="alert"></p><button class="primary">Create passport</button></form>`,
      );
    }
    if (action === "event")
      openModal(
        "Add lifecycle note",
        `<form id="passportEvent">${select("Event type", "kind", ["Manufacture note", "Installation note", "Service note", "Warranty note", "Correction note"])}${field("Event date", "occurred_on", new Date().toISOString().slice(0, 10), "date", "required")}${area("Note", "note", "", 'required maxlength="10000"')}<p class="muted">This note is retained and visible to your company. It does not certify installation, warranty coverage or authorise remedial work.</p><p class="error form-error" role="alert"></p><button class="primary">Save note</button></form>`,
      );
    if (action === "link") {
      const jobs = await api("/api/jobs");
      if (!jobs.length) {
        toast("Save an inspection before linking it.", true);
        return;
      }
      openModal(
        "Link an inspection",
        `<form id="passportLink">${select(
          "Inspection",
          "job_id",
          jobs.map((j) => ({
            id: j.id,
            name: (j.reference || "Inspection") + " · " + j.customer,
          })),
          "",
          "Select inspection…",
        )}<p class="muted">Confirm this inspection concerns this physical product. The link is retained and cannot be moved to another passport.</p><p class="error form-error" role="alert"></p><button class="primary">Link inspection</button></form>`,
      );
    }
  });
});
document.addEventListener("submit", async (e) => {
  const f = e.target;
  if (
    !["siteForm", "passportCreate", "passportEvent", "passportLink"].includes(
      f.id,
    )
  )
    return;
  e.preventDefault();
  const b = f.querySelector("button");
  if (b.disabled) return;
  await busy(b, async () => {
    try {
      const data = Object.fromEntries(new FormData(f));
      const endpoint = {
        siteForm: "/api/sites",
        passportCreate: "/api/passports",
        passportEvent: `/api/passports/${activePassport}/events`,
        passportLink: `/api/passports/${activePassport}/inspections`,
      }[f.id];
      const result = await send(endpoint, data);
      if (f.id === "passportCreate") activePassport = result.id;
      $("modal").close();
      await go(f.id === "siteForm" ? "passports" : "passport");
      toast("Saved");
    } catch (error) {
      f.querySelector(".form-error").textContent = error.message;
    }
  });
});
