let reviewingSource = null;
document.addEventListener("click", async (e) => {
  const b = e.target.closest("button");
  if (!b?.dataset.sourceReview) return;
  await busy(b, async () => {
    reviewingSource = await api(
      `/api/documents/${b.dataset.sourceReview}/reviews`,
    );
    const d = reviewingSource.document,
      h = reviewingSource.history[0];
    const history = reviewingSource.history
      .map(
        (r) =>
          `<div class="visit"><h4>${esc(r.status)}</h4><small>${esc(r.reviewer)} · ${date(r.created_at)}</small><p>${esc(r.title)} · ${esc(r.revision)} · PDF pages ${r.page_start}–${r.page_end}</p><p>${esc(r.applicability)}</p><p>${esc(r.note)}</p></div>`,
      )
      .join("");
    const form =
      user.role === "admin"
        ? `<form id="sourceReviewForm">${select("Review decision", "status", ["Approved for reference", "Rejected", "Withdrawn"], "", "Choose a decision")}${field("Document title checked against source", "title", h?.title || d.title, "text", 'required maxlength="300"')}${field("Manufacturer / publisher", "manufacturer", h?.manufacturer || d.manufacturer, "text", 'required maxlength="180"')}${field("Revision / issue as shown in source", "revision", h?.revision || "", "text", 'required maxlength="180"')}${area("Product/system applicability and limits", "applicability", h?.applicability || "", "required")}<div class="form-grid">${field("First reviewed PDF page", "page_start", h?.page_start || 1, "number", `required min="1" max="${d.page_count}"`)}${field("Last reviewed PDF page", "page_end", h?.page_end || 1, "number", `required min="1" max="${d.page_count}"`)}</div>${area("Review evidence / rationale", "note", "", "required")}<label class="check"><input name="attested" type="checkbox">I personally reviewed the cited source pages, revision and stated applicability.</label><p class="notice">Approval applies only to reference use within this company and the stated page range. It does not verify every numerical value, update diagnostic rules or authorise remedial work.</p><p class="error form-error" role="alert"></p><button class="primary">Record review</button></form>`
        : "<p>Your company administrator records source reviews.</p>";
    openModal(
      "Source review",
      `<h3>${esc(d.title)}</h3>${badge(reviewingSource.current.status)}<p><button data-document="${d.id}">Read original PDF</button></p><p class="muted">Read the original first, then reopen this form to record your review. Existing review history is retained.</p>${form}<h3>Review history</h3>${history || "<p>No review recorded. This source remains pending.</p>"}`,
    );
  });
});
document.addEventListener("submit", async (e) => {
  const f = e.target;
  if (f.id !== "sourceReviewForm") return;
  e.preventDefault();
  const b = f.querySelector("button");
  if (b.disabled) return;
  await busy(b, async () => {
    try {
      const data = Object.fromEntries(new FormData(f));
      data.page_start = Number(data.page_start);
      data.page_end = Number(data.page_end);
      data.attested = f.elements.attested.checked;
      data.previous_id = reviewingSource.history[0]?.id || null;
      data.document_sha256 = reviewingSource.document.sha256;
      await send(`/api/documents/${reviewingSource.document.id}/reviews`, data);
      $("modal").close();
      await go("library");
      toast("Source review recorded");
    } catch (error) {
      f.querySelector(".form-error").textContent = error.message;
    }
  });
});
