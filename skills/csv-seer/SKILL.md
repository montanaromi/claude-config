---
name: csv-seer
description: Analyze structured datasets (CSV, JSON, JSONL) and generate a Q&A-ready summary with key statistics, anomalies, and pre-computed answers to common questions
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash(python3:*)
  - Bash(wc:*)
  - Bash(file:*)
  - Bash(head:*)
---

# CSV Seer — Dataset Analyzer for Q&A Prep

Analyze structured datasets (CSV, JSON, JSONL) and produce a standalone Q&A-ready report. The report contains schema, statistics, anomalies, and pre-computed answers to common stakeholder questions. **Never modify the source data files.**

## Arguments

| Arg | Required | Description |
|-----|----------|-------------|
| `<path>` | Yes | Path to file or directory containing datasets |
| `--format <csv\|json\|jsonl>` | No | Force format detection (default: auto-detect from extension and content) |
| `--top <N>` | No | Limit analysis to first N rows for large files (default: 10000) |
| `--questions "<q1>; <q2>"` | No | Semicolon-separated custom questions to answer from the data |
| `--output <path>` | No | Write the report to a file instead of stdout |

If `<path>` is empty, ask: "Provide a path to the dataset file or directory to analyze."

## Phase 1 — Inject Data

### Step 1: Locate Files

If `<path>` is a directory, Glob for `*.csv`, `*.json`, `*.jsonl` files. If no matching files found, report: "No supported dataset files found in `<path>`. Supported formats: CSV, JSON, JSONL."

If `<path>` is a single file, verify it exists with Read (first 5 lines).

### Step 2: Detect Format

| Signal | Format |
|--------|--------|
| Extension `.csv` or first line contains comma-separated headers | CSV |
| Extension `.json` or first line starts with `[` or `{` (single object/array) | JSON |
| Extension `.jsonl` or each line is a valid JSON object | JSONL |
| None of the above | Report: "Unsupported format. Provide CSV, JSON, or JSONL." Stop. |

If `--format` is provided, use it and skip auto-detection. If the forced format doesn't match the actual content, warn but proceed.

### Step 3: Detect Data Domain

After format detection, infer the data domain from column names, value patterns, and file naming to adapt analysis strategy:

| Domain Signal | Domain | Analysis Adaptation |
|---------------|--------|---------------------|
| Columns matching `price`, `amount`, `revenue`, `cost`, currency symbols in values | Financial | Use decimal-safe parsing; flag rounding anomalies; default questions focus on totals, averages, distributions |
| Columns matching `timestamp`, `created_at`, `date`, `event`; ISO 8601 values | Temporal/Event | Detect time gaps, frequency patterns, seasonality; default questions focus on date ranges and event rates |
| Columns matching `user_id`, `email`, `name`, `age`, `address` | User/Entity | Flag PII columns; check for duplicates by identifier; default questions focus on demographics and segmentation |
| Columns matching `level`, `message`, `status`, `error`, `trace` | Log/Diagnostic | Frequency-rank status/level values; detect error spikes; default questions focus on error rates and top messages |
| Columns matching `lat`, `lng`, `longitude`, `latitude`, `zip`, `country` | Geographic | Validate coordinate ranges; detect region distribution; default questions focus on geographic spread |
| None of the above | General | Use default analysis strategy |

**Locale awareness:** If numeric columns contain comma-decimal notation (e.g., `1.234,56`) or date columns use non-ISO formats (e.g., `DD/MM/YYYY`), detect and adapt the parser. Warn: "Non-standard number/date format detected — using `<format>` interpretation."

### Step 4: Measure Size

Run `wc -l <file>` and `file <file>` to determine row count and encoding.

- If rows > `--top` threshold (default 10000): warn "Analyzing first N rows of M total. Use `--top` to adjust." Truncate analysis to the first N rows.
- If file size > 100MB: warn "Large file detected. Analysis may be slow."
- If file is empty (0 bytes): report "File is empty." Stop.

**Gate:** At least one valid dataset file identified with known format and non-zero size.

## Phase 2 — Parse

Use `python3 -c` to parse the dataset and extract structural metadata. Build the Python inline — do not write temporary script files.

### Step 1: Schema Extraction

For each dataset file, extract:
- **Column names** (CSV headers, JSON top-level keys)
- **Data types** per column (inferred: string, integer, float, boolean, datetime, null, mixed)
- **Nullable columns** (columns containing null/empty/NaN values)
- **Row count** (actual parsed rows)
- **Column count**

Output a schema table:

```
| Column | Type | Nullable | Unique Count | Sample Values |
```

### Step 2: Parse Validation

Count and report:
- Rows that failed to parse (malformed CSV lines, invalid JSON objects)
- Type inconsistencies within a column (e.g., column is mostly integers but has string values)
- Encoding issues (non-UTF-8 characters)

If parse failure rate > 20%, warn: "High parse failure rate (N%). Data quality may be poor. Check encoding and format."

**Gate:** Schema extracted with at least 1 column and 1 parseable row.

## Phase 3 — Analyze

Run analysis via `python3 -c` scripts. Split into independent analysis passes.

### Pass 1: Descriptive Statistics

For **numeric columns**: count, mean, median, std dev, min, max, Q1, Q3, IQR.
For **string columns**: count, unique count, top 5 most frequent values with counts, avg length, min/max length.
For **datetime columns**: min date, max date, date range, gaps (missing days/periods).
For **boolean columns**: true count, false count, null count, ratio.

### Pass 2: Anomaly Detection

Flag the following as anomalies with severity (High/Medium/Low):

| Anomaly | Severity | Detection | Remediation |
|---------|----------|-----------|-------------|
| Null rate > 50% in a column | High | Count nulls per column | If > 80%: recommend dropping column. If 50-80%: investigate upstream data source for missing values; consider imputation only if domain supports it (e.g., forward-fill for time series) |
| Single-value column (0 variance) | Medium | Unique count = 1 | Drop column — it adds no analytical value. Check if it was a filter artifact (e.g., export filtered to one status) |
| Extreme outliers (> 3 IQR from Q1/Q3) | High | IQR method on numeric columns | List the top 5 outlier values with row indices. Investigate: data entry error, unit mismatch, or legitimate extreme? Flag for manual review |
| Duplicate rows | Medium | Full row dedup count | Report exact duplicate count and percentage. If > 5%: likely a data pipeline issue (double-ingestion). Deduplicate before analysis |
| Type inconsistencies (mixed types in column) | High | Type variance from Phase 2 | List the minority-type values with row indices. Common cause: CSV export encoding booleans as strings, or null sentinels like "N/A", "-", "null" |
| Suspicious patterns (all same timestamp, sequential IDs with gaps) | Low | Frequency analysis | Timestamps: check for timezone flattening or batch-insert artifacts. ID gaps: check for filtered/deleted records |
| Columns with > 90% unique values (potential ID/key) | Low | Unique ratio | Likely an identifier column — exclude from statistical aggregation. Confirm if it should be the primary key |

### Pass 3: Relationship Detection

For datasets with multiple columns:
- Identify potential primary key columns (100% unique, non-null)
- Detect columns that look like foreign keys (name patterns: `*_id`, `*_key`, `*_ref`)
- Flag columns with high cardinality that might need grouping for analysis
- Detect obvious correlations between numeric columns (Pearson > 0.8 or < -0.8)

### Pass 4: Answer Custom Questions

If `--questions` was provided, attempt to answer each question programmatically:
1. Parse the natural-language question to identify target columns and operations (count, sum, average, filter, group-by, max, min).
2. Generate and execute a Python expression against the parsed data.
3. If the question cannot be mapped to a computation, report: "Could not auto-answer: `<question>`. Requires manual analysis."

If no custom questions provided, generate 5 default questions based on the schema:
- "How many total records are there?"
- "What is the distribution of `<most interesting categorical column>`?"
- "What is the average/total of `<primary numeric column>`?"
- "Are there any duplicate records?"
- "What date range does the data cover?" (if datetime columns exist)

**Gate:** At least descriptive statistics and anomaly detection completed.

## Phase 4 — Report

Produce the report in this exact format:

```
## Dataset Analysis: <filename>

**File:** <path> | **Format:** <CSV/JSON/JSONL> | **Rows:** <count> | **Columns:** <count>
**Analyzed:** <date> | **Sample:** <"all rows" or "first N of M rows">

### Schema

| Column | Type | Nullable | Unique | Sample Values |
|--------|------|----------|--------|---------------|
| ...    | ...  | ...      | ...    | ...           |

### Key Statistics

<Descriptive stats tables, one per data-type group>

### Anomalies (<count> found)

| # | Column | Anomaly | Severity | Detail |
|---|--------|---------|----------|--------|
| 1 | ...    | ...     | High     | ...    |

<If no anomalies: "No anomalies detected.">

### Relationships

- **Potential primary key:** <column> (100% unique, non-null)
- **Potential foreign keys:** <columns matching *_id pattern>
- **Correlations:** <column_a> ~ <column_b> (r=0.95)

<If insufficient columns for relationship analysis: "Single-column dataset — relationship analysis skipped.">

### Q&A

**Q: <question>**
A: <computed answer with supporting numbers>

**Q: <question>**
A: <answer>

...

### Data Quality Score

| Dimension | Score | Reasoning |
|-----------|-------|-----------|
| Completeness | <1-5> | <null rate summary> |
| Consistency | <1-5> | <type consistency, format uniformity> |
| Uniqueness | <1-5> | <duplicate rate> |
| Validity | <1-5> | <parse failure rate, outlier rate> |
| **Overall** | **<avg>** | |
```

If `--output` was provided, write the report to the specified path. Otherwise, output directly.

## Edge Cases

- **Binary file provided:** `file` command detects non-text. Report: "Binary file detected — not a supported dataset format." Stop.
- **CSV with no header row:** Detect if first row looks like data (all numeric, no distinct naming pattern). If so, generate synthetic headers (`col_0`, `col_1`, ...) and warn.
- **Nested JSON:** Flatten top-level keys only. For nested objects/arrays, report the type as `object` or `array` and note: "Nested structures detected — flatten before analysis for deeper insights."
- **Mixed encodings:** Try UTF-8 first, fall back to latin-1, then cp1252. Report which encoding succeeded.
- **TSV or pipe-delimited files:** Detect tab or pipe delimiters in `.csv` files. Adjust parser accordingly and note the detected delimiter.
- **Single-row dataset:** Skip statistical analysis (meaningless with n=1). Report schema and the single row's values only.
- **All columns are strings:** Skip numeric statistics. Focus on frequency analysis, unique counts, and pattern detection.
- **File path contains spaces or special characters:** Quote all paths in shell commands.
- **Python not available:** If `python3` is not found, report: "Python 3 is required for dataset analysis. Install Python 3 and retry." Stop.
- **Permission denied on file:** Report the exact path and error. Suggest checking file permissions. Stop.
- **Compressed files (.csv.gz, .json.gz):** Detect `.gz` extension. Decompress with `python3 -c "import gzip; ..."` before parsing. If decompression fails, report: "Compressed file could not be decompressed. Verify the archive is not corrupted."
- **Extremely wide datasets (1000+ columns):** Warn "Wide dataset detected (N columns). Schema table truncated to first 50 columns. Use `--questions` to target specific columns." Truncate schema display but analyze all columns for anomalies.
- **URL or remote path provided:** Report: "Remote paths not supported. Download the file locally first and provide the local path." Stop.
- **Dataset with only null values:** Report: "All values are null across all columns. The dataset contains no analyzable data. Check the data export process." Stop after schema.

## Composability

- **After analysis:** Run `/z` to generate a structured prompt using the dataset insights as context.
- **For data issues found:** Open the file with Read and investigate anomalies manually.
- **To share findings:** Run `/commit` if the report was written to a file.
- **For code generation:** Use the schema and statistics as input to generate data processing scripts or SQL queries.
- **For visualization:** Use the statistics output to generate charts with a plotting library.
