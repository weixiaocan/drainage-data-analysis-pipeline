# Pipeline架构重构计划

## Context

用户需要重构pipeline架构，实现：
1. **两条独立分析路径**：旱天路径和雨天路径（可选）
2. **新增前置模块**：监测点位数据收集率统计
3. **条件执行逻辑**：无降雨数据时只执行旱天路径
4. **动态报告内容**：无降雨数据时删除报告中的雨天章节

当前问题：所有模块线性执行，无法灵活应对有无降雨数据的场景。

---

## 核心改动

### 1. 新增模块：`data_stats`

**位置**：`src/pipeline/data_stats/`

**计算指标**（按用户确认的计算方式）：
| 指标 | 计算方式 |
|------|----------|
| 监测数据条数 | 该点位CSV文件的实际记录行数 |
| 监测天数 | (数据结束时间 - 数据开始时间).days + 1 |
| 理论数据条数 | 监测天数 × 1440 |
| 数据收集率 | 监测数据条数 / 理论数据条数 × 100%，保留两位小数 |

**输出**：写入 `综合分析结果.xlsx` 的 "数据收集率统计" Sheet

**文件结构**：
```
src/pipeline/data_stats/
├── __init__.py
├── runner.py        # 入口函数 run(config, logger)
├── calculator.py    # 计算逻辑
└── __main__.py      # 独立运行入口
```

---

### 2. 条件执行架构

**修改文件**：`src/orchestrator/pipeline_runner.py`

**扩展 ModuleInfo**：
```python
@dataclass
class ModuleInfo:
    name: str
    runner_path: str
    critical: bool = True
    needs_dry_curve_data: bool = False
    needs_event_data: bool = False
    # 新增
    condition: str | None = None  # "has_rainfall_data" 或 None
```

**扩展 PipelineState**：
```python
@dataclass
class PipelineState:
    data: dict = field(default_factory=dict)
    executed_modules: list = field(default_factory=list)
    failed_modules: list = field(default_factory=list)
    skipped_modules: list = field(default_factory=list)
    # 新增
    has_rainfall_data: bool = True
    rainfall_check_done: bool = False
```

**新模块注册表顺序**：
```python
MODULES = [
    # 公共前置
    ModuleInfo("data_stats", ...),           # 新增
    ModuleInfo("data_filter", ...),
    # 介入点 1
    # 雨天路径（条件执行）
    ModuleInfo("rainfall_analysis", ..., condition="has_rainfall_data"),
    # 介入点 2（条件触发）
    # 旱天路径
    ModuleInfo("dry_analysis", ...),
    ModuleInfo("event_stats", ..., condition="has_rainfall_data", needs_event_data=True),
    ModuleInfo("pattern_analysis", ..., needs_dry_curve_data=True),
    # 介入点 3
    ModuleInfo("rdii_analysis", ..., condition="has_rainfall_data", critical=False),
    ModuleInfo("risk_analysis", ..., needs_event_data=True),
    ModuleInfo("report_assembler", ..., needs_dry_curve_data=True),
]
```

---

### 3. 降雨数据检查

**检查时机**：`data_filter` 执行完成后、`rainfall_analysis` 执行前

**检查逻辑**（在 `Orchestrator` 中新增方法）：
```python
def _check_rainfall_data(self) -> bool:
    rainfall_path = self.config.rainfall_data_path
    # 1. 文件是否存在
    # 2. 文件是否为空
    # 3. 尝试读取验证有效性
```

**条件执行逻辑**：
```python
def run(self) -> bool:
    for module_info in self.MODULES:
        # 条件检查
        if module_info.condition == "has_rainfall_data":
            if not self.state.rainfall_check_done:
                self.state.has_rainfall_data = self._check_rainfall_data()
                self.state.rainfall_check_done = True
            if not self.state.has_rainfall_data:
                self.state.skipped_modules.append(module_info.name)
                continue
        # ... 其余逻辑
```

---

### 4. 介入点调整

**修改介入点定义**：
```python
INTERVENTION_POINTS = [
    {"after": "data_filter", "message": "...", "type": "review"},
    # 介入点2增加条件
    {"after": "rainfall_analysis", "message": "...", "type": "reload",
     "condition": "has_rainfall_data"},
    {"after": "pattern_analysis", "message": "...", "type": "review"},
]
```

**新增介入点检查方法**：
```python
def _should_trigger_intervention(self, point: dict) -> bool:
    condition = point.get("condition")
    if condition == "has_rainfall_data":
        return self.state.has_rainfall_data
    return True
```

---

### 5. 报告动态调整

**修改文件**：`src/pipeline/report_assembler/runner.py` 和 `assembler.py`

**新增参数**：
```python
def run(config, logger, dry_curve_data=None, has_rainfall_data=True):
```

**删除雨天章节逻辑**：
```python
def _remove_rainy_sections(doc: Document) -> None:
    """删除报告中的雨天相关章节"""
    # 查找并删除包含"降雨分析"、"雨天溢流"关键词的段落和其后表格
```

**调整表格填充**：
- 表格2（日降雨量统计）：仅在 `has_rainfall_data=True` 时填充
- 表格3（场次降雨统计）：仅在 `has_rainfall_data=True` 时填充
- 表格18（雨天溢流风险）：仅在 `has_rainfall_data=True` 时填充

---

## 执行流程图

```
data_stats（新增）
      ↓
data_filter
      ↓
【介入点1】审核筛选结果
      ↓
检查降雨数据是否存在？
      ├─ 是 ──────────────────────────────┐
      │                                   ↓
      │                    rainfall_analysis
      │                           ↓
      │                    【介入点2】填写选中场次
      │                           ↓
      │                           event_stats
      │                           ↓
      │                           rdii_analysis
      │                           ↓
      ↓                           ↓
dry_analysis ←────────────────────┘
      ↓
pattern_analysis
      ↓
【介入点3】审核排污规律
      ↓
risk_analysis（旱天风险 + 雨天溢流风险(条件)）
      ↓
report_assembler（根据 has_rainfall_data 调整内容）
```

---

## 关键文件修改清单

| 文件 | 改动类型 | 说明 |
|------|----------|------|
| `src/pipeline/data_stats/runner.py` | 新增 | 入口函数 |
| `src/pipeline/data_stats/calculator.py` | 新增 | 计算逻辑 |
| `src/orchestrator/pipeline_runner.py` | 修改 | 条件执行架构 |
| `src/pipeline/report_assembler/runner.py` | 修改 | 新增 has_rainfall_data 参数 |
| `src/pipeline/report_assembler/assembler.py` | 修改 | 删除雨天章节逻辑 |
| `src/pipeline/risk_analysis/runner.py` | 修改 | 条件执行雨天部分 |

---

## 验证方案

1. **无降雨数据场景测试**：
   - 删除或重命名 `data/降雨数据.csv`
   - 运行 `python run.py`
   - 验证：只执行旱天路径，报告无雨天章节

2. **有降雨数据场景测试**：
   - 保持 `data/降雨数据.csv` 存在
   - 运行 `python run.py`
   - 验证：完整执行两条路径，报告包含全部内容

3. **数据收集率计算测试**：
   - 检查 `综合分析结果.xlsx` 的 "数据收集率统计" Sheet
   - 验证计算公式：收集率 = 实际条数 / (时间跨度天数 × 1440)

---

## 向后兼容性

- `has_rainfall_data` 默认值为 `True`，保持原有行为
- 所有现有模块接口保持不变（仅新增可选参数）
- `data_stats` 模块失败不影响整体流程（可作为非关键模块）
