# 项目现状盘点

> 生成时间: 2026-05-22
> 盘点工具: Claude Code

---

## 1. 项目结构

### 1.1 目录概览

```
.
├── _archive_old_agents/        # 旧版 Agent 实现（已归档，保留参考）
│   ├── agents/                 # 旧版 Agent 代码
│   ├── utils/                  # 旧版工具函数
│   ├── cli.py                  # 旧版 CLI
│   ├── orchestrator.py         # 旧版编排器
│   └── models.py               # 旧版数据模型
├── colleague_tool/             # 同事的原始工具代码
│   ├── code/                   # 核心分析脚本（.py 文件）
│   ├── data/                   # 原始数据目录
│   ├── figure/                 # 生成的图表
│   └── Introduction.py         # 工具入口
├── data/                       # 当前项目数据目录
│   ├── flow/                   # 流量监测 CSV 数据
│   └── rainfall/               # 降雨数据 CSV
├── docs/                       # 项目文档
├── outputs/                    # 输出目录
│   ├── charts/                 # 生成的图表 PNG
│   ├── logs/                   # 运行日志
│   └── 特征曲线图/              # 特征曲线图
├── pipeline/                   # 独立管道模块（可单独运行）
│   ├── data_filter/            # 数据筛选模块
│   ├── dry_analysis/           # 旱天分析模块
│   ├── pattern_analysis/       # 排污规律分析模块
│   ├── rainfall_analysis/      # 降雨分析模块
│   ├── rdii_analysis/          # RDII 分析模块
│   └── report_assembler/       # 报告组装模块
├── sewage_monitoring/          # 主代码包
│   ├── agents/                 # Agent 实现（当前版本）
│   ├── utils/                  # 工具函数
│   ├── cli.py                  # CLI 入口
│   ├── orchestrator.py         # 主流程编排器
│   ├── models.py               # 数据模型定义
│   └── settings.py             # 配置加载
├── tests/                      # 单元测试
├── run.py                      # 主入口脚本
├── config.yaml                 # 配置文件
└── requirements.txt            # Python 依赖
```

### 1.2 技术栈

- **语言**: Python 3.x
- **数据处理**: pandas, numpy, scipy
- **可视化**: matplotlib
- **Excel 处理**: openpyxl, xlsxwriter
- **Word 报告**: python-docx
- **LLM 集成**: openai SDK（用于 DeepSeek API）
- **配置管理**: PyYAML, python-dotenv

### 1.3 组织方式

项目采用 **"固定主流程 + 多 Agent 分工"** 的架构：
- 主入口 `run.py` → `cli.py` → `orchestrator.py`
- 编排器按顺序调用 6 个 Agent 完成数据处理流水线
- 存在两套并行代码：`sewage_monitoring/`（主）和 `pipeline/`（独立模块）

---

## 2. 入口文件

| 路径 | 行数 | 功能说明 |
|------|------|----------|
| `run.py` | 7 | 主入口，调用 `sewage_monitoring.cli.main()` |
| `sewage_monitoring/cli.py` | 39 | 解析命令行参数，加载配置，启动编排器 |
| `colleague_tool/Introduction.py` | 未统计 | 同事原始工具的入口（未被当前系统调用） |

**运行命令**:
```bash
python run.py --config config.yaml
python run.py --continue-after-confirm  # 人工确认后继续
python run.py --no-prompt-after-filter  # 筛选后不等待确认
```

---

## 3. 模块清单

### 3.1 主代码包 `sewage_monitoring/`

| 路径 | 行数 | 功能说明 |
|------|------|----------|
| `__init__.py` | 2 | 包初始化 |
| `cli.py` | 39 | 命令行入口，参数解析 |
| `orchestrator.py` | 184 | 主流程编排器，串联 6 个 Agent |
| `models.py` | 107 | 数据模型定义（SiteData, SiteMeta, PipelineContext 等） |
| `settings.py` | 137 | 配置加载（从 YAML 文件读取设置） |

#### 3.1.1 Agent 模块 `sewage_monitoring/agents/`

| 路径 | 行数 | 功能说明 |
|------|------|----------|
| `filter_agent.py` | 765 | 数据筛选 Agent：筛选有效旱天数据 |
| `pattern_agent.py` | 424 | 排污规律分析 Agent：分类判断流量曲线特征 |
| `rainfall_agent.py` | 182 | 降雨分析 Agent：统计降雨日、降雨场次 |
| `report_agent.py` | 1100 | 报告组装 Agent：填充 Word 模板生成报告 |
| `risk_agent.py` | 192 | 风险分析 Agent：淤积/运行/溢流风险评估 |
| `statistics_agent.py` | 94 | 数据统计 Agent：基础指标统计 |

#### 3.1.2 工具模块 `sewage_monitoring/utils/`

| 路径 | 行数 | 功能说明 |
|------|------|----------|
| `data_loader.py` | 168 | 数据加载：读取 CSV、点位信息、降雨数据 |
| `logger.py` | 23 | 日志配置 |
| `pattern_feature_engine.py` | 933 | 特征计算引擎：Kz、峰识别、曲线分类等 |
| `pattern_llm_client.py` | 396 | LLM 客户端：调用 DeepSeek 进行规律分析 |

### 3.2 管道模块 `pipeline/`

| 路径 | 行数 | 功能说明 |
|------|------|----------|
| `__init__.py` | 2 | 包初始化 |
| `data_filter/__init__.py` | 2 | 模块初始化 |
| `data_filter/__main__.py` | 62 | CLI 入口：`python -m pipeline.data_filter` |
| `data_filter/filter.py` | 478 | 数据筛选核心逻辑（独立可运行） |
| `dry_analysis/__init__.py` | 2 | 模块初始化 |
| `dry_analysis/__main__.py` | 未详细统计 | CLI 入口 |
| `dry_analysis/analyzer.py` | 未详细统计 | 旱天分析核心逻辑 |
| `pattern_analysis/__init__.py` | 2 | 模块初始化 |
| `pattern_analysis/__main__.py` | 未详细统计 | CLI 入口 |
| `rainfall_analysis/__init__.py` | 2 | 模块初始化 |
| `rainfall_analysis/__main__.py` | 未详细统计 | CLI 入口 |
| `rdii_analysis/__init__.py` | 2 | 模块初始化 |
| `rdii_analysis/__main__.py` | 未详细统计 | CLI 入口 |
| `rdii_analysis/analyzer.py` | 未详细统计 | RDII 分析核心逻辑 |
| `report_assembler/__init__.py` | 2 | 模块初始化 |
| `report_assembler/__main__.py` | 62 | CLI 入口 |
| `report_assembler/assembler.py` | 264 | 报告组装核心逻辑 |

### 3.3 归档代码 `_archive_old_agents/`

| 路径 | 行数 | 功能说明 |
|------|------|----------|
| `agents/filter_agent.py` | 未统计 | 旧版筛选 Agent（已被 sewage_monitoring 版本替代） |
| `agents/pattern_agent.py` | 未统计 | 旧版规律分析 Agent |
| `agents/rainfall_agent.py` | 未统计 | 旧版降雨分析 Agent |
| `agents/report_agent.py` | 未统计 | 旧版报告组装 Agent |
| `agents/risk_agent.py` | 未统计 | 旧版风险分析 Agent |
| `agents/statistics_agent.py` | 未统计 | 旧版统计 Agent |
| `cli.py` | 未统计 | 旧版 CLI |
| `orchestrator.py` | 未统计 | 旧版编排器 |
| `models.py` | 未统计 | 旧版数据模型 |
| `settings.py` | 未统计 | 旧版配置 |
| `utils/data_loader.py` | 未统计 | 旧版数据加载 |
| `utils/logger.py` | 未统计 | 旧版日志 |
| `utils/pattern_feature_engine.py` | 未统计 | 旧版特征引擎 |
| `utils/pattern_llm_client.py` | 未统计 | 旧版 LLM 客户端 |

### 3.4 同事原始工具 `colleague_tool/code/`

| 路径 | 行数 | 功能说明 |
|------|------|----------|
| `analyze_dry_flow.py` | 258 | 旱天流量分析 |
| `analyze_event_RDII.py` | 197 | 降雨事件 RDII 分析 |
| `analyze_event_flow.py` | 74 | 降雨事件流量分析 |
| `analyze_rain.py` | 144 | 降雨数据分析 |
| `base_info.py` | 89 | 基础信息处理 |
| `prepro_flowdata.py` | 45 | 流量数据预处理 |
| `prepro_flowdata_不处理负值.py` | 45 | 流量数据预处理（不处理负值版本） |
| `read_and_sta_flowdata.py` | 84 | 流量数据读取和统计 |
| `read_prepro_rain_data.py` | 52 | 降雨数据预处理读取 |

---

## 4. 核心数据流

### 4.1 主流程数据流

```
运行 python run.py
    │
    ▼
cli.py: 解析参数，加载 config.yaml
    │
    ▼
orchestrator.py: _build_context()
    │   ├── 读取 data/点位信息.xlsx → site_meta_map
    │   ├── 读取 data/降雨数据.csv → rainfall_daily
    │   └── 读取 data/*.csv → sites (每个点位的 DataFrame)
    │
    ▼
Agent 1: DataFilterAgent.run(ctx)
    │   ├── 输入: ctx.sites, ctx.rainfall_daily
    │   ├── 处理: 筛选有效旱天（剔除雨天、缺失率高、异常流量日）
    │   └── 输出: outputs/筛选结果.xlsx (Excel 文件)
    │
    ├── [用户人工确认/修改筛选结果]
    │
    ▼
Agent 2: RainfallAnalysisAgent.run(ctx)
    │   ├── 输入: ctx.rainfall_daily
    │   ├── 处理: 统计降雨日、划分降雨场次
    │   └── 输出: ctx.rainfall_analysis (RainfallAnalysisResult 对象)
    │
    ▼
Agent 3: StatisticsAgent.run(ctx)
    │   ├── 输入: ctx.sites (筛选后数据)
    │   ├── 处理: 计算日均流量、液位、收集率等基础指标
    │   └── 输出: ctx.intermediate["collect_df"], ctx.intermediate["metric_df"]
    │
    ▼
Agent 4: RiskAnalysisAgent.run(ctx)
    │   ├── 输入: metric_df, ctx.site_meta_map
    │   ├── 处理: 计算淤积风险、运行风险、溢流风险
    │   └── 输出: ctx.intermediate["risk_df"], ctx.intermediate["rainy_risk_df"]
    │
    ▼
Agent 5: PatternAnalysisAgent.run(ctx)
    │   ├── 输入: ctx.sites (筛选后数据)
    │   ├── 处理: 计算流量曲线特征，调用 LLM 分类判断
    │   └── 输出: ctx.intermediate["pattern_df"], outputs/charts/*.png
    │
    ▼
Agent 6: ReportAssemblyAgent.run(ctx)
    │   ├── 输入: 所有中间结果 + 监测数据分析报告模板-更新.docx
    │   ├── 处理: 填充 Word 模板表格和段落
    │   └── 输出: outputs/报告初稿.docx
    │
    ▼
orchestrator.py: _write_combined_results(ctx)
    │   └── 输出: outputs/综合分析结果.xlsx (多 Sheet Excel)
    │
    ▼
完成
```

### 4.2 关键数据文件

| 文件 | 来源 | 用途 |
|------|------|------|
| `data/点位信息.xlsx` | 外部输入 | 点位元数据（管径、井深、类型等） |
| `data/降雨数据.csv` | 外部输入 | 降雨时间序列数据 |
| `data/*.csv` | 外部输入 | 各点位监测数据（流量、液位、流速） |
| `outputs/筛选结果.xlsx` | Agent 1 输出 | 有效旱天标记，供人工确认 |
| `outputs/综合分析结果.xlsx` | 编排器输出 | 汇总所有分析结果 |
| `outputs/报告初稿.docx` | Agent 6 输出 | 最终 Word 报告 |

---

## 5. 外部依赖

### 5.1 Python 包依赖 (requirements.txt)

| 包名 | 版本要求 | 项目中的用途 |
|------|----------|--------------|
| pandas | >=2.0.0 | 数据处理核心（所有模块） |
| numpy | >=1.24.0 | 数值计算（统计、特征计算） |
| scipy | >=1.10.0 | 峰值检测（pattern_feature_engine.py） |
| matplotlib | >=3.7.0 | 绘制特征曲线图 |
| openpyxl | >=3.1.0 | Excel 读写（筛选结果、分析结果） |
| xlsxwriter | >=3.1.0 | Excel 写入 |
| python-docx | >=1.1.0 | Word 报告生成 |
| python-dotenv | >=1.0.0 | 环境变量加载 |
| openai | >=1.0.0 | LLM API 调用（DeepSeek） |
| PyYAML | >=6.0.0 | 配置文件解析 |

### 5.2 外部 API/服务

| 服务 | 用途 | 配置方式 |
|------|------|----------|
| DeepSeek API | 排污规律智能分析 | 环境变量: DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL |

### 5.3 配置文件

| 文件 | 用途 |
|------|------|
| `config.yaml` | 主配置文件（输入输出路径、分析参数、LLM 配置） |
| `.env` | 环境变量（API Key 等，通过 python-dotenv 加载） |

### 5.4 关键配置参数 (config.yaml)

```yaml
analysis:
  missing_rate_threshold: 0.1        # 缺失率阈值
  expected_rows_per_day: 1440        # 每日理论数据条数
  rain_day_filter_threshold: 2.0     # 雨天剔除阈值(mm)
  zero_like_threshold: 0.02          # 近零值阈值
  high_zero_ratio_threshold: 0.5     # 高零值比例阈值
  iqr_factor: 1.5                    # IQR 异常值因子
  mean_lower_ratio: 0.5              # 均值下限比例
  mean_upper_ratio: 2.0              # 均值上限比例
  smooth_window: 30                  # 曲线平滑窗口

llm:
  enabled: true                      # 是否启用 LLM
  api_key_env: "DEEPSEEK_API_KEY"    # API Key 环境变量名
  base_url_env: "DEEPSEEK_BASE_URL"  # API Base URL 环境变量名
  model_name_env: "DEEPSEEK_MODEL"   # 模型名环境变量名
```

---

## 6. 测试现状

### 6.1 测试文件清单

| 路径 | 行数 | 覆盖范围 |
|------|------|----------|
| `tests/test_filter_agent.py` | 263 | 数据筛选 Agent 的单元测试 |
| `tests/test_data_filter.py` | 未统计 | 数据筛选模块测试 |
| `tests/test_dry_analysis.py` | 未统计 | 旱天分析模块测试 |
| `tests/test_pattern_analysis.py` | 未统计 | 排污规律分析模块测试 |
| `tests/test_rainfall_analysis.py` | 未统计 | 降雨分析模块测试 |
| `tests/test_rdii_analysis.py` | 未统计 | RDII 分析模块测试 |
| `tests/test_report_assembler.py` | 未统计 | 报告组装模块测试 |

### 6.2 测试覆盖情况

- `test_filter_agent.py`: 测试了筛选逻辑的核心方法（高零值比例检测、均值比例规则、雨天阈值等）
- 其他测试文件：存在但未详细分析内容

### 6.3 运行测试命令

```bash
python -m pytest tests/ -v
```

---

## 7. 文档现状

### 7.1 Markdown 文档清单

| 路径 | 内容说明 |
|------|----------|
| `docs/00-项目目录结构.md` | 项目目录结构说明 |
| `docs/01-项目总览.md` | 项目目标和主流程概述 |
| `docs/02-输入输出与字段规范.md` | 输入输出文件格式规范 |
| `docs/03-报告模板映射说明.md` | Word 模板字段映射说明 |
| `docs/04-运行与验收.md` | 运行命令和验收标准 |
| `docs/05-DeepSeek接入说明.md` | DeepSeek API 接入说明 |
| `docs/06-项目架构与流程说明.md` | 架构和流程详细说明 |
| `docs/COLLEAGUE_TOOL_INTERFACE.md` | 同事工具接口说明 |
| `docs/DATA_FILTER_MIGRATION.md` | 数据筛选模块迁移说明 |
| `docs/DRY_ANALYSIS_MIGRATION.md` | 旱天分析模块迁移说明 |
| `docs/PROJECT_OVERVIEW.md` | 项目总览（英文版） |
| `docs/RAINFALL_ANALYSIS_MIGRATION.md` | 降雨分析模块迁移说明 |
| `docs/RDII_ANALYSIS_MIGRATION.md` | RDII 分析模块迁移说明 |
| `AGENTS.md` | 项目协作约定和模块接口定义 |

### 7.2 代码注释和 Docstring

- **Docstring 覆盖**: 核心类和方法有 docstring，部分模块注释完整（如 `pattern_feature_engine.py`、`pattern_llm_client.py`）
- **注释风格**: 中英文混合，部分模块有详细的参数说明
- **示例代码**: `pattern_feature_engine.py` 和 `pattern_llm_client.py` 包含测试/示例代码块

---

## 8. 未完成标记

**搜索结果**: 未在代码中发现 `TODO`、`FIXME`、`XXX`、`HACK`、`not_implemented` 等标记。

**注意**: 代码中存在一些中文注释描述的"回退"、"兜底"逻辑，这些是正常的功能实现，不是未完成标记。

---

## 9. 用户补充（待手动填写）

### 9.1 隐性知识

（用户填写: 那些代码里看不出来，但你心里知道的事——比如"这块逻辑其实是临时凑的"、"那个函数应该改但我没敢动"、"这里有个坑当时绕过去了"）

_待填写_

### 9.2 已知问题

（用户填写: 你心里清楚但代码里没标 TODO 的问题）

_待填写_

### 9.3 业务逻辑确认

（用户填写: 某些代码逻辑你看的时候不确定"当初为什么这么写"，标记出来，可能是 bug 也可能是有原因的）

_待填写_

---

## 10. 附录：关键代码行数统计

| 模块 | 总行数 |
|------|--------|
| sewage_monitoring/ (含 agents, utils) | ~8,581 行 |
| pipeline/ | 未精确统计 |
| tests/ | ~263+ 行 |
| colleague_tool/code/ | ~988 行 |
| _archive_old_agents/ | 未精确统计（与 sewage_monitoring 结构类似） |

---

**报告完成时间**: 2026-05-22
