"""
监测数据分析与报告生成系统 - 主入口

运行方式:
    python run.py

流程:
    1. 加载配置
    2. 初始化日志
    3. 创建 Orchestrator
    4. 执行 Pipeline
    5. 输出结果
"""

import sys
from pathlib import Path

from src.core.config import Config
from src.core.logger import setup_logger
from src.orchestrator.pipeline_runner import Orchestrator


def main() -> int:
    """主入口"""
    # 1. 加载配置
    config = Config.load()

    # 确保输出目录存在
    config.output_dir.mkdir(parents=True, exist_ok=True)

    # 2. 初始化日志
    log_file = setup_logger(config.output_dir)
    print(f"日志文件: {log_file}")

    # 3. 创建 Orchestrator
    import logging

    logger = logging.getLogger("main")
    orchestrator = Orchestrator(config, logger)
    orchestrator.non_interactive = True  # 非交互模式

    # 4. 执行 Pipeline（跳过报告生成模块）
    success = orchestrator.run(stop_before="report_assembler")

    # 5. 输出结果
    if success:
        print("\n" + "=" * 60)
        print("Pipeline 执行成功！")
        print(f"  输出目录: {config.output_dir}")
        print(f"  综合分析结果: {config.combined_xlsx_path}")
        print(f"  分析报告: {config.report_output_path}")
        print("=" * 60)
        return 0
    else:
        print("\n" + "=" * 60)
        print("Pipeline 执行失败，请检查日志。")
        print(f"  日志文件: {log_file}")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
