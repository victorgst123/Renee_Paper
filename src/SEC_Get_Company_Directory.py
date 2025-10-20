import json
from pathlib import Path

import pandas as pd
import requests

from SEC_API_HEADERS import HEADERS

# 官方公司列表 JSON
URL = "https://www.sec.gov/files/company_tickers.json"
OUTPUT_PATH = Path("data/tickers.csv")

print("开始从 SEC 下载 company_tickers.json ...")

try:
    response = requests.get(URL, headers=HEADERS, timeout=60)
    response.raise_for_status()
    data = response.json()
    print(f"下载完成，共获取到 {len(data)} 条公司记录。")
except requests.exceptions.RequestException as err:
    print("请求 SEC 数据时出现网络错误：", err)
    raise SystemExit(1)
except json.JSONDecodeError as err:
    print("解析 JSON 响应时失败：", err)
    raise SystemExit(1)

rows = []
for key, item in data.items():
    try:
        ticker = item["ticker"].upper()
        cik = f'{int(item["cik_str"]):010d}'  # 补齐为 10 位数字
        name = item["title"]
    except (KeyError, TypeError, ValueError) as err:
        print(f"跳过索引 {key}，字段不完整或格式错误：{err}")
        continue

    rows.append({"ticker": ticker, "cik": cik, "name": name})

if not rows:
    print("未能成功解析任何公司记录，程序终止。")
    raise SystemExit(1)

df = (
    pd.DataFrame(rows)
    .sort_values("ticker")
    .reset_index(drop=True)
)

print(f"转换为 DataFrame 后共有 {len(df)} 条记录。")
print("示例预览：")
print(df.head())

try:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"CSV 已保存到 {OUTPUT_PATH.resolve()}")
except Exception as err:
    print("写入 CSV 时出现异常：", err)
