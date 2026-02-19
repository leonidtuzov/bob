import subprocess
import shutil
import stat
import sys
import os

try:
    import curses
    HAS_CURSES = True
except ImportError:
    HAS_CURSES = False

VERSION = "0.1.0"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.txt")
USER_CONFIG_PATH = os.path.expanduser("~/.bob/config.txt")

ALLOWED_BINARIES = {"ollama", "claude", "codex", "gemini"}

OPTIONS_KEYS = {"colored menu"}
DEFAULT_OPTIONS = {"colored menu": True}


def resolve_config_path():
    if os.path.exists(USER_CONFIG_PATH):
        return USER_CONFIG_PATH
    return DEFAULT_CONFIG_PATH


def check_config_permissions(path):
    """Warn if config is writable by others (group/world)."""
    try:
        st = os.stat(path)
        mode = st.st_mode
        if mode & (stat.S_IWGRP | stat.S_IWOTH):
            print(f"[warning: {path} is writable by others — consider chmod 600]\n")
        if st.st_uid != os.getuid():
            print(f"[warning: {path} is not owned by you — using defaults]\n")
            return False
    except OSError:
        pass
    return True


def load_config(path):
    if not os.path.exists(path):
        return {}, DEFAULT_OPTIONS.copy()

    if not check_config_permissions(path):
        return {}, DEFAULT_OPTIONS.copy()

    config = {}
    options = DEFAULT_OPTIONS.copy()
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                if not key:
                    continue
                if key in OPTIONS_KEYS:
                    options[key] = value.strip() == "1"
                    continue
                parts = value.strip().split()
                if not parts:
                    continue
                binary = parts[0]
                if binary not in ALLOWED_BINARIES:
                    print(f"[config: skipping '{key}' — unknown binary '{binary}'")
                    print(f" add it to ALLOWED_BINARIES in bob.py to enable]\n")
                    continue
                config[key] = {
                    "cmd":   parts,
                    "label": f"{key} -> {' '.join(parts)}",
                }
        return config, options
    except Exception as e:
        print(f"[config error: {e}]\n")
        return {}, DEFAULT_OPTIONS.copy()


# --- curses TUI (macOS / Linux) ---

def init_gradient_colors(n):
    """Init curses color pairs: fuchsia (255,0,255) -> cyan (0,200,255)."""
    if not curses.can_change_color():
        for i in range(n):
            curses.init_pair(i + 1, curses.COLOR_MAGENTA, -1)
        return

    for i in range(n):
        t = i / max(n - 1, 1)
        r = int(255 * (1 - t))
        g = int(200 * t)
        b = 255
        # curses uses 0-1000 range
        color_id = 20 + i
        curses.init_color(color_id, r * 1000 // 255, g * 1000 // 255, b * 1000 // 255)
        curses.init_pair(i + 1, color_id, -1)


def pick_command(stdscr, keys, config, colored, missing):
    """Hybrid input: type to filter, arrow down to select, enter to launch."""
    curses.curs_set(1)
    curses.use_default_colors()
    if colored:
        init_gradient_colors(len(keys))

    stdscr.clear()  # force full repaint after subprocess

    text = ""
    selected = -1  # -1 = cursor in text field, 0+ = in list
    filtered = keys[:]
    max_key_len = max((len(k) for k in keys), default=1)
    key_idx = {k: i for i, k in enumerate(keys)}
    descs = {}
    for k in keys:
        desc = " ".join(config[k]["cmd"])
        if k in missing:
            desc += "  [not found]"
        descs[k] = desc
    hint = "type to filter · ↑↓ select · enter launch · /about · esc quit"

    while True:
        # draw
        max_y, max_x = stdscr.getmaxyx()
        stdscr.erase()

        if max_y < 5 or max_x < 20:
            try:
                stdscr.addstr(0, 0, "terminal too small")
            except curses.error:
                pass
            ch = stdscr.get_wch()
            if ch == "\x1b":
                return ("quit", None)
            continue

        try:
            stdscr.addstr(1, 2, "bob> ", curses.A_BOLD)
            if text:
                stdscr.addstr(1, 7, text[:max_x - 8])
            else:
                stdscr.addstr(1, 7, "", curses.A_DIM)

            visible_rows = max_y - 5
            for i, key in enumerate(filtered):
                if i >= visible_rows:
                    break
                is_missing = key in missing
                color = curses.color_pair(key_idx[key] + 1) if colored and not is_missing else 0
                if is_missing:
                    attr = curses.A_DIM
                elif i == selected:
                    attr = color | curses.A_BOLD
                else:
                    attr = color
                if i == selected:
                    prefix = " ❯ "
                else:
                    prefix = "   "
                line = f"{prefix}{key:<{max_key_len}}   {descs[key]}"
                stdscr.addstr(i + 3, 1, line[:max_x - 2], attr)

            hint_row = min(len(filtered) + 4, max_y - 1)
            stdscr.addstr(hint_row, 2, hint[:max_x - 3], curses.A_DIM)
        except curses.error:
            pass

        if selected == -1:
            curses.curs_set(1)
            try:
                stdscr.move(1, 7 + len(text))
            except curses.error:
                pass
        else:
            curses.curs_set(0)

        # input
        try:
            ch = stdscr.get_wch()
        except KeyboardInterrupt:
            return ("quit", None)

        if ch == "\x1b":
            return ("quit", None)
        elif ch == curses.KEY_DOWN:
            if filtered:
                limit = min(len(filtered), max_y - 5)
                if selected == limit - 1:
                    selected = -1
                else:
                    selected += 1
        elif ch == curses.KEY_UP:
            if selected == -1 and filtered:
                selected = min(len(filtered), max_y - 5) - 1
            elif selected > -1:
                selected -= 1
        elif ch in (curses.KEY_ENTER, "\n", "\r"):
            if selected >= 0 and filtered:
                return ("launch", filtered[selected])
            elif text in config:
                return ("launch", text)
            elif text == "/new":
                return ("new", None)
            elif text == "/about":
                return ("about", None)
            elif text in ("exit", "quit"):
                return ("quit", None)
        elif ch in (curses.KEY_BACKSPACE, "\x7f", "\x08"):
            text = text[:-1]
            selected = -1
        elif isinstance(ch, str) and ch.isprintable():
            text += ch
            selected = -1

        # re-filter
        filtered = [k for k in keys if text in k] if text else keys[:]
        if selected >= len(filtered):
            selected = len(filtered) - 1
        if not filtered:
            selected = -1


# --- plain text fallback (Windows without curses) ---

def pick_command_plain(keys, config, missing):
    """Simple text menu for terminals without curses."""
    max_key_len = max((len(k) for k in keys), default=1)
    print()
    for i, key in enumerate(keys):
        desc = " ".join(config[key]["cmd"])
        tag = "  [not found]" if key in missing else ""
        print(f"  {i + 1:>2}. {key:<{max_key_len}}   {desc}{tag}")
    print(f"\n  type a name or number · /about · quit\n")

    try:
        text = input("bob> ").strip()
    except (KeyboardInterrupt, EOFError):
        return ("quit", None)

    if not text:
        return ("noop", None)
    if text in ("exit", "quit", "q!"):
        return ("quit", None)
    if text == "/about":
        return ("about", None)
    if text == "/new":
        return ("new", None)
    if text in config:
        return ("launch", text)
    # try by number
    try:
        idx = int(text) - 1
        if 0 <= idx < len(keys):
            return ("launch", keys[idx])
    except ValueError:
        pass
    # try partial match
    matches = [k for k in keys if text in k]
    if len(matches) == 1:
        return ("launch", matches[0])

    print(f"  [unknown command: {text}]")
    return ("noop", None)


def gradient_text(text):
    """Apply fuchsia→cyan gradient to text using ANSI true color."""
    chars = [c for c in text if c.isprintable() and c != " "]
    n = max(len(chars) - 1, 1)
    result = []
    ci = 0
    for c in text:
        if c == " " or not c.isprintable():
            result.append(c)
        else:
            t = ci / n
            r = int(255 * (1 - t))
            g = int(200 * t)
            b = 255
            result.append(f"\033[38;2;{r};{g};{b}m{c}")
            ci += 1
    result.append("\033[0m")
    return "".join(result)


def launch(cmd):
    """Run a subprocess, absorb Ctrl+C."""
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass
    except FileNotFoundError:
        print(f"\n[error: '{cmd[0]}' not found — check your config]\n")
    except OSError as e:
        print(f"\n[error: {e}]\n")


def run(config, options, missing):
    keys = list(config.keys())
    if not keys:
        print("[no commands configured — check your config.txt]\n")
        return

    active = None
    colored = options.get("colored menu", True)
    use_curses = HAS_CURSES
    farewell = "bob out. your ai, your rules."

    while True:
        if use_curses:
            try:
                action, arg = curses.wrapper(pick_command, keys, config, colored, missing)
            except KeyboardInterrupt:
                print(f"\n{gradient_text(farewell) if colored else farewell}\n")
                break
        else:
            action, arg = pick_command_plain(keys, config, missing)

        if action == "noop":
            continue

        if action == "quit":
            print(f"\n{gradient_text(farewell) if colored else farewell}\n")
            break

        if action == "new":
            if active is None:
                print("\n[no active session — pick a command first]\n")
                input("press enter...")
            else:
                entry = config[active]
                label = gradient_text(f"[new session] {entry['label']}") if colored else f"[new session] {entry['label']}"
                print(f"\n{label}\n")
                launch(entry["cmd"])
                print(f"\n[back to bob]\n")
            continue

        if action == "about":
            lines = [
                f"  bob {VERSION} — one menu for all your AI tools.",
                f"  no history, no sessions, no data sent anywhere.",
                f"  github.com/leonidtuzov/bob",
            ]
            print()
            for line in lines:
                print(gradient_text(line) if colored else line)
            print()
            input("press enter...")
            continue

        if action == "launch":
            if arg in missing:
                binary = config[arg]["cmd"][0]
                print(f"\n[{binary} not found — install it first]\n")
                input("press enter...")
                continue
            active = arg
            entry = config[active]
            label = gradient_text(entry['label']) if colored else entry['label']
            print(f"\n{label}\n")
            launch(entry["cmd"])
            print(f"\n[back to bob]\n")


def check_availability(config):
    """Check which commands are installed. Returns set of missing keys."""
    missing = set()
    for key, entry in config.items():
        binary = entry["cmd"][0]
        if not shutil.which(binary):
            missing.add(key)
    return missing


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ("-v", "--version"):
            print(f"bob {VERSION}")
            return
        if arg in ("-h", "--help"):
            print(f"bob {VERSION} — CLI router for AI agents")
            print(f"\nUsage: bob [command]")
            print(f"\nConfig: ~/.bob/config.txt or config.txt")
            print(f"Format: command = cli args")
            return

    config, options = load_config(resolve_config_path())

    # direct launch: bob <command>
    if len(sys.argv) > 1:
        name = " ".join(sys.argv[1:])
        if name in config:
            missing = check_availability(config)
            if name in missing:
                print(f"[{config[name]['cmd'][0]} not found — install it first]")
                sys.exit(1)
            launch(config[name]["cmd"])
            return
        print(f"[unknown command: {name}]")
        sys.exit(1)

    missing = check_availability(config)
    run(config, options, missing)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
