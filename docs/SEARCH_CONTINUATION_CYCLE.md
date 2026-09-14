# Search continuation cycle

Development branch: feniq-phase1-platform. Adds offset/snapshot continuation to the reviewed-evidence API and a Search next batch button. Each batch checks at most 100 pages or returns 20 matches. Total reviewed-page coverage is shown. Query or reviewed-source changes invalidate continuation; changing form inputs resets the search. No migration or private-source approval.

24 tests pass, including retrieval of a match on page 105 after an empty first batch, completion coverage, changed query/review rejection and missing-snapshot rejection. Existing exact-PDF citation and company-access tests pass. JavaScript syntax passes. The local demo was restarted with the update. Positive continuation was API-tested with a mocked 105-page source; the private library still has no approved sources.

Remaining: extraction/hash caching and larger-library performance, semantic retrieval, human source review, and governed repair outcomes. Main remains untouched. Commits are local pending GitHub authentication.
