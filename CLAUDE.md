# 项目协作约定

## 代码导入约束（重构期间强制执行）

> **⚠️ 红线规则**：从重构开始（2026-05-23），所有新写的代码**绝对不能** `import sewage_monitoring/` 或 `import _archive_old_agents/`，只能 `import core/` 和 `pipeline/`。

### 允许的导入

```python
# ✅ 正确
from core.config import Config
from core.llm_client import LLMClient
from core.logger import setup_logger
from core.exceptions import LLMFailedAfterRetry
from pipeline.data_filter.runner import run as run_filter
from pipeline.risk_analysis.runner import run as run_risk
```

### 禁止的导入

```python
# ❌ 错误 - 重构期间禁止
from sewage_monitoring.agents import ...
from sewage_monitoring.utils import ...
from sewage_monitoring.orchestrator import ...
from _archive_old_agents import ...
```

### 为什么有这条规则

1. 重构目标是统一代码主线到 `pipeline/`，新代码依赖旧代码会导致无法删除旧目录
2. `sewage_monitoring/` 和 `_archive_old_agents/` 将在 Phase 5 删除
3. 需要参考旧代码逻辑时，直接读取文件内容，而不是 import

### 如何处理需要参考旧代码的情况

```python
# 如果需要了解旧代码的逻辑：
# 1. 用 Read 工具读取旧代码文件
# 2. 理解逻辑后，在 pipeline/ 或 core/ 中重写
# 3. 不要复制粘贴，理解后重新实现
```

## 模块入口约定

所有 `pipeline/` 下的模块必须遵守统一接口：

```python
# pipeline/<module_name>/runner.py
from core.config import Config
from core.logger import Logger

def run(config: Config, logger: Logger) -> None:
    """
    模块入口函数。
    
    参数:
        config: 全局配置对象，从中获取所有路径和参数
        logger: 日志器
    
    行为:
        - 从 config 指定的路径读取输入
        - 执行模块业务逻辑
        - 把结果写到 config 指定的输出路径
    
    返回:
        None（数据通过文件传递，不通过返回值）
    """
    pass
```

## 配置使用约定

所有路径和参数从 Config 获取，禁止硬编码：

```python
# ✅ 正确
input_path = config.flow_data_dir
output_path = config.combined_xlsx_path
threshold = config.missing_rate_threshold

# ❌ 错误
input_path = Path("data/flow/")
output_path = Path("outputs/综合分析结果.xlsx")
threshold = 0.1
```

## 测试约定

使用 `Config.for_testing()` 进行单元测试：

```python
def test_module(tmp_path):
    config = Config.for_testing(
        flow_data_dir="tests/data_sample/flow/",
        output_dir=tmp_path
    )
    logger = logging.getLogger("test")
    
    run(config, logger)
    
    assert (config.output_dir / "expected_output.xlsx").exists()
```

## Phase 完成后推送约定

每个 Phase 完成后，自动将修改推送到 GitHub：

```bash
# Phase N 完成后执行
git add .
git commit -m "feat(phase-N): 完成 Phase N 描述"
git push origin main
```

**提交信息格式**：
- `feat(phase-1): 完成基础设施实现`
- `feat(phase-2): 完成模块补齐与标准化`
- `feat(phase-3): 完成 Orchestrator 重构`
- `feat(phase-4): 完成报告组装修复`
- `feat(phase-5): 完成清理与验收`

---

## 相关文档

- [产品需求文档](./PRD-v0.3.md)
- [架构设计文档](./ARCHITECTURE.md)
- [重构路线图](./REFACTOR-ROADMAP.md)
