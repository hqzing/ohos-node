#!/usr/bin/env python3
"""deploy-nodejs-dist.py -- one-shot self-hosted Node.js dist source deployer

Serves a dist source compatible with nodejs.org/dist for nvm, fnm, node-gyp
and similar tools.

Usage:
  ./deploy-nodejs-dist.py [output-dir]
  VERSIONS="v24.2.0 v24.3.0" ./deploy-nodejs-dist.py [output-dir]

  output-dir defaults to /var/www/html/dist (nginx 80 port web root).

Layout (compatible with nodejs.org/dist):
  <output-dir>/
  |-- index.html                # root browse page (static, CDN-friendly)
  |-- index.tab                 # version index (required by nvm ls-remote/install)
  |-- index.json                # JSON index (nvm-windows etc.)
  `-- v<version>/
      |-- index.html            # version browse page (size/sha256/download links)
      |-- node-v<ver>-<os>-<arch>.tar.xz     # OpenHarmony build xz
      |-- node-v<ver>-<os>-<arch>.tar.gz     # OpenHarmony build gz
      |-- node-v<ver>-headers.tar.xz/.tar.gz  # upstream headers (nodejs.org)
      `-- SHASUMS256.txt        # checksums (nvm compares, names must match)

Behavior:
  - Versions auto-discovered from GitHub API releases; override with $VERSIONS
  - Any failed download aborts the run (no silent skips)
  - Idempotent: existing non-empty files are skipped

Deps: python3 (stdlib only)
"""

import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date

# ---------- Config ----------
REPO = "hqzing/ohos-node"              # repo with OpenHarmony build assets
OS = "openharmony"                     # target os
ARCH = "arm64"                         # target arch
UPSTREAM = "https://nodejs.org/dist"   # headers upstream
VERSIONS = os.environ.get("VERSIONS", "").split()  # empty = auto-discover
# ----------------------------

UA = "deploy-nodejs-dist/1.0"
TAB = "\t"


def info(msg):
    print(f"[INFO] {msg}", file=sys.stderr)


def ok(msg):
    print(f"[ OK ] {msg}", file=sys.stderr)


def fetch(url, timeout=600):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def download(url, dest):
    """Idempotent download; abort the run on failure."""
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return
    print(f"       {url}")
    try:
        data = fetch(url)
        with open(dest, "wb") as f:
            f.write(data)
    except urllib.error.HTTPError as e:
        sys.exit(f"ERROR: download failed (HTTP {e.code}): {url}")
    except Exception as e:
        sys.exit(f"ERROR: download failed: {e}: {url}")


def discover_versions():
    if VERSIONS:
        return VERSIONS
    info(f"Discovering releases of {REPO} via GitHub API...")
    versions = []
    page = 1
    while True:
        api = f"https://api.github.com/repos/{REPO}/releases?per_page=100&page={page}"
        try:
            data = json.loads(fetch(api, timeout=30))
        except Exception as e:
            sys.exit(f"ERROR: GitHub API failed: {e}")
        if not data:
            break
        versions.extend(r["tag_name"] for r in data
                        if not r.get("draft") and not r.get("prerelease"))
        if len(data) < 100:
            break
        page += 1
    return versions


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def ver_key(v):
    return [int(x) for x in re.findall(r"\d+", v)]


# ---------- Browse pages (nginx autoindex style, matches nodejs.org/dist) ----------

AUTOINDEX_HEAD = (
    "<!DOCTYPE html><html><head><title>Index of {path}/</title>"
    "<style>@media (prefers-color-scheme:dark){{"
    "body{{color:#fff;background-color:#1c1b22}}"
    "a{{color:#3391ff}}a:visited{{color:#c63b65}}"
    "}}</style></head><body><h1>Index of {path}/</h1><hr><pre>"
)
AUTOINDEX_FOOT = "</pre><hr></body></html>"


def human_size(num):
    """nginx-style human readable size: '566 B', '3.8 KB', '25 MB'."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num < 1024 or unit == "TB":
            if unit == "B":
                s = str(int(num))
            else:
                s = f"{num:.1f}".rstrip("0").rstrip(".")
            return f"{s} {unit}"
        num /= 1024
    return "0 B"


def fmt_mtime(path):
    """File mtime as nginx autoindex date: '09-Jun-2025 21:47' (UTC)."""
    ts = os.path.getmtime(path)
    return time.strftime("%d-%b-%Y %H:%M", time.gmtime(ts))


def gen_version_index(dir_path, version):
    """Version dir page: Index of /dist/vX.Y.Z/ (nginx autoindex format)."""
    entries = []  # (name, is_dir)
    for name in os.listdir(dir_path):
        if name == "index.html":
            continue  # the page itself, not listed (official pages have none)
        if os.path.isdir(os.path.join(dir_path, name)):
            entries.append((name + "/", True))
        else:
            entries.append((name, False))
    # dirs first, then files, each sorted lexicographically (nginx behavior)
    entries.sort(key=lambda e: (0 if e[1] else 1, e[0]))

    lines = ['<a href="../">../</a>']
    for name, is_dir in entries:
        if is_dir:
            pad = max(1, 66 - len(name))
            lines.append(f'<a href="{name}">{name}</a>' + " " * pad + "-" + " " * 19 + "-")
        else:
            abs_href = f"/dist/{version}/{name}"
            date = fmt_mtime(os.path.join(dir_path, name))
            size = human_size(os.path.getsize(os.path.join(dir_path, name)))
            pad = max(1, 51 - len(name))
            # date occupies cols 51..67; size right-aligned ending at col 88
            size_start = 89 - len(size)
            pad_size = max(1, size_start - 68)
            lines.append(
                f'<a href="{abs_href}">{name}</a>'
                + " " * pad + date + " " * pad_size + size
            )

    html = AUTOINDEX_HEAD.format(path=f"/dist/{version}") \
        + "\n".join(lines) + "\n" + AUTOINDEX_FOOT
    with open(os.path.join(dir_path, "index.html"), "w") as f:
        f.write(html)


def gen_root_index(out_dir, versions):
    """Root page: Index of /dist/ (nginx autoindex format)."""
    entries = []  # (name, is_dir)
    for v in versions:
        if os.path.isdir(os.path.join(out_dir, v)):
            entries.append((v + "/", True))
    for name in sorted(os.listdir(out_dir)):
        if name == "index.html":
            continue  # the page itself, not listed (official pages have none)
        if name.startswith("index.") or name.endswith(".txt"):
            entries.append((name, False))
    entries.sort(key=lambda e: (0 if e[1] else 1, e[0]))

    lines = ['<a href="../">../</a>']
    for name, is_dir in entries:
        if is_dir:
            pad = max(1, 66 - len(name))
            lines.append(f'<a href="{name}">{name}</a>' + " " * pad + "-" + " " * 19 + "-")
        else:
            abs_href = f"/dist/{name}"
            date = fmt_mtime(os.path.join(out_dir, name))
            size = human_size(os.path.getsize(os.path.join(out_dir, name)))
            pad = max(1, 51 - len(name))
            size_start = 89 - len(size)
            pad_size = max(1, size_start - 68)
            lines.append(
                f'<a href="{abs_href}">{name}</a>'
                + " " * pad + date + " " * pad_size + size
            )

    html = AUTOINDEX_HEAD.format(path="/dist") \
        + "\n".join(lines) + "\n" + AUTOINDEX_FOOT
    with open(os.path.join(out_dir, "index.html"), "w") as f:
        f.write(html)


# ---------- Version processing ----------

def process_version(version, out_dir):
    if not version.startswith("v"):
        version = "v" + version
    dir_path = os.path.join(out_dir, version)
    os.makedirs(dir_path, exist_ok=True)

    gh_base = f"https://github.com/{REPO}/releases/download/{version}"
    base = f"node-{version}-{OS}-{ARCH}"

    jobs = [
        # OpenHarmony builds xz + gz (GitHub)
        (f"{gh_base}/{base}.tar.xz", f"{base}.tar.xz"),
        (f"{gh_base}/{base}.tar.gz", f"{base}.tar.gz"),
        # Upstream headers xz + gz
        (f"{UPSTREAM}/{version}/node-{version}-headers.tar.xz", f"node-{version}-headers.tar.xz"),
        (f"{UPSTREAM}/{version}/node-{version}-headers.tar.gz", f"node-{version}-headers.tar.gz"),
    ]
    for url, name in jobs:
        download(url, os.path.join(dir_path, name))

    # Checksums: only files that exist; names must match what nvm requests
    sums = []
    for name in sorted(os.listdir(dir_path)):
        if name.startswith("node-") and os.path.isfile(os.path.join(dir_path, name)):
            sums.append(f"{sha256_of(os.path.join(dir_path, name))}  {name}")
    with open(os.path.join(dir_path, "SHASUMS256.txt"), "w") as f:
        f.write("\n".join(sums) + "\n")

    gen_version_index(dir_path, version)

    ok(f"{version}: ready")
    return version


# ---------- Index rebuild ----------

def official_metadata():
    """Parse upstream index.tab into {version: row-fields}; {} on failure."""
    try:
        text = fetch(f"{UPSTREAM}/index.tab", timeout=30).decode("utf-8")
        meta = {}
        for line in text.splitlines():
            cols = line.split(TAB)
            if len(cols) >= 11 and cols[0].startswith("v"):
                meta[cols[0]] = cols
        return meta
    except Exception:
        return {}


def build_index_rows(versions, out_dir, official):
    rows = []
    for v in versions:
        dir_path = os.path.join(out_dir, v)
        v_base = f"node-{v}-{OS}-{ARCH}"

        # files column derived from actual files
        files_list = []
        if os.path.exists(os.path.join(dir_path, f"{v_base}.tar.xz")) or \
           os.path.exists(os.path.join(dir_path, f"{v_base}.tar.gz")):
            files_list.append(f"{OS}-{ARCH}")
        if os.path.exists(os.path.join(dir_path, f"node-{v}-headers.tar.xz")) or \
           os.path.exists(os.path.join(dir_path, f"node-{v}-headers.tar.gz")):
            files_list.append("headers")
        files = ",".join(files_list)

        # Metadata from official index.tab row when available; own files column
        meta = official.get(v)
        if meta:
            date_s, npm_s = meta[1], meta[3]
            v8_s, uv_s, zlib_s = meta[4], meta[5], meta[6]
            openssl_s, modules_s = meta[7], meta[8]
            lts_s, security_s = meta[9], meta[10]
        else:
            date_s = date.today().isoformat()
            npm_s = v8_s = uv_s = zlib_s = openssl_s = modules_s = "-"
            lts_s = security_s = "-"

        rows.append((v, date_s, files, npm_s, v8_s, uv_s, zlib_s,
                     openssl_s, modules_s, lts_s, security_s))
    rows.sort(key=lambda r: ver_key(r[0]), reverse=True)
    return rows


def write_index_tab(out_dir, rows):
    header = TAB.join(["version", "date", "files", "npm", "v8", "uv",
                       "zlib", "openssl", "modules", "lts", "security"])
    lines = [header]
    for r in rows:
        lines.append(TAB.join(r))
    with open(os.path.join(out_dir, "index.tab"), "w") as f:
        f.write("\n".join(lines) + "\n")


def write_index_json(out_dir, rows):
    data = []
    for v, date_s, files, npm_s, v8_s, uv_s, zlib_s, openssl_s, modules_s, lts_s, security_s in rows:
        data.append({
            "version": v,
            "date": date_s,
            "files": [x for x in files.split(",") if x] or ["-"],
            "npm": npm_s if npm_s != "-" else None,
            "v8": v8_s if v8_s != "-" else None,
            "uv": uv_s if uv_s != "-" else None,
            "zlib": zlib_s if zlib_s != "-" else None,
            "openssl": openssl_s if openssl_s != "-" else None,
            "modules": modules_s if modules_s != "-" else None,
            "lts": lts_s if lts_s != "-" else False,
            "security": security_s if security_s != "-" else False,
        })
    with open(os.path.join(out_dir, "index.json"), "w") as f:
        json.dump(data, f, indent=1)


# ---------- Main ----------

def main():
    out_dir = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "/var/www/html/dist")
    os.makedirs(out_dir, exist_ok=True)

    info(f"Output dir: {out_dir}")
    info(f"Config: repo={REPO} os={OS} arch={ARCH}")

    versions = discover_versions()
    if not versions:
        sys.exit("ERROR: no versions available")
    info(f"{len(versions)} version(s): {' '.join(versions)}")

    for v in versions:
        process_version(v, out_dir)

    info("Rebuilding index.tab / index.json ...")
    official = official_metadata()
    if official:
        info("Fetched official index.tab as metadata reference")

    rows = build_index_rows(versions, out_dir, official)
    write_index_tab(out_dir, rows)
    write_index_json(out_dir, rows)
    gen_root_index(out_dir, versions)

    print()
    info("Deployment complete")
    with open(os.path.join(out_dir, "index.tab")) as f:
        line_count = len(f.readlines())
    # out_dir is served at /<basename>/ under the parent dir, so the nginx
    # root must be the parent (e.g. /var/www/html/dist -> root /var/www/html,
    # URL prefix /dist).  Do not use "listen 80 default_server;" in a new
    # block unless you are replacing the existing default server.
    nginx_root = os.path.dirname(out_dir)
    url_prefix = "/" + os.path.basename(out_dir)
    # Heredoc marker must start at column 0 for the pasted script to work.
    print(f"""    Output dir: {out_dir}
    Served versions: {' '.join(versions)}
    index.tab: {line_count} lines (incl. header)

nginx: replace your default site (copy-paste the whole block):
    rm -f /etc/nginx/sites-enabled/default
    cat > /etc/nginx/sites-enabled/default <<'EOF'
    server {{
        listen 80 default_server;
        listen [::]:80 default_server;
        root {nginx_root};
        location {url_prefix} {{ try_files $uri $uri/ =404; }}
    }}
EOF
    nginx -t && systemctl reload nginx

Client usage:
    NVM_NODEJS_ORG_MIRROR=http://<host>{url_prefix} nvm install {versions[0]}""")


if __name__ == "__main__":
    main()
