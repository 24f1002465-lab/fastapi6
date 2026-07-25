import hashlib
import json
import re
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/mcp"
EMAIL = "24f1002465@ds.study.iitm.ac.in"


def parse(body: bytes):
    text = body.decode("utf-8")
    # Streamable HTTP may reply as JSON or as SSE (event: message\ndata: {...}).
    if "data:" in text and "event:" in text:
        for line in text.splitlines():
            if line.startswith("data:"):
                return json.loads(line[5:].strip())
    return json.loads(text)


def call(method, params=None, notif=False, session=None, extra_headers=None, _id=1):
    payload = {"jsonrpc": "2.0", "method": method}
    if not notif:
        payload["id"] = _id
    if params is not None:
        payload["params"] = params
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session:
        headers["Mcp-Session-Id"] = session
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(BASE, data=json.dumps(payload).encode(), headers=headers, method="POST")
    resp = urllib.request.urlopen(req, timeout=15)
    sid = resp.headers.get("Mcp-Session-Id")
    raw = resp.read()
    return resp.status, sid, (None if notif or not raw.strip() else parse(raw))


# 1. initialize
status, sid, res = call("initialize", {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {"name": "grader", "version": "1.0"},
})
print("initialize:", status, "session:", sid)
print("  serverInfo:", res["result"].get("serverInfo"))

# 2. notifications/initialized
status, _, _ = call("notifications/initialized", notif=True, session=sid)
print("notifications/initialized:", status)

# 3. tools/list
status, _, res = call("tools/list", {}, session=sid, _id=2)
tools = res["result"]["tools"]
names = [t["name"] for t in tools]
print("tools/list:", names)
tool = tools[0]
print("  input schema:", json.dumps(tool.get("inputSchema", {})))
assert names == ["solve_challenge"], "tool must be exactly solve_challenge"
assert not tool.get("inputSchema", {}).get("required"), "no required properties allowed"

# 4. tools/call five times with fresh challenges via header
ok = 0
for i in range(5):
    challenge = hashlib.md5(f"chal{i}".encode()).hexdigest()  # 32 lowercase hex
    expected = hashlib.sha256(f"{challenge}:{EMAIL}".encode()).hexdigest()[:16]
    status, _, res = call(
        "tools/call",
        {"name": "solve_challenge", "arguments": {}},
        session=sid,
        extra_headers={
            "X-Exam-Challenge": challenge,
            "X-Exam-Timestamp": "1730000000000",
        },
        _id=100 + i,
    )
    text = res["result"]["content"][0]["text"]
    good = text == expected
    ok += good
    print(f"call {i}: challenge={challenge[:8]}... got={text} expected={expected} {'OK' if good else 'FAIL'}")

print(f"\n{ok}/5 correct")
assert ok == 5
print("ALL GOOD")
