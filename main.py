import os
import sys
import logging
import json
import time
from dns_resolver import setup_dns
from downloader import extract_manga_id, process_manga_download, check_existing_download
from locales import get_txt, load_config, save_config

# Logger configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Main")

# ANSI escape codes for styling
CLR_HEADER = "\033[95m"   # Magenta
CLR_BLUE = "\033[94m"     # Blue
CLR_CYAN = "\033[96m"     # Cyan
CLR_GREEN = "\033[92m"    # Green
CLR_YELLOW = "\033[93m"   # Yellow
CLR_RED = "\033[91m"      # Red
CLR_GRAY = "\033[90m"     # Gray
CLR_BOLD = "\033[1m"
CLR_RESET = "\033[0m"

def clear_screen():
    """Clears the terminal screen in a cross-platform and terminal-resilient manner."""
    try:
        if os.name == 'nt':
            os.system('cls')
        else:
            sys.stdout.write("\033[H\033[J")
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
    
    # Hide terminal cursor if possible (ANSI sequence)
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()
    
    try:
        while True:
            # Clear screen using OS-native / fallback call
            clear_screen()
            
            # Print title banner
            border_len = max(len(title) + 6, 60)
            sys.stdout.write(f"{CLR_BOLD}{CLR_BLUE}┌" + "─" * (border_len - 2) + "┐\n")
            # Center the title
            padded_title = title.center(border_len - 4)
            sys.stdout.write(f"│ {CLR_CYAN}{CLR_BOLD}{padded_title}{CLR_BLUE} │\n")
            sys.stdout.write("└" + "─" * (border_len - 2) + f"┘{CLR_RESET}\n\n")
            
            # Print choices
            for idx, choice in enumerate(choices):
                if idx == current_idx:
                    sys.stdout.write(f" {CLR_BOLD}{CLR_GREEN}➔  {choice}{CLR_RESET}\n")
                else:
                    sys.stdout.write(f"    {CLR_GRAY}{choice}{CLR_RESET}\n")
            
            if show_help:
                sys.stdout.write(f"\n{CLR_GRAY}[Use ↑/↓ or 1-{num_choices} keys, Enter to select]{CLR_RESET}\n")
            
            sys.stdout.flush()
            
            key = read_key()
            if key is None:
                return None
            elif key == 'up':
                current_idx = (current_idx - 1) % num_choices
            elif key == 'down':
                current_idx = (current_idx + 1) % num_choices
            elif key == 'enter':
                clear_screen()
                return current_idx
            elif key == 'esc':
                raise KeyboardInterrupt()
            elif len(key) == 1 and key.isdigit():
                val = int(key)
                if 1 <= val <= num_choices:
                    clear_screen()
                    return val - 1
    except (KeyboardInterrupt, EOFError):
        # Propagate interrupts
        raise
    except Exception:
        return None
    finally:
        # Show terminal cursor again
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
        print(f"\n{get_txt('no_history')}")
        return
        
    try:
        with open(history_file, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception as e:
        print(f"\n{get_txt('history_read_failed', e=e)}")
        return
        
    if not history:
        print(f"\n{get_txt('no_history')}")
        return
        
    print(f"\n====================== {get_txt('history_title')} ({len(history)} items) ======================")
    h_id = get_txt('history_header_id')
    h_fmt = get_txt('history_header_format')
    h_pgs = get_txt('history_header_pages')
    h_sz = get_txt('history_header_size')
    h_dt = get_txt('history_header_date')
    h_ttl = get_txt('history_header_title')
    print(f"{h_id:<10} | {h_fmt:<6} | {h_pgs:<4} | {h_sz:<11} | {h_dt:<19} | {h_ttl}")
    print("-" * 90)
    for item in history:
        size_mb = item.get("file_size_bytes", 0) / (1024 * 1024)
        title_short = item.get("title", "")
        if len(title_short) > 35:
            title_short = title_short[:32] + "..."
        print(f"{item.get('id'):<10} | {item.get('format'):<6} | {item.get('pages'):<4} | {size_mb:<11.2f} | {item.get('download_date'):<19} | {title_short}")
    print("================================================================================")

def view_changelog():
    """Displays the project changelog in the selected language."""
    print(f"\n================ {get_txt('changelog_title')} ================")
    print(get_txt('changelog_body'))
    print("=================================================================")

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
        
    print("\n--- MANUAL DOWNLOAD ---")
    item = input(get_txt('manual_prompt_id')).strip()
    if not item:
        print(get_txt('manual_empty_input'))
        return
        
    manga_id = extract_manga_id(item)
    if not manga_id:
        print(get_txt('manual_invalid_format'))
        return
        
    # Skip check
    existing = check_existing_download(manga_id, output_dir=output_dir)
    if existing:
        print(f"\n" + get_txt('smart_skip_message', manga_id=manga_id, filename=os.path.basename(existing)))
        lang = load_config().get("language", "en")
        yes_txt = {"en": "Yes", "id": "Ya", "zh": "是", "ja": "はい"}.get(lang, "Yes")
        no_txt = {"en": "No", "id": "Tidak", "zh": "否", "ja": "いいえ"}.get(lang, "No")
        
        skip_prompt_title = get_txt('manual_skip_prompt', manga_id=manga_id, filename=os.path.basename(existing)).replace("(y/N):", "").strip()
        skip_choices = [yes_txt, no_txt]
        skip_idx = interactive_select(skip_prompt_title, skip_choices)
        if skip_idx is not None:
            re_download = (skip_idx == 0)
        else:
            choice = input(get_txt('manual_skip_prompt', manga_id=manga_id, filename=os.path.basename(existing))).strip().lower()
            re_download = (choice == 'y')
            
        if not re_download:
            print(get_txt('manual_download_cancelled'))
            return
            
    format_choices = [
        "PDF (default)",
        "CBZ"
    ]
    fmt_idx = interactive_select(get_txt('prompt_format').upper(), format_choices)
    if fmt_idx is not None:
        file_format = "cbz" if fmt_idx == 1 else "pdf"
    else:
        print("\n" + get_txt('prompt_format'))
        print("[1] PDF (default)")
        print("[2] CBZ")
        fmt_choice = input(get_txt('prompt_choice') + ": ").strip()
        file_format = "cbz" if fmt_choice == "2" else "pdf"
    
    print(f"\n" + get_txt('manual_download_starting', manga_id=manga_id))
    try:
        out_path, title, pages = process_manga_download(manga_id, output_dir=output_dir, file_format=file_format, threads=threads, compress=compress, compress_quality=compress_quality)
        add_to_history(manga_id, title, file_format, pages, out_path)
        print(f"\n" + get_txt('manual_download_success', out_path=out_path))
    except Exception as e:
        print(f"\n" + get_txt('manual_download_failed', e=e))

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
        print("\n================ LANGUAGE SETUP ================")
        print("Please choose your language / Silakan pilih bahasa Anda:")
        for idx, lang in enumerate(lang_choices, 1):
            print(f"{idx}. {lang}")
        print("=================================================")
        lang_choice = input("Choice (1-4): ").strip()
        lang_map = {"1": "en", "2": "id", "3": "zh", "4": "ja"}
        selected_lang = lang_map.get(lang_choice, "en")
    
    config = load_config()
    config["language"] = selected_lang
    save_config(config)
    print(f"Language set to: {selected_lang.upper()}\n")

def setup_threads_selection():
    """Renders the thread configuration screen and updates the settings."""
    config = load_config()
    default_threads = config.get("threads", 4)
    
    print(f"\n================ {get_txt('menu_option_threads', threads=default_threads).upper()} ================")
    try:
        prompt_msg = get_txt('prompt_threads', default=default_threads)
        val = input(prompt_msg).strip()
        if not val:
            threads = default_threads
        else:
            threads = int(val)
            if threads < 1 or threads > 32:
                raise ValueError()
    except ValueError:
        print(get_txt('invalid_threads'))
        return
        
    config["threads"] = threads
    save_config(config)
    print(get_txt('threads_updated', threads=threads))

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
        print(f"\n================ {get_txt('menu_option_compress', state=current_state_str, quality=default_quality).upper()} ================")
        toggle_val = input(get_txt('prompt_compress_toggle')).strip().lower()
        if not toggle_val:
            compress = default_compress
        else:
            compress = toggle_val == 'y'
        
    quality = default_quality
    if compress:
        try:
            quality_msg = get_txt('prompt_compress_quality', default=default_quality)
            quality_val = input(quality_msg).strip()
            if not quality_val:
                quality = default_quality
            else:
                quality = int(quality_val)
                if quality < 1 or quality > 100:
                    raise ValueError()
        except ValueError:
            print(get_txt('invalid_compress_quality'))
            return
            
    config["compress"] = compress
    config["compress_quality"] = quality
    save_config(config)
    
    state_txt = "ON" if compress else "OFF"
    print(get_txt('compress_updated', state=state_txt, quality=quality))

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
