#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""SillyTavern MCP Server 自测脚本（只读，不改动任何数据）。"""
import json
import os
import subprocess
import sys

# 解释器：默认用当前 Python；多版本共存时可用 ST_PY 环境变量指定
PY = os.environ.get("ST_PY") or sys.executable
SRV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sillytavern_mcp.py")
LOGDIR = os.path.dirname(os.path.abspath(__file__))
ERRLOG = os.path.join(LOGDIR, "_selftest_stderr.log")

env = dict(os.environ)
env["ST_MCP_LOG"] = os.path.join(LOGDIR, "_debug.log")

errf = open(ERRLOG, "wb")
proc = subprocess.Popen(
    [PY, SRV], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    stderr=errf, env=env,
)

counter = [0]


def call(method, params=None, notify=False):
    counter[0] += 1
    msg = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        msg["params"] = params
    if not notify:
        msg["id"] = counter[0]
    proc.stdin.write((json.dumps(msg, ensure_ascii=False) + "\n").encode("utf-8"))
    proc.stdin.flush()
    if notify:
        return None
    line = proc.stdout.readline()
    if not line:
        raise RuntimeError("服务无响应（进程可能已退出，见 %s）" % ERRLOG)
    return json.loads(line.decode("utf-8"))


def show(title, resp, limit=700):
    print("\n" + "=" * 62)
    print("◆ " + title)
    print("=" * 62)
    if "error" in resp:
        print("!! 协议错误:", resp["error"])
        return
    result = resp.get("result", {})
    if "content" in result:
        flag = "ERR" if result.get("isError") else "ok"
        print("[%s] %s" % (flag, result["content"][0]["text"][:limit]))
    else:
        print(json.dumps(result, ensure_ascii=False)[:limit])


try:
    r = call("initialize", {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "selftest", "version": "1.0"},
    })
    show("initialize 握手", r, 500)
    call("notifications/initialized", {}, notify=True)

    r = call("tools/list")
    names = [t["name"] for t in r["result"]["tools"]]
    print("\n工具总数: %d" % len(names))
    print("工具清单: %s" % ", ".join(names))

    show("st_status", call("tools/call", {"name": "st_status", "arguments": {}}))

    r = call("tools/call", {"name": "st_list_characters", "arguments": {}})
    show("st_list_characters", r, 900)

    chars = []
    try:
        txt = r["result"]["content"][0]["text"]
        for line in txt.splitlines():
            if "avatar:" in line:
                chars.append(line.split("avatar:")[1].split("|")[0].strip())
    except Exception:
        pass

    if chars:
        show("st_get_character（%s）" % chars[0],
             call("tools/call", {"name": "st_get_character", "arguments": {"character": chars[0]}}), 700)
        show("st_list_chats（%s）" % chars[0],
             call("tools/call", {"name": "st_list_chats", "arguments": {"character": chars[0]}}), 600)
        show("st_get_chat（%s，最后 3 条）" % chars[0],
             call("tools/call", {"name": "st_get_chat", "arguments": {"character": chars[0], "limit": 3}}), 700)

    show("st_list_worldinfo", call("tools/call", {"name": "st_list_worldinfo", "arguments": {}}), 600)

    r = call("tools/call", {"name": "st_list_worldinfo", "arguments": {}})
    wi = None
    for line in r["result"]["content"][0]["text"].splitlines():
        if "file_id:" in line:
            wi = line.split("file_id:")[1].strip().rstrip("）").strip()
            break
    if wi:
        show("st_get_worldinfo（%s）" % wi,
             call("tools/call", {"name": "st_get_worldinfo", "arguments": {"name": wi, "limit": 2}}), 700)

    show("st_search_chats（关键词测试）",
         call("tools/call", {"name": "st_search_chats", "arguments": {"keyword": "的"}}), 600)

    # ---- v1.1 设定注入引擎与自测三件套 ----
    if chars:
        show("st_prompt_preview（无命中对照）",
             call("tools/call", {"name": "st_prompt_preview",
                                 "arguments": {"character": chars[0], "show_prompt": False}}), 900)
        show("st_card_audit（%s）" % chars[0],
             call("tools/call", {"name": "st_card_audit", "arguments": {"character": chars[0]}}), 1200)

    show("st_prompt_preview 缺少必填参数（应报错）",
         call("tools/call", {"name": "st_prompt_preview", "arguments": {}}), 300)

    show("st_delete_character 安全闸（应拒绝执行）",
         call("tools/call", {"name": "st_delete_character", "arguments": {"character": chars[0] if chars else "x"}}), 400)

    show("未知工具（应报错）",
         call("tools/call", {"name": "st_no_such_tool", "arguments": {}}), 300)

    show("未知方法（应返回 -32601）", call("tools/notexist"), 300)

finally:
    try:
        proc.stdin.close()
    except Exception:
        pass
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    errf.close()
    print("\n--- 进程退出码:", proc.returncode, "---")
    try:
        with open(ERRLOG, "r", encoding="utf-8", errors="replace") as f:
            err = f.read().strip()
        if err:
            print("--- stderr ---")
            print(err[:1500])
    except Exception:
        pass
