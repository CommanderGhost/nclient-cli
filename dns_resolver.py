import socket
import logging
import json
import urllib.request
import threading

# Logger configuration
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("DNSResolver")

# Cache to store resolved IPs and avoid duplicate queries
_dns_cache = {}
_dns_lock = threading.Lock()
_original_getaddrinfo = socket.getaddrinfo

def resolve_doh_cloudflare(host):
    """Resolves host using Cloudflare DNS-over-HTTPS JSON API."""
    url = f"https://cloudflare-dns.com/dns-query?name={host}&type=A"
    req = urllib.request.Request(url, headers={"accept": "application/dns-json"})
    with urllib.request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read().decode("utf-8"))
        answers = data.get("Answer", [])
        # Filter for A records (type 1)
        ips = [ans["data"] for ans in answers if ans.get("type") == 1]
        return ips

def resolve_doh_google(host):
    """Resolves host using Google DNS-over-HTTPS JSON API."""
    url = f"https://dns.google/resolve?name={host}&type=A"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read().decode("utf-8"))
        answers = data.get("Answer", [])
        # Filter for A records (type 1)
        ips = [ans["data"] for ans in answers if ans.get("type") == 1]
        return ips

def resolve_doh_adguard(host):
    """Resolves host using AdGuard DNS-over-HTTPS JSON API."""
    url = f"https://dns.adguard-dns.com/resolve?name={host}&type=A"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as response:
        data = json.loads(response.read().decode("utf-8"))
        answers = data.get("Answer", [])
        # Filter for A records (type 1)
        ips = [ans["data"] for ans in answers if ans.get("type") == 1]
        return ips

def resolve_host_doh(host):
    """Attempts resolving host using Cloudflare DoH, then Google DoH, then AdGuard DoH."""
    try:
        ips = resolve_doh_cloudflare(host)
        if ips:
            return ips
    except Exception as e:
        logger.debug(f"[DNS Bypass] Cloudflare DoH failed for '{host}': {e}. Trying Google DoH...")
    
    try:
        ips = resolve_doh_google(host)
        if ips:
            return ips
    except Exception as e:
        logger.debug(f"[DNS Bypass] Google DoH failed for '{host}': {e}. Trying AdGuard DoH...")
        
    try:
        ips = resolve_doh_adguard(host)
        if ips:
            return ips
    except Exception as e:
        logger.debug(f"[DNS Bypass] AdGuard DoH failed for '{host}': {e}")
    
    return []

def patched_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    """
    Patched version of socket.getaddrinfo that intercepts resolution requests for nhentai domains
    and queries Cloudflare/Google DNS-over-HTTPS (DoH) to bypass ISP DNS blockades.
    """
    if host and ("nhentai.net" in host or "nhentai.org" in host):
        with _dns_lock:
            if host not in _dns_cache:
                try:
                    ips = resolve_host_doh(host)
                    if ips:
                        _dns_cache[host] = ips[0]
                        logger.debug(f"[DNS Bypass] Resolved '{host}' -> '{_dns_cache[host]}' via DNS-over-HTTPS (DoH)")
                    else:
                        logger.warning(f"[DNS Bypass] DoH resolution returned no IPs for '{host}'. Using system default DNS.")
                except Exception as e:
                    logger.warning(f"[DNS Bypass] DoH resolution failed for '{host}': {e}. Using system default DNS.")
        
        if host in _dns_cache:
            # Direct socket connection to the resolved IP while keeping the original port
            return _original_getaddrinfo(_dns_cache[host], port, family, type, proto, flags)
            
    # Default fallback for other domains or if resolution failed
    return _original_getaddrinfo(host, port, family, type, proto, flags)

def setup_dns():
    """Applies the socket monkey patch to bypass DNS blocking."""
    socket.getaddrinfo = patched_getaddrinfo
    logger.info("[DNS Bypass] Custom DNS-over-HTTPS Resolver activated.")

