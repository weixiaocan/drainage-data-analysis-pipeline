# Phase 3 实施记录

> **执行日期**: 2026-05-23
> **执行阶段**: Phase 3 - Orchestrator 实现

---

## 1. 实际产出文件清单

### 新建文件

| 目录 | 文件 | 说明 |
|------|------|------|
| `orchestrator/` | `__init__.py` | 模块导出 (`Orchestrator`, `ModuleInfo`, `PipelineState`) |
| | `pipeline_runner.py` | 流程编排核心实现 (~350 行) |

### 修改文件

| 文件 | 修改内容 |
|------|---------|
| `run.py` | 替换旧的 `sewage_monitoring.cli.main` 入口，改用 `Orchestrator` |
| `config.yaml` | 修正 `data_dir` 路径为 `data/flow` |

---

## 2. 与原 ROADMAP 的偏差

### 2.1 无偏差的部分

- 创建 `orchestrator/` 目录结构
- 实现 `Orchestrator`、`ModuleInfo`、`PipelineState` 三类
- 三处人工介入点按计划实现
- 模块分级处理（核心模块失败终止，辅助模块失败跳过）
- 复用机制检查输出文件并询问用户

### 2.2 实现细节调整

| 原计划 | 实际实现 | 调整原因 |
|--------|---------|----------|
| `PipelineState` 未明确设计 | 实现为 dataclass，包含 `data`、`executed_modules`、`failed_modules`、`skipped_modules` | 更清晰的状态管理 |
| 辅助模块失败静默跳过 | 创建占位 Sheet 记录失败信息 | 用户明确要求不能静默跳过 |

### 2.3 执行顺序

按计划执行：Task 3.1 → Task 3.2 → Task 3.3 → 端到端验证

---

## 3. 关键决策记录

### 决策 1: ModuleInfo 使用 dataclass 封装模块元信息

**背景**: 需要在 Orchestrator 中注册模块信息，包括名称、路径、是否核心、数据依赖。

**决策**: 使用 `@dataclass` 定义 `ModuleInfo` 类。

```python
@dataclass
class ModuleInfo:
    name: str                    # 模块名称
    runner_path: str             # runner 模块路径
    critical: bool = True        # 是否为核心模块
    needs_dry_curve_data: bool = False  # 是否需要旱天特征曲线
    needs_event_data: bool = False      # 是否需要场次降雨数据
```

**理由**:
- 数据结构清晰，易于扩展
- IDE 自动补全支持
- 便于后续添加新的依赖类型

### 决策 2: PipelineState 提供便捷方法获取上游数据

**背景**: 下游模块需要获取上游模块产出的数据（如 `dry_curve_data`、`event_data`）。

**决策**: 在 `PipelineState` 中提供 `get_dry_curve_data()` 和 `get_event_data()` 方法。

```python
def get_dry_curve_data(self) -> dict[str, pd.DataFrame] | None:
    if "dry_analysis" in self.data:
        return self.data["dry_analysis"].get("dry_curve_data")
    return None
```

**理由**:
- 封装数据访问逻辑
- 上游模块名称变更时只需修改一处
- 返回 `None` 时模块会自动从 Excel 读取（fallback）

### 决策 3: 介入点使用阻塞式 input()

**背景**: 需要在特定节点暂停等待用户确认。

**决策**: 使用 `input()` 阻塞等待用户输入。

```python
def _wait_for_user(self, point: dict[str, Any]) -> bool:
    print(point["message"])
    while True:
        ans = input("输入 y 继续 (q 退出): ").strip().lower()
        if ans == "q":
            return False
        if ans == "y":
            if point["type"] == "reload":
                self.config.reload_baseinfo()
            return True
```

**理由**:
- 简单直接，符合 CLI 交互习惯
- 介入点 2 需要重新加载 `baseinfo.xlsx`
- 用户可随时选择退出

### 决策 4: 复用机制同时从文件加载数据到 state

**背景**: 用户选择复用已有输出时，后续模块仍需要上游数据。

**决策**: 复用时从 Excel 文件读取数据到 `state.data`。

```python
def _load_module_output_to_state(self, module_info: ModuleInfo) -> None:
    if module_info.name == "dry_analysis":
        dry_curve_data = self._load_dry_curve_data_from_excel(combined_xlsx)
        if dry_curve_data:
            self.state.data["dry_analysis"] = {"dry_curve_data": dry_curve_data}
```

**理由**:
- 复用模块的数据仍可传递给下游
- 与重新执行的效果一致
- 避免下游模块因缺少上游数据而从空 Excel 读取

### 决策 5: 辅助模块失败时创建占位 Sheet

**背景**: 辅助模块（如 `rdii_analysis`）失败时不能静默跳过。

**决策**: 在 `综合分析结果.xlsx` 中创建对应的 Sheet，标明计算失败及原因。

```python
def _handle_auxiliary_module_failure(self, module_name: str) -> None:
    error_df = pd.DataFrame([{
        "状态": "计算失败",
        "失败时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "说明": "该模块为辅助模块，失败后跳过...",
    }])
    # 写入 Excel
```

**理由**:
- 用户可在报告中看到失败信息
- 便于排查问题
- 符合 PRD 对辅助模块失败处理的要求

---

## 4. Orchestrator 接口规范

### 4.1 模块注册表

```python
MODULES: list[ModuleInfo] = [
    ModuleInfo("data_filter", "pipeline.data_filter.runner", critical=True),
    # === 介入点 1 ===
    ModuleInfo("rainfall_analysis", "pipeline.rainfall_analysis.runner", critical=True),
    # === 介入点 2 ===
    ModuleInfo("dry_analysis", "pipeline.dry_analysis.runner", critical=True),
    ModuleInfo("event_stats", "pipeline.event_stats.runner", critical=True, needs_event_data=True),
    ModuleInfo("pattern_analysis", "pipeline.pattern_analysis.runner", critical=True, needs_dry_curve_data=True),
    # === 介入点 3 ===
    ModuleInfo("rdii_analysis", "pipeline.rdii_analysis.runner", critical=False, needs_dry_curve_data=True, needs_event_data=True),
    ModuleInfo("risk_analysis", "pipeline.risk_analysis.runner", critical=True, needs_event_data=True),
    ModuleInfo("report_assembler", "pipeline.report_assembler.runner", critical=True, needs_dry_curve_data=True),
]
```

### 4.2 介入点定义

```python
INTERVENTION_POINTS: list[dict[str, Any]] = [
    {
        "after": "data_filter",
        "message": "【介入点 1】数据筛选完成，请审核筛选结果.xlsx",
        "type": "review",
    },
    {
        "after": "rainfall_analysis",
        "message": "【介入点 2】请在 baseinfo.xlsx 填写选中场次编号",
        "type": "reload",  # 会调用 config.reload_baseinfo()
    },
    {
        "after": "pattern_analysis",
        "message": "【介入点 3】请审核综合分析结果.xlsx 的排污规律分析 Sheet",
        "type": "review",
    },
]
```

### 4.3 数据传递链

```
dry_analysis.dry_curve_data
    ├──→ pattern_analysis (介入点 3 前)
    ├──→ rdii_analysis (介入点 3 后)
    └──→ report_assembler

rainfall_analysis.event_data_dict
    ├──→ event_stats
    ├──→ rdii_analysis
    └──→ risk_analysis
```

---

## 5. 留给 Phase 4 的注意事项

### 5.1 当前 Pipeline 流程完整性

Phase 3 完成后，Pipeline 已可端到端运行：

```bash
python run.py
```

流程：
1. 加载配置 (`Config.load()`)
2. 初始化日志 (`setup_logger()`)
3. 创建 Orchestrator
4. 执行 Pipeline（含 3 个介入点）
5. 输出结果文件

### 5.2 Phase 4 任务：报告组装修复

当前 `report_assembler` 已能生成报告，但可能存在以下问题：

1. **Word 模板占位符**: 需确认所有占位符是否正确填充
2. **图表生成**: 需确认特征曲线图是否正确插入
3. **表格数据**: 需确认各表格数据是否完整

验证方法：
- 打开 `outputs/报告初稿.docx`
- 对比模板检查各部分是否正确填充

### 5.3 介入点交互优化建议

当前介入点使用 `input()` 阻塞，后续可考虑：

1. 添加 `--auto` 模式跳过介入点（用于 CI/CD）
2. 添加 `--skip-reuse` 模式强制重新执行
3. 支持从指定模块开始执行（断点续跑）

### 5.4 复用机制优化建议

当前复用检查基于文件存在性，后续可考虑：

1. 检查文件修改时间与输入数据的时间戳对比
2. 记录上次执行的配置参数，参数变化时自动失效
3. 支持"全部复用"或"全部重新执行"选项

---

## 6. 已知的小问题

### 6.1 复用检查时 dry_analysis 的特殊处理

**问题**: `dry_analysis` 的输出是 `综合分析结果.xlsx` 的一部分，但用户选择复用时，如果该文件存在但"特征曲线_*" Sheet 不存在，会导致后续模块失败。

**当前处理**: 复用时会从 Excel 读取特征曲线数据，如果不存在则返回空字典。

**影响**: 用户需要确保复用的输出文件包含完整的数据。

**状态**: 暂不处理，用户选择复用时需谨慎。

### 6.2 中文路径编码问题

**问题**: Windows 下中文路径在某些终端显示乱码。

**影响**: 仅影响日志显示，不影响文件操作正确性。

**状态**: Python 3 默认使用 UTF-8，文件操作正常。

### 6.3 介入点 2 的场次选择

**问题**: 如果用户在 `baseinfo.xlsx` 中未填写任何场次，`selected_rainfall_events` 为空列表。

**当前处理**: 各模块会处理空列表情况（如 `rdii_analysis` 返回空结果）。

**影响**: 报告中雨天相关分析可能为空。

**状态**: 符合设计预期，用户可选择不分析特定场次。

---

## 7. 端到端验证结果

### 7.1 执行统计

| 指标 | 数值 |
|------|------|
| 执行模块数 | 8 |
| 成功模块数 | 8 |
| 失败模块数 | 0 |
| 跳过模块数 | 0 |
| 总耗时 | ~27 秒 |

### 7.2 输出文件

| 文件 | 大小 | Sheet 数量 |
|------|------|-----------|
| `筛选结果.xlsx` | 6.4 KB | 1 |
| `综合分析结果.xlsx` | 551 KB | 24 |
| `报告初稿.docx` | 2.0 MB | - |

### 7.3 综合分析结果 Sheet 清单

- 日降雨量统计
- 场次降雨统计
- 旱天分析
- 特征曲线_* (13 个点位)
- 雨天事件统计
- 排污规律分析
- 降雨事件最大液位
- 降雨事件平均流量
- RDII总量统计
- 雨天流量总量
- 旱天风险
- 雨天溢流风险
- 数据缺失统计

---

## 8. 下一步行动

Phase 4 的主要任务：

1. **Task 4.1**: 验证报告组装结果，检查 Word 文档各部分
2. **Task 4.2**: 修复报告组装中的问题（如有）
3. **Task 4.3**: 完善错误处理和边界情况

**前置条件**: 
- Phase 3 已完成，Pipeline 可端到端运行
- 输出文件结构完整

**验收标准**:
- 报告内容正确填充
- 所有表格和图表正常显示
- 数据与综合分析结果一致

---

**END of PHASE-3-NOTES**
