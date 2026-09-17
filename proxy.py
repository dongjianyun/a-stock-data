"""
极简微信 API 反代服务
- 部署到 Render.com 后,得到固定 onrender.com 域名
- 把该域名出口 IP 加入微信公众号白名单即可一劳永逸
- TraeWork 沙箱无论出口 IP 怎么变,都先打到这里再转发给 api.weixin.qq.com
"""
import os
import requests
from flask import Flask, request, Response, stream_with_context

app = Flask(__name__)

UPSTREAM = "https://api.weixin.qq.com"

FORWARD_HEADERS = {
    "accept", "accept-language", "content-type", "user-agent",
    "referer", "x-forwarded-for",
}

RESPONSE_DROP_HEADERS = {
    "connection", "transfer-encoding", "content-encoding",
}


@app.route("/", defaults={"path": ""}, methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"])
@app.route("/<path:path>", methods=["GET", "POST", "PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"])
def proxy(path):
    url = f"{UPSTREAM}/{path}"
    if request.query_string:
        url = f"{url}?{request.query_string.decode()}"

    fwd_headers = {k: v for k, v in request.headers.items()
                   if k.lower() in FORWARD_HEADERS}
    fwd_headers["host"] = "api.weixin.qq.com"

    body = request.get_data() if request.method not in ("GET", "HEAD", "OPTIONS") else None

    try:
        resp = requests.request(
            method=request.method,
            url=url,
            headers=fwd_headers,
            data=body,
            stream=True,
            timeout=120,
            allow_redirects=False,
        )
    except Exception as e:
        return Response(f"Upstream error: {e}", status=502)

    out_headers = [(k, v) for k, v in resp.raw.headers.items()
                   if k.lower() not in RESPONSE_DROP_HEADERS]
    out_headers.append(("Access-Control-Allow-Origin", "*"))
    out_headers.append(("Access-Control-Allow-Methods", "GET, POST, OPTIONS"))
    out_headers.append(("Access-Control-Allow-Headers", "*"))

    return Response(
        stream_with_context(resp.iter_content(chunk_size=65536)),
        status=resp.status_code,
        headers=out_headers,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
