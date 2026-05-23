# Phase 1 实施记录

> **执行日期**: 2026-05-23
> **执行阶段**: Phase 1 - 基础设施完整实现

---

## 1. 实际产出文件清单

### core/ 目录

| 文件 | 说明 | 行数 |
|------|------|------|
| `core/__init__.py` | 导出主要类 | ~20 |
| `core/exceptions.py` | 3 个自定义异常 | ~25 |
| `core/logger.py` | 日志配置（全局 logging） | ~40 |
| `core/config.py` | 统一 Config 类（三层配置） | ~340 |
| `core/llm_client.py` | LLM 客户端（重试 + 禁用） | ~140 |

### tests/unit/ 目录

| 文件 | 说明 |
|------|------|
| `tests/unit/__init__.py` | 包初始化 |
| `tests/unit/test_config.py` | Config 类单元测试（10 tests） |
| `tests/unit/test_llm_client.py` | LLMClient 单元测试（6 tests） |

### 配置文件

| 文件 | 说明 |
|------|------|
| `data/baseinfo.xlsx` | 用户配置模板（3 个 Sheet） |

### prompts/ 目录

| 文件 | 说明 |
|------|------|
| `prompts/pattern_analysis.txt` | 排污规律分析 System Prompt |
| `prompts/report_summary.txt` | 报告小结生成 Prompt |

---

## 2. 与原 ROADMAP 的偏差

### 2.1 无偏差的部分

- 文件结构完全符合 ROADMAP 定义
- Config 类实现了三层配置加载
- LLMClient 实现了重试机制（3 次，指数退避）
- 单元测试覆盖了核心功能
- baseinfo.xlsx 的 Sheet 结构符合设计

### 2.2 小幅调整

| 原计划 | 实际实现 | 调整原因 |
|--------|---------|---------|
| Config 从 `__init__` 直接加载三层配置 | 分离为 `load()` 和 `for_testing()` 两个入口 | `for_testing()` 需要完全跳过文件加载，便于单元测试 |
| logger 返回 Logger 对象 | logger 返回日志文件路径 | 使用 `logging.basicConfig` 配置全局日志，模块通过 `logging.getLogger(__name__)` 获取 logger |

### 2.3 无缺失功能

所有 ROADMAP 中定义的验收标准均已达成。

---

## 3. 关键决策记录

### 决策 1: Config.for_testing() 设计为完全跳过文件加载

**背景**: 测试时需要构造临时路径，不想依赖真实文件。

**决策**: `for_testing()` 不调用任何 `_load_*` 方法，直接设置内部属性。

**理由**:
- 测试隔离更彻底
- 避免测试环境缺少文件时报错
- 符合 ROADMAP 中"跳过文件加载"的要求

### 决策 2: baseinfo.xlsx 不存在时使用默认值，不抛错

**背景**: Phase 1 Task 1.2 创建 baseinfo.xlsx 前，Task 1.1 的 Config 类需要能运行。

**决策**: `_load_baseinfo()` 在文件不存在时返回默认值字典，不抛 `ConfigLoadError`。

**理由**:
- 开发阶段更灵活
- 用户可以先跑起来，再创建配置文件
- 但 `config.yaml` 缺失时仍抛错（这是必需文件）

### 决策 3: LLMClient 增加 chat_json() 方法

**背景**: pattern_llm_client.py 中使用了 `response_format={"type": "json_object"}`。

**决策**: 新增 `chat_json()` 方法，自动添加 JSON 格式要求。

**理由**:
- 排污规律分析需要 JSON 输出
- 与普通 `chat()` 分开，语义更清晰

### 决策 4: prompt 模板从旧代码提取，而非复制

**背景**: pattern_llm_client.py 中有完整的排污规律分析 prompt。

**决策**: 提取到独立文件，内容基本保持一致，格式稍作整理。

**理由**:
- 保持 prompt 内容与旧代码一致，降低风险
- 后续 Phase 4 优化报告组装时可以迭代

---

## 4. 留给 Phase 2 的注意事项

### 4.1 模块入口统一

所有 `pipeline/` 下的模块需要改造为：

```python
from core.config import Config

def run(config: Config, logger) -> None:
    """模块入口函数"""
    pass
```

**当前状态**: 现有模块尚未改造，仍使用旧的 Settings 类或直接硬编码路径。

### 4.2 Config 类的使用方式

```python
# 生产环境
from core import Config
config = Config.load()

# 测试环境
config = Config.for_testing(
    output_dir=tmp_path,
    flow_data_dir="tests/data_sample/flow/"
)
```

**重要**: 所有路径从 config 获取，禁止硬编码。

### 4.3 导入约束

**红线规则**: 从 Phase 1 开始，所有新代码**绝对不能** `import sewage_monitoring/`。

Phase 2 迁移模块时，需要：
1. 用 Read 工具读取旧代码逻辑
2. 在 `pipeline/` 中重写（不复制粘贴）
3. 使用新的 Config 和 Logger

### 4.4 baseinfo.xlsx 的 selected_rainfall_events

当前为空列表。Phase 3 实现介入点 2 后，用户会在 Excel 中填写选中的降雨场次编号，然后调用 `config.reload_baseinfo()` 重新加载。

---

## 5. 已知的小问题

### 5.1 Windows 路径兼容性

**问题**: 测试中 `Path("/tmp/test")` 在 Windows 下会被 resolve 为 `D:/tmp/test`。

**影响**: 单元测试需要用字符串后缀匹配而非精确路径比较。

**状态**: 已在测试代码中处理，不影响生产代码。

### 5.2 prompt 文件编码

**问题**: 控制台输出中文时可能乱码（Windows CMD 默认编码问题）。

**影响**: 仅影响调试输出，不影响文件读写。

**状态**: 文件使用 UTF-8 编码保存，程序内部读取正常。

### 5.3 测试覆盖率

**现状**: 单元测试覆盖了 Config 和 LLMClient 的核心功能。

**未覆盖**:
- Config 与真实 baseinfo.xlsx 的交互（需要集成测试）
- LLMClient 的实际 API 调用（需要 mock 或真实 API）

**建议**: Phase 5 验收前补充集成测试。

---

## 6. 下一步行动

Phase 2 的主要任务：

1. **Task 2.1**: 新建 `pipeline/event_stats/` 模块
2. **Task 2.2**: 新建 `pipeline/risk_analysis/` 模块
3. **Task 2.3**: 标准化现有 6 个模块的入口（data_filter, dry_analysis, rainfall_analysis, rdii_analysis, pattern_analysis, report_assembler）

**前置条件**: Config 类已就绪，可直接使用。

---

**END of PHASE-1-NOTES**
