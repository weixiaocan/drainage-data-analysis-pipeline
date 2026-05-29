# Phase 3: Orchestrator 实现计划

## Context

**背景**：Phase 1 和 Phase 2 已完成，core/ 目录和 pipeline/ 下 8 个模块全部实现并标准化。现在需要实现 Orchestrator 来串联所有模块，实现完整的 Pipeline 流程。

**目标**：
1. 创建 orchestrator/ 目录
2. 实现 Pipeline 主流程编排
3. 实现三处人工介入点
4. 实现复用机制
5. 更新 run.py 入口文件

**约束**：
- 红线规则：新代码禁止 `import sewage_monitoring/` 或 `import _archive_old_agents/`
- 数据传递：通过返回值传递上游数据给下游模块
- 错误分级：核心模块失败终止，辅助模块失败跳过

---

## 现有模块接口

| 模块 | 函数签名 | 上游数据参数 | 返回值 key |
|------|----------|-------------|-----------|
| data_filter | `run(config, logger) -> dict` | 无 | `selected` |
| dry_analysis | `run(config, logger) -> dict` | 无 | `dry_curve_data`, `statistics` |
| rainfall_analysis | `run(config, logger) -> dict` | 无 | `event_data_dict`, `daily_rain`, `event_rain` |
| event_stats | `run(config, logger, event_data=None) -> dict` | `event_data` | `event_stats` |
| pattern_analysis | `run(config, logger, dry_curve_data=None) -> dict` | `dry_curve_data` | `pattern_df`, `descriptions` |
| rdii_analysis | `run(config, logger, dry_curve_data=None, event_data=None) -> dict` | `dry_curve_data`, `event_data` | `max_level`, `avg_flow`, ... |
| risk_analysis | `run(config, logger, event_data=None) -> dict` | `event_data` | `dry_risk`, `rainy_risk` |
| report_assembler | `run(config, logger, dry_curve_data=None) -> dict` | `dry_curve_data` | `output_file`, `stats` |

**数据传递链**：
```
dry_analysis.dry_curve_data → pattern_analysis, rdii_analysis, report_assembler
rainfall_analysis.event_data_dict → event_stats, rdii_analysis, risk_analysis
```

---

## 模块分级

**核心模块**（失败终止 Pipeline）：
- data_filter, rainfall_analysis, dry_analysis, event_stats, pattern_analysis, risk_analysis, report_assembler

**辅助模块**（失败跳过继续）：
- rdii_analysis

---

## 实施步骤

### Task 3.1: 创建 orchestrator/ 目录结构

```
orchestrator/
├── __init__.py
└── pipeline_runner.py
```

### Task 3.2: 实现 pipeline_runner.py

**Orchestrator 类核心设计**：

```python
class Orchestrator:
    # 模块注册表（执行顺序）
    MODULES = [
        ModuleInfo("data_filter", "pipeline.data_filter.runner", critical=True),
        # === 介入点 1 ===
        ModuleInfo("rainfall_analysis", "pipeline.rainfall_analysis.runner", critical=True),
        # === 介入点 2 ===
        ModuleInfo("dry_analysis", "pipeline.dry_analysis.runner", critical=True),
        ModuleInfo("event_stats", "pipeline.event_stats.runner", critical=True),
        ModuleInfo("pattern_analysis", "pipeline.pattern_analysis.runner", critical=True),
        # === 介入点 3 ===
        ModuleInfo("rdii_analysis", "pipeline.rdii_analysis.runner", critical=False),
        ModuleInfo("risk_analysis", "pipeline.risk_analysis.runner", critical=True),
        ModuleInfo("report_assembler", "pipeline.report_assembler.runner", critical=True),
    ]

    INTERVENTION_POINTS = [
        {"after": "data_filter", "message": "数据筛选完成，请审核筛选结果.xlsx", "type": "review"},
        {"after": "rainfall_analysis", "message": "请在 baseinfo.xlsx 填写选中场次编号", "type": "reload"},
        {"after": "pattern_analysis", "message": "请审核综合分析结果.xlsx 的排污规律分析 Sheet", "type": "review"},
    ]
```

**关键方法**：

1. `run()` - 主流程
   - 遍历 MODULES 执行
   - 在介入点暂停等待用户确认
   - 根据模块分级处理失败

2. `_run_module(module_info, logger)` - 执行单个模块
   - 检查复用机制
   - 动态导入 runner
   - 准备上游数据参数
   - 捕获异常并处理

3. `_prepare_module_kwargs(module_info)` - 准备上游数据
   ```python
   # 从 state.data 获取上游数据
   if module needs dry_curve_data:
       kwargs["dry_curve_data"] = state.data["dry_analysis"]["dry_curve_data"]
   if module needs event_data:
       kwargs["event_data"] = state.data["rainfall_analysis"]["event_data_dict"]
   ```

4. `_wait_for_user(point)` - 阻塞式等待
   ```python
   print(message)
   ans = input("输入 y 继续 (q 退出): ")
   if ans == "q": sys.exit(0)
   if type == "reload": config.reload_baseinfo()
   ```

5. `_should_skip_module(module_info)` - 复用机制
   - 检查输出文件是否存在
   - 询问用户是否复用

### Task 3.3: 更新 run.py

```python
# run.py
from orchestrator.pipeline_runner import Orchestrator
from core.config import Config

def main():
    config = Config.load()
    orchestrator = Orchestrator(config)
    success = orchestrator.run()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
```

---

## 介入点详细设计

### 介入点 1: 数据筛选完成后
- 触发时机：data_filter 模块执行后
- 行为：打印提示，等待用户输入 y 继续
- 文件：`outputs/筛选结果.xlsx`

### 介入点 2: 降雨分析完成后
- 触发时机：rainfall_analysis 模块执行后
- 行为：
  1. 打印提示，等待用户在 baseinfo.xlsx 填写选中场次
  2. 用户输入 y 后，调用 `config.reload_baseinfo()`
  3. 打印选中的场次编号

### 介入点 3: 排污规律分析完成后
- 触发时机：pattern_analysis 模块执行后
- 行为：打印提示，等待用户审核综合分析结果.xlsx

---

## 数据传递逻辑

```python
# 阶段 1
filter_result = data_filter.run(config, logger)
# 介入点 1

# 阶段 2
rainfall_result = rainfall_analysis.run(config, logger)
# 介入点 2
config.reload_baseinfo()

# 阶段 3
dry_result = dry_analysis.run(config, logger)
event_stats.run(config, logger, event_data=rainfall_result["event_data_dict"])
pattern_analysis.run(config, logger, dry_curve_data=dry_result["dry_curve_data"])
# 介入点 3

# 阶段 4
rdii_analysis.run(config, logger,
    dry_curve_data=dry_result["dry_curve_data"],
    event_data=rainfall_result["event_data_dict"])
risk_analysis.run(config, logger, event_data=rainfall_result["event_data_dict"])

# 阶段 5
report_assembler.run(config, logger, dry_curve_data=dry_result["dry_curve_data"])
```

---

## 复用机制

当模块输出已存在时：
1. 检查输出文件是否存在
2. 如果存在，询问用户是否复用
3. 用户选择 y 则跳过该模块，选择 n 则重新执行

---

## 辅助模块失败处理

当辅助模块（rdii_analysis）失败时，**不能静默跳过**，需要：

1. 在 `综合分析结果.xlsx` 中创建对应的 Sheet
2. Sheet 内容标明计算失败及原因
3. 日志记录失败详情

**示例实现**：

```python
def _handle_auxiliary_module_failure(self, module_name: str, error: Exception, logger):
    """处理辅助模块失败，创建占位 Sheet"""
    import pandas as pd
    from datetime import datetime
    
    combined_xlsx = self.config.combined_xlsx_path
    
    # 创建失败说明 DataFrame
    error_df = pd.DataFrame([{
        "状态": "计算失败",
        "失败时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "失败原因": str(error),
        "说明": "该模块为辅助模块，失败后跳过。请检查数据或参数后重新运行该模块。",
    }])
    
    # 追加到综合分析结果
    sheet_mapping = {
        "rdii_analysis": "RDII分析",
    }
    
    sheet_name = sheet_mapping.get(module_name, module_name)
    
    try:
        with pd.ExcelWriter(combined_xlsx, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            error_df.to_excel(writer, sheet_name=sheet_name, index=False)
        logger.info(f"已在 {sheet_name} Sheet 中记录失败信息")
    except Exception as e:
        logger.warning(f"写入失败信息到 Excel 时出错: {e}")
```

---

## 关键文件

- `core/config.py` - Config 类，包含 reload_baseinfo() 方法
- `core/logger.py` - setup_logger() 函数
- `pipeline/*/runner.py` - 各模块入口
- `docs/PHASE-2-NOTES.md` - 数据传递约定参考

---

## 验收标准

1. `orchestrator/` 目录创建完成
2. `orchestrator/pipeline_runner.py` 实现完整
3. 三处介入点工作正常
4. 数据传递正确（上游数据传递给下游模块）
5. 错误分级处理正确（核心模块失败终止，辅助模块失败跳过）
6. 复用机制工作正常
7. `run.py` 更新完成，可以启动 Pipeline
8. 端到端测试：运行 `python run.py` 完成完整流程

---

## 测试验证

```bash
# 1. 单元测试
pytest tests/unit/test_orchestrator.py -v

# 2. 端到端测试（使用 sample 数据）
python run.py

# 3. 验证介入点
# - 介入点 1 后暂停，审核筛选结果.xlsx
# - 介入点 2 后暂停，填写 baseinfo.xlsx
# - 介入点 3 后暂停，审核综合分析结果.xlsx
```
