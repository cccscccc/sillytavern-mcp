# SillyTavern MCP Server

让支持 MCP 的 AI 客户端直接操作本地 **SillyTavern**：角色卡、世界书、聊天记录、以及借用其配置的模型后端生成文本。

**核心用途：写完角色卡后，让 AI 自己把卡测一遍** —— 体检、查设定有没有注入、多轮真跑。

- **纯 Python 标准库实现，零第三方依赖**，不需要 `pip install`
- 传输：MCP stdio（换行分隔的 JSON-RPC 2.0）
- 单文件：`sillytavern_mcp.py`

---

## 运行前提

| 条件 | 说明 |
|---|---|
| Python | **3.6+**（实测 3.9 / 3.13）。无需任何第三方包 |
| SillyTavern | 需要**正在运行**，且开启 HTTP API。默认地址 `http://127.0.0.1:8000` |
| MCP 客户端 | Claude Desktop / Cursor / Cline / Cherry Studio / LM Studio / WorkBuddy 等，任何支持 MCP 的都行 |

> ⚠️ 这不是一个"发过去就能聊天"的程序。**接收方必须在自己电脑上把 Python 进程跑起来**，并在自己的 MCP 客户端里注册。

---

## 接入配置

把下面这段填进客户端的 MCP 配置文件（各家文件名不同，见下表），把路径换成实际路径：

```json
{
  "mcpServers": {
    "sillytavern": {
      "command": "python",
      "args": ["/绝对路径/sillytavern_mcp.py"],
      "env": {
        "ST_BASE_URL": "http://127.0.0.1:8000"
      }
    }
  }
}
```

- `command` 建议写 **Python 的绝对路径**（多版本共存时最稳），Windows 例：`C:\Python39\python.exe`
- 路径含空格/中文要加引号，Windows 下 JSON 里的反斜杠要写成 `\\`

常见客户端的配置文件位置：

| 客户端 | 配置位置 |
|---|---|
| Claude Desktop | Windows `%APPDATA%\Claude\claude_desktop_config.json`；macOS `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Cursor | `~/.cursor/mcp.json` |
| Cline / Roo | 扩展面板里的 MCP Servers 配置 |
| WorkBuddy | `~/.workbuddy/mcp.json` |

配好后**通常要重启客户端**才生效。部分客户端（如 WorkBuddy）还需要在界面里对该服务点一次「信任」。

---

## 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `ST_BASE_URL` | `http://127.0.0.1:8000` | SillyTavern 地址。异地/换端口时改这里 |
| `ST_TIMEOUT` | `180` | 单次请求超时（秒） |
| `ST_MCP_LOG` | 空（不写日志） | 设为文件路径则记录调试日志 |
| `ST_EXPORT_DIR` | `~/sillytavern-mcp-exports` | 角色卡导出目录 |

---

## 工具清单（23 个）

**状态**
- `st_status` —— 是否在运行、版本、卡/书数量、当前模型。**任何操作前先跑这个**

**角色卡**
- `st_list_characters` / `st_get_character` / `st_create_character` / `st_update_character`
- `st_set_avatar` / `st_import_character` / `st_export_character` / `st_duplicate_character`
- `st_delete_character` ⚠️ 需 `confirm=true`

**世界书**
- `st_list_worldinfo` / `st_get_worldinfo` / `st_save_worldinfo`（建/追加/合并）
- `st_delete_worldinfo` ⚠️ 需 `confirm=true`

**聊天**
- `st_list_chats` / `st_get_chat` / `st_search_chats` / `st_new_chat`
- `st_delete_chat` ⚠️ 需 `confirm=true`

**生成**
- `st_generate` —— 借用其模型后端出文。指定 `character` 时会**自动带上该卡绑定的世界书、内嵌世界书、depth_prompt、对话示例**，并按关键词触发规则只注入命中的条目。**会消耗对应 API 额度**

**写卡自测（v1.1 新增）**
- `st_card_audit` —— **静态体检，零成本**。查字段完整性、`{{char}}`/`{{user}}` 占位符、对话示例格式，以及世界书健康度：永不触发的死条、过泛关键词、**内嵌世界书与线上不同步**等，输出分级问题清单
- `st_prompt_preview` —— **提示词X光，零成本**。展示这张卡在指定对话下会被组装成什么提示词，逐条列出哪些条目命中注入、哪些被跳过、原因是什么，并给出 token 估算与超限告警
- `st_test_character` —— **多轮真跑**。以该卡开场白起手，按给定台词逐轮真实生成，**每轮回显本轮触发了哪些世界书条目**，最后给出完整对话记录，可存 JSON 便于改动前后 diff

⚠️ 删除类工具第一次调用只返回"将要删什么"，必须再带 `confirm=true` 才真正执行。

---

## 写卡自测怎么用

内置的**设定注入引擎**按 SillyTavern 前端的规则复刻了触发逻辑：`constant` 常驻 / `disable` 停用 / 主关键词命中 / `selective` 次关键词逻辑（AND ANY、NOT ALL、NOT ANY、AND ALL）/ `order` 降序 / `position` 分位（角色定义前、后、按深度插入、示例对话）/ `depth_prompt`，并且**自动加载卡片 `extensions.world` 绑定的世界书**（读不到才退回内嵌的 `character_book`）。

推荐的测试顺序：

1. **`st_card_audit`** —— 先排低级错误。零成本，先跑不吃亏
2. **`st_prompt_preview`** —— 用几句典型台词试，看**该触发的设定有没有真的进去**。这是最容易出问题的一环：设定写成世界书条目后，很常见的翻车是关键词写得太泛（误触发）或太生僻（永不触发）
3. **`st_test_character`** —— 确认注入没问题了再真跑，看人格稳不稳定、抗不抗越狱
4. 改卡 → 回第 1 步。配合 `save_to` 存记录做对比

> **诚实的边界**：这是**复刻**的组装，不是 SillyTavern 浏览器里真正发给模型的那一份。差异在于：ST 的预设（preset）、正则、作者注、以及提示词模板都在浏览器侧，纯 HTTP API 取不到。所以本工具能准确告诉你**「卡片自带的设定与世界书有没有正确注入」**，但不能替代"在酒馆里实际聊几句"的最终验收。
>
> 另外它**不做上下文预算裁剪**，只是估算并告警；真实 ST 会因为超出预算而丢弃条目。

---

## 隐私提醒（重要）

- **谁运行它，谁就能读到那台机器上 SillyTavern 的全部聊天记录与角色卡。**
- 但它默认只连 `127.0.0.1`，也就是**运行者自己的机器** —— 别人拿到这份脚本，只能读到他自己的酒馆数据，读不到你的。
- 反过来说：**不要**把 `ST_BASE_URL` 指向别人或公网上的 SillyTavern 实例，那等于把账号和数据交出去。
- 脚本本身不含任何密钥、token 或账号信息；SillyTavern 的 CSRF 令牌是运行时动态获取的。

---

## 自测

```bash
python _selftest.py
```

只读回归测试：握手 → 工具清单 → 逐个调用只读工具 → 校验安全闸。改过代码后跑一遍。

> 注意：测试输出会包含聊天正文，**不要外传该输出**。
