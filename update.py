"""Minecraft Language File Updater"""

import hashlib
import re
import sys
import time
from pathlib import Path
from typing import Final
from zipfile import ZipFile

import ujson
import requests as r
from requests.exceptions import SSLError, ReadTimeout, RequestException

# Current absolute path
P: Final[Path] = Path(__file__).resolve().parent

# Language file directories
LANG_DIR_FULL: Final[Path] = P / "full"
LANG_DIR_VALID: Final[Path] = P / "valid"
LANG_DIR_FULL.mkdir(exist_ok=True)
LANG_DIR_VALID.mkdir(exist_ok=True)

# Language list
LANG_LIST: Final[tuple[str, ...]] = (
    "en_us",
    "zh_cn",
    "zh_hk",
    "zh_tw",
    "lzh",
    "ja_jp",
    "ko_kr",
    "vi_vn",
    "de_de",
    "es_es",
    "fr_fr",
    "it_it",
    "nl_nl",
    "pt_br",
    "ru_ru",
    "th_th",
    "uk_ua"
)

MAX_RETRIES: Final[int] = 3  # Maximum retry attempts


def get_response(url: str) -> r.Response | None:
    """Get HTTP response and handle exceptions and retry logic.

    Args:
        url (str): URL to request

    Returns:
        r.Response | None: Response object, or None if request fails
    """

    retries = 0
    while retries < MAX_RETRIES:
        try:
            resp = r.get(url, timeout=60)
            resp.raise_for_status()
            return resp
        except SSLError as e:
            print(f"SSL Error encountered: {e}")
            if retries < MAX_RETRIES - 1:
                print("Server access restricted, retrying in 15 seconds...")
                time.sleep(15)
            else:
                print("Maximum retry attempts reached. Operation terminated.")
                return None
        except ReadTimeout as e:
            print(f"Request timeout: {e}")
            if retries < MAX_RETRIES - 1:
                print("Retrying in 5 seconds...")
                time.sleep(5)
            else:
                print("Maximum retry attempts reached. Operation terminated.")
                return None
        except RequestException as ex:
            print(f"Request error occurred: {ex}")
            return None
        finally:
            retries += 1

    return None


def check_sha1(file_path: Path, sha1: str) -> bool:
    """Verify file's SHA1 value.

    Args:
        file_path (Path): Path to the file
        sha1 (str): Expected SHA1 checksum

    Returns:
        bool: Whether verification passed
    """

    with file_path.open("rb") as f:
        return hashlib.file_digest(f, "sha1").hexdigest() == sha1


def get_file(url: str, file_name: str, file_path: Path, sha1: str) -> None:
    """Download file and verify SHA1 value.

    Args:
        url (str): File download URL
        file_name (str): File name
        file_path (Path): File save path
        sha1 (str): Expected SHA1 checksum
    """

    start_time = time.time()
    success = False

    for _ in range(MAX_RETRIES):
        try:
            with open(file_path, "wb") as f:
                f.write(get_response(url).content)
            size_in_bytes = file_path.stat().st_size
            size = (
                f"{round(size_in_bytes / 1048576, 2)} MB"
                if size_in_bytes > 1048576
                else f"{round(size_in_bytes / 1024, 2)} KB"
            )

            if check_sha1(file_path, sha1):
                print(f"File SHA1 checksum matches. File size: {size_in_bytes} B ({size})")
                success = True
                break
            print("File SHA1 checksum mismatch, retrying download.")
        except RequestException as e:
            print(f"Request error: {e}")
            sys.exit()

    elapsed_time = time.time() - start_time
    if success:
        print(f'File "{file_name}" downloaded successfully. Time elapsed: {elapsed_time:.2f} s.\n')
    else:
        print(f'Unable to download file "{file_name}". Time elapsed: {elapsed_time:.2f} s.\n')


# Get version_manifest_v2.json
version_manifest_path = P / "version_manifest_v2.json"
print('Retrieving content of version manifest "version_manifest_v2.json"...\n')
version_manifest_json: dict = get_response(
    "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
).json()

# Get version
V: str = version_manifest_json["latest"]["snapshot"]
with open(P / "version.txt", "w", encoding="utf-8") as ver:
    ver.write(V)
version_info: dict = next(
    (_ for _ in version_manifest_json["versions"] if _["id"] == V), {}
)
if not version_info:
    print("Could not find the latest version in the version manifest.")
    sys.exit()
print(f"Selected version: {V}\n")

# Get client.json
client_manifest_url: str = version_info["url"]
print(f"Fetching client manifest file '{client_manifest_url.rsplit('/', 1)[-1]}'...")
client_manifest: dict = get_response(client_manifest_url).json()

# Get asset index file
asset_index_url: str = client_manifest["assetIndex"]["url"]
print(f"Fetching asset index file '{asset_index_url.rsplit('/', 1)[-1]}'...\n")
asset_index: dict[str, dict[str, str]] = get_response(asset_index_url).json()["objects"]

# Get client JAR
client_url: str = client_manifest["downloads"]["client"]["url"]
client_sha1: str = client_manifest["downloads"]["client"]["sha1"]
client_path = LANG_DIR_FULL / "client.jar"
print(f"Downloading client Java archive 'client.jar' ({client_sha1})...")
get_file(client_url, "client.jar", client_path, client_sha1)

# Extract English (United States) language file
with ZipFile(client_path) as client:
    with client.open("assets/minecraft/lang/en_us.json") as content:
        with open(LANG_DIR_FULL / "en_us.json", "wb") as en:
            print("Extracting language file 'en_us.json' from client.jar...")
            en.write(content.read())

# Delete client JAR
print("Deleting client.jar...\n")
client_path.unlink()

# Get language files
language_files_list = [f"{_}.json" for _ in LANG_LIST if _ != "en_us"]
for lang in language_files_list:
    lang_asset = asset_index.get(f"minecraft/lang/{lang}")
    if lang_asset:
        file_hash = lang_asset["hash"]
        print(f'Downloading language file "{lang}" ({file_hash})...')
        get_file(
            f"https://resources.download.minecraft.net/{file_hash[:2]}/{file_hash}",
            lang,
            LANG_DIR_FULL / lang,
            file_hash,
        )
    else:
        print(f"{lang} does not exist.\n")

# Define constants
VALID_PATTERN = re.compile(
    r"^(block\.minecraft\.[^.]*"
    r"|entity\.minecraft\.[^.]*"
    r"|item\.minecraft\.[^.]*"
    r"|item\.minecraft\.[^.]*\.effect\.[^.]*"
    r"|biome\..*"
    r"|effect\.minecraft\.[^.]*"
    r"|enchantment\.minecraft\..*"
    r"|upgrade\..*"
    r"|filled_map\..*"
    r"|trim_pattern\..*"
    r"|advancements\.[^.]*\.[^.]*\.title)$"
)

EXCLUSIONS: set[str] = {
    "block.minecraft.set_spawn",
    "enchantment.minecraft.sweeping",
    "entity.minecraft.falling_block_type",
    "filled_map.id",
    "filled_map.level",
    "filled_map.locked",
    "filled_map.scale",
    "filled_map.unknown",
}


def is_valid_key(translation_key: str) -> bool:
    """Determine if a translation key is valid.

    Args:
        translation_key (str): Key name to validate

    Returns:
        bool: Whether the key is valid
    """
    return (
        translation_key not in EXCLUSIONS
        and "pottery_shard" not in translation_key
        and bool(VALID_PATTERN.match(translation_key))
    )


# Modify language files
for lang_name in LANG_LIST:
    with open(LANG_DIR_FULL / f"{lang_name}.json", "r", encoding="utf-8") as l:
        data: dict[str, str] = ujson.load(l)
    edited_data: dict[str, str] = {k: v for k, v in data.items() if is_valid_key(k)}
    with open(
        LANG_DIR_VALID / f"{lang_name}.json", "w", encoding="utf-8", newline="\n"
    ) as l:
        ujson.dump(edited_data, l, ensure_ascii=False, indent=2)
    print(f'Valid strings extracted from "{lang_name}.json".')

