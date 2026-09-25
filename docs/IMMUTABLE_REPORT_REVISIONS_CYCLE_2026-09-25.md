# Immutable report revisions cycle — 25 September 2026

Migration `0016_report_revisions` adds append-only PDF report revisions. An assigned engineer or company administrator can retain the current report only after engineer review. Each revision stores the exact PDF bytes, byte count, PDF SHA-256, a canonical source-state SHA-256, actor and timestamp. Database triggers reject updates and deletes.

The source fingerprint covers every field rendered in the report, engineer identity, actual photo bytes and metadata, reviewed citation content/status, the latest outcome revision and the latest customer acceptance. Later changes preserve earlier PDFs and mark them as historical. An unchanged report cannot be retained twice, and optimistic version checks prevent stale submissions.

The inspection screen lists retained revisions with integrity and current/historical state. Authorised users can download the original stored bytes. Creating a report revision is audited. A retained report records what FenIQ rendered; it is not a cryptographic customer signature, a commercial approval or proof that every technical statement is correct.

Privacy-request inventories count and checksum customer acceptances and retained report revisions for linked inspections. Their content and PDF bytes remain outside the internal Access draft pending manual third-party-content and redaction review.
