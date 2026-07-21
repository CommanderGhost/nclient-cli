import os
import sys
import logging
import json
import time

# Import rich library elements
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich.text import Text
from rich.box import ROUNDED, DOUBLE_EDGE
from rich.markup import escape
from rich.logging import RichHandler

# Initialize Rich Console
console = Console()

# Configure root logger with RichHandler immediately
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True, show_path=False)]
)

from dns_resolver import setup_dns
from downloader import extract_manga_id, process_manga_download, check_existing_download
from locales import get_txt, load_config, save_config

logger = logging.getLogger("Main")

# Keep ANSI escape codes as simple fallback string mappings
CLR_HEADER = ""
CLR_BLUE = ""
CLR_CYAN = ""
CLR_GREEN = ""
CLR_YELLOW = ""
CLR_RED = ""
CLR_GRAY = ""
CLR_BOLD = ""
CLR_RESET = ""

def clear_screen(full=False):
    """Clears the terminal screen. If full is False, only moves the cursor home
    for flicker-free in-place updates. If full is True, clears the entire display buffer.
    """
    try:
        if full:
            sys.stdout.write("\033[2J\033[H")
        else:
            sys.stdout.write("\033[H")
        sys.stdout.flush()
    except Exception:
        try:
            if os.name == 'nt':
                os.system('cls')
            else:
                sys.stdout.write("\033[2J\033[H")
                sys.stdout.flush()
        except Exception:
            print("\n" * 50)

def read_key():
    """Reads a single keypress from standard input in a cross-platform manner.
    Returns:
        str or None: Key representation ('up', 'down', 'left', 'right', 'enter', 'esc', or char).
    """
    if not sys.stdin.isatty():
        return None

    # Windows implementation
    try:
        import msvcrt
        try:
            ch = msvcrt.getch()
        except Exception:
            return None
            
        if not ch:  # EOF or non-blocking read with no key
            return None

        if ch in (b'\x00', b'\xe0'):  # Arrow key or function key prefix
            try:
                ch2 = msvcrt.getch()
            except Exception:
                return None
            if ch2 == b'H':
                return 'up'
            elif ch2 == b'P':
                return 'down'
            elif ch2 == b'K':
                return 'left'
            elif ch2 == b'M':
                return 'right'
            return None
        elif ch in (b'\r', b'\n'):
            return 'enter'
        elif ch == b'\x1b':
            return 'esc'
        elif ch == b'\x03':  # Ctrl+C
            raise KeyboardInterrupt()
        elif ch == b'\x04':  # Ctrl+D
            raise EOFError()
        else:
            try:
                decoded = ch.decode('utf-8', errors='ignore')
                return decoded if decoded else None
            except Exception:
                return None
    except ImportError:
        # UNIX / termios implementation
        try:
            import termios
            import tty
        except ImportError:
            return None

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if not ch:
                return None
            if ch == '\x1b':
                # Read escape sequence
                ch2 = sys.stdin.read(2)
                if ch2 == '[A':
                    return 'up'
                elif ch2 == '[B':
                    return 'down'
                elif ch2 == '[C':
                    return 'right'
                elif ch2 == '[D':
                    return 'left'
                return 'esc'
            elif ch in ('\r', '\n'):
                return 'enter'
            elif ch == '\x03':  # Ctrl+C
                raise KeyboardInterrupt()
            elif ch == '\x04':  # Ctrl+D
                raise EOFError()
            return ch
        except Exception:
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

def interactive_select(title, choices, initial_idx=0, show_help=True):
    """Renders an interactive selection menu with arrow keys.
    If stdin is not a TTY or key reading fails, returns None (falls back to traditional prompt).
    """
    if not sys.stdin.isatty():
        return None
        
    current_idx = initial_idx
    num_choices = len(choices)
    
    # Hide terminal cursor if possible
    try:
        console.show_cursor(False)
    except Exception:
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()
    
    first_render = True
    try:
        while True:
            # Clear screen fully on first run; move cursor home on subsequent updates (flicker-free)
            if first_render:
                clear_screen(full=True)
                first_render = False
            else:
                clear_screen(full=False)
            
            # Print title banner
            if "DOWNLOADER" in title or "SETUP" in title or "MENU" in title or "PILIH" in title or "CHOICE" in title:
                config = load_config()
                lang_name = {"en": "English", "id": "Indonesia", "zh": "Chinese (中文)", "ja": "Japanese (日本語)"}.get(config.get("language", "en"), "English")
                threads = config.get("threads", 4)
                compress = config.get("compress", False)
                quality = config.get("compress_quality", 85)
                comp_str = f"[bold green]ON[/] ({quality}%)" if compress else "[bold red]OFF[/]"
                
                info_text_markup = (
                    f"🌐 [bold cyan]Language:[/] {lang_name}  |  "
                    f"🧵 [bold cyan]Threads:[/] {threads}  |  "
                    f"🗜️ [bold cyan]Compress:[/] {comp_str}  |  "
                    f"🛡️ [bold cyan]DNS Bypass:[/] [bold green]Active[/]"
                )
                info_text = Text.from_markup(info_text_markup, style="dim white")
                banner_content = Text.assemble(
                    Text(f"🔥 {title} 🔥\n\n", style="bold magenta"),
                    info_text
                )
                banner = Panel(
                    Align.center(banner_content),
                    border_style="bold magenta",
                    box=ROUNDED,
                    padding=(1, 2)
                )
            else:
                banner = Panel(
                    Align.center(Text(title, style="bold cyan")),
                    border_style="bold blue",
                    box=ROUNDED,
                    padding=(1, 2)
                )
            console.print(banner)
            console.print()
            
            # Print choices
            for idx, choice in enumerate(choices):
                if idx == current_idx:
                    console.print(f"  [bold green]➤  {choice}[/]")
                else:
                    console.print(f"     [dim white]{choice}[/]")
            
            if show_help:
                console.print(f"\n  [dim grey][Use ↑/↓ or 1-{num_choices} keys, Enter to select][/]")
            
            # Erase any leftover text from the previous menu render
            try:
                sys.stdout.write("\033[J")
                sys.stdout.flush()
            except Exception:
                pass
            
            key = read_key()
            if key is None:
                return None
            elif key == 'up':
                current_idx = (current_idx - 1) % num_choices
            elif key == 'down':
                current_idx = (current_idx + 1) % num_choices
            elif key == 'enter':
                clear_screen(full=True)
                return current_idx
            elif key == 'esc':
                raise KeyboardInterrupt()
            elif len(key) == 1 and key.isdigit():
                val = int(key)
                if 1 <= val <= num_choices:
                    clear_screen(full=True)
                    return val - 1
    except (KeyboardInterrupt, EOFError):
        # Propagate interrupts
        raise
    except Exception:
        return None
    finally:
        # Show terminal cursor again
        try:
            console.show_cursor(True)
        except Exception:
            sys.stdout.write("\033[?25h")
            sys.stdout.flush()

def add_to_history(manga_id, title, file_format, num_pages, file_path):
    """Saves metadata of successfully downloaded manga to history.json."""
    history_file = "history.json"
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except Exception:
            pass
            
    if not isinstance(history, list):
        history = []
            
    size_bytes = os.path.getsize(file_path) if os.path.exists(file_path) else 0
    history.append({
        "id": manga_id,
        "title": title,
        "format": file_format.upper(),
        "pages": num_pages,
        "file_size_bytes": size_bytes,
        "download_date": time.strftime("%Y-%m-%d %H:%M:%S")
    })
    
    with open(history_file, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

def view_history():
    """Displays the download history in a structured console table."""
    history_file = "history.json"
    if not os.path.exists(history_file):
        console.print(f"\n[bold yellow]⚠ {get_txt('no_history')}[/]")
        return
        
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception as e:
        console.print(f"\n[bold red]❌[/] {escape(get_txt('history_read_failed', e=e))}")
        return
        
    if not history:
        console.print(f"\n[bold yellow]⚠ {get_txt('no_history')}[/]")
        return
        
    table = Table(
        title=f"📜 {get_txt('history_title')} ({len(history)} items)",
        box=DOUBLE_EDGE,
        border_style="magenta",
        title_style="bold magenta",
        header_style="bold cyan"
    )
    table.add_column(get_txt('history_header_id'), justify="center", style="cyan")
    table.add_column(get_txt('history_header_format'), justify="center", style="green")
    table.add_column(get_txt('history_header_pages'), justify="right", style="magenta")
    table.add_column(get_txt('history_header_size'), justify="right", style="yellow")
    table.add_column(get_txt('history_header_date'), justify="center", style="dim white")
    table.add_column(get_txt('history_header_title'), justify="left", style="white")
    
    for item in history:
        size_bytes = item.get("file_size_bytes", 0)
        # Format size dynamically
        if size_bytes >= 1024 * 1024 * 1024:
            size_str = f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
        elif size_bytes >= 1024 * 1024:
            size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            size_str = f"{size_bytes / 1024:.2f} KB"
            
        table.add_row(
            str(item.get("id")),
            str(item.get("format")),
            str(item.get("pages")),
            size_str,
            str(item.get("download_date")),
            str(item.get("title"))
        )
    
    console.print(table)

def view_changelog():
    """Displays the project changelog in the selected language."""
    title = get_txt('changelog_title')
    body = get_txt('changelog_body')
    
    formatted_body = ""
    for line in body.split("\n"):
        line_strip = line.strip()
        if line_strip.startswith("-"):
            formatted_body += f"⚡ [bold cyan]-[/] [white]{line_strip[1:].strip()}[/]\n"
        else:
            formatted_body += f"{line}\n"
            
    panel = Panel(
        formatted_body.strip(),
        title=f"🚀 {title}",
        title_align="center",
        border_style="bold magenta",
        box=ROUNDED,
        padding=(1, 2)
    )
    console.print(panel)

def run_batch_download(list_file="download_list.txt", output_dir="downloads", default_format="pdf", threads=None, compress=None, compress_quality=None):
    """Downloads all manga IDs in the download list sequentially or in parallel, skips duplicates, and auto-retries failed queue."""
    failed_file = "failed_downloads.txt"
    config = load_config()
    if threads is None:
        threads = config.get("threads", 4)
    if compress is None:
        compress = config.get("compress", False)
    if compress_quality is None:
        compress_quality = config.get("compress_quality", 85)
    
    # Reset failed download list at beginning of the session
    if os.path.exists(failed_file):
        try:
            os.remove(failed_file)
        except Exception:
            pass

    # Generate template list file if not exists
    if not os.path.exists(list_file):
        with open(list_file, "w", encoding="utf-8") as f:
            f.write("# Enter manga ID or nHentai URL below (one per line)\n")
            f.write("# Empty lines or lines starting with '#' will be ignored\n")
            f.write("# Example:\n")
            f.write("# 123456\n")
            f.write("# https://nhentai.net/g/654321/\n")
        logger.info(get_txt('batch_template_created', list_file=list_file))
        return

    # Read items
    with open(list_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    items = []
    for line in lines:
        line_strip = line.strip()
        if not line_strip or line_strip.startswith("#"):
            continue
        items.append(line_strip)
        
    if not items:
        logger.warning(get_txt('batch_template_created', list_file=list_file))
        return
        
    logger.info(get_txt('batch_found_manga', count=len(items)))
    
    success_count = 0
    failed_items = []
    
    # 1. First Pass Download Loop
    for idx, item in enumerate(items):
        manga_id = extract_manga_id(item)
        print(f"\n======================================== [{idx+1}/{len(items)}]")
        if not manga_id:
            logger.error(get_txt('batch_invalid_line', item=item))
            with open(failed_file, "a", encoding="utf-8") as fe:
                fe.write(f"{item} - Invalid URL/ID format\n")
            continue
            
        # Smart skip check
        existing = check_existing_download(manga_id, output_dir=output_dir)
        if existing:
            logger.info(get_txt('smart_skip_message', manga_id=manga_id, filename=os.path.basename(existing)))
            success_count += 1
            continue
            
        try:
            out_path, title, pages = process_manga_download(manga_id, output_dir=output_dir, file_format=default_format, threads=threads, compress=compress, compress_quality=compress_quality)
            add_to_history(manga_id, title, default_format, pages, out_path)
            success_count += 1
        except Exception as e:
            logger.error(get_txt('batch_failed_to_download_manga', manga_id=manga_id, e=e))
            failed_items.append((item, manga_id, e))

    # 2. Auto-Retry Failures Pass
    still_failed_items = []
    if failed_items:
        print(f"\n======================================== AUTO RETRY QUEUE")
        logger.info(get_txt('batch_retry_starting', count=len(failed_items)))
        for idx, (item, manga_id, orig_err) in enumerate(failed_items):
            print(f"\n======================================== [Retry {idx+1}/{len(failed_items)}]")
            try:
                out_path, title, pages = process_manga_download(manga_id, output_dir=output_dir, file_format=default_format, threads=threads, compress=compress, compress_quality=compress_quality)
                add_to_history(manga_id, title, default_format, pages, out_path)
                success_count += 1
                logger.info(get_txt('batch_retry_success', manga_id=manga_id))
            except Exception as e:
                logger.error(get_txt('batch_retry_failed', manga_id=manga_id, e=e))
                still_failed_items.append((item, e))

    # Record final failures
    if still_failed_items:
        with open(failed_file, "a", encoding="utf-8") as fe:
            for item, err in still_failed_items:
                fe.write(f"{item} - {err}\n")

    print("\n======================================== ")
    logger.info(get_txt('batch_process_finished'))
    logger.info(get_txt('batch_summary', success_count=success_count, failed_count=len(still_failed_items)))
    if still_failed_items:
        logger.warning(get_txt('batch_failures_logged', count=len(still_failed_items), failed_file=failed_file))

def run_manual_download(output_dir="downloads", threads=None, compress=None, compress_quality=None):
    """Handles interactive prompts for a single manual manga download."""
    config = load_config()
    if threads is None:
        threads = config.get("threads", 4)
    if compress is None:
        compress = config.get("compress", False)
    if compress_quality is None:
        compress_quality = config.get("compress_quality", 85)
        
    console.print(Panel(
        "Enter manga ID (e.g. [bold cyan]123456[/]) or full nHentai URL.",
        title="📥 MANUAL DOWNLOAD",
        border_style="bold cyan",
        box=ROUNDED
    ))
    item = console.input(f"[bold yellow]{get_txt('manual_prompt_id')}[/]").strip()
    if not item:
        console.print(f"[bold red]❌ {get_txt('manual_empty_input')}[/]")
        time.sleep(1.5)
        return
        
    manga_id = extract_manga_id(item)
    if not manga_id:
        console.print(f"[bold red]❌ {get_txt('manual_invalid_format')}[/]")
        time.sleep(1.5)
        return
        
    # Skip check
    existing = check_existing_download(manga_id, output_dir=output_dir)
    if existing:
        console.print(f"\n[bold yellow]⚠[/] {escape(get_txt('smart_skip_message', manga_id=manga_id, filename=os.path.basename(existing)))}")
        lang = load_config().get("language", "en")
        yes_txt = {"en": "Yes", "id": "Ya", "zh": "是", "ja": "はい"}.get(lang, "Yes")
        no_txt = {"en": "No", "id": "Tidak", "zh": "否", "ja": "いいえ"}.get(lang, "No")
        
        skip_prompt_title = get_txt('manual_skip_prompt', manga_id=manga_id, filename=os.path.basename(existing)).replace("(y/N):", "").strip()
        skip_choices = [yes_txt, no_txt]
        skip_idx = interactive_select(skip_prompt_title, skip_choices)
        if skip_idx is not None:
            re_download = (skip_idx == 0)
        else:
            choice = console.input(f"[bold yellow]{escape(get_txt('manual_skip_prompt', manga_id=manga_id, filename=os.path.basename(existing)))}[/]").strip().lower()
            re_download = (choice == 'y')
            
        if not re_download:
            console.print(f"[bold yellow]⚠ {get_txt('manual_download_cancelled')}[/]")
            time.sleep(1.5)
            return
            
    format_choices = [
        "PDF (default)",
        "CBZ"
    ]
    fmt_idx = interactive_select(get_txt('prompt_format').upper(), format_choices)
    if fmt_idx is not None:
        file_format = "cbz" if fmt_idx == 1 else "pdf"
    else:
        console.print("\n" + get_txt('prompt_format'))
        console.print("[1] PDF (default)")
        console.print("[2] CBZ")
        fmt_choice = console.input(get_txt('prompt_choice') + ": ").strip()
        file_format = "cbz" if fmt_choice == "2" else "pdf"
    
    console.print(f"\n[bold green]✔ " + get_txt('manual_download_starting', manga_id=manga_id) + "[/]")
    try:
        out_path, title, pages = process_manga_download(manga_id, output_dir=output_dir, file_format=file_format, threads=threads, compress=compress, compress_quality=compress_quality)
        add_to_history(manga_id, title, file_format, pages, out_path)
        console.print(f"\n[bold green]✔[/] {escape(get_txt('manual_download_success', out_path=out_path))}")
    except Exception as e:
        console.print(f"\n[bold red]❌[/] {escape(get_txt('manual_download_failed', e=e))}")
    input(f"\n[dim grey]Press Enter to return to menu...[/]")

def setup_language_selection():
    """Renders the language setup terminal screen and updates configuration."""
    lang_choices = [
        "English (Default)",
        "Indonesia",
        "Chinese (中文)",
        "Japanese (日本語)"
    ]
    selected_idx = interactive_select("LANGUAGE SETUP / PILIH BAHASA", lang_choices)
    if selected_idx is not None:
        lang_map = {0: "en", 1: "id", 2: "zh", 3: "ja"}
        selected_lang = lang_map.get(selected_idx, "en")
    else:
        # Fallback
        console.print(Panel(
            "Please choose your language / Silakan pilih bahasa Anda:",
            title="LANGUAGE SETUP",
            border_style="bold blue",
            box=ROUNDED
        ))
        for idx, lang in enumerate(lang_choices, 1):
            console.print(f"[{idx}] {lang}")
        lang_choice = console.input("[bold yellow]Choice (1-4): [/]").strip()
        lang_map = {"1": "en", "2": "id", "3": "zh", "4": "ja"}
        selected_lang = lang_map.get(lang_choice, "en")
    
    config = load_config()
    config["language"] = selected_lang
    save_config(config)
    console.print(f"[bold green]✔ Language set to: {selected_lang.upper()}[/]\n")
    time.sleep(1.5)

def setup_threads_selection():
    """Renders the thread configuration screen and updates the settings."""
    config = load_config()
    default_threads = config.get("threads", 4)
    
    console.print(Panel(
        f"Current Threads Configuration: [bold green]{default_threads}[/]\n"
        "Configure threads count to parallelize page downloads.\n"
        "Value must be between [bold cyan]1[/] and [bold cyan]32[/].",
        title=f"🧵 {get_txt('menu_option_threads', threads=default_threads).upper()}",
        border_style="bold cyan",
        box=ROUNDED
    ))
    try:
        prompt_msg = get_txt('prompt_threads', default=default_threads)
        val = console.input(f"[bold yellow]{prompt_msg}[/]").strip()
        if not val:
            threads = default_threads
        else:
            threads = int(val)
            if threads < 1 or threads > 32:
                raise ValueError()
    except ValueError:
        console.print(f"[bold red]❌ {get_txt('invalid_threads')}[/]")
        time.sleep(1.5)
        return
        
    config["threads"] = threads
    save_config(config)
    console.print(f"[bold green]✔ {get_txt('threads_updated', threads=threads)}[/]")
    time.sleep(1.5)

def setup_compress_selection():
    """Renders the image compression configuration screen and updates settings."""
    config = load_config()
    default_compress = config.get("compress", False)
    default_quality = config.get("compress_quality", 85)
    
    current_state_str = "ON" if default_compress else "OFF"
    
    lang = load_config().get("language", "en")
    yes_txt = {"en": "Yes", "id": "Ya", "zh": "是", "ja": "はい"}.get(lang, "Yes")
    no_txt = {"en": "No", "id": "Tidak", "zh": "否", "ja": "いいえ"}.get(lang, "No")
    
    compress_title = get_txt('prompt_compress_toggle').replace("(y/N):", "").strip()
    compress_choices = [yes_txt, no_txt]
    
    compress_idx = interactive_select(compress_title, compress_choices)
    if compress_idx is not None:
        compress = (compress_idx == 0)
    else:
        # Fallback
        console.print(Panel(
            f"Current Compression: [bold green]{current_state_str}[/] (Quality: [bold green]{default_quality}%[/])\n"
            "Smart image compression will optimize PNG, JPEG, and WEBP file sizes.",
            title="🗜️ COMPRESSION SETTINGS",
            border_style="bold cyan",
            box=ROUNDED
        ))
        toggle_val = console.input(f"[bold yellow]{get_txt('prompt_compress_toggle')}[/]").strip().lower()
        if not toggle_val:
            compress = default_compress
        else:
            compress = toggle_val == 'y'
        
    quality = default_quality
    if compress:
        try:
            console.print(Panel(
                "Configure compression quality (lossy JPEG compression).\n"
                "Value must be between [bold cyan]1[/] and [bold cyan]100[/] (default: 85).",
                title="🗜️ COMPRESSION QUALITY",
                border_style="bold cyan",
                box=ROUNDED
            ))
            quality_msg = get_txt('prompt_compress_quality', default=default_quality)
            quality_val = console.input(f"[bold yellow]{quality_msg}[/]").strip()
            if not quality_val:
                quality = default_quality
            else:
                quality = int(quality_val)
                if quality < 1 or quality > 100:
                    raise ValueError()
        except ValueError:
            console.print(f"[bold red]❌ {get_txt('invalid_compress_quality')}[/]")
            time.sleep(1.5)
            return
            
    config["compress"] = compress
    config["compress_quality"] = quality
    save_config(config)
    
    state_txt = "ON" if compress else "OFF"
    console.print(f"[bold green]✔ {get_txt('compress_updated', state=state_txt, quality=quality)}[/]")
    time.sleep(1.5)

def main():
    try:
        os.system('')  # Enable VT100 / ANSI escape sequences in Windows Console
    except Exception:
        pass
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    try:
        sys.stdin.reconfigure(encoding='utf-8')
    except Exception:
        pass
        
    setup_dns()
    
    # Parse potential command-line flags
    import argparse
    parser = argparse.ArgumentParser(description="nHentai Batch Downloader CLI")
    parser.add_argument("--batch", action="store_true", help="Run batch downloads automatically")
    parser.add_argument("--id", type=str, help="Download a specific manga by ID/URL")
    parser.add_argument("--format", type=str, choices=["pdf", "cbz"], default="pdf", help="Output file format (pdf/cbz)")
    parser.add_argument("--threads", type=int, default=None, help="Number of download threads")
    parser.add_argument("--compress", action="store_true", default=None, help="Enable smart image compression")
    parser.add_argument("--quality", type=int, default=None, help="Compression quality (1-100)")
    args = parser.parse_args()
    
    output_dir = "downloads"
    list_file = "download_list.txt"
    config_file = "config.json"
    
    # Language/Config default initialization
    if not os.path.exists(config_file):
        save_config({"language": "en", "threads": 4, "compress": False, "compress_quality": 85})
        
    # Read/Merge config to get current threads default
    config = load_config()
    threads_to_use = args.threads if args.threads is not None else config.get("threads", 4)
    compress_to_use = args.compress if args.compress is not None else config.get("compress", False)
    if args.compress is True:
        compress_to_use = True
    if args.quality is not None:
        if args.compress is not False:
            compress_to_use = True
    quality_to_use = args.quality if args.quality is not None else config.get("compress_quality", 85)
    
    # CLI Bypass if arguments are provided
    if args.id:
        manga_id = extract_manga_id(args.id)
        if not manga_id:
            logger.error("Invalid ID or URL format.")
            sys.exit(1)
            
        # Smart skip check
        existing = check_existing_download(manga_id, output_dir=output_dir)
        if existing:
            logger.info(get_txt('smart_skip_message', manga_id=manga_id, filename=os.path.basename(existing)))
            return
            
        try:
            out_path, title, pages = process_manga_download(manga_id, output_dir=output_dir, file_format=args.format, threads=threads_to_use, compress=compress_to_use, compress_quality=quality_to_use)
            add_to_history(manga_id, title, args.format, pages, out_path)
        except Exception as e:
            logger.error(f"Failed to download: {e}")
            sys.exit(1)
        return
        
    if args.batch:
        run_batch_download(list_file=list_file, output_dir=output_dir, default_format=args.format, threads=threads_to_use, compress=compress_to_use, compress_quality=quality_to_use)
        return
        
    # Interactive CLI Menu loop
    while True:
        config = load_config()
        current_threads = config.get("threads", 4)
        current_compress = config.get("compress", False)
        current_quality = config.get("compress_quality", 85)
        compress_state_str = "ON" if current_compress else "OFF"
        
        choices = [
            get_txt('menu_option_batch'),
            get_txt('menu_option_manual'),
            get_txt('menu_option_history'),
            get_txt('menu_option_language'),
            get_txt('menu_option_threads', threads=current_threads),
            get_txt('menu_option_compress', state=compress_state_str, quality=current_quality),
            get_txt('menu_option_changelog'),
            get_txt('menu_option_exit')
        ]
        
        selected_idx = interactive_select(get_txt('menu_title').upper(), choices)
        if selected_idx is not None:
            choice = str(selected_idx + 1)
        else:
            # Fallback to standard text menu
            print(f"\n================ {get_txt('menu_title')} ================")
            for idx, ch_text in enumerate(choices, 1):
                print(f"{idx}. {ch_text}")
            print("=====================================================")
            choice = input(f"{get_txt('prompt_choice')}: ").strip()
        
        if choice == "1":
            format_choices = [
                "PDF (default)",
                "CBZ"
            ]
            fmt_idx = interactive_select(get_txt('prompt_format_batch').upper(), format_choices)
            if fmt_idx is not None:
                file_format = "cbz" if fmt_idx == 1 else "pdf"
            else:
                print("\n" + get_txt('prompt_format_batch'))
                print("[1] PDF (default)")
                print("[2] CBZ")
                fmt_choice = input(get_txt('prompt_choice') + ": ").strip()
                file_format = "cbz" if fmt_choice == "2" else "pdf"
            run_batch_download(list_file=list_file, output_dir=output_dir, default_format=file_format, threads=current_threads, compress=current_compress, compress_quality=current_quality)
        elif choice == "2":
            run_manual_download(output_dir=output_dir, threads=current_threads, compress=current_compress, compress_quality=current_quality)
        elif choice == "3":
            view_history()
            input(f"\n{CLR_GRAY}Press Enter to return to menu...{CLR_RESET}")
        elif choice == "4":
            setup_language_selection()
        elif choice == "5":
            setup_threads_selection()
        elif choice == "6":
            setup_compress_selection()
        elif choice == "7":
            view_changelog()
            input(f"\n{CLR_GRAY}Press Enter to return to menu...{CLR_RESET}")
        elif choice == "8":
            print("\n" + get_txt('goodbye'))
            break
        else:
            print("\n" + get_txt('invalid_choice'))
            time.sleep(1.5)

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nProcess cancelled by user.")
        sys.exit(0)
