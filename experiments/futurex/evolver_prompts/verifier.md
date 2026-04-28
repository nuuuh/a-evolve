For FutureX temporal prediction tasks, verify each pipeline against:

1. ANSWER QUALITY: Does the output contain a specific, extractable
   answer? The solver should be able to read the output and commit
   to an answer without further searching. Reject outputs that are
   vague, narrative, or just a list of links.

2. DATE COMPLIANCE: Query with a cutoff date and verify no returned
   content is from after that date. This is critical — future data
   leakage invalidates the entire prediction task.

3. SCRAPING ROBUSTNESS: Try queries with non-ASCII characters,
   unusual formatting, very old dates. The pipeline should return
   "" gracefully, not crash or return garbage.

4. SOURCE DIVERSITY: Check that the fallback chain actually works —
   disable the primary source (bad query) and verify the secondary
   returns data.

5. OUTPUT FORMAT: Verify the response is under 2000 characters,
   contains no raw HTML/JSON blobs, and leads with the key fact.
