-- FenIQ V11 launch-candidate indexes / audit support
CREATE INDEX IF NOT EXISTS ix_jobs_company_created ON jobs(company_id, created_at);
CREATE INDEX IF NOT EXISTS ix_work_orders_company_status ON work_orders(company_id, status);
CREATE INDEX IF NOT EXISTS ix_approval_company_status ON approval_requests(company_id, status);
CREATE INDEX IF NOT EXISTS ix_learning_company_created ON learning_records(company_id, created_at);
