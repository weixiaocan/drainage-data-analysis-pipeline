"""测试 data_filter 模块

测试流程：
1. 检查是否已有筛选结果
2. 如果有，询问是否覆盖
3. 根据用户选择决定是否执行模块

用法:
    python tests/test_data_filter_interactive.py          # 交互模式
    python tests/test_data_filter_interactive.py --force  # 强制覆盖
    python tests/test_data_filter_interactive.py --skip   # 跳过已有结果
"""

import argparse
import logging
import sys
from pathlib import Path

# 添加项目根目录到 path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import Config
from src.core.logger import setup_logger
from src.pipeline.data_filter.runner import run as run_data_filter


def check_existing_result(config: Config) -> bool:
    """检查筛选结果文件是否存在"""
    result_path = config.filter_result_path
    return result_path.exists()


def ask_overwrite() -> bool:
    """询问用户是否覆盖已有结果"""
    while True:
        try:
            response = input("\n发现已有筛选结果，是否覆盖？(y/n): ").strip().lower()
            if response in ('y', 'yes', '是'):
                return True
            elif response in ('n', 'no', '否'):
                return False
            else:
                print("请输入 y/n")
        except EOFError:
            print("\n无法读取输入，默认跳过")
            return False


def main():
    parser = argparse.ArgumentParser(description="测试 data_filter 模块")
    parser.add_argument("--force", action="store_true", help="强制覆盖已有结果")
    parser.add_argument("--skip", action="store_true", help="如有已有结果则跳过")
    args = parser.parse_args()

    # 加载配置
    config = Config.load()
    setup_logger(config.output_dir)
    logger = logging.getLogger("test_data_filter")

    print("=" * 60)
    print("测试 data_filter 模块")
    print("=" * 60)

    # Step 1: 检查是否已有筛选结果
    result_path = config.filter_result_path
    print(f"\n筛选结果文件路径: {result_path}")

    if check_existing_result(config):
        print(f"[OK] 发现已有筛选结果文件")
        print(f"  文件大小: {result_path.stat().st_size} bytes")

        # Step 2: 决定是否覆盖
        if args.force:
            should_overwrite = True
            print("\n--force 参数: 将覆盖已有结果")
        elif args.skip:
            should_overwrite = False
            print("\n--skip 参数: 跳过已有结果")
        else:
            should_overwrite = ask_overwrite()

        if not should_overwrite:
            print("\n跳过 data_filter 模块")
            print("测试结束")
            return

        print("\n将重新运行 data_filter 模块...")
    else:
        print("[NEW] 筛选结果文件不存在，将运行 data_filter 模块...")

    # Step 3: 执行模块
    print("\n" + "-" * 60)
    print("开始执行 data_filter 模块")
    print("-" * 60)

    try:
        result = run_data_filter(config, logger)

        print("\n" + "-" * 60)
        print("执行完成")
        print("-" * 60)

        # 打印结果摘要
        selected = result.get("selected", {})
        total_days = sum(len(days) for days in selected.values())

        print(f"\n结果摘要:")
        print(f"  处理点位数: {len(selected)}")
        print(f"  有效旱天总数: {total_days}")

        if selected:
            print(f"\n各点位有效天数:")
            for point_id, days in sorted(selected.items()):
                print(f"  {point_id}: {len(days)} 天")

        # 确认输出文件已生成
        if result_path.exists():
            print(f"\n[OK] 输出文件已生成: {result_path}")
            print(f"  文件大小: {result_path.stat().st_size} bytes")
        else:
            print(f"\n[WARN] 警告: 输出文件未生成: {result_path}")

    except Exception as e:
        logger.exception("执行失败")
        print(f"\n[ERR] 执行失败: {e}")
        raise


if __name__ == "__main__":
    main()
