let citationPage = null;
async function citationPanel(job) {
  const rows = await api(`/api/jobs/${job.id}/citations`);
  return `<section class="panel" style="margin-bottom:20px"><div class="panel-head"><h3>Source citations</h3><button data-citation-add="${job.id}">Attach reviewed excerpt</button></div>${rows.length ? rows.map((c) => `<div class="visit"><h4>${esc(c.title)}</h4><small>${esc(c.manufacturer)} · Revision ${esc(c.revision)} · PDF page ${c.page}</small><p>${badge(c.current ? "Current reference review" : "Historical reference")}</p><blockquote style="margin:12px 0;white-space:pre-wrap">${esc(c.excerpt)}</blockquote><p><b>Relevance:</b> ${esc(c.relevance)}</p><small>${esc(c.status)}<br>Reviewed applicability: ${esc(c.applicability)}</small></div>`).join("") : "<p>No reviewed source excerpts attached.</p>"}<p class="muted">Reference approval is separate from technical specification verification. Added evidence requires a fresh engineer review; historical citations remain visible after withdrawal.</p></section>`;
}
document.addEventListener("click", async (e) => {
  const b = e.target.closest("button");
  if (!b?.dataset.citationAdd) return;
  await busy(b, async () => {
    const sources = (await api("/api/documents")).filter(
      (d) => d.source_review?.reference_approved,
    );
    if (!sources.length) {
      openModal(
        "Attach reviewed excerpt",
        "<p>No sources currently have reference approval for this company.</p><p>An administrator must first review the original PDF, its revision, applicability and page range in the Knowledge library.</p>",
      );
      return;
    }
    openModal(
      "Select reviewed source page",
      `<form id="citationChoose">${select(
        "Reviewed source",
        "document_id",
        sources.map((d) => ({
          id: d.id,
          name:
            d.title +
            " · pages " +
            d.source_review.page_start +
            "–" +
            d.source_review.page_end,
        })),
        "",
        "Select source",
      )}${field("PDF page", "page", 1, "number", 'required min="1"')}<p class="error form-error" role="alert"></p><button class="primary">Load source page</button></form>`,
    );
  });
});
document.addEventListener("submit", async (e) => {
  const f = e.target;
  if (!["citationChoose", "citationAttach"].includes(f.id)) return;
  e.preventDefault();
  const b = f.querySelector("button");
  if (b.disabled) return;
  await busy(b, async () => {
    try {
      const data = Object.fromEntries(new FormData(f));
      if (f.id === "citationChoose") {
        if (!data.document_id) throw Error("Choose a reviewed source");
        const page = await api(
          `/api/documents/${encodeURIComponent(data.document_id)}/reviewed-pages/${Number(data.page)}`,
        );
        citationPage = { ...page, document_id: data.document_id };
        openModal(
          "Attach exact source excerpt",
          `<form id="citationAttach"><label>Extracted source text<textarea readonly style="min-height:170px">${esc(page.text || "No extractable text on this page. A source quote cannot be attached until extraction is available.")}</textarea></label><p class="muted">Reviewed applicability: ${esc(page.applicability)}</p>${area("Exact excerpt (copy from the source text)", "excerpt", "", 'required minlength="10" maxlength="2000"')}${area("Why this source applies to this inspection", "relevance", "", 'required maxlength="5000"')}<p class="notice">Adding this citation clears engineer review. It does not change the original diagnosis or authorise corrective work.</p><p class="error form-error" role="alert"></p><button class="primary">Attach citation</button></form>`,
        );
      } else {
        await send(`/api/jobs/${activeJob.id}/citations`, {
          ...data,
          document_id: citationPage.document_id,
          review_id: citationPage.review_id,
          page: citationPage.page,
        });
        $("modal").close();
        await showReport(activeJob.id);
        toast("Citation attached; engineer review required");
      }
    } catch (error) {
      f.querySelector(".form-error").textContent = error.message;
    }
  });
});
