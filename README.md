# 监测数据分析与报告生成系统

模板驱动的排水监测分析流水线，包含 5 个步骤：
1. 数据筛选
2. 数据统计
3. 旱天运行风险评估
4. 排污规律分析（支持 LLM 文本生成）
5. Word 报告装配（按模板样式填充）

## 当前项目结构

```text
.
├─ data/                          # 分点位 CSV 监测数据
├─ docs/                          # 项目文档
├─ outputs/                       # 运行输出（可清理）
├─ sewage_monitoring/             # 主工程
│  ├─ agents/
│  ├─ utils/                      # 含 pattern_feature_engine / pattern_llm_client
│  ├─ cli.py
│  ├─ orchestrator.py
│  └─ settings.py
├─ config.yaml                    # 运行配置
├─ config.example.yaml            # 配置模板
├─ run.py                         # 入口
├─ requirements.txt
├─ 点位信息.xlsx
├─ 降雨数据.csv
└─ 监测数据分析报告模板.docx
```

## 环境（Anaconda）

```bash
conda create -n sewage-agent python=3.11 -y
conda activate sewage-agent
pip install -r requirements.txt
```

## DeepSeek 接入

在系统环境变量或 `.env` 中设置：

```bash
DEEPSEEK_API_KEY=你的key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

说明：
- `DEEPSEEK_MODEL` 也可用 `deepseek-reasoner`。
- 代码使用 OpenAI 兼容接口调用 DeepSeek。

## 运行

```bash
python run.py --config config.yaml
```

## 清理输出与缓存

```powershell
powershell -ExecutionPolicy Bypass -File scripts/cleanup.ps1
```

## 文档

- [项目目录结构](docs/00-项目目录结构.md)
- [项目总览](docs/01-项目总览.md)
- [输入输出与字段规范](docs/02-输入输出与字段规范.md)
- [报告模板映射说明](docs/03-报告模板映射说明.md)
- [运行与验收](docs/04-运行与验收.md)
- [DeepSeek 接入说明](docs/05-DeepSeek接入说明.md)
