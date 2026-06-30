import os
import json

LOCALES = {
    "en": {
        "menu_title": "NHENTAI DOWNLOADER",
        "menu_option_batch": "Run batch downloads from download_list.txt",
        "menu_option_manual": "Manual download (Enter ID/URL)",
        "menu_option_history": "View download history",
        "menu_option_language": "Change language",
        "menu_option_changelog": "View changelog",
        "menu_option_exit": "Exit",
        "prompt_choice": "Your choice (1-8)",
        "prompt_format": "Choose Output Format:",
        "prompt_format_batch": "Choose Batch Output Format:",
        "invalid_choice": "Invalid choice. Please enter a valid number.",
        "goodbye": "Thank you for using this application. Goodbye!",
        "no_history": "No download history found.",
        "history_read_failed": "Failed to read download history: {e}",
        "history_title": "DOWNLOAD HISTORY",
        "history_header_id": "ID",
        "history_header_format": "Format",
        "history_header_pages": "Pgs",
        "history_header_size": "Size (MB)",
        "history_header_date": "Download Date",
        "history_header_title": "Title",
        "manual_prompt_id": "Enter manga ID or nHentai URL: ",
        "manual_empty_input": "Cancelled. Input cannot be empty.",
        "manual_invalid_format": "Invalid URL or ID format.",
        "smart_skip_message": "[Smart Skip] Manga ID {manga_id} already downloaded: '{filename}'. Skipping.",
        "manual_skip_prompt": "[Smart Skip] Manga ID {manga_id} already downloaded: '{filename}'.\nDo you want to download it again anyway? (y/N): ",
        "manual_download_cancelled": "Download cancelled (skipped).",
        "manual_download_starting": "Starting download for ID {manga_id}...",
        "manual_download_success": "Success! File saved at: {out_path}",
        "manual_download_failed": "Failed to download: {e}",
        "batch_template_created": "File '{list_file}' was just created. Please populate it with manga IDs/URLs, then run this program again.",
        "batch_found_manga": "Found {count} manga in the download queue.",
        "batch_invalid_line": "Invalid format or ID not found on line: '{item}'",
        "batch_failed_to_download_manga": "Failed to download manga ID {manga_id}: {e}. Added to retry queue at end of session.",
        "batch_retry_starting": "Starting auto-retry for {count} failed items...",
        "batch_retry_success": "Successfully downloaded manga ID {manga_id} on retry!",
        "batch_retry_failed": "Failed to download manga ID {manga_id} after retry: {e}",
        "batch_process_finished": "Batch Downloader Process Finished!",
        "batch_summary": "Successfully Downloaded: {success_count} | Permanently Failed: {failed_count}",
        "batch_failures_logged": "There are {count} permanently failed items. Details recorded in '{failed_file}'",
        "menu_option_threads": "Change thread count (Current: {threads})",
        "prompt_threads": "Enter number of threads (1-32) [Default: {default}]: ",
        "invalid_threads": "Invalid number of threads. Please enter a number between 1 and 32.",
        "threads_updated": "Thread count updated to {threads}.",
        "menu_option_compress": "Toggle image compression (Current: {state}, Quality: {quality}%)",
        "prompt_compress_toggle": "Enable smart image compression? (y/N): ",
        "prompt_compress_quality": "Enter compression quality (1-100) [Default: {default}]: ",
        "invalid_compress_quality": "Invalid quality value. Please enter a number between 1 and 100.",
        "compress_updated": "Compression settings updated. Enabled: {state}, Quality: {quality}%",
        
        # Downloader logs
        "downloader_starting": "Starting download: '{manga_title}' ({num_pages} pages)",
        "downloader_cdns": "Using CDNs: {servers}",
        "downloader_sequential": "Starting sequential downloads (1 thread) to maximize bandwidth stability...",
        "downloader_threads": "Starting parallel downloads ({threads} threads)...",
        "downloader_all_downloaded": "All pages already downloaded. Preparing compilation...",
        "downloader_compiling_cbz": "Compiling CBZ to '{path}'...",
        "downloader_compiling_pdf": "Compiling PDF to '{path}'...",
        "downloader_success": "Successfully downloaded and created: '{filename}'",
        
        # Changelog
        "changelog_title": "PROJECT CHANGELOG (Version v0.7)",
        "changelog_body": (
            "- Added Smart Image Compression (Lossless PNG and lossy JPEG quality configurations).\n"
            "- Added High-Speed Multi-threaded download support.\n"
            "- Added Configurable download threads via CLI settings.\n"
            "- Added Interactive CLI Menu dashboard.\n"
            "- Added Multi-language localization support (English, Indonesian, Chinese, Japanese).\n"
            "- Added Output Format Selection: Compile downloads to PDF or CBZ (Comic Book Zip).\n"
            "- Added Smart Skip: Automatically skip already downloaded manga IDs.\n"
            "- Added Crash Session Recovery: Resume incomplete downloads from cached pages.\n"
            "- Added Download History Tracker: View previous download records directly in CLI.\n"
            "- Added Auto-Retry Failed Queue: Re-run failed downloads at the end of a session.\n"
            "- Upgraded DNS bypass mechanism to use DNS-over-HTTPS (DoH) with multi-resolver fallback.\n"
            "- Updated output filename format to '[ID] Title.ext'."
        )
    },
    "id": {
        "menu_title": "DOWNLOADER NHENTAI",
        "menu_option_batch": "Jalankan unduhan massal dari download_list.txt",
        "menu_option_manual": "Unduh manga manual (Masukkan ID/URL)",
        "menu_option_history": "Lihat riwayat unduhan",
        "menu_option_language": "Ubah bahasa",
        "menu_option_changelog": "Lihat riwayat pembaruan (Changelog)",
        "menu_option_exit": "Keluar",
        "prompt_choice": "Pilihan Anda (1-8)",
        "prompt_format": "Pilih Format Output:",
        "prompt_format_batch": "Pilih Format Output untuk Batch:",
        "invalid_choice": "Pilihan tidak valid. Silakan masukkan angka yang valid.",
        "goodbye": "Terima kasih telah menggunakan aplikasi ini. Sampai jumpa!",
        "no_history": "Belum ada riwayat unduhan.",
        "history_read_failed": "Gagal membaca riwayat unduhan: {e}",
        "history_title": "RIWAYAT UNDUHAN",
        "history_header_id": "ID",
        "history_header_format": "Format",
        "history_header_pages": "Hal",
        "history_header_size": "Ukuran (MB)",
        "history_header_date": "Tanggal Unduh",
        "history_header_title": "Judul",
        "manual_prompt_id": "Masukkan ID manga atau URL nHentai: ",
        "manual_empty_input": "Batal. Input tidak boleh kosong.",
        "manual_invalid_format": "Format URL atau ID tidak valid.",
        "smart_skip_message": "[Smart Skip] Manga ID {manga_id} sudah pernah diunduh: '{filename}'. Melewati.",
        "manual_skip_prompt": "[Smart Skip] Manga ID {manga_id} sudah pernah diunduh: '{filename}'.\nApakah Anda ingin tetap mengunduh ulang? (y/N): ",
        "manual_download_cancelled": "Pengunduhan dibatalkan (skip).",
        "manual_download_starting": "Memulai pengunduhan untuk ID {manga_id}...",
        "manual_download_success": "Sukses! Berkas disimpan di: {out_path}",
        "manual_download_failed": "Gagal mengunduh: {e}",
        "batch_template_created": "File '{list_file}' baru saja dibuat. Silakan isi file tersebut dengan daftar manga, lalu jalankan kembali program ini.",
        "batch_found_manga": "Ditemukan {count} manga dalam antrean unduhan.",
        "batch_invalid_line": "Format tidak valid atau ID tidak ditemukan pada baris: '{item}'",
        "batch_failed_to_download_manga": "Gagal mengunduh manga ID {manga_id}: {e}. Dimasukkan ke antrean retry di akhir sesi.",
        "batch_retry_starting": "Memulai auto-retry otomatis untuk {count} item yang sempat gagal...",
        "batch_retry_success": "Sukses mengunduh manga ID {manga_id} pada percobaan retry!",
        "batch_retry_failed": "Tetap gagal mengunduh manga ID {manga_id} setelah retry: {e}",
        "batch_process_finished": "Proses Batch Downloader Selesai!",
        "batch_summary": "Sukses diunduh: {success_count} | Gagal Permanen: {failed_count}",
        "batch_failures_logged": "Ada {count} item yang gagal permanen. Detail kegagalan dicatat di file '{failed_file}'",
        "menu_option_threads": "Ubah jumlah thread (Saat ini: {threads})",
        "prompt_threads": "Masukkan jumlah thread (1-32) [Default: {default}]: ",
        "invalid_threads": "Jumlah thread tidak valid. Silakan masukkan angka antara 1 dan 32.",
        "threads_updated": "Jumlah thread diperbarui menjadi {threads}.",
        "menu_option_compress": "Ubah kompresi gambar (Saat ini: {state}, Kualitas: {quality}%)",
        "prompt_compress_toggle": "Aktifkan kompresi gambar pintar? (y/N): ",
        "prompt_compress_quality": "Masukkan kualitas kompresi (1-100) [Default: {default}]: ",
        "invalid_compress_quality": "Nilai kualitas tidak valid. Silakan masukkan angka antara 1 dan 100.",
        "compress_updated": "Pengaturan kompresi diperbarui. Aktif: {state}, Kualitas: {quality}%",
        
        # Downloader logs
        "downloader_starting": "Memulai unduhan: '{manga_title}' ({num_pages} halaman)",
        "downloader_cdns": "Menggunakan CDN: {servers}",
        "downloader_sequential": "Memulai unduhan sekuensial (1 thread) untuk kestabilan bandwidth maksimal...",
        "downloader_threads": "Memulai unduhan paralel ({threads} thread)...",
        "downloader_all_downloaded": "Semua halaman sudah terunduh. Mempersiapkan kompilasi...",
        "downloader_compiling_cbz": "Mengompilasi CBZ ke '{path}'...",
        "downloader_compiling_pdf": "Mengompilasi PDF ke '{path}'...",
        "downloader_success": "Sukses mengunduh dan membuat: '{filename}'",
        
        # Changelog
        "changelog_title": "RIWAYAT PEMBARUAN PROYEK (Versi v0.7)",
        "changelog_body": (
            "- Menambahkan fitur Kompresi Gambar Pintar (PNG lossless & JPEG dengan konfigurasi kualitas).\n"
            "- Menambahkan dukungan unduhan Multi-thread Berkecepatan Tinggi.\n"
            "- Menambahkan pengaturan jumlah thread unduhan yang dapat dikonfigurasi lewat CLI.\n"
            "- Menambahkan antarmuka Menu CLI interaktif.\n"
            "- Menambahkan dukungan lokalisasi Multi-bahasa (Inggris, Indonesia, Cina, Jepang).\n"
            "- Menambahkan Pilihan Format Output: Simpan hasil unduhan dalam format PDF atau CBZ.\n"
            "- Menambahkan Smart Skip: Melewati komik yang sudah pernah diunduh secara otomatis.\n"
            "- Menambahkan Crash Session Recovery: Melanjutkan unduhan yang terputus dari halaman sisa.\n"
            "- Menambahkan Riwayat Unduhan: Melihat catatan riwayat unduhan sukses di CLI.\n"
            "- Menambahkan Auto-Retry Antrean Gagal: Mencoba ulang unduhan yang gagal di akhir sesi.\n"
            "- Peningkatan bypass pemblokiran DNS menggunakan DNS-over-HTTPS (DoH) dengan resolver bertingkat.\n"
            "- Pembaruan format nama file keluaran menjadi '[ID] Title.ext'."
        )
    },
    "zh": {
        "menu_title": "NHENTAI 下载器",
        "menu_option_batch": "运行 download_list.txt 中的批量下载",
        "menu_option_manual": "手动下载（输入 ID/URL）",
        "menu_option_history": "查看下载历史",
        "menu_option_language": "更改语言",
        "menu_option_changelog": "查看更新日志 (Changelog)",
        "menu_option_exit": "退出",
        "prompt_choice": "您的选择 (1-8)",
        "prompt_format": "选择输出格式：",
        "prompt_format_batch": "选择批量输出格式：",
        "invalid_choice": "选择无效。请输入有效数字。",
        "goodbye": "感谢您使用本程序。再见！",
        "no_history": "未找到下载历史。",
        "history_read_failed": "读取下载历史失败: {e}",
        "history_title": "下载历史",
        "history_header_id": "ID",
        "history_header_format": "格式",
        "history_header_pages": "页数",
        "history_header_size": "大小 (MB)",
        "history_header_date": "下载日期",
        "history_header_title": "标题",
        "manual_prompt_id": "请输入漫画 ID 或 nHentai 链接: ",
        "manual_empty_input": "已取消。输入不能为空。",
        "manual_invalid_format": "无效的链接或 ID 格式。",
        "smart_skip_message": "[智能跳过] 漫画 ID {manga_id} 已下载：'{filename}'。正在跳过。",
        "manual_skip_prompt": "[智能跳过] 漫画 ID {manga_id} 已下载：'{filename}'。\n您确定要重新下载吗？(y/N): ",
        "manual_download_cancelled": "下载已取消（跳过）。",
        "manual_download_starting": "正在启动 ID {manga_id} 的下载...",
        "manual_download_success": "成功！文件保存在: {out_path}",
        "manual_download_failed": "下载失败: {e}",
        "batch_template_created": "文件 '{list_file}' 已创建。请填写漫画 ID/链接，然后重新运行此程序。",
        "batch_found_manga": "在下载队列中找到 {count} 部漫画。",
        "batch_invalid_line": "格式无效或在此行未找到 ID: '{item}'",
        "batch_failed_to_download_manga": "下载漫画 ID {manga_id} 失败: {e}。已添加到会话结束时的重试队列中。",
        "batch_retry_starting": "正在为 {count} 个失败项目启动自动重试...",
        "batch_retry_success": "重试时成功下载漫画 ID {manga_id}！",
        "batch_retry_failed": "重试后下载漫画 ID {manga_id} 仍失败: {e}",
        "batch_process_finished": "批量下载进程已结束！",
        "batch_summary": "成功下载: {success_count} | 永久失败: {failed_count}",
        "batch_failures_logged": "有 {count} 个永久失败的项目。详情记录在 '{failed_file}'",
        "menu_option_threads": "更改线程数（当前：{threads}）",
        "prompt_threads": "输入线程数 (1-32) [默认: {default}]: ",
        "invalid_threads": "线程数无效。请输入 1 到 32 之间的数字。",
        "threads_updated": "线程数已更新为 {threads}。",
        "menu_option_compress": "更改图片压缩设置 (当前：{state}, 质量: {quality}%)",
        "prompt_compress_toggle": "是否启用智能图片压缩？(y/N): ",
        "prompt_compress_quality": "请输入压缩质量 (1-100) [默认: {default}]: ",
        "invalid_compress_quality": "压缩质量无效。请输入 1 到 100 之间的数字。",
        "compress_updated": "图片压缩设置已更新。启用：{state}, 质量：{quality}%",
        
        # Downloader logs
        "downloader_starting": "开始下载：'{manga_title}'（{num_pages} 页）",
        "downloader_cdns": "使用 CDN：{servers}",
        "downloader_sequential": "启动顺序下载（1 个线程）以最大化带宽稳定性...",
        "downloader_threads": "正在启动并行下载（{threads} 个线程）...",
        "downloader_all_downloaded": "所有页面均已下载。正在准备编译...",
        "downloader_compiling_cbz": "正在将 CBZ 编译为 '{path}'...",
        "downloader_compiling_pdf": "正在将 PDF 编译为 '{path}'...",
        "downloader_success": "成功下载并创建：'{filename}'",
        
        # Changelog
        "changelog_title": "项目更新日志 (版本 v0.6)",
        "changelog_body": (
            "- 增加了高速多线程下载支持。\n"
            "- 增加了可通过 CLI 设置配置的下载线程数。\n"
            "- 添加了交互式 CLI 菜单面板。\n"
            "- 添加了多语言本地化支持（英文、印尼文、中文、日文）。\n"
            "- 添加了输出格式选择：将下载内容编译为 PDF 或 CBZ 格式。\n"
            "- 添加了智能跳过：自动跳过已下载的漫画 ID。\n"
            "- 添加了崩溃会话恢复：从缓存页面恢复未完成的下载。\n"
            "- 添加了下载历史记录器：直接在 CLI 中查看以前的下载记录。\n"
            "- 添加了自动重试失败队列：在会话结束时重新运行失败的下载。\n"
            "- 升级了 DNS 绕过机制，以使用具有多解析器回退的 DNS-over-HTTPS (DoH)。\n"
            "- 更新了输出文件名格式为 '[ID] Title.ext'。"
        )
    },
    "ja": {
        "menu_title": "NHENTAI ダウンローダー",
        "menu_option_batch": "download_list.txt から一括ダウンロードを実行",
        "menu_option_manual": "手動ダウンロード（ID/URLを入力）",
        "menu_option_history": "ダウンロード履歴を表示",
        "menu_option_language": "言語の変更",
        "menu_option_changelog": "更新履歴を表示 (Changelog)",
        "menu_option_exit": "Exit",
        "prompt_choice": "あなたの選択 (1-8)",
        "prompt_format": "出力形式 of 選択：",
        "prompt_format_batch": "一括出力形式の選択：",
        "invalid_choice": "選択が無効です。有効な数字を入力してください。",
        "goodbye": "本プログラムをご利用いただきありがとうございました。さようなら！",
        "no_history": "ダウンロード履歴が見つかりません。",
        "history_read_failed": "ダウンロード履歴の読み込みに失敗しました: {e}",
        "history_title": "ダウンロード履歴",
        "history_header_id": "ID",
        "history_header_format": "形式",
        "history_header_pages": "ページ数",
        "history_header_size": "サイズ (MB)",
        "history_header_date": "ダウンロード日時",
        "history_header_title": "タイトル",
        "manual_prompt_id": "漫画IDまたはnHentaiのURLを入力してください: ",
        "manual_empty_input": "キャンセルされました。入力は空にできません。",
        "manual_invalid_format": "無効なURLまたはIDの形式です。",
        "smart_skip_message": "[スマートスキップ] 漫画ID {manga_id} は既にダウンロードされています: '{filename}'。スキップします。",
        "manual_skip_prompt": "[スマートスキップ] 漫画ID {manga_id} は既にダウンロードされています: '{filename}'。\nそれでも再ダウンロードしますか？(y/N): ",
        "manual_download_cancelled": "ダウンロードがキャンセルされました（スキップ）。",
        "manual_download_starting": "ID {manga_id} のダウンロードを開始します...",
        "manual_download_success": "成功しました！ファイルは {out_path} に保存されました",
        "manual_download_failed": "ダウンロードに失敗しました: {e}",
        "batch_template_created": "ファイル '{list_file}' が作成されました。漫画IDまたはURLを入力し、このプログラムを再実行してください。",
        "batch_found_manga": "ダウンロードキューに {count} 作品 of 漫画が見つかりました。",
        "batch_invalid_line": "無効な形式または行にIDが見つかりません: '{item}'",
        "batch_failed_to_download_manga": "漫画ID {manga_id} のダウンロードに失敗しました: {e}。セッション終了時のリトライキューに追加されました。",
        "batch_retry_starting": "{count} 件の失敗したアイテムの自動リトライを開始します...",
        "batch_retry_success": "リトライで漫画ID {manga_id} のダウンロードに成功しました！",
        "batch_retry_failed": "リトライ後も漫画ID {manga_id} のダウンロードに失敗しました: {e}",
        "batch_process_finished": "一括ダウンロード処理が完了しました！",
        "batch_summary": "ダウンロード成功: {success_count} | 永久的な失敗: {failed_count}",
        "batch_failures_logged": "永久に失敗したアイテムが {count} 件あります。詳細は '{failed_file}' に記録されています",
        "menu_option_threads": "スレッド数の変更（現在：{threads}）",
        "prompt_threads": "スレッド数を入力してください (1-32) [デフォルト: {default}]: ",
        "invalid_threads": "無効なスレッド数です。1から32の間の数字を入力してください。",
        "threads_updated": "スレッド数を {threads} に更新しました。",
        "menu_option_compress": "画像圧縮設定の変更 (現在：{state}, 画質: {quality}%)",
        "prompt_compress_toggle": "スマート画像圧縮を有効にしますか？(y/N): ",
        "prompt_compress_quality": "圧縮品質を入力してください (1-100) [デフォルト: {default}]: ",
        "invalid_compress_quality": "無効な画質設定です。1から100の間の数字を入力してください。",
        "compress_updated": "画像圧縮設定を更新しました。有効：{state}, 画質：{quality}%",
        
        # Downloader logs
        "downloader_starting": "ダウンロードを開始：'{manga_title}'（{num_pages} ページ）",
        "downloader_cdns": "CDNを使用中：{servers}",
        "downloader_sequential": "帯域幅の安定性を最大化するため、シーケンシャルダウンロード（1スレッド）を開始します...",
        "downloader_threads": "並行ダウンロードを開始します ({threads} スレッド)...",
        "downloader_all_downloaded": "全ページがすでにダウンロードされています。コンパイルの準備中...",
        "downloader_compiling_cbz": "CBZを '{path}' にコンパイル中...",
        "downloader_compiling_pdf": "PDFを '{path}' にコンパイル中...",
        "downloader_success": "ダウンロードと作成に成功しました：'{filename}'",
        
        # Changelog
        "changelog_title": "プロジェクト更新履歴 (バージョン v0.6)",
        "changelog_body": (
            "- 高速マルチスレッドダウンロードのサポートを追加しました。\n"
            "- CLI設定から設定可能なダウンロードスレッド数を追加しました。\n"
            "- 対話型 CLI メニュー ダッシュボードを追加しました。\n"
            "- 多言語ローカリゼーション サポート（英語、インドネシア語、中国語、日本語）を追加しました。\n"
            "- 出力形式の選択を追加しました：PDF または CBZ 形式で保存可能。\n"
            "- スマートスキップを追加しました：ダウンロード済みの漫画IDを自動的にスキップ。\n"
            "- クラッシュセッション回復を追加しました：キャッシュページから未完了のダウンロードを再開。\n"
            "- ダウンロード履歴トラッカーを追加しました：CLI 内で以前のダウンロード履歴を表示。\n"
            "- 失敗キューの自動リトライを追加しました：セッション終了時に失敗したダウンロードを再実行。\n"
            "- 複数のリゾルバーによるDNS-over-HTTPS (DoH) を使用するように DNS バイパスをアップグレードしました。\n"
            "- 出力ファイル名の形式を「[ID] Title.ext」に更新しました。"
        )
    }
}

def load_config():
    """Loads configuration from config.json, defaulting to English, 4 threads, and disabled compression."""
    config_file = "config.json"
    default_config = {"language": "en", "threads": 4, "compress": False, "compress_quality": 85}
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)
                for k, v in default_config.items():
                    if k not in config:
                        config[k] = v
                return config
        except Exception:
            pass
    return default_config

def save_config(config):
    """Saves configuration to config.json."""
    config_file = "config.json"
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        pass

def get_txt(key, **kwargs):
    """Fetches localized string based on configured language and formats it."""
    config = load_config()
    lang = config.get("language", "en")
    text = LOCALES.get(lang, LOCALES["en"]).get(key, LOCALES["en"].get(key, ""))
    if kwargs:
        return text.format(**kwargs)
    return text
