# nclient-cli

A robust, multi-threaded command-line interface (CLI) tool designed to batch download and compile comic/manga pages into single PDF or CBZ files. Featuring custom DNS fallback, resume capability, and intelligent image compression, it provides a high-speed, resilient download experience.

## Features

- 🚀 **Multi-threaded Downloads:** High-speed parallel downloading utilizing Python's `ThreadPoolExecutor`.
- 📁 **Auto-Compilation:** Automatically converts and bundles downloaded images into standard single-file **PDF** (lossless) or **CBZ** formats.
- ⚡ **DNS-over-HTTPS (DoH) Fallback:** Programmatic monkey-patching of the standard DNS resolution to bypass local ISP restrictions (Cloudflare, Google, and AdGuard DNS support) without system-wide VPN.
- 🔄 **Crash Session Recovery (Resumable):** Retains partially downloaded pages and skips already completed files, letting you resume downloads seamlessly.
- 🖼️ **Smart Image Compression:** Optional image preprocessing and compression (lossy JPEG optimization / lossless PNG compression) to save disk space while preserving visual quality.
- 🌍 **Localization Support:** Full console interface translation supporting English, Indonesian, Chinese (中文), and Japanese (日本語).
- 📊 **Download History Tracker:** Keeps a structured log of all successful downloads in a local JSON database.

## Installation

### Prerequisites
- Python 3.8 or higher
- Pip (Python Package Installer)

### Clone & Install
```bash
# Clone the repository
git clone https://github.com/CommanderGhost/nclient-cli.git
cd nclient-cli

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Interactive Menu
Simply run the main entry point to launch the interactive CLI:
```bash
python main.py
```
Use the menu options (1–8) to run batch downloads, configure settings, toggle compression, or view download history.

### CLI Flags (Non-Interactive)
Bypass the interactive menu and run commands directly using CLI arguments:

| Flag | Argument | Description |
|------|----------|-------------|
| `--batch` | None | Run batch downloads automatically using `download_list.txt` |
| `--id` | `[ID/URL]` | Download a specific comic/manga |
| `--format` | `pdf` / `cbz` | Set output compilation format (default: `pdf`) |
| `--threads` | `[int]` | Specify the number of concurrent download threads |
| `--compress` | None | Enable smart image compression |
| `--quality` | `[1-100]` | Set JPEG compression quality |

#### Examples:
```bash
# Download a single gallery into a CBZ file with 8 threads
python main.py --id 173013 --format cbz --threads 8

# Run batch download using list file with image compression active
python main.py --batch --compress --quality 80
```

## File Structure

- `main.py`: Main interactive CLI interface and command-line argument parser.
- `downloader.py`: Core downloader engine handling parallel asset retrieval, PDF/CBZ packaging, and crash recovery.
- `dns_resolver.py`: Custom monkey-patched DNS-over-HTTPS client socket wrapper.
- `locales.py`: Multilingual text manager and system settings reader (`config.json`).
- `requirements.txt`: Project package dependencies list.
- `download_list.txt`: List of target URLs or IDs to be batch-downloaded.

## License
MIT License
