"""
顺序执行 SEC 数据采集的三个阶段脚本：
1. 生成公司目录（SEC_Get_Company_Directory.py）
2. 生成 10-K 索引（SEC_Get_Company_10k_Index.py）
3. 下载 10-K 文档（SEC_Download_10k.py）
"""

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run_script(relative_path: str, description: str) -> None:
    """调用单个 Python 脚本并检查返回码。"""
    script_path = ROOT / relative_path
    print(f"\n>>> 开始执行：{description} ({script_path})")
    result = subprocess.run([sys.executable, str(script_path)], cwd=ROOT)
    if result.returncode != 0:
        raise SystemExit(f"{description} 执行失败，退出码：{result.returncode}")
    print(f"<<< 完成：{description}")


def main() -> None:
    """依次运行三个数据处理脚本。"""
    run_script("src/SEC_Get_Company_Directory.py", "生成公司目录")
    run_script("src/SEC_Get_Company_10k_Index.py", "生成 10-K 索引")
    run_script("src/SEC_Download_10k.py", "下载 10-K 文档")


if __name__ == "__main__":
    main()
