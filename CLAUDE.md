# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the full pipeline
python run.py

# Run all tests
pytest tests/

# Run a single test file
pytest tests/test_rainfall_analysis.py -v

# Run unit tests only
pytest tests/unit/ -v
```

## Architecture

The system is a pipeline for analyzing drainage monitoring data and generating reports. Key directories:

- `src/core/` - Shared infrastructure (Config, LLM client, logger, data utilities)
- `src/pipeline/` - 8 analysis modules, each with a `runner.py` entry point
- `src/orchestrator/` - Pipeline orchestration with intervention points

### Pipeline Execution Order

```
data_filter → rainfall_analysis → dry_analysis → event_stats → pattern_analysis → rdii_analysis → risk_analysis → report_assembler
     │              │                              │
  Intervention 1  Intervention 2              Intervention 3
```

### Module Entry Point Convention

Every module under `src/pipeline/` follows this interface:

```python
# src/pipeline/<module_name>/runner.py
def run(config: Config, logger, **kwargs) -> dict | None:
    """
    Read from config paths, execute logic, write to config paths.
    Returns dict with data for downstream modules, or None on failure.
    """
```

### Data Flow

- Modules pass data through memory (`dry_curve_data`, `event_data`)
- All outputs are also written to Excel files for debugging and recovery
- Main output file: `outputs/综合分析结果.xlsx` (multiple sheets)
- Final report: `outputs/报告初稿.docx`

### Configuration (Three Layers)

1. **User layer** (`data/baseinfo.xlsx`): Project info, analysis parameters, selected rainfall events
2. **Technical layer** (`config.yaml`): Paths, thresholds, LLM settings
3. **Secrets layer** (`.env`): `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `DEEPSEEK_MODEL`

Access via `Config` class:

```python
config = Config.load()
input_path = config.flow_data_dir
output_path = config.combined_xlsx_path
threshold = config.missing_rate_threshold
```

For testing:

```python
config = Config.for_testing(output_dir=tmp_path, flow_data_dir="tests/data_sample/flow/")
```

### Shared Data Utilities

Use `src/core/data_utils.py` for common operations:

```python
from src.core.data_utils import (
    read_csv_with_fallback,      # Multi-encoding CSV reader
    detect_flow_columns,          # Auto-detect time/flow/level columns
    detect_site_info_columns,     # Auto-detect site info columns
    parse_point_name,             # Extract point ID from filename
)
```

### LLM Usage

LLM is used for:
- `pattern_analysis`: Generate discharge pattern descriptions
- `report_assembler`: Generate report summary

Handle failures gracefully:

```python
try:
    result = llm_client.chat(prompt)
except LLMFailedAfterRetry:
    result = "LLM failed, manual review needed"
```

## Key Constraints

- **No hardcoded paths**: All paths from `Config`
- **No imports from `sewage_monitoring/` or `_archive_old_agents/`**: Those are deprecated
- **Column detection by keywords, not indices**: Excel column order may change

## Related Documentation

- [Architecture](docs/ARCHITECTURE.md) - Full architecture design
- [PRD](docs/PRD-v0.3.md) - Product requirements
- [Refactor Roadmap](docs/REFACTOR-ROADMAP.md) - Migration plan
