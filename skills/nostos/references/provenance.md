# Ingestion provenance

Use one compact JSON comment immediately before every declaration derived from a document or code location:

```nostos
// @provenance {"kind":"document","locator":"section 2","sha256":"...","source":"docs/design.md"}
node design {}
```

The record fields are:

- `kind`: `document` or `code`;
- `source`: normalized project-relative path, or an explicit portable label for an external file;
- `locator`: stable page, section, heading, symbol, or line-range description;
- `sha256`: lowercase SHA-256 of the exact input bytes.

Generate the comment before extraction with `nostos_provenance.py`; do not type hashes manually. After building the candidate, run it again with `--expected-sha256 <recorded-hash>`. Discard and re-review the extraction if the helper reports a source conflict. The helper intentionally emits no timestamp so identical evidence produces identical source. It refuses absolute-path disclosure unless the caller supplies `--source-label`.

Provenance supports review; it does not prove truth. Keep uncertain extraction decisions visible and do not overwrite a declaration merely because a later input uses the same display name.
