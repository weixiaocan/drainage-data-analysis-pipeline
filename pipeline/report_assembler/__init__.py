"""报告组装模块 - 将分析结果组装成 Word 报告"""

from .runner import run
from .assembler import run_report_assembler

__all__ = ["run", "run_report_assembler"]
