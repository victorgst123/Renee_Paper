UA = "Victor/1.0 (Personal; guosite@gmail.com)"  # 按 SEC 要求提供可联系的 User-Agent
HEADERS = {
    "User-Agent": UA,                       # 缺少有效 UA 时 SEC 会拒绝请求
    "Accept-Encoding": "gzip, deflate"      # 默认启用压缩，降低响应体积
}
