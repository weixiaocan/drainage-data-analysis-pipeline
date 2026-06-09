"""测试 dry_analysis 模块

依赖:
    - 数据筛选结果 (筛选结果.xlsx)
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import logging
import pandas as pd
from src.core.config import Config
from src.core.logger import setup_logger
from src.pipeline.dry_analysis.runner import run as run_dry_analysis


def main():
    config = Config.load()
    setup_logger(config.output_dir)
    logger = logging.getLogger("test_dry_analysis")

    print("=" * 60)
    print("测试 dry_analysis 模块")
    print("=" * 60)

    # 检查依赖
    filter_result = config.filter_result_path
    if not filter_result.exists():
        print(f"\n[ERR] 筛选结果文件不存在: {filter_result}")
        print("请先运行 data_filter 模块")
        return

    print(f"\n筛选结果文件: {filter_result}")
    print(f"综合分析结果: {config.combined_xlsx_path}")

    # 运行模块
    print("\n" + "-" * 60)
    print("开始执行 dry_analysis 模块")
    print("-" * 60)

    try:
        result = run_dry_analysis(config, logger)

        print("\n" + "-" * 60)
        print("执行完成")
        print("-" * 60)

        # 打印结果摘要
        dry_curve_data = result.get("dry_curve_data", {})
        print(f"\n结果摘要:")
        print(f"  处理点位数: {len(dry_curve_data)}")

        if dry_curve_data:
            print(f"\n各点位特征曲线数据行数:")
            for point_id in sorted(dry_curve_data.keys())[:5]:
                df = dry_curve_data[point_id]
                print(f"  {point_id}: {len(df)} 行")
            if len(dry_curve_data) > 5:
                print(f"  ... 共 {len(dry_curve_data)} 个点位")

        # 检查输出文件
        combined_xlsx = config.combined_xlsx_path
        if combined_xlsx.exists():
            print(f"\n[OK] 输出文件已生成: {combined_xlsx}")
            print(f"  文件大小: {combined_xlsx.stat().st_size} bytes")

            # 读取并显示 Sheet 信息
            xlsx = pd.ExcelFile(combined_xlsx)
            print(f"  包含 Sheet: {xlsx.sheet_names}")

            # 检查旱天分析 Sheet
            if "旱天分析" in xlsx.sheet_names:
                df = pd.read_excel(combined_xlsx, sheet_name="旱天分析")
                print(f"\n  旱天分析 Sheet:")
                print(f"    行数: {len(df)}")
                print(f"    列数: {len(df.columns)}")
                print(f"    列名: {list(df.columns[:10])}{'...' if len(df.columns) > 10 else ''}")

                # 显示前几行数据
                print(f"\n  数据预览 (前3行):")
                print(df.head(3).to_string())
        else:
            print(f"\n[WARN] 输出文件未生成: {combined_xlsx}")

    except Exception as e:
        logger.exception("执行失败")
        print(f"\n[ERR] 执行失败: {e}")
        raise


if __name__ == "__main__":
    main()
