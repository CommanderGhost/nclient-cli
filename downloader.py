import os
import re
import time
import shutil
import logging
import requests
import img2pdf
from tqdm import tqdm
from locales import get_txt

logger = logging.getLogger("Downloader")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://nhentai.net/"
}

def extract_manga_id(url_or_id):
    """Extracts the numeric manga ID from a full nHentai URL or a raw ID string."""
    clean_str = str(url_or_id).strip()
    # Match pattern like /g/123456/
    match = re.search(r'/g/(\d+)', clean_str)
    if match:
        return match.group(1)
    if clean_str.isdigit():
        return clean_str
    return None

def sanitize_filename(name):
    """Sanitizes strings to be safe for Windows file paths."""
    sanitized = re.sub(r'[\\/*?:"<>|]', "", name)
    # Remove leading/trailing spaces and limit length to avoid path length limits
    return sanitized.strip()[:150]

def fetch_manga_metadata(manga_id, max_retries=3):
    """Fetches manga metadata from nHentai JSON API v2 with retry mechanism."""
    url = f"https://nhentai.net/api/v2/galleries/{manga_id}"
    backoff = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Fetching metadata for ID {manga_id} (Attempt {attempt}/{max_retries})...")
            response = requests.get(url, headers=HEADERS, timeout=15)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                logger.error(f"Manga with ID {manga_id} not found (404).")
                return None
            else:
                logger.warning(f"Unexpected status code {response.status_code} for ID {manga_id}.")
        except Exception as e:
            logger.warning(f"Network error on attempt {attempt} for ID {manga_id}: {e}")
        
        if attempt < max_retries:
            time.sleep(backoff)
            backoff *= 2
    return None

def fetch_cdn_servers(max_retries=3):
    """Fetches list of active image CDN servers from nHentai API v2."""
    url = "https://nhentai.net/api/v2/cdn"
    backoff = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"Fetching CDN servers list (Attempt {attempt}/{max_retries})...")
            response = requests.get(url, headers=HEADERS, timeout=15)
            if response.status_code == 200:
                data = response.json()
                servers = data.get("image_servers", [])
                if servers:
                    return servers
            else:
                logger.warning(f"Unexpected status code {response.status_code} for CDN configuration.")
        except Exception as e:
            logger.warning(f"Network error on fetching CDN config on attempt {attempt}: {e}")
        
        if attempt < max_retries:
            time.sleep(backoff)
            backoff *= 2
    return ["https://i3.nhentai.net", "https://i.nhentai.net"]  # fallback servers

def compress_image(image_path, quality=85):
    """Compresses a single image file using Pillow to reduce file size."""
    tmp_path = image_path + ".tmp"
    try:
        from PIL import Image
        with Image.open(image_path) as img:
            fmt = img.format
            if fmt == "PNG":
                img.save(tmp_path, format="PNG", optimize=True)
            elif fmt == "WEBP":
                img.save(tmp_path, format="WEBP", quality=quality, optimize=True)
            else:
                # Handle images with transparency (RGBA, LA, or P with transparency info) safely for JPEG format
                if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    if img.mode == "RGBA":
                        bg.paste(img, mask=img.split()[3])
                    elif img.mode == "LA":
                        bg.paste(img, mask=img.split()[1])
                    else:
                        bg.paste(img.convert("RGBA"), mask=img.convert("RGBA").split()[3])
                    bg.save(tmp_path, format="JPEG", quality=quality, optimize=True)
                else:
                    if img.mode != "RGB" and img.mode != "L":
                        img = img.convert("RGB")
                    img.save(tmp_path, format="JPEG", quality=quality, optimize=True)
        # Replace original file with compressed tmp file
        if os.path.exists(tmp_path):
            os.replace(tmp_path, image_path)
    except Exception as e:
        logger.warning(f"Failed to compress image {image_path}: {e}")
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

def download_image(url, save_path, max_retries=5, compress=False, compress_quality=85):
    """Downloads a single image to the specified path with retries and optional compression."""
    backoff = 2.0
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            if response.status_code == 200:
                with open(save_path, 'wb') as f:
                    f.write(response.content)
                if compress:
                    compress_image(save_path, quality=compress_quality)
                return True
            else:
                logger.warning(f"Failed download {url} (Attempt {attempt}/{max_retries}). Status: {response.status_code}")
        except Exception as e:
            logger.warning(f"Exception downloading {url} (Attempt {attempt}/{max_retries}): {e}")
        
        if attempt < max_retries:
            time.sleep(backoff)
            backoff *= 2
    return False

def check_existing_download(manga_id, output_dir="downloads"):
    """Checks if a PDF or CBZ for this manga ID already exists in the output directory."""
    if not os.path.exists(output_dir):
        return None
    prefix = f"[{manga_id}]"
    for filename in os.listdir(output_dir):
        if filename.startswith(prefix) and (filename.endswith(".pdf") or filename.endswith(".cbz")):
            return os.path.join(output_dir, filename)
    return None

def process_manga_download(manga_id, output_dir="downloads", file_format="pdf", threads=1, compress=False, compress_quality=85):
    """
    Handles the complete flow for a single manga ID:
    Fetches metadata -> Downloads images to temp folder (resumable) -> Compiles to PDF/CBZ -> Cleans up temp.
    """
    metadata = fetch_manga_metadata(manga_id)
    if not metadata:
        raise Exception("Failed to retrieve manga metadata.")

    media_id = metadata.get("media_id")
    title_dict = metadata.get("title", {})
    # Use English or Pretty title, fallback to ID if empty
    manga_title = title_dict.get("english") or title_dict.get("pretty") or f"manga_{manga_id}"
    safe_title = sanitize_filename(manga_title)
    
    # API v2 has pages directly at root level
    pages = metadata.get("pages", [])
    num_pages = len(pages)
    
    if not media_id or not pages:
        raise Exception("Manga data is incomplete or corrupted.")

    logger.info(get_txt('downloader_starting', manga_title=manga_title, num_pages=num_pages))
    
    # Setup directories
    os.makedirs(output_dir, exist_ok=True)
    temp_dir = os.path.join(output_dir, f"temp_{manga_id}")
    os.makedirs(temp_dir, exist_ok=True)

    downloaded_files = []
    
    # Download pages concurrently with progress bar
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    cdn_servers = fetch_cdn_servers()
    logger.info(get_txt('downloader_cdns', servers=cdn_servers))
    
    tasks = []
    for idx, page in enumerate(pages):
        page_num = idx + 1
        relative_path = page.get("path")
        if not relative_path:
            raise Exception(f"Page {page_num} missing relative image path.")
            
        _, ext = os.path.splitext(relative_path)
        if not ext:
            ext = ".jpg"
            
        cdn_base = cdn_servers[idx % len(cdn_servers)].rstrip("/")
        img_url = f"{cdn_base}/{relative_path.lstrip('/')}"
        
        file_name = f"{page_num:03d}{ext}"
        save_path = os.path.join(temp_dir, file_name)
        
        # Check if file already exists in temp directory (Crash Recovery)
        if os.path.exists(save_path) and os.path.getsize(save_path) > 100:
            downloaded_files.append(save_path)
            continue
            
        tasks.append((img_url, save_path, page_num, compress, compress_quality))

    # If there are pages to download
    if tasks:
        if threads > 1:
            logger.info(get_txt('downloader_threads', threads=threads))
        else:
            logger.info(get_txt('downloader_sequential'))
        initial_count = len(pages) - len(tasks)
        with ThreadPoolExecutor(max_workers=threads) as executor:
            future_to_page = {
                executor.submit(download_image, img_url, save_path, compress=compress, compress_quality=compress_quality): (img_url, save_path, page_num)
                for img_url, save_path, page_num, compress, compress_quality in tasks
            }
            
            with tqdm(total=len(pages), initial=initial_count, desc="Downloading", bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}") as pbar:
                for future in as_completed(future_to_page):
                    img_url, save_path, page_num = future_to_page[future]
                    try:
                        success = future.result()
                        if not success:
                            raise Exception(f"Failed to download page {page_num} after retries from {img_url}.")
                        downloaded_files.append(save_path)
                        pbar.update(1)
                    except Exception as e:
                        # Cancel other pending futures on error
                        for f in future_to_page:
                            f.cancel()
                        raise e
    else:
        logger.info(get_txt('downloader_all_downloaded'))
        
    # Convert images to PDF or CBZ
    file_format = file_format.lower()
    if file_format not in ["pdf", "cbz"]:
        file_format = "pdf"
        
    filename = f"[{manga_id}] {safe_title}.{file_format}"
    output_path = os.path.join(output_dir, filename)
    
    # Sort files to ensure correct PDF/CBZ ordering (sort numerically by page number)
    def get_page_num_key(file_path):
        base = os.path.basename(file_path)
        match = re.match(r'^(\d+)', base)
        return int(match.group(1)) if match else 0
    downloaded_files.sort(key=get_page_num_key)
    
    if file_format == "cbz":
        logger.info(get_txt('downloader_compiling_cbz', path=output_path))
        import zipfile
        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as cbz:
            for img_path in downloaded_files:
                cbz.write(img_path, arcname=os.path.basename(img_path))
    else:
        logger.info(get_txt('downloader_compiling_pdf', path=output_path))
        with open(output_path, "wb") as f:
            f.write(img2pdf.convert(downloaded_files))
        
    logger.info(get_txt('downloader_success', filename=filename))
    
    # Cleanup temporary files and folder ONLY on success
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
        
    return output_path, manga_title, num_pages
