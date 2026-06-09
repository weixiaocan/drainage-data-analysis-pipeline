"""测试风险分析模块"""

import logging
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import Config
from src.pipeline.risk_analysis.runner import run as run_risk_analysis

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def main():
    # 加载配置
    config = Config.load()

    print("=" * 60)
    print("风险分析模块测试")
    print("=" * 60)
    print(f"流量数据目录: {config.flow_data_dir}")
    print(f"综合分析结果: {config.combined_xlsx_path}")
    print(f"点位信息: {config.site_info_path}")
    print(f"选中降雨场次: {config.selected_rainfall_events}")
    print("=" * 60)

    # 运行风险分析
    result = run_risk_analysis(config, logger)

    print("\n" + "=" * 60)
    print("分析结果:")
    print("=" * 60)
    print(f"旱天风险分析: {len(result['dry_risk'])} 个点位")
    if not result['rainy_risk'].empty:
        print(f"雨天溢流风险: {len(result['rainy_risk'])} 条记录")
    else:
        print("雨天溢流风险: 无数据")

    print("\n旱天风险数据预览:")
    print(result['dry_risk'].to_string())

    if not result['rainy_risk'].empty:
        print("\n雨天溢流风险数据预览:")
        print(result['rainy_risk'].to_string())

if __name__ == "__main__":
    main()
