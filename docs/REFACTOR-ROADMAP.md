# 重构路线图 (REFACTOR-ROADMAP)

> **版本**: v0.1
> **创建日期**: 2026-05-23
> **配套文档**: [PRD-v0.3.md](./PRD-v0.3.md), [ARCHITECTURE.md](./ARCHITECTURE.md)

---

## 1. 现状分析

### 1.1 代码结构现状

项目目前存在**两套并行代码**：

| 目录 | 状态 | 说明 |
|------|------|------|
| `sewage_monitoring/` | 当前主代码 | 有完整 Orchestrator、6 个 Agent、LLM 集成、数据加载 |
| `pipeline/` | 目标架构 | 模块边界清晰，但缺 Orchestrator、缺部分模块 |
| `_archive_old_agents/` | 已归档 | 旧版代码，保留参考 |

### 1.2 模块对比表

| PRD 要求模块 | `sewage_monitoring/agents/` | `pipeline/` | 差距 |
|-------------|----------------------------|-------------|------|
| data_filter | ✅ filter_agent.py | ✅ data_filter/ | 两边都有实现 |
| dry_analysis | ❌ 合并在 statistics_agent.py | ✅ dry_analysis/ | sewage_monitoring 缺独立模块 |
| rainfall_analysis | ✅ rainfall_agent.py | ✅ rainfall_analysis/ | 两边都有实现 |
| event_stats | ❌ 内嵌在 rdii_analysis | ❌ 不存在 | 需新建独立步骤 |
| rdii_analysis | ❌ 无 | ✅ rdii_analysis/ | sewage_monitoring 缺此模块 |
| risk_analysis | ✅ risk_agent.py | ❌ 不存在 | pipeline 缺此模块 |
| pattern_analysis | ✅ pattern_agent.py | ✅ pattern_analysis/ | 两边都有实现 |
| report_assembler | ✅ report_agent.py | ✅ report_assembler/ | 两边都有实现，但有已知问题 |

### 1.3 基础设施对比

| PRD 要求 | `sewage_monitoring/` | `pipeline/` | 差距 |
|----------|---------------------|-------------|------|
| `core/config.py` | settings.py (部分功能) | 无 | 需新建统一 Config 类 |
| `core/llm_client.py` | utils/pattern_llm_client.py | 无 | 需提取为公共模块 |
| `core/logger.py` | utils/logger.py | 无 | 需迁移到 core/ |
| `core/exceptions.py` | 无 | 无 | 需新建 |
| `orchestrator/pipeline_runner.py` | orchestrator.py | 无 | 需重构迁移 |
| `prompts/` 目录 | 无 (内嵌在代码中) | 无 | 需新建 |

### 1.4 已知问题

根据 PRD 第 5.8 节，报告组装模块存在以下问题：
- ❌ 字段填错位置（模板字段映射有问题）
- ❌ 视觉错位（填对了字段但格式乱了）
- ❌ 生成文字不通顺（LLM prompt 需要优化）

### 1.5 介入点对比

| PRD 要求 | 当前实现 | 差距 |
|----------|---------|------|
| 介入点 1: 筛选结果审核 | ✅ 已实现 | 需增加"复用上次结果"机制 |
| 介入点 2: 降雨场次选择 | ❌ 未实现 | 需新增 baseinfo.xlsx 交互 |
| 介入点 3: 排污规律 LLM 审核 | ❌ 未实现 | 需新增 |

---

## 2. 重构目标

### 2.1 总体目标

**以 `pipeline/` 的模块边界为目标架构，合并 `sewage_monitoring/` 的集成能力，统一为单一代码主线。**

### 2.2 具体目标

1. **统一目录结构**：实现 ARCHITECTURE.md 定义的目录结构
2. **补齐缺失模块**：event_stats、risk_analysis
3. **统一配置系统**：实现三层配置（baseinfo.xlsx + config.yaml + .env）
4. **完善介入点**：实现 3 个人工介入点
5. **修复报告组装**：解决字段映射和格式问题
6. **删除冗余代码**：清理 `sewage_monitoring/` 和 `_archive_old_agents/`

---

## 3. 重构阶段规划

> **⚠️ 重要约束**：从 Phase 1 开始，所有新写的代码**绝对不能** `import sewage_monitoring/`，只能 `import core/` 和 `pipeline/`。这条规则必须严格遵守，否则无法完成代码主线统一。

### Phase 1: 基础设施完整实现（预计 3-4 天）

**目标**：完整实现 `core/` 目录和 `prompts/` 目录，**包括 Config 类的完整实现**

> **为什么 Config 必须在 Phase 1 完成**：Phase 2 的所有模块入口都需要 `run(config: Config, logger)`，如果 Config 不存在，模块代码根本跑不起来。

#### Task 1.1: 创建 core/ 目录结构（完整实现）

```
core/
├── __init__.py
├── config.py          # 统一 Config 类（完整实现三层配置）
├── llm_client.py      # LLM 客户端
├── logger.py          # 日志配置
└── exceptions.py      # 自定义异常
```

**步骤**：
1. 创建 `core/exceptions.py`，定义 LLMDisabledError, LLMFailedAfterRetry, ConfigLoadError 等异常
2. 创建 `core/logger.py`，从零实现日志配置（不依赖旧代码）
3. 创建 `core/config.py`，**完整实现**三层配置加载：
   ```python
   class Config:
       def __init__(self):
           self._env = self._load_env(".env")
           self._yaml = self._load_yaml("config.yaml")
           self._baseinfo = self._load_baseinfo(...)
       
       @classmethod
       def load(cls) -> "Config": ...
       
       @classmethod
       def for_testing(cls, **kwargs) -> "Config": ...
       
       def reload_baseinfo(self): ...
       
       # 输入路径（完整实现）
       @property
       def flow_data_dir(self) -> Path: ...
       
       @property
       def rainfall_data_path(self) -> Path: ...
       
       # 输出路径（完整实现）
       @property
       def output_dir(self) -> Path: ...
       
       @property
       def combined_xlsx_path(self) -> Path: ...
       
       @property
       def filter_result_path(self) -> Path: ...
       
       # 用户参数（完整实现）
       @property
       def smooth_window_minutes(self) -> int: ...
       
       @property
       def rainfall_gap_hours(self) -> int: ...
       
       @property
       def rainfall_delay_hours(self) -> int: ...
       
       @property
       def selected_rainfall_events(self) -> list[int]: ...
   ```
4. 创建 `core/llm_client.py`，实现统一 LLM 客户端（参考旧代码但不依赖）

**验收标准**：
- [ ] `core/` 目录创建完成
- [ ] Config 类所有属性可正常访问
- [ ] 单元测试覆盖 Config 类加载逻辑
- [ ] LLM 客户端支持重试机制
- [ ] **Config.for_testing() 工厂方法可用**

#### Task 1.2: 创建 baseinfo.xlsx 模板

**位置**：`data/baseinfo.xlsx`

**Sheet 结构**：
- `项目基本信息`: 项目名称、监测起止时间、报告标题、撰写人
- `分析参数`: 平滑窗口(分钟)、降雨场次划分间隔(小时)、降雨影响延迟(小时)
- `降雨场次选择`: 用户填写选中场次编号（介入点 2 后填写）

**验收标准**：
- [ ] Excel 文件创建完成
- [ ] Config 类能正确读取所有参数

#### Task 1.3: 创建 prompts/ 目录

```
prompts/
├── pattern_analysis.txt    # 排污规律分析 prompt
└── report_summary.txt      # 报告小结 prompt
```

**步骤**：
1. 从旧代码中提取 prompt 模板内容
2. 写入独立文件，便于版本管理

---

### Phase 2: 模块补齐与标准化（预计 3-4 天）

**目标**：补齐缺失模块，统一模块接口

> **前置条件**：Phase 1 完成后，Config 类已可用，所有模块可以直接使用 `run(config: Config, logger)`

#### Task 2.1: 新建 event_stats 模块

**位置**：`pipeline/event_stats/`

**来源**：从 `pipeline/rdii_analysis/analyzer.py` 提取降雨事件统计逻辑

**输出**：
- `综合分析结果.xlsx` 的 `雨天事件统计` Sheet

**模块入口**：
```python
# pipeline/event_stats/runner.py
from core.config import Config
from core.logger import Logger

def run(config: Config, logger: Logger) -> None:
    """
    雨天事件统计入口。
    
    输入:
        - 选定的降雨场次（从 config.selected_rainfall_events）
        - 降雨影响延迟参数（从 config.rainfall_delay_hours）
        - 各点位监测数据（从 config.flow_data_dir）
    
    输出:
        - config.combined_xlsx_path 的"雨天事件统计" Sheet
    """
    pass
```

#### Task 2.2: 新建 risk_analysis 模块

**位置**：`pipeline/risk_analysis/`

**来源**：从旧代码迁移并拆分（手动重写，不 import 旧代码）

**输出**：
- `综合分析结果.xlsx` 的 `旱天风险` Sheet（Part 1）
- `综合分析结果.xlsx` 的 `雨天溢流风险` Sheet（Part 2）

**关键改动**：
- 原 risk_agent.py 需拆分为旱天风险 + 雨天溢流风险两部分
- 雨天溢流风险依赖 event_stats 的输出

#### Task 2.3: 标准化现有模块入口

**涉及模块**：data_filter, dry_analysis, rainfall_analysis, rdii_analysis, pattern_analysis, report_assembler

**统一接口**：
```python
# pipeline/<module_name>/runner.py
from core.config import Config

def run(config: Config, logger) -> None:
    """模块入口函数"""
    pass
```

**步骤**：
1. 为每个模块创建或修改 `runner.py`
2. 确保所有路径从 config 获取，不硬编码
3. 统一输入输出约定
4. **每个模块独立可测试**（使用 Config.for_testing()）

---

### Phase 3: Orchestrator 重构（预计 2-3 天）

**目标**：实现编排器，串联所有模块

#### Task 3.1: 创建 orchestrator/ 目录

```
orchestrator/
├── __init__.py
└── pipeline_runner.py    # Pipeline 主流程
```

#### Task 3.2: 实现三阶段介入点

```python
# orchestrator/pipeline_runner.py
from core.config import Config
from core.logger import setup_logger

class Orchestrator:
    def __init__(self, config: Config):
        self.config = config
        self.logger = setup_logger(config.output_dir)
    
    def run(self):
        # 阶段 1: 数据筛选
        self._run_module("data_filter", critical=True)
        self._wait_for_user("数据筛选完成,请审核 outputs/筛选结果.xlsx")  # 介入点 1

        # 阶段 2: 降雨分析
        self._run_module("rainfall_analysis", critical=True)
        self._wait_for_user("请在 baseinfo.xlsx 中填写选中场次编号")  # 介入点 2
        self.config.reload_baseinfo()

        # 阶段 3: 并行分析
        self._run_module("dry_analysis", critical=True)
        self._run_module("event_stats", critical=True)
        self._run_module("pattern_analysis", critical=False)
        self._wait_for_user("排污规律分析完成,请审核")  # 介入点 3

        # 阶段 4: 后续分析
        self._run_module("rdii_analysis", critical=False)
        self._run_module("risk_analysis", critical=True)

        # 阶段 5: 报告组装
        self._run_module("report_assembler", critical=True)

def main():
    config = Config.load()
    orchestrator = Orchestrator(config)
    orchestrator.run()
```

#### Task 3.3: 实现复用机制

```python
def _should_skip(self, module_name: str) -> bool:
    """检查模块是否已有输出,询问用户是否复用"""
    output_path = self._get_module_output_path(module_name)
    if not output_path.exists():
        return False
    ans = input(f"检测到已有 {module_name} 输出,是否直接使用?(y/n): ")
    return ans == 'y'
```

#### Task 3.4: 更新入口文件

```python
# run.py
from orchestrator.pipeline_runner import main

if __name__ == "__main__":
    main()
```

---

### Phase 4: 报告组装修复（预计 2-3 天）

**目标**：修复字段映射和格式问题

#### Task 4.1: 字段映射表梳理

**问题根源**：
- 模板表格列顺序与代码假设不一致
- 段落匹配关键词不准确

**解决方案**：
1. 解析 Word 模板，提取所有表格列名
2. 建立明确的字段映射表（占位符 → 数据源）
3. 使用列名匹配而非索引匹配

#### Task 4.2: 格式保持优化

**问题根源**：
- 填充单元格时丢失原有格式
- 插入段落时样式继承不正确

**解决方案**：
1. 使用 `cell.text = value` 前保存原有格式
2. 填充后恢复格式属性
3. 新增段落继承相邻段落样式

#### Task 4.3: LLM Prompt 优化

**优化方向**：
1. 明确输出格式要求
2. 添加示例文本
3. 限制字数范围

---

### Phase 5: 清理与验收（预计 1-2 天）

**目标**：删除冗余代码，完成验收

> **保留 sewage_monitoring/ 直到 Phase 5**：在确认新架构完全可用之前，保留旧代码作为参考。但新代码从不 import 它。

#### Task 5.1: 删除冗余代码

```bash
# 删除旧代码目录
rm -rf sewage_monitoring/
rm -rf _archive_old_agents/
```

**前提条件**：
- 所有模块已迁移到 pipeline/
- Orchestrator 已迁移到 orchestrator/
- 测试全部通过
- 端到端 Pipeline 跑通

#### Task 5.2: 验收测试

**验收清单**（来自 PRD 第 9 节）：

**功能验收**：
- [ ] 7 个核心模块 + 1 个内部步骤全部实现
- [ ] 端到端 Pipeline 跑通,产出 Word 报告
- [ ] 数据筛选支持"复用上次结果"机制
- [ ] 3 个人工介入点工作正常
- [ ] baseinfo.xlsx 的 3 个核心参数能正确读取
- [ ] Word 报告字段填充位置正确、格式正确

**工程化验收**：
- [ ] `sewage_monitoring/` 和 `_archive_old_agents/` 已删除
- [ ] 代码主线统一在 `pipeline/`
- [ ] 报告组装模块有单元测试
- [ ] README 完整
- [ ] Git 提交规范化

---

## 4. 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 迁移过程中破坏现有功能 | 高 | 每个模块迁移前后运行测试对比 |
| 报告组装修复工作量超预期 | 中 | 优先打通字段映射，格式问题迭代优化 |
| 三层配置复杂度 | 低 | 参考 ARCHITECTURE.md 设计实现 |
| 介入点交互设计 | 低 | 保持简单命令行交互 |

---

## 5. 里程碑

| 阶段 | 预计完成 | 交付物 |
|------|---------|--------|
| Phase 1 | Day 4 | core/ 目录（含完整 Config）、prompts/、baseinfo.xlsx 模板 |
| Phase 2 | Day 8 | event_stats、risk_analysis 模块、所有模块入口标准化 |
| Phase 3 | Day 11 | orchestrator/ 目录、3 个介入点、run.py 更新 |
| Phase 4 | Day 14 | 修复后的报告组装模块 |
| Phase 5 | Day 16 | 清理完成、验收通过 |

---

## 6. 执行策略

### 6.1 分支策略

建议在独立分支进行重构：
```bash
git checkout -b refactor/unified-pipeline
```

### 6.2 提交规范

使用 Conventional Commits：
- `feat(core): add unified Config class`
- `refactor(pipeline): migrate risk_analysis module`
- `fix(report): correct field mapping for risk table`

### 6.3 测试策略

- 每完成一个模块迁移，立即补充/更新单元测试
- 使用 `data_sample/` 进行集成测试
- 保留一份真实数据作为回归测试基准

---

## 7. 附录：文件迁移映射表

| 源文件 | 目标位置 | 操作 |
|--------|---------|------|
| `sewage_monitoring/utils/logger.py` | `core/logger.py` | 迁移 |
| `sewage_monitoring/utils/pattern_llm_client.py` | `core/llm_client.py` | 提取通用部分 |
| `sewage_monitoring/orchestrator.py` | `orchestrator/pipeline_runner.py` | 重构迁移 |
| `sewage_monitoring/settings.py` | `core/config.py` | 合并重构 |
| `sewage_monitoring/agents/filter_agent.py` | `pipeline/data_filter/runner.py` | 接口适配 |
| `sewage_monitoring/agents/rainfall_agent.py` | `pipeline/rainfall_analysis/runner.py` | 接口适配 |
| `sewage_monitoring/agents/statistics_agent.py` | `pipeline/dry_analysis/runner.py` | 拆分合并 |
| `sewage_monitoring/agents/risk_agent.py` | `pipeline/risk_analysis/runner.py` | 拆分迁移 |
| `sewage_monitoring/agents/pattern_agent.py` | `pipeline/pattern_analysis/runner.py` | 接口适配 |
| `sewage_monitoring/agents/report_agent.py` | `pipeline/report_assembler/runner.py` | 修复迁移 |
| `pipeline/rdii_analysis/analyzer.py` (部分) | `pipeline/event_stats/runner.py` | 提取新建 |

---

**END of REFACTOR-ROADMAP**
