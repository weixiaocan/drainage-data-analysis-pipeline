# 排水监测数据处理 Pipeline - 架构设计文档

> 版本: v0.1 (初稿)
> 撰写日期: 2026-05-22
> 状态: 待 review
> 配套文档: [PRD-v0.3.md](./PRD-v0.3.md)

---

## 文档说明

本文档是项目的**架构设计文档 (ARCHITECTURE)**,回答以下问题:

- 代码怎么组织
- 模块之间怎么协作
- 数据怎么流转
- 关键技术决策是什么、为什么

本文档**不回答**:

- 具体某个函数怎么实现(那是代码层面)
- 产品要做什么功能(那是 PRD 层面)

本文档面向两类读者:

- **作者本人**: 长期维护这个项目的参考
- **AI 协作工具(Claude Code 等)**: 每次开发前先读本文档,确保产出的代码符合架构约束

---

## 1. 设计原则

本项目的架构遵循以下核心原则:

### 1.1 简单优先

不为想象中的复杂度提前设计。能用 100 行代码解决的不写 200 行,能用一个文件搞定的不拆成三个文件。**等真正需要再抽象**。

### 1.2 路径不硬编码

所有输入输出路径都从 Config 对象获取,不在代码里写死。这是测试方便、未来部署灵活的基础。

### 1.3 模块通过约定协作,不通过基类

每个模块都遵守同一个"入口函数约定"(见 § 3.2),但不强制继承统一基类。**约定保证一致性,松散保留灵活性**。

### 1.4 配置三层分离

- **用户层** (`baseinfo.xlsx`): 用户填写,Excel 友好
- **技术层** (`config.yaml`): 开发者维护,用户基本不动
- **密钥层** (`.env`): 敏感信息,不进 git

### 1.5 关键节点落盘

模块间数据传递以**内存为主**,在介入点前后**落盘**(Excel 文件)。这样既快,又支持"中断恢复"。

### 1.6 错误分级处理

- **核心模块失败** → Pipeline 终止
- **辅助模块失败** → 跳过,继续后续
- **LLM 调用失败** → 三次重试 → 失败兜底

---

## 2. 顶层目录结构

```
sewage-monitoring-pipeline/
│
├── pipeline/                    # 业务模块(7 个核心模块 + 1 个内部步骤)
│   ├── data_filter/             # 数据筛选
│   ├── dry_analysis/            # 旱天分析
│   ├── rainfall_analysis/       # 降雨分析
│   ├── event_stats/             # 雨天事件统计(内部步骤)
│   ├── rdii_analysis/           # RDII 分析
│   ├── risk_analysis/           # 风险分析(旱天 + 雨天)
│   ├── pattern_analysis/        # 排污规律分析(含 LLM)
│   └── report_assembler/        # 报告组装(含 LLM)
│
├── core/                        # 公共基础设施
│   ├── config.py                # 配置加载(baseinfo + yaml + env)
│   ├── llm_client.py            # LLM 客户端(统一调用入口)
│   ├── logger.py                # 日志配置
│   └── exceptions.py            # 自定义异常
│
├── orchestrator/                # 总编排
│   └── pipeline_runner.py       # Pipeline 主流程 + 介入点
│
├── prompts/                     # LLM prompt 模板(单独文件,便于迭代)
│   ├── pattern_analysis.txt
│   └── report_summary.txt
│
├── tests/                       # 测试
│   ├── unit/                    # 单元测试
│   └── integration/             # 集成测试
│
├── docs/                        # 文档
│   ├── PRD.md
│   ├── ARCHITECTURE.md          # 本文档
│   ├── CURRENT-STATE.md
│   └── decisions/               # ADR(架构决策记录)
│       ├── ADR-001-配置选-Excel.md
│       ├── ADR-002-LLM-使用边界.md
│       └── ADR-003-代码主线合并.md
│
├── data/                        # 真实数据(不进 git)
│   ├── baseinfo.xlsx            # 用户配置(Excel)
│   ├── 点位信息.xlsx
│   ├── flow/                    # 各点位 CSV
│   ├── rainfall.csv             # 降雨数据
│   └── 监测数据分析报告模板.docx
│
├── data_sample/                 # 脱敏样例数据(进 git,供测试用)
│
├── outputs/                     # 运行产出(不进 git)
│   ├── 筛选结果.xlsx
│   ├── 综合分析结果.xlsx
│   ├── 降雨分析图/
│   ├── RDII 分析图/
│   ├── 排污规律图/
│   ├── 分析报告.docx
│   └── logs/
│       └── 2026-05-22-14-30.log
│
├── config.yaml                  # 技术层配置
├── .env                         # 密钥层(不进 git)
├── .env.example                 # 示例(进 git,告诉用户该填什么)
├── .gitignore
├── run.py                       # 顶层启动入口
├── requirements.txt
└── README.md
```

### 关键说明

**`pipeline/`** 放业务,**`core/`** 放公共基础设施,**`orchestrator/`** 放总编排——三个目录职责清楚,新人一眼就懂。

**`event_stats/`** 是"内部步骤",不是对外暴露的独立模块,但放在 `pipeline/` 下保持结构一致。它没有独立 CLI 入口,只被 RDII 和风险分析调用。

**`prompts/`** 单独成目录: prompt 模板版本化管理,改 prompt 不需要改代码。

**`tests/`** 分单元和集成两类,方便分别运行。

**`outputs/logs/`** 每次运行一个时间戳文件,保留历史。

---

## 3. 模块设计

### 3.1 模块依赖关系(DAG)

```
                    [数据筛选 data_filter]
                            │
                  ┌─────────┴─────────┐
                  │  介入点 1: 用户审核 │
                  │  改 Excel 颜色      │
                  └─────────┬─────────┘
                            │
                  [降雨分析 rainfall_analysis]
                            │
                  ┌─────────┴─────────┐
                  │  介入点 2: 用户选场次 │
                  │  填 baseinfo Excel   │
                  └─────────┬─────────┘
                            │
            ┌───────────────┼───────────────┐
            │               │               │
    [旱天分析]      [雨天事件统计]    [排污规律分析(LLM)]
    dry_analysis    event_stats       pattern_analysis
            │               │               │
            │               │       ┌───────┴───────┐
            │               │       │  介入点 3:    │
            │               │       │  用户审核 LLM │
            │               │       └───────┬───────┘
            │               │               │
            │       ┌───────┴───────┐       │
            │       │               │       │
            │   [RDII 分析]   [风险分析     │
            │   rdii_analysis  Part 1+2]    │
            │                 risk_analysis │
            │                       │       │
            └───────────────┬───────┴───────┘
                            │
                    [报告组装 report_assembler] (含 LLM)
                            │
                            ▼
                    outputs/分析报告.docx
```

### 3.2 模块入口约定

每个模块都遵守这个约定:

```python
# pipeline/<module_name>/runner.py

def run(config: Config, logger: Logger) -> None:
    """
    模块入口函数。
    
    参数:
        config: 全局配置对象,从中获取所有路径和参数
        logger: 日志器
    
    行为:
        - 从 config 指定的路径读取输入
        - 执行模块业务逻辑
        - 把结果写到 config 指定的输出路径
    
    返回:
        None(数据通过文件传递,不通过返回值)
    
    异常:
        模块内部异常向上抛出,由 Orchestrator 决定处理策略。
    """
    pass
```

**核心约束**:

- 所有模块都有一个 `run(config, logger) -> None` 函数
- 输入输出路径**全部从 config 来**,不硬编码
- 数据通过约定的文件路径传递,不通过返回值
- 模块内部组织代码自由,可以拆多个文件,也可以单文件

**模块内部典型组织**:

```
pipeline/<module_name>/
├── __init__.py
├── runner.py            # 入口,定义 run() 函数
├── core.py              # 核心计算逻辑(纯函数,易测试)
├── io.py                # 文件读写(如果逻辑复杂)
└── README.md            # 模块说明
```

不强制分这么多文件,简单模块可以全在 `runner.py` 里。

### 3.3 模块之间的数据传递

**原则**: 内存为主,介入点前后落盘。

**具体落盘规则**:

| 模块 | 输出去向 |
|------|---------|
| 数据筛选 | `outputs/筛选结果.xlsx`(必须,介入点 1 用) |
| 降雨分析 | `综合分析结果.xlsx` 的 3 个 Sheet + `outputs/降雨分析图/`(必须,介入点 2 用) |
| 旱天分析 | `综合分析结果.xlsx` 的"旱天分析" Sheet |
| 雨天事件统计 | `综合分析结果.xlsx` 的"雨天事件统计" Sheet |
| RDII 分析 | `综合分析结果.xlsx` 的"RDII 分析" Sheet + `outputs/RDII 分析图/` |
| 排污规律分析 | `综合分析结果.xlsx` 的"排污规律分析" Sheet + `outputs/排污规律图/`(必须,介入点 3 用) |
| 风险分析 | `综合分析结果.xlsx` 的"旱天风险" + "雨天溢流风险" Sheet |
| 报告组装 | `outputs/分析报告.docx` |

**为什么所有模块输出都落盘?**

- 中断恢复:任一模块完成后,Pipeline 即使挂了,下次启动可以从已完成的模块的输出继续(见 § 5 复用机制)
- 调试方便:每个模块的输出都可见,出问题时容易定位
- 没有性能压力:写一个 Sheet 的开销微乎其微

---

## 4. 配置系统设计

### 4.1 三层结构

```
baseinfo.xlsx (用户层)
    │
    ├── Sheet: 项目基本信息
    ├── Sheet: 分析参数
    └── Sheet: 降雨场次选择(介入点 2 后填)
                     │
                     ▼
config.yaml (技术层)
    │
    ├── 输入路径 (data/flow/, data/rainfall.csv, ...)
    ├── 输出路径 (outputs/)
    ├── LLM 配置 (provider, model, enabled)
    └── Pipeline 控制 (介入点开关)
                     │
                     ▼
.env (密钥层)
    │
    ├── DEEPSEEK_API_KEY
    └── DEEPSEEK_BASE_URL
                     │
                     ▼
        合并加载,通过 Config 对象访问
```

### 4.2 Config 类设计

```python
# core/config.py

class Config:
    """运行时配置对象,聚合三层配置。"""
    
    def __init__(self):
        # 三层加载
        self._env = self._load_env(".env")
        self._yaml = self._load_yaml("config.yaml")
        self._baseinfo = self._load_baseinfo(self._yaml["input"]["baseinfo_path"])
        
        # 校验关键参数(略)
    
    @classmethod
    def load(cls) -> "Config":
        return cls()
    
    # ===== 输入输出路径 =====
    @property
    def flow_data_dir(self) -> Path: ...
    
    @property
    def rainfall_data_path(self) -> Path: ...
    
    @property
    def output_dir(self) -> Path: ...
    
    @property
    def combined_xlsx_path(self) -> Path:
        return self.output_dir / "综合分析结果.xlsx"
    
    @property
    def filter_result_path(self) -> Path:
        return self.output_dir / "筛选结果.xlsx"
    
    # ===== 用户参数(从 baseinfo)=====
    @property
    def smooth_window_minutes(self) -> int: ...      # 默认 20
    
    @property
    def rainfall_gap_hours(self) -> int: ...         # 默认 12
    
    @property
    def rainfall_delay_hours(self) -> int: ...       # 默认 48
    
    @property
    def selected_rainfall_events(self) -> list[int]: ...  # 介入点 2 后填
    
    # ===== LLM 配置 =====
    @property
    def llm_enabled(self) -> bool: ...
    
    @property
    def llm_api_key(self) -> str: ...
    
    @property
    def llm_model(self) -> str: ...
```

**为什么用类不用字典**:

- IDE 自动补全,改名时全项目跟着改
- 类型提示明确(`int` vs `str` 一目了然)
- 校验集中在 `__init__` 里做,失败立即报错

### 4.3 测试时的 Config 替换

测试不读真实文件,直接构造一个 Config 实例,指向临时目录:

```python
def test_xxx(tmp_path):
    config = Config.for_testing(
        flow_data_dir="data_sample/flow/",
        output_dir=tmp_path / "outputs"
    )
    run_filter(config, test_logger)
```

`Config.for_testing()` 是一个工厂方法,跳过文件加载,直接用参数构造对象。

---

## 5. Orchestrator 设计

### 5.1 职责

- 知道 7 个模块 + 1 个内部步骤的执行顺序
- 按顺序调度模块
- 在介入点暂停等待用户确认
- 处理模块失败(分级策略)
- 实现"复用机制"(已有输出时询问是否跳过)

### 5.2 主流程伪代码

```python
# orchestrator/pipeline_runner.py

class Orchestrator:
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger("orchestrator")
        self.llm_client = LLMClient(config)  # 全局共享一个实例
    
    def run(self):
        self.logger.info("Pipeline 启动")
        
        # === 阶段 1: 数据筛选 ===
        if self._should_skip("filter"):
            self.logger.info("跳过数据筛选(复用已有结果)")
        else:
            self._run_module("filter", critical=True)
        
        # 介入点 1
        self._wait_for_user("数据筛选完成,请审核 outputs/筛选结果.xlsx")
        
        # === 阶段 2: 降雨分析 ===
        self._run_module("rainfall", critical=True)
        
        # 介入点 2
        self._wait_for_user(
            "降雨分析完成,请在 baseinfo.xlsx 的'降雨场次选择' sheet 中填写选中编号"
        )
        # 重新加载 baseinfo(因为用户改了)
        self.config.reload_baseinfo()
        
        # === 阶段 3: 并行类分析(实际串行) ===
        self._run_module("dry_analysis", critical=True)
        self._run_module("event_stats", critical=True)
        self._run_module("pattern_analysis", critical=False)  # 辅助,失败不终止
        
        # 介入点 3
        self._wait_for_user(
            "排污规律分析完成,请审核综合分析结果.xlsx 的'排污规律分析' sheet"
        )
        
        # === 阶段 4: 后续分析 ===
        self._run_module("rdii_analysis", critical=False)
        self._run_module("risk_analysis", critical=True)
        
        # === 阶段 5: 报告组装 ===
        self._run_module("report_assembler", critical=True)
        
        self.logger.info("Pipeline 完成")
    
    def _run_module(self, name: str, critical: bool):
        """运行单个模块,处理异常。"""
        try:
            self.logger.info(f"开始: {name}")
            module = self._get_module(name)
            module.run(self.config, self.logger)
            self.logger.info(f"完成: {name}")
        except Exception as e:
            if critical:
                self.logger.error(f"核心模块 {name} 失败,Pipeline 终止: {e}", exc_info=True)
                raise
            else:
                self.logger.warning(f"辅助模块 {name} 失败,跳过: {e}", exc_info=True)
    
    def _wait_for_user(self, message: str):
        """阻塞式介入点。"""
        print(f"\n{'='*60}\n{message}\n{'='*60}")
        while True:
            ans = input("完成后输入 y 继续 (q 退出): ").strip().lower()
            if ans == 'y':
                break
            elif ans == 'q':
                self.logger.info("用户主动退出")
                sys.exit(0)
            else:
                print("请输入 y 或 q")
    
    def _should_skip(self, module_name: str) -> bool:
        """检查模块是否已有输出,询问用户是否复用。"""
        output_path = self._get_module_output_path(module_name)
        if not output_path.exists():
            return False
        
        ans = input(
            f"检测到已有 {module_name} 输出 ({output_path}),"
            f"是否直接使用?(y/n): "
        ).strip().lower()
        return ans == 'y'
```

### 5.3 关键设计点

**模块加载**: `self._get_module(name)` 通过名字找到对应模块的 `run` 函数。可以用字典映射,简单粗暴:

```python
MODULES = {
    "filter": "pipeline.data_filter.runner",
    "rainfall": "pipeline.rainfall_analysis.runner",
    # ...
}
```

**LLM 客户端共享**: `self.llm_client` 在 Orchestrator 初始化时创建一次,通过 config 传递给需要 LLM 的模块。

**Pipeline 阶段划分(阶段 1-5)只是注释,不是代码结构**——别想太多,就是文档化的"逻辑分段"。

---

## 6. LLM 客户端设计

### 6.1 职责

- 提供统一的 chat 接口,屏蔽底层 API 细节
- 实现重试机制(3 次,指数退避)
- 实现"全局关闭" (config.llm_enabled = False)
- 加载 prompt 模板

### 6.2 接口

```python
# core/llm_client.py

class LLMClient:
    
    def __init__(self, config: Config):
        self.config = config
        self.enabled = config.llm_enabled
        # 初始化底层 API 客户端(deepseek / openai 等)
        self._client = self._init_provider()
    
    def chat(self, prompt: str, system: str = None) -> str:
        """
        统一的 LLM 调用入口。
        
        参数:
            prompt: 用户消息
            system: 系统消息(可选)
        
        返回:
            LLM 的文本响应
        
        异常:
            LLMDisabledError: config.llm_enabled = False 时抛出
            LLMFailedAfterRetry: 3 次重试都失败时抛出
        """
        if not self.enabled:
            raise LLMDisabledError("LLM 已关闭")
        
        for attempt in range(3):
            try:
                return self._do_chat(prompt, system)
            except Exception as e:
                if attempt < 2:
                    wait = 2 ** attempt  # 1, 2, 4 秒
                    self.config.logger.warning(
                        f"LLM 调用失败(第 {attempt+1} 次),{wait} 秒后重试: {e}"
                    )
                    time.sleep(wait)
                else:
                    raise LLMFailedAfterRetry(f"LLM 调用失败 3 次: {e}")
    
    @staticmethod
    def load_prompt(name: str) -> str:
        """加载 prompts/ 目录下的模板。"""
        prompt_path = Path("prompts") / f"{name}.txt"
        return prompt_path.read_text(encoding="utf-8")
```

### 6.3 使用示例

```python
# pipeline/pattern_analysis/runner.py

def run(config, logger):
    llm = LLMClient(config)
    
    for site_id, features in all_sites.items():
        prompt_template = LLMClient.load_prompt("pattern_analysis")
        prompt = prompt_template.format(features=features)
        
        try:
            result = llm.chat(prompt)
            # 解析并保存
        except LLMDisabledError:
            result = "LLM 已关闭,未分类"
        except LLMFailedAfterRetry:
            logger.warning(f"点位 {site_id} LLM 失败,标记为待人工")
            result = "LLM 失败,待人工判断"
        
        save_to_excel(site_id, result)
```

**关键设计**:

- 每个调用都被 try/except 包围,失败有兜底
- 兜底值是显式的字符串("未分类"、"待人工"),写到 Excel 里用户能看到
- 整个 Pipeline 不会因为 LLM 失败而崩溃

---

## 7. 日志策略

### 7.1 设计

- 使用 Python 标准 logging
- 每次运行一个时间戳日志文件: `outputs/logs/YYYY-MM-DD-HH-MM-SS.log`
- 同时输出到控制台
- 三级:INFO、WARNING、ERROR

### 7.2 日志格式

```
2026-05-22 14:30:15 | INFO  | orchestrator | 开始: filter
2026-05-22 14:30:20 | INFO  | pipeline.data_filter | 加载了 30 个点位
2026-05-22 14:30:35 | WARNING | core.llm_client | LLM 调用失败(第 1 次),1 秒后重试
2026-05-22 14:30:36 | INFO  | pipeline.pattern_analysis | 点位 P001 判断完成
```

格式: `时间 | 级别 | 模块名 | 消息`

### 7.3 实现

```python
# core/logger.py

def setup_logger(output_dir: Path):
    log_dir = output_dir / "logs"
    log_dir.mkdir(exist_ok=True, parents=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    log_file = log_dir / f"{timestamp}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-7s | %(name)-30s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding="utf-8")
        ]
    )
    
    return log_file
```

### 7.4 模块中使用

```python
import logging
logger = logging.getLogger(__name__)

logger.info("开始处理")
logger.warning("某个边界情况", exc_info=True)
```

---

## 8. 错误处理策略

### 8.1 分级

| 模块 | 级别 | 失败后行为 |
|------|------|-----------|
| data_filter | 核心 | Pipeline 终止 |
| rainfall_analysis | 核心 | Pipeline 终止 |
| dry_analysis | 核心 | Pipeline 终止 |
| event_stats | 核心 | Pipeline 终止 |
| rdii_analysis | 辅助 | 跳过,继续 |
| risk_analysis | 核心 | Pipeline 终止 |
| pattern_analysis | 辅助 | 跳过,继续 |
| report_assembler | 核心 | Pipeline 终止 |

**判断标准**:

- 核心 = 不做的话报告生成不完整或会乱
- 辅助 = 不做的话报告少一节,但仍可交付

`rdii_analysis` 标"辅助"是因为它本来就不进报告,失败不影响最终交付。`pattern_analysis` 标"辅助"是因为如果 LLM 整体不可用,排污规律一节可以空着或显示"未分析",报告主体仍能产出。

### 8.2 LLM 失败的特殊处理

LLM 失败有两层:

- **单次调用失败** → 自动重试 3 次(在 LLMClient 内部)
- **3 次重试都失败** → 抛 LLMFailedAfterRetry,调用方决定兜底

排污规律分析里,**每个点位独立调用 LLM**——某个点位的 LLM 失败,只影响那一个点位,其他点位正常分析。

---

## 9. 测试策略

### 9.1 测试分层

**单元测试** (`tests/unit/`):
- 测试纯函数: 特征计算、阈值判断、数据转换等
- 不读真实文件,不调 LLM
- 跑得快,改代码后秒级反馈

**集成测试** (`tests/integration/`):
- 测试模块的 `run()` 函数,用 `data_sample/` 里的小数据
- 验证模块的输入 → 输出端到端正确
- 跑得慢一些(秒级),改架构后跑

### 9.2 测试数据

`data_sample/` 目录放**脱敏的小样本数据**,提供 1-2 个点位 × 7 天的数据,足够覆盖所有模块的代码路径。

### 9.3 v1 测试范围

按 PRD 的工程化验收要求:

- **报告组装模块**: 必须有单元测试覆盖核心逻辑(字段映射、模板渲染)
- **其他模块**: 现有测试保留,不强制扩充
- **集成测试**: 至少有一个端到端冒烟测试(用 data_sample 跑通整个 Pipeline)

---

## 10. 关键技术决策(摘要)

完整的决策记录见 `docs/decisions/` 目录。这里列出核心 3 个:

| ADR | 决策 | 理由 |
|-----|------|------|
| ADR-001 | 用户配置用 Excel(`baseinfo.xlsx`),不用 YAML | 同事熟悉 Excel,YAML 对非技术用户不友好;技术参数仍用 `config.yaml` |
| ADR-002 | LLM 仅用于排污规律分析和报告小结生成 | 其他环节 LLM 拿到的输入跟规则一样,用 LLM 不稳定且不必要;LLM 仅在"规则拿不到的输入"或"规则不擅长的输出"用 |
| ADR-003 | 代码主线统一到 `pipeline/`,合并 `sewage_monitoring/` 的集成能力 | `pipeline/` 模块边界更清晰,`sewage_monitoring/` 有 Orchestrator 和 LLM 客户端可复用;统一一套代码避免分叉 |

---

## 11. 开放问题(待开发阶段确认)

以下问题在架构层面不展开,留到开发时决定:

- **Q1**: Word 模板的字段映射机制具体怎么设计?(占位符语法、嵌套结构处理)
- **Q2**: `event_stats` 是真的成独立模块,还是作为 `rdii_analysis` 和 `risk_analysis` 的公共工具函数?
- **Q3**: baseinfo.xlsx 的"降雨场次选择"格式(单元格 1 列多行 vs 逗号分隔)
- **Q4**: 风险分析的具体阈值规则(在代码中实现,可能需要 ADR 记录)

这些都不影响架构层面的设计,开发时遇到再决定。

---

## 附录 A: 文件命名约定

- **Python 文件**: snake_case (e.g. `data_filter.py`)
- **Excel/Word 文件(用户可见)**: 中文 (e.g. `综合分析结果.xlsx`)
- **配置文件**: 小写 (e.g. `config.yaml`, `.env`)
- **文档**: 大写英文 (e.g. `PRD.md`, `ARCHITECTURE.md`)
- **ADR**: `ADR-NNN-中文标题.md` (e.g. `ADR-001-配置选-Excel.md`)

---

## 附录 B: 依赖库参考

预计需要的核心依赖:

```
# 数据处理
pandas
numpy
openpyxl                  # 读写 Excel
python-docx               # 读写 Word

# 图表
matplotlib

# 配置
pyyaml
python-dotenv             # 读 .env

# LLM
openai                    # 兼容 deepseek API

# 日志(标准库,无需安装)
# logging
```

---

**END of ARCHITECTURE v0.1**
