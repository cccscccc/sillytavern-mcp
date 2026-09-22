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
- `st_generate` —— 借用其模型后端出文。指定 `character` 时会**自动带上该卡绑定的世界书、内嵌世界书、ST 的全局挂载世界书、按深度插入的条目与对话示例**，并按关键词触发规则只注入命中的条目。**会消耗对应 API 额度**：第一次调用只回报「用哪个模型、提示词多大」，必须再带 `confirm=true` 才真正生成

**写卡自测（v1.1 新增）**
- `st_card_audit` —— **静态体检，零成本**。查字段完整性、`{{char}}`/`{{user}}` 占位符、对话示例格式，以及世界书健康度：永不触发的死条、过泛关键词、**内嵌世界书与线上不同步**等，输出分级问题清单
- `st_prompt_preview` —— **提示词X光，零成本**。展示这张卡在指定对话下会被组装成什么提示词，逐条列出哪些条目命中注入、哪些被跳过、原因是什么，并给出 token 估算与超限告警
- `st_test_character` —— **多轮真跑**。以该卡开场白起手，按给定台词逐轮真实生成，**每轮回显本轮触发了哪些世界书条目**，最后给出完整对话记录，可存 JSON 便于改动前后 diff。**每一轮消耗一次 API 调用**：第一次调用只回报要跑几轮，必须再带 `confirm=true` 才开始

⚠️ 删除类工具第一次调用只返回"将要删什么"，必须再带 `confirm=true` 才真正执行。

---

## 写卡自测怎么用

内置的**设定注入引擎**按 SillyTavern 前端的规则复刻了触发逻辑：`constant` 常驻 / `disable` 停用 /
主关键词命中 / `selective` 次关键词逻辑（AND ANY、NOT ALL、NOT ANY、AND ALL）/ `order` 降序 /
`position` 分位（角色定义前、后、作者注、按深度插入、示例对话）/ `depth_prompt`。

组装本身也对齐了 ST 的实际行为：

- **按深度插入**（`position=atDepth`）按 ST 的 `doChatInject` 算法实现：同「深度 + 角色（system / user / assistant）」
  归为一组、组内用换行连接，再从对话末尾倒数第 N 条插进去；深度超出对话长度时按 ST 的方式钳制到最前面。
  所以卡片 `depth_prompt`、以及 TavernDB / MVU 那类「深度 0 贴末尾、深度 1000 以上顶最前」的写法都能还原。
- 世界书来源包含 **卡片 `extensions.world` 绑定的世界书**（读不到才退回内嵌的 `character_book`）
  和 **ST 的全局挂载世界书**（`world_info.globalSelect`），两者重复时会去重。

推荐的测试顺序：

1. **`st_card_audit`** —— 先排低级错误。零成本，先跑不吃亏
2. **`st_prompt_preview`** —— 用几句典型台词试，看**该触发的设定有没有真的进去**。这是最容易出问题的一环：设定写成世界书条目后，很常见的翻车是关键词写得太泛（误触发）或太生僻（永不触发）
3. **`st_test_character`** —— 确认注入没问题了再真跑，看人格稳不稳定、抗不抗越狱
4. 改卡 → 回第 1 步。配合 `save_to` 存记录做对比

> **诚实的边界**：这是**复刻**的组装，不是 SillyTavern 浏览器里真正发给模型的那一份。差异在于：ST 的预设（preset）、正则、作者注、以及提示词模板都在浏览器侧，纯 HTTP API 取不到。所以本工具能准确告诉你**「卡片自带的设定与世界书有没有正确注入」**，但不能替代"在酒馆里实际聊几句"的最终验收。
>
> 另外它**不做上下文预算裁剪**，只是估算并告警；真实 ST 会因为超出预算而丢弃条目。
> 也就是说，报告里「注入 N 条」是按触发规则算出的**理论值**，不等于真实进模型的条数。
> 作者注（ANTop / ANBottom）的位置也仍是近似——它的深度记在聊天元数据里，纯 HTTP API 取不到。

---

## 更新记录

### v1.3.0

**修掉两个会静默出错的坑：**

- **重名卡不再静默取第一张。** 以前用角色名调用时，一旦对上多张卡（包括「名字刚好等于另一张卡 avatar 主干」这种情形）会悄悄用第一张，写操作可能改错卡。现在会报错，并把每一张的 `handle` 列出来。
- **全局挂载世界书以前根本没读。** `world_info.globalSelect` 读出来了却从未使用，导致 X 光和生成的提示词都缺了这些常驻条目。现在会并入并标注来源，与卡片绑定的书重复时去重。

**按 SillyTavern 1.18.0 源码对齐组装行为：**

- `position=atDepth` 的条目改为**真的插进对话**（同深度 + 角色归组、组内换行连接、从对话末尾倒数第 N 条插入），不再统一塞进最前面的系统块；深度超出对话长度时按 ST 的方式钳制。
- 示例位置条目（`EMTop` / `EMBottom`）贴在对话示例前后，不再被当成深度 0。
- 卡片 `depth_prompt` 按自身深度 / 角色插入。
- 报告口径拆开：系统块 / 按深度插入 / 对话历史 / 合计，并写明这是**未做预算裁剪的理论值**。

**其它修复：**

- `st_save_worldinfo` 以前写条目时**硬编码** `depth=4`、`role=null`、`order=100`，根本写不出带自定义深度的条目。现在 `depth` / `role` / `order` / `selective_logic` / `probability` / `use_regex` 等会透传。
- 世界书地图视图补上**位置 / 深度 / 角色**。
- **生成类工具加上额度闸门**：`st_generate` / `st_test_character` 第一次调用只回报「跑几轮、用哪个模型、提示词多大」，必须再带 `confirm=true` 才真正生成。以前这两个工具没有任何确认，而删卡反而要两次确认。
- 查不存在的世界书不再谎报「是一本空世界书」，改为「找不到」并列出可用的书。
- 只写 `char:` 前缀时给出明确提示，不再掉进「找不到角色」分支。
- `st_duplicate_character` 返回规范的 `handle`，不再吐内部原始数据。
- `_selftest.py` 修正两处：角色卡解析用了旧标签 `avatar:`，导致角色卡相关测试被**静默跳过**；中文 Windows 控制台下打印 `✓` 会直接抛异常崩溃（现在强制 UTF-8）。修完后自测从 5 项 [ok] 提升到 11 项。

> 组装逻辑是按 **SillyTavern 1.18.0** 的源码对齐的。换版本后如有出入，以你实际安装的那份为准。

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
