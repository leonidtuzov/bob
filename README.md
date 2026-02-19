# bob

*it's not much, but it's honest bob.*

Not all models are created equal — you use Claude for code, Codex for chat, Ollama for offline, maybe Gemini for search. Each needs its own terminal tab, its own flags, its own model names. By evening you have 12 tabs open and can't remember which is which.

bob is one terminal, one menu. Short names, your rules — `q` for quick free questions, `talk` to chat, `code` to code, `local` for offline. Edit the config, add your own. No history, no sessions, no data sent anywhere.

```
  bob>

  ❯ q           ollama run glm-5:cloud
    talk        codex --model gpt-5.2 --full-auto
    code        claude --model claude-sonnet-4-6
    code hard   claude --model claude-opus-4-6
    code light  claude --model claude-haiku-4-5
    local       ollama run qwen3:8b

  type to filter · ↑↓ select · enter launch · /about · esc quit
```

## Install

```bash
git clone https://github.com/leonidtuzov/bob
cd bob
python3 bob.py
```

No dependencies. Python 3.10+. On Windows works too — falls back to a simple text menu if curses is unavailable.

## Config

`~/.bob/config.txt` or `config.txt` next to `bob.py`.

```
# commands
code = claude --model claude-sonnet-4-6
local = ollama run qwen3:8b

# options
colored menu = 1
```

`colored menu = 1` — gradient colors in the menu (fuchsia → cyan). Set to `0` to disable.

---

## CLI Args Reference

Copy-paste into your config. Run `<tool> --help` for the full list.

### Claude Code

```
code = claude --model claude-sonnet-4-6
```

| Flag | Description |
|------|-------------|
| `--model <id>` | `claude-opus-4-6`, `claude-sonnet-4-6`, `claude-haiku-4-5` |
| `-p "prompt"` | Non-interactive, print and exit |
| `-c` | Continue last conversation |
| `-r` | Resume session by ID or picker |
| `--permission-mode plan` | `default`, `acceptEdits`, `plan` |
| `--effort high` | `low`, `medium`, `high` |
| `--system-prompt "..."` | Custom system prompt |
| `--allowed-tools "Bash Edit"` | Whitelist specific tools |
| `--output-format json` | `text`, `json`, `stream-json` |
| `--add-dir /path` | Additional writable dirs |

### OpenAI Codex

```
talk = codex --model gpt-5.2 --full-auto
```

| Flag | Description |
|------|-------------|
| `--model <id>` | Model to use |
| `--full-auto` | Auto-edit workspace, ask before external actions |
| `-a on-request` | Approval: `untrusted`, `on-request`, `never` |
| `-s workspace-write` | Sandbox: `read-only`, `workspace-write` |
| `--search` | Enable web search |
| `-C /project` | Set working directory |
| `--add-dir /extra` | Additional writable dirs |

### Google Gemini

```
web = gemini
```

| Flag | Description |
|------|-------------|
| `--model <id>` | `gemini-2.5-pro`, `gemini-2.5-flash` |
| `-p "prompt"` | Non-interactive mode |
| `--approval-mode auto_edit` | `default`, `auto_edit`, `plan` |
| `-r latest` | Resume session (`latest` or index) |
| `--include-directories /path` | Additional workspace dirs |
| `-o json` | `text`, `json`, `stream-json` |

### Ollama

```
local = ollama run qwen3:8b
```

| Flag | Description |
|------|-------------|
| `--think` | Enable thinking mode |
| `--keepalive 10m` | Keep model loaded in memory |
| `--format json` | Force output format |
| `--verbose` | Show timing info |
| `--nowordwrap` | Disable word wrapping |

**Models:** `qwen3:8b`, `qwen3:32b`, `qwen3:72b`, `deepseek-r1`, `llama3.3`, `codestral`, `mistral`, `phi4`, `gemma3`, `glm4`

---

```
bob out. your ai, your rules.
```

MIT License · Leonid Tuzov, 2026
