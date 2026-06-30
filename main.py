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
        choice = input(get_txt('manual_skip_prompt', manga_id=manga_id, filename=os.path.basename(existing))).strip().lower()
        if choice != 'y':
            print(get_txt('manual_download_cancelled'))
            return
            
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
    print("\n================ LANGUAGE SETUP ================")
    print("Please choose your language / Silakan pilih bahasa Anda:")
    print("1. English (Default)")
    print("2. Indonesia")
    print("3. Chinese (中文)")
    print("4. Japanese (日本語)")
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
        
        print(f"\n================ {get_txt('menu_title')} ================")
        print(f"1. {get_txt('menu_option_batch')}")
        print(f"2. {get_txt('menu_option_manual')}")
        print(f"3. {get_txt('menu_option_history')}")
        print(f"4. {get_txt('menu_option_language')}")
        print(f"5. {get_txt('menu_option_threads', threads=current_threads)}")
        print(f"6. {get_txt('menu_option_compress', state=compress_state_str, quality=current_quality)}")
        print(f"7. {get_txt('menu_option_changelog')}")
        print(f"8. {get_txt('menu_option_exit')}")
        print("=====================================================")
        choice = input(f"{get_txt('prompt_choice')}: ").strip()
        
        if choice == "1":
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
        elif choice == "4":
            setup_language_selection()
        elif choice == "5":
            setup_threads_selection()
        elif choice == "6":
            setup_compress_selection()
        elif choice == "7":
            view_changelog()
        elif choice == "8":
            print("\n" + get_txt('goodbye'))
            break
        else:
            print("\n" + get_txt('invalid_choice'))

if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nProcess cancelled by user.")
        sys.exit(0)
