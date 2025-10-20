# -*- coding: utf-8 -*-
"""
从 SEC Submissions API 获取指定公司的全部 10-K / 10-K/A 申报记录。
"""

import json
import time
from pathlib import Path
from typing import Iterable

import pandas as pd
import requests
from tqdm import tqdm

from SEC_API_HEADERS import HEADERS

SUBMISSIONS_BASE = "https://data.sec.gov/submissions/"


def list_10k_for_cik(
    cik_10: str,
    include_amends: bool = False,
):
    """
    根据 10 位补零的 CIK 号码抓取公司最近与历史文件中的 10-K 相关条目。

    每条结果包含 accession 编号、主文档文件名、申报日期以及原始下载链接。
    """
    url = f"{SUBMISSIONS_BASE}CIK{cik_10}.json"
    print(f"开始请求 CIK={cik_10} 的申报信息：{url}")

    try:
        response = requests.get(url, headers=HEADERS, timeout=60)
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.RequestException as err:
        print(f"访问 SEC Submissions API 失败（CIK={cik_10}）：{err}")
        return []
    except json.JSONDecodeError as err:
        print(f"解析 SEC 返回的 JSON 失败（CIK={cik_10}）：{err}")
        return []

    collected = []

    # recent filings
    try:
        recent = payload.get("filings", {}).get("recent", {})
        for idx, form in enumerate(recent.get("form", [])):
            if form == "10-K" or (include_amends and form == "10-K/A"):
                accession = recent["accessionNumber"][idx]
                primary_doc = recent["primaryDocument"][idx]
                filing_date = recent.get("filingDate", [""])[idx]
                collected.append((accession, primary_doc, filing_date))
        print(f"最近文件中匹配到 {len(collected)} 条记录。")
    except Exception as err:
        print(f"处理 recent 节点时出错（CIK={cik_10}）：{err}")

    # historical files
    try:
        files = payload.get("filings", {}).get("files", [])
        for f in files:
            hist_url = SUBMISSIONS_BASE + f["name"]
            print(f"  下载历史分页：{hist_url}")
            try:
                hist_resp = requests.get(hist_url, headers=HEADERS, timeout=60)
                hist_resp.raise_for_status()
                hist_payload = hist_resp.json()
            except (requests.exceptions.RequestException, json.JSONDecodeError) as err:
                print(f"  历史分页错误：{err}")
                continue

            for row in hist_payload.get("filings", []):
                form = row.get("form")
                if form == "10-K" or (include_amends and form == "10-K/A"):
                    accession = row.get("accessionNumber", "")
                    primary_doc = row.get("primaryDocument", "")
                    filing_date = row.get("filingDate", "")
                    collected.append((accession, primary_doc, filing_date))
        print(f"累计收集到 {len(collected)} 条 10-K 相关记录。")
    except Exception as err:
        print(f"处理历史文件清单时出错（CIK={cik_10}）：{err}")

    # 去重
    deduplicated = []
    seen = set()
    for accession, primary_doc, filing_date in collected:
        key = (accession, primary_doc)
        if key not in seen:
            seen.add(key)
            deduplicated.append((accession, primary_doc, filing_date))
    print(f"去重后剩余 {len(deduplicated)} 条记录。")

    # 构建最终结构
    rows = []
    for accession, primary_doc, filing_date in deduplicated:
        accession_compact = accession.replace("-", "")
        cik_no_zero = str(int(cik_10))
        tenk_url = f"https://www.sec.gov/Archives/edgar/data/{cik_no_zero}/{accession_compact}/{primary_doc}"
        rows.append(
            {
                "cik": cik_10,
                "accession": accession,
                "filing_date": filing_date,
                "primary_doc": primary_doc,
                "tenk_url": tenk_url,
            }
        )

    print(f"CIK={cik_10} 最终输出 {len(rows)} 条记录。")
    return rows


def build_10k_index(
    tickers_csv: str = "tickers.csv",
    out_csv: str = "tenk_index.csv",
    tickers_subset: Iterable[str] | None = None,
    include_amends: bool = False,
    sleep_sec: float = 0.6,
):
    """
    读取公司列表 CSV，批量抓取全部 10-K 申报信息并导出到新的 CSV。
    """
    print(f"读取公司目录：{tickers_csv}")
    try:
        df = pd.read_csv(tickers_csv, dtype={"cik": str})
    except Exception as err:
        print(f"加载 {tickers_csv} 失败：{err}")
        return pd.DataFrame()

    if tickers_subset:
        targets = [t.upper() for t in tickers_subset]
        df = df[df["ticker"].isin(targets)]
        print(f"选择 {len(df)} 个指定的股票代码：{targets}")
    else:
        print(f"未指定子集，将处理全部 {len(df)} 家公司。")

    all_rows = []

    for _, row in tqdm(df.iterrows(), total=len(df), desc="抓取 10-K", unit="家"):
        cik = row["cik"]
        ticker = row["ticker"]
        name = row["name"]
        print(f"\n处理 {ticker}（{name}），CIK={cik}")

        entries = list_10k_for_cik(
            cik_10=cik,
            include_amends=include_amends,
        )

        if not entries:
            print(f"{ticker} 未找到符合条件的 10-K。")
        else:
            for entry in entries:
                entry.update({"ticker": ticker, "company": name})
            all_rows.extend(entries)
            print(f"当前累计 {len(all_rows)} 条 10-K 记录。")

        time.sleep(sleep_sec)

    if not all_rows:
        print("没有获取到任何 10-K 记录。")
        return pd.DataFrame()

    index_df = (
        pd.DataFrame(all_rows)
        .sort_values(["ticker", "filing_date"], na_position="last")
        .reset_index(drop=True)
    )

    print(f"\n共整理出 {len(index_df)} 条 10-K 记录。")
    print("示例预览：")
    print(index_df.head())

    try:
        index_df.to_csv(out_csv, index=False)
        print(f"结果已保存到 {Path(out_csv).resolve()}")
    except Exception as err:
        print(f"写入 {out_csv} 时出错：{err}")

    return index_df


if __name__ == "__main__":
    #sample_tickers = ["AAPL", "MSFT", "AMZN", "GOOG", "META", "TSLA", "NVDA", "JNJ", "JPM", "WMT"]
    sample_tickers = ["AAPL"]

    build_10k_index(
        tickers_csv="data/tickers.csv",
        out_csv="data/tenk_index_test10.csv",
        tickers_subset=sample_tickers,
        include_amends=False,
        sleep_sec=0.6,
    )
