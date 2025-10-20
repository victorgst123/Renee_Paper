import argparse  # 解析命令行参数
import csv  # 读取 CSV 文件
import sys  # 访问系统级别的退出等功能
import time  # 控制下载节奏
from pathlib import Path  # 处理文件路径

import requests  # 发送 HTTP 请求
from requests import Session  # 创建持久会话

from SEC_API_HEADERS import HEADERS  # 复用 SEC 要求的请求头


def safe_filename(name: str) -> str:  # 将文件名转换为安全格式
    chars = []  # 临时存放合法字符
    for char in name:  # 遍历原始文件名中的每个字符
        if char.isalnum() or char in ("-", "_", "."):  # 保留字母数字和常见符号
            chars.append(char)  # 添加合法字符
        else:  # 否则
            chars.append("_")  # 用下划线替换非法字符
    return "".join(chars)  # 拼接为最终文件名


def download_file(session: Session, url: str, target_path: Path, sleep_sec: float) -> None:  # 下载单个文件的函数
    try:  # 捕获下载时可能出现的异常
        response = session.get(url, headers=HEADERS, timeout=60)  # 发起 HTTP GET 请求
        response.raise_for_status()  # 确认返回状态正常
    except requests.exceptions.RequestException as err:  # 处理网络相关错误
        print(f"下载失败：{url} -> {err}")  # 打印错误消息
        return  # 直接返回，不继续保存

    target_path.parent.mkdir(parents=True, exist_ok=True)  # 确保输出目录存在
    target_path.write_bytes(response.content)  # 写入二进制内容到目标文件
    print(f"已保存：{target_path}")  # 提示已完成保存
    time.sleep(sleep_sec)  # 按需暂停，避免触发限流


def read_tenk_urls(csv_path: Path) -> list[dict]:  # 从 CSV 中读取 10-K 信息
    rows = []  # 存放结果的列表
    with csv_path.open("r", encoding="utf-8-sig", newline="") as csvfile:  # 打开 CSV 文件
        reader = csv.DictReader(csvfile)  # 创建字典读取器
        for row in reader:  # 遍历每一行
            url = (row.get("tenk_url") or "").strip()  # 提取并清理 URL
            if not url:  # 如果 URL 为空
                continue  # 跳过该行
            rows.append(row)  # 添加有效行到结果
    return rows  # 返回全部记录


def build_filename(row: dict) -> str:  # 根据记录生成文件名
    ticker = safe_filename((row.get("ticker") or "UNKNOWN").upper())  # 获取股票代码并转为安全格式
    filing_date = safe_filename(row.get("filing_date") or "no_date")  # 处理申报日期
    primary_doc = safe_filename(row.get("primary_doc") or Path(row["tenk_url"]).name)  # 处理主文档名
    return f"{ticker}_{filing_date}_{primary_doc}"  # 组合成文件名


def parse_args() -> argparse.Namespace:  # 解析命令行参数
    parser = argparse.ArgumentParser(description="批量下载 10-K 文档到 data 目录")  # 创建参数解析器
    parser.add_argument(  # 添加输入 CSV 参数
        "--csv",
        default="data/tenk_index_test10.csv",
        help="包含 tenk_url 列的 CSV 文件路径（默认：data/tenk_index_test10.csv）",
    )
    parser.add_argument(  # 添加输出目录参数
        "--out",
        default="data/tenk_filings",
        help="保存 10-K 文档的目录（默认：data/tenk_filings）",
    )
    parser.add_argument(  # 添加休眠时间参数
        "--sleep",
        type=float,
        default=0.6,
        help="每次下载后的暂停秒数，避免请求过于频繁（默认 0.6 秒）",
    )
    return parser.parse_args()  # 返回解析得到的参数


def main() -> None:  # 程序入口函数
    args = parse_args()  # 读取命令行参数
    csv_path = Path(args.csv)  # 将输入路径转换为 Path 对象
    out_dir = Path(args.out)  # 将输出目录转换为 Path 对象

    if not csv_path.exists():  # 检查 CSV 文件是否存在
        print(f"未找到 CSV 文件：{csv_path}")  # 提示缺少文件
        sys.exit(1)  # 使用非零状态退出

    rows = read_tenk_urls(csv_path)  # 读取所有 10-K 记录
    if not rows:  # 如果没有数据
        print("CSV 中未找到 tenk_url 字段或没有有效记录")  # 给出提示
        sys.exit(0)  # 正常退出

    session = requests.Session()  # 创建 HTTP 会话
    for row in rows:  # 遍历每一条 10-K 记录
        url = row["tenk_url"]  # 获取下载地址
        filename = build_filename(row)  # 构建文件名
        target_path = out_dir / filename  # 生成完整的输出路径
        if target_path.exists():  # 如果文件已经存在
            print(f"已存在，跳过：{target_path}")  # 提示并跳过
            continue  # 继续处理下一个
        download_file(session, url, target_path, args.sleep)  # 调用下载函数


if __name__ == "__main__":  # 确保脚本被直接运行时执行
    main()  # 调用主函数
