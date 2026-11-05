# Genomic and clinical data on screen (domain rules)

Read when the adapter sets `domain: genomics` (or the screens show variants, genes, samples, QC,
pharmacogenomics, or other biomedical data). Same precedence as dashboards.md: the project's design
system and decision log win; these rules fill the gaps. A finding cites the ID ("G9").

## Identifiers and nomenclature

- **G1 Gene symbols** follow the official nomenclature exactly: human gene symbols uppercase and in
  italics (*BRCA1*, *CYP2D6*), protein products upright. Never apply `text-transform` to a gene
  cell. Exports must not let spreadsheets turn symbols into dates (current HGNC symbols such as
  *SEPTIN1* / *MARCHF1* replaced the date-like ones; show the current symbol, keep aliases searchable).
- **G2 HGVS and other variant notations** are shown verbatim (`c.`, `p.`, `g.` prefixes, one amino
  acid convention throughout). Long notations wrap at a separator (`:`, `_`), never inside a token;
  the full string is copyable in one action.
- **G3 Coordinates always carry the genome build** (GRCh37 / GRCh38, or the organism's assembly) and
  one chromosome naming convention (`chr7` or `7`, not both). Display positions with thousands
  separators for reading; copy them without. State 0- or 1-based where the user could mix them.
- **G4 Identifiers (rsIDs, HGVS, sample IDs, transcript IDs)** are set in the text face with tabular
  figures — monospace is reserved for sequences (G20). Database identifiers link to their source.

## Numbers

- **G5 Allele frequencies use significant figures, not fixed decimals**: two significant figures,
  scientific notation (1.2 × 10⁻⁴) below a project-chosen cut-off, or one percentage convention —
  one formatter, used everywhere. Never round a non-zero frequency to 0; below the dataset's
  resolution write "< 1 × 10⁻⁵". Name the dataset, version and population.
- **G6 p-values and q-values** in scientific notation; plots use −log₁₀; thresholds named.
- **G7 Variant allele fraction travels with depth** ("VAF 48% · DP 52"): a fraction without its depth
  cannot be judged. Zygosity in words (heterozygous, homozygous, hemizygous) or one documented
  abbreviation set.
- **G8 Coverage** in ×, with the project's threshold drawn as a reference line, and the fraction of the
  target at or above it; low-coverage regions listed, not just coloured.

## States that must never look alike

- **G9 Not tested ≠ not covered ≠ no-call ≠ reference/normal ≠ absent from a database.** Each is
  its own rendered state, with a word, not only a colour. A no-call must never render as the
  reference result (in pharmacogenomics, a missing call must not display as the normal diplotype).
  A variant absent from a population database is "not found in <dataset>", not frequency 0.

## Ordered categories (classifications and phenotypes)

- **G10 Pathogenicity classes** (pathogenic, likely pathogenic, uncertain significance, likely benign,
  benign) form one ordered scale: a diverging ramp with the uncertain class neutral, defined once as
  tokens and used on every screen, chart and export. Always the word (or a documented abbreviation)
  with the colour. Conflicting interpretations are a separate state, not a blend.
- **G11 Pharmacogenomic phenotypes** (poor, intermediate, normal, rapid, ultrarapid metabolizer;
  plus indeterminate) form an ordered scale with *normal* neutral and both extremes marked; the
  phenotype is shown with the diplotype or activity score it came from, and a recommendation with
  its strength and guideline source.
- **G12 Evidence and provenance** sit beside the value: source, version or release date, review
  status. A clinical value without its source is not reviewable.
- **G13 Colour-blind safe and never colour alone.** Red/green pairs fail for many readers: use a
  blue–orange axis or add text/shape; check the ramp in a colour-vision simulation.

## Tables and terms

- **G14 Large variant tables**: render only visible rows (virtualised), keep identity columns
  (gene, variant) frozen, show active filters as removable chips with the count
  ("1,204 of 48,331 variants"), keep the filter state in the URL (one source of truth for the view:
  shareable and reproducible), and let users choose columns.
- **G15 Clinical and ontology terms wrap; they are never ellipsised.** Phenotype terms show the
  name with the identifier (name first), never a bare ID.
- **G16 Sizes** in bp / kb / Mb from one formatter; CNV and SV sizes with their unit.

## Charts specific to the domain

- **G17** Prefer an established component for genome-browser tracks over drawing your own; coverage
  as a line or area with the threshold line; protein-position variants as a lollipop over the domain
  map; association results as a Manhattan plot with the significance line labelled and chromosomes in
  two alternating neutral tones (the one place alternation carries information); QC metrics as
  distributions with pass/fail thresholds; heatmaps sequential single-hue, or diverging only around
  a meaningful zero.
- **G18 Sample data on screens and in demos** uses synthetic sample IDs — never names or other
  personal data in screenshots, galleries, fixtures or tickets.
- **G19 Printed or PDF reports** are a separate medium (page size, print contrast): exempt from
  screen-only rules, but they take colours, fonts and number formats from the same tokens and
  formatters.
- **G20 Sequences and alignments** are the place for monospace (columns must line up), with one
  documented base-colour convention used everywhere.
