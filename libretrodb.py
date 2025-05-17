import os
import requests
import xml.etree.ElementTree as ET
import hashlib
import time
import zlib

LIBRETRO_DB_URL = "https://raw.githubusercontent.com/libretro/libretro-database/master/dat/"
CACHE_DIR = "cache/libretrodb"
os.makedirs(CACHE_DIR, exist_ok=True)

# Download and cache a .dat file
def download_dat(system, max_age=86400):
    dat_filename = f"{system}.dat"
    cache_path = os.path.join(CACHE_DIR, dat_filename)
    url = LIBRETRO_DB_URL + dat_filename
    # Download if not present or too old
    if not os.path.exists(cache_path) or (time.time() - os.path.getmtime(cache_path) > max_age):
        r = requests.get(url)
        if r.status_code == 200:
            with open(cache_path, "wb") as f:
                f.write(r.content)
        else:
            raise Exception(f"Failed to download {url}")
    return cache_path

# Parse a .dat file and return a lookup dict by filename and by hash
def parse_dat(dat_path):
    tree = ET.parse(dat_path)
    root = tree.getroot()
    by_filename = {}
    by_crc = {}
    by_md5 = {}
    by_sha1 = {}
    for game in root.findall('game'):
        name = game.get('name')
        description = game.findtext('description')
        year = game.findtext('year')
        manufacturer = game.findtext('manufacturer')
        rom = game.find('rom')
        crc = rom.get('crc') if rom is not None else None
        md5 = rom.get('md5') if rom is not None else None
        sha1 = rom.get('sha1') if rom is not None else None
        entry = {
            'name': name,
            'description': description,
            'year': year,
            'manufacturer': manufacturer,
            'crc': crc,
            'md5': md5,
            'sha1': sha1,
        }
        by_filename[name] = entry
        if crc:
            by_crc[crc.lower()] = entry
        if md5:
            by_md5[md5.lower()] = entry
        if sha1:
            by_sha1[sha1.lower()] = entry
    return {'by_filename': by_filename, 'by_crc': by_crc, 'by_md5': by_md5, 'by_sha1': by_sha1}

# Get metadata for a given ROM file (by filename or hash)
def get_metadata_for_rom(rom_path, system):
    dat_path = download_dat(system)
    db = parse_dat(dat_path)
    # Try by filename
    base = os.path.basename(rom_path)
    if base in db['by_filename']:
        return db['by_filename'][base]
    # Try by hash
    with open(rom_path, 'rb') as f:
        data = f.read()
        crc = f"{zlib.crc32(data) & 0xFFFFFFFF:08x}"
        md5 = hashlib.md5(data).hexdigest()
        sha1 = hashlib.sha1(data).hexdigest()
    if crc in db['by_crc']:
        return db['by_crc'][crc]
    if md5 in db['by_md5']:
        return db['by_md5'][md5]
    if sha1 in db['by_sha1']:
        return db['by_sha1'][sha1]
    return None 