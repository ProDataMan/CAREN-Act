# CDC WONDER exports

Put hand-made CDC WONDER exports (`.txt`, tab-delimited, as downloaded) here. The data build parses every `.txt` file in this folder into `../cdc_wonder_states.json`, which feeds the state table on the contested-deaths page.

The step-by-step export instructions are at https://prodataman.github.io/CAREN-Act/website/deaths.html#export

Rules (from the CDC WONDER data use restrictions):
- Never back-calculate or publish counts that WONDER marks "Suppressed".
- Never try to identify individuals.
- Keep the footer WONDER adds to each export; it records the query and dataset.
