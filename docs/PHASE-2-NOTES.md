# Phase 2 实施记录

> **执行日期**: 2026-05-23
> **执行阶段**: Phase 2 - 模块补齐与标准化

---

## 1. 实际产出文件清单

### 新建模块

| 目录 | 文件 | 说明 |
|------|------|------|
| `pipeline/event_stats/` | `__init__.py` | 模块导出 |
| | `analyzer.py` | 雨天事件统计核心逻辑 (~150 行) |
| | `runner.py` | 统一入口 `run(config, logger)` (~80 行) |
| `pipeline/risk_analysis/` | `__init__.py` | 模块导出 |
| | `analyzer.py` | 风险分析核心逻辑 (~280 行) |
| | `runner.py` | 统一入口 `run(config, logger, event_data=None)` (~90 行) |

### 改造模块（新增 runner.py）

| 目录 | 新增文件 | 改造文件 |
|------|---------|---------|
| `pipeline/data_filter/` | `runner.py` | `__init__.py` |
| `pipeline/dry_analysis/` | `runner.py` | `analyzer.py`, `__init__.py` |
| `pipeline/rainfall_analysis/` | `runner.py` | `analyzer.py`, `__init__.py` |
| `pipeline/pattern_analysis/` | `runner.py` | `analyzer.py`, `__init__.py` |
| `pipeline/rdii_analysis/` | `runner.py` | `analyzer.py`, `__init__.py` |
| `pipeline/report_assembler/` | `runner.py` | `assembler.py`, `__init__.py` |

---

## 2. 与原 ROADMAP 的偏差

### 2.1 执行顺序调整

| 原计划顺序 | 实际执行顺序 | 调整原因 |
|-----------|-------------|---------|
| Task 2.1 → Task 2.2 → Task 2.3 | Task 2.3 → Task 2.1 → Task 2.2 | 先改造现有模块入口，新建模块可参考已改造模块的输出格式 |

### 2.2 无偏差的部分

- event_stats 模块从 rdii_analysis 提取逻辑，输出到"雨天事件统计" Sheet
- risk_analysis 模块拆分为旱天风险 + 雨天溢流风险两部分
- 所有模块统一使用 `run(config: Config, logger) -> dict` 接口

### 2.3 关键改动

| 原计划 | 实际实现 | 调整原因 |
|--------|---------|---------|
| 模块输出到单独的分析结果.xlsx | 统一输出到 `综合分析结果.xlsx` 对应 Sheet | 符合 ARCHITECTURE.md §3.3 的数据传递约定 |
| 中间数据用 pickle 存储 | 删除 pickle，改为内存传递 + Excel 落盘 | 用户明确要求不保留 pickle |

---

## 3. 关键决策记录

### 决策 1: 模块入口返回 dict 而非 None

**背景**: 原计划 `run()` 返回 `None`，数据通过文件传递。

**决策**: `run()` 返回 `dict`，包含后续模块需要的数据结构。

**理由**:
- 后续模块可以直接通过参数接收数据，无需从文件读取
- 内存传递比文件 I/O 更快
- 同时保留 Excel 输出，便于调试和用户查看

**示例**:
```python
# dry_analysis 返回旱天特征曲线
result = dry_analysis.run(config, logger)
dry_curve_data = result["dry_curve_data"]

# 传递给 pattern_analysis
pattern_analysis.run(config, logger, dry_curve_data=dry_curve_data)
```

### 决策 2: 旱天特征曲线保存到独立 Sheet

**背景**: 旱天特征曲线是 1440 行 × 3 列的 DataFrame，每个点位一份。

**决策**: 为每个点位创建独立 Sheet，命名为 `特征曲线_点位编号`。

**理由**:
- pattern_analysis 和 report_assembler 需要读取特征曲线数据
- 从 Excel 读取比从 pickle 读取更透明
- 用户可以直接查看特征曲线数值

### 决策 3: 模块支持从 Excel 读取上游数据

**背景**: Orchestrator 可能传递上游数据，也可能不传递（独立运行场景）。

**决策**: 所有模块的 `run()` 支持可选参数接收上游数据，如果未传入则从 Excel 读取。

**示例**:
```python
# 方式1: 内存传递（Orchestrator 调用）
dry_result = dry_analysis.run(config, logger)
pattern_analysis.run(config, logger, dry_curve_data=dry_result["dry_curve_data"])

# 方式2: 从 Excel 读取（独立运行）
pattern_analysis.run(config, logger)  # 自动从 Excel 读取旱天特征曲线
```

### 决策 4: event_stats 作为独立模块

**背景**: 原 ROADMAP 将 event_stats 标注为"内部步骤"。

**决策**: 实现为独立模块，有完整的 `runner.py` 和 `analyzer.py`。

**理由**:
- 与其他模块结构一致，便于维护
- 可以独立运行进行调试
- 输出到独立的"雨天事件统计" Sheet

---

## 4. 模块接口规范

### 4.1 统一入口签名

所有模块的 `runner.py` 都遵循以下规范：

```python
from core.config import Config
import logging
from typing import Any

def run(config: Config, logger: logging.Logger, **kwargs) -> dict[str, Any]:
    """
    模块入口函数。

    参数:
        config: 全局配置对象
        logger: 日志器
        **kwargs: 可选的上游数据（如 dry_curve_data, event_data）

    返回:
        dict，包含本模块产出的数据结构
    """
    pass
```

### 4.2 输入输出约定

| 模块 | 输入来源 | 输出 Sheet | 返回值 |
|------|---------|-----------|--------|
| data_filter | config.flow_data_dir, config.rainfall_data_path | 筛选结果.xlsx | `{selected: {...}}` |
| dry_analysis | config.flow_data_dir, config.filter_result_path | "旱天分析" + "特征曲线_*" | `{dry_curve_data, statistics, ...}` |
| rainfall_analysis | config.rainfall_data_path | "日降雨量统计" + "场次降雨统计" | `{daily_rain, event_rain, event_data_dict}` |
| event_stats | flow_data + event_data | "雨天事件统计" | `{event_stats}` |
| pattern_analysis | dry_curve_data | "排污规律分析" | `{pattern_df, descriptions}` |
| rdii_analysis | dry_curve_data + event_data | "降雨事件最大液位"等 | `{max_level, avg_flow, rdii_total, ...}` |
| risk_analysis | dry_stats + event_data | "旱天风险" + "雨天溢流风险" | `{dry_risk, rainy_risk}` |
| report_assembler | combined_xlsx + dry_curve_data | 分析报告.docx | `{output_file, stats}` |

---

## 5. 留给 Phase 3 的注意事项

### 5.1 Orchestrator 数据传递

Orchestrator 应按以下方式传递数据：

```python
# 阶段 1: 数据筛选
filter_result = data_filter.run(config, logger)

# 介入点 1: 用户审核筛选结果.xlsx

# 阶段 2: 降雨分析
rainfall_result = rainfall_analysis.run(config, logger)

# 介入点 2: 用户在 baseinfo.xlsx 选择场次
config.reload_baseinfo()

# 阶段 3: 并行分析
dry_result = dry_analysis.run(config, logger)
event_stats_result = event_stats.run(
    config, logger,
    event_data=rainfall_result["event_data_dict"]
)
pattern_result = pattern_analysis.run(
    config, logger,
    dry_curve_data=dry_result["dry_curve_data"]
)

# 介入点 3: 用户审核排污规律分析

# 阶段 4: 后续分析
rdii_result = rdii_analysis.run(
    config, logger,
    dry_curve_data=dry_result["dry_curve_data"],
    event_data=rainfall_result["event_data_dict"]
)
risk_result = risk_analysis.run(
    config, logger,
    event_data=rainfall_result["event_data_dict"]
)

# 阶段 5: 报告组装
report_result = report_assembler.run(
    config, logger,
    dry_curve_data=dry_result["dry_curve_data"]
)
```

### 5.2 介入点实现

三处介入点需要阻塞等待用户确认：

1. **介入点 1**: 数据筛选完成后，等待用户审核 `筛选结果.xlsx`
2. **介入点 2**: 降雨分析完成后，等待用户在 `baseinfo.xlsx` 填写选中场次编号
3. **介入点 3**: 排污规律分析完成后，等待用户审核 `综合分析结果.xlsx` 的"排污规律分析" Sheet

### 5.3 复用机制

Orchestrator 应检查模块输出是否已存在，询问用户是否复用：

```python
def _should_skip(module_name: str, output_path: Path) -> bool:
    if not output_path.exists():
        return False
    ans = input(f"检测到已有 {module_name} 输出，是否复用？(y/n): ")
    return ans.lower() == 'y'
```

---

## 6. 已知的小问题

### 6.1 特征曲线 Sheet 数量较多

**问题**: 如果点位数量多（如 30+），会创建 30+ 个 Sheet，Excel 打开可能较慢。

**影响**: 仅影响用户体验，不影响功能正确性。

**状态**: 暂不处理，Phase 5 验收时评估是否需要优化。

### 6.2 从 Excel 读取时间数据

**问题**: 从 Excel 读取特征曲线时，时间列需要重新生成时间索引。

**当前处理**: 使用 `pd.date_range("00:00:00", "23:59:00", freq="T")[:len(df)]` 生成。

**状态**: 可正常工作，但假设特征曲线始终从 00:00 开始。

### 6.3 点位编号解析

**问题**: 从文件名解析点位编号的逻辑（如 `35891_#1.csv` -> `#1`）可能与实际文件名不匹配。

**影响**: 如果文件名格式不同，可能导致点位匹配失败。

**状态**: 需要根据实际数据调整解析逻辑。

---

## 7. 下一步行动

Phase 3 的主要任务：

1. **Task 3.1**: 创建 `orchestrator/` 目录
2. **Task 3.2**: 实现 `pipeline_runner.py`，串联所有模块
3. **Task 3.3**: 实现三处人工介入点
4. **Task 3.4**: 实现复用机制
5. **Task 3.5**: 更新 `run.py` 入口文件

**前置条件**: 
- Phase 2 已完成，所有模块入口已标准化
- Config 类可用
- 模块可通过返回值传递数据

---

**END of PHASE-2-NOTES**
