let activeCase = null,
  caseDetail = null;
pages.cases = async function () {
  const records = await api("/api/cases");
  return (
    head(
      "TECHNICAL INVESTIGATIONS",
      "Technical cases",
      "Track complex faults, evidence and resolution.",
      '<button class="primary" data-case-action="create">New technical case</button>',
    ) +
    '<div class="notice">Cases are visible to their owner and company administrators. Awaiting Response records an internal status; no message is sent to a manufacturer or supplier. Case resolution does not authorise chargeable work.</div>' +
    `<div class="cards">${records.length ? records.map((c) => `<article class="panel"><div class="actions">${badge(c.status)}${badge(c.priority)}</div><h3>${esc(c.title)}</h3><p>${esc(c.description)}</p><button data-case-id="${c.id}">Open case →</button></article>`).join("") : empty("No technical cases yet", "Create a case linked to a product passport or inspection.")}</div>`
  );
};
pages.case = async function () {
  caseDetail = await api("/api/cases/" + activeCase);
  const c = caseDetail.case;
  return (
    head(
      "TECHNICAL CASE",
      c.title,
      `${c.status} · Owner: ${caseDetail.owner_name}`,
      '<button data-go="cases">All cases</button>',
    ) +
    `<section class="panel"><div class="actions">${badge(c.status)}${badge(c.priority)}</div><p style="white-space:pre-wrap">${esc(c.description)}</p><div class="actions">${c.passport_id ? `<button data-passport-id="${c.passport_id}">Open passport</button>` : ""}${c.job_id ? `<button data-report="${c.job_id}">Open inspection</button>` : ""}</div>${c.resolution ? `<h3>Resolution</h3><p style="white-space:pre-wrap">${esc(c.resolution)}</p>` : ""}<div class="actions" style="margin-top:20px">${c.status !== "Closed" ? '<button data-case-action="note">Add investigation note</button>' : ""}${c.status !== "Closed" || user.role === "admin" ? '<button data-case-action="update">Update case</button>' : ""}</div></section>` +
    `<section class="panel" style="margin-top:24px"><h3>Case history</h3><p class="muted">Notes and changes are retained. Add a new note to correct an earlier entry.</p>${caseDetail.events.map((e) => `<div class="visit"><small>${date(e.created_at)}</small><h4>${esc(e.kind)}</h4><p style="white-space:pre-wrap">${esc(e.note)}</p></div>`).join("")}</section>`
  );
};
document.addEventListener("click", async (e) => {
  const b = e.target.closest("button");
  if (!b) return;
  if (b.dataset.caseId) {
    activeCase = b.dataset.caseId;
    await go("case");
    return;
  }
  const action = b.dataset.caseAction;
  if (!action) return;
  await busy(b, async () => {
    if (action === "create") {
      const [passports, jobs, users] = await Promise.all([
        api("/api/passports"),
        api("/api/jobs"),
        user.role === "admin" ? api("/api/company/users") : Promise.resolve([]),
      ]);
      openModal(
        "New technical case",
        `<form id="caseCreate">${field("Case title", "title", "", "text", 'required maxlength="240"')}${area("Investigation description", "description", "", "required")}${select("Priority", "priority", ["Low", "Normal", "High", "Urgent"], "Normal")}${select(
          "Product passport",
          "passport_id",
          passports.map((p) => ({ id: p.id, name: p.label })),
          "",
          "No passport selected",
        )}${select(
          "Inspection",
          "job_id",
          jobs.map((j) => ({
            id: j.id,
            name: (j.reference || "Inspection") + " · " + j.customer,
          })),
          "",
          "No inspection selected",
        )}${user.role === "admin" ? select("Case owner", "owner_id", users, user.id) : ""}<p class="muted">Select a passport or inspection. If both are selected, the inspection must already be linked to that passport. An engineer owner must have access to the inspection.</p><p class="error form-error" role="alert"></p><button class="primary">Create case</button></form>`,
      );
    }
    if (action === "note")
      openModal(
        "Investigation note",
        `<form id="caseNote">${area("Note", "note", "", 'required maxlength="10000"')}<p class="error form-error" role="alert"></p><button class="primary">Save note</button></form>`,
      );
    if (action === "update") {
      const c = caseDetail.case;
      const allowed = {
        Open: ["Open", "Investigating"],
        Investigating: ["Investigating", "Awaiting Response", "Resolved"],
        "Awaiting Response": ["Awaiting Response", "Investigating", "Resolved"],
        Resolved: ["Resolved", "Investigating", "Closed"],
        Closed: ["Investigating"],
      }[c.status];
      const users =
        user.role === "admin" ? await api("/api/company/users") : [];
      openModal(
        "Update technical case",
        `<form id="caseUpdate">${select("Status", "status", allowed, c.status === "Closed" ? "Investigating" : c.status)}${user.role === "admin" ? select("Case owner", "owner_id", users, c.owner_id) : ""}${area("Reason / update", "note", "", "required")}${area("Resolution (required to resolve)", "resolution", c.resolution)}<p class="muted">Closing retains the resolution. Reopening starts further investigation. No purchasing or remedial work is authorised by this change.</p><p class="error form-error" role="alert"></p><button class="primary">Save changes</button></form>`,
      );
    }
  });
});
document.addEventListener("submit", async (e) => {
  const f = e.target;
  if (!["caseCreate", "caseNote", "caseUpdate"].includes(f.id)) return;
  e.preventDefault();
  const b = f.querySelector("button");
  if (b.disabled) return;
  await busy(b, async () => {
    try {
      const data = Object.fromEntries(new FormData(f));
      if (f.id === "caseCreate") {
        data.passport_id = data.passport_id || null;
        data.job_id = data.job_id || null;
        data.owner_id = data.owner_id ? Number(data.owner_id) : null;
        const result = await send("/api/cases", data);
        activeCase = result.id;
      } else {
        data.version = caseDetail.case.version;
        if (data.owner_id) data.owner_id = Number(data.owner_id);
        await send(
          "/api/cases/" + activeCase + (f.id === "caseNote" ? "/notes" : ""),
          data,
          f.id === "caseUpdate" ? "PATCH" : "POST",
        );
      }
      $("modal").close();
      await go("case");
      toast("Case saved");
    } catch (error) {
      f.querySelector(".form-error").textContent = error.message;
    }
  });
});
