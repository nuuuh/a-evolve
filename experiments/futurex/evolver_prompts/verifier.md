For FutureX temporal prediction tasks, verify each source module:

1. ANSWER QUALITY: Does the output contain a specific, extractable
   answer? The solver should be able to read the output and commit
   to an answer without further searching. Reject outputs that are
   vague, narrative, or just a list of links.

2. DATE COMPLIANCE: Query with a cutoff date and verify no returned
   content is from after that date.

3. SCRAPING ROBUSTNESS: Try queries with non-ASCII characters,
   unusual formatting, very old dates. The source should return
   "" gracefully, not crash or return garbage.

4. FALLBACK CHAIN: Try a query the primary API can't answer and
   verify the secondary source in the chain returns data.

5. OUTPUT FORMAT: Verify the response is under 2000 characters,
   contains no raw HTML/JSON blobs, and leads with the key fact.

6. ROUTER: Verify that different query types route to the correct
   source module (e.g. a price query goes to finance, not news).
