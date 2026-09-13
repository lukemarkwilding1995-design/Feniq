# Site identity and Product Passports

Migration `0004_passports` adds sites, product passports, inspection links and lifecycle events without modifying existing inspections or customers. Existing text-only customer/site fields are not guessed or automatically merged into identities.

Company administrators create a site under an existing customer and register a physical product at that site. Product label, type, manufacturer, system and serial number are team-supplied identification, not verified specifications. Each passport receives a persistent UUID.

Company members can read their company's passports and add dated manufacture, installation, service, warranty or correction notes. Notes are company-shared assertions, not certificates or commercial approvals. The event date and recording timestamp are distinct. Entries and inspection links are append-only at the API and database-trigger level; corrections are new notes. Privileged database administrators can bypass triggers, so this is not cryptographic tamper-proof storage.

An inspection can be linked to one passport; repeated links to the same passport are idempotent. Links to another company's records or an unassigned engineer's inspection are rejected. Linked report listings preserve assigned-engineer/admin access. The shared lifecycle only records a generic inspection-link event, not restricted diagnostic/report details.

Use **Product passports → Add site → Create passport**, then **Add lifecycle note** or **Link inspection**. Create the customer and inspection through their existing workflows first. No old data is deleted or reclassified.

Current limits: no metadata editing, relocation, archive/unlink correction workflow, file attachments, external sharing, QR printing, verified manufacturer identity or warranty adjudication. Site/Product identity is now usable; the full manufacture-to-replacement lifecycle remains staged work. PostgreSQL DDL is supplied but server integration remains unverified. SQLite is the tested local demo database.
