# -*- encoding: utf-8 -*-
"""Minecraft语言文件更新器"""

import hashlib
import json
import re
import sys
import time
from pathlib import Path
from typing import Tuple, Dict, Set
from zipfile import ZipFile

import requests as r

# 当前绝对路径
P = Path(__file__).resolve().parent

# 语言文件文件夹
LANG_DIR_FULL = P / "full"
LANG_DIR_VALID = P / "valid"
LANG_DIR_FULL.mkdir(exist_ok=True)
LANG_DIR_VALID.mkdir(exist_ok=True)

# 语言列表
LANG_LIST: Tuple[str, ...] = (
    "en_us",
    "zh_cn",
    "zh_hk",
    "zh_tw",
    "lzh",
    "ja_jp",
    "ko_kr",
    "vi_vn",
)


def get_response(url: str) -> r.Response:
    """
    获取HTTP响应。

    Args:
        url (str): 请求的URL

    Returns:
        r.Response: 响应对象
    """

    try:
        resp = r.get(url, timeout=60)
        resp.raise_for_status()
        return resp
    except r.exceptions.RequestException as ex:
        print(f"请求发生错误: {ex}")
        sys.exit()


def get_file(url: str, file_name: str, file_path: Path, sha1: str) -> None:
    """
    下载文件并校验SHA1值。

    Args:
        url (str): 文件下载URL
        file_name (str): 文件名称
        file_path (Path): 文件保存路径
        sha1 (str): 文件的SHA1校验值
    """

    start_time = time.time()
    success = False
    for _ in range(3):
        with open(file_path, "wb") as f:
            f.write(get_response(url).content)

        size_in_bytes = file_path.stat().st_size
        size = (
            f"{round(size_in_bytes / 1048576, 2)} MB"
            if size_in_bytes > 1048576
            else f"{round(size_in_bytes / 1024, 2)} KB"
        )

        with file_path.open("rb") as f:
            if hashlib.file_digest(f, "sha1").hexdigest() == sha1:
                print(f"文件SHA1校验一致。文件大小：{size_in_bytes} B（{size}）")
                success = True
                break
            print("文件SHA1校验不一致，重新尝试下载。")

    elapsed_time = time.time() - start_time
    if success:
        print(f"文件“{file_name}”已下载完成，耗时{elapsed_time:.2f} s。\n")
    else:
        print(f"无法下载文件“{file_name}”。耗时{elapsed_time:.2f} s。\n")


# 获取version_manifest_v2.json
version_manifest_path = P / "version_manifest_v2.json"
print("正在获取版本清单“version_manifest_v2.json”的内容……\n")
version_manifest_json: Dict = get_response(
    "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"
).json()

# 获取版本
V: str = version_manifest_json["latest"]["snapshot"]
with open(P / "version.txt", "w", encoding="utf-8") as ver:
    ver.write(V)
version_info: Dict = next(
    (_ for _ in version_manifest_json["versions"] if _["id"] == V), {}
)
if not version_info:
    print("无法在版本清单中找到最新版本。")
    sys.exit()
print(f"选择的版本：{V}\n")

# 获取client.json
client_manifest_url: str = version_info["url"]
print(f"正在获取客户端索引文件“{client_manifest_url.rsplit('/', 1)[-1]}”的内容……")
client_manifest: Dict = get_response(client_manifest_url).json()

# 获取资产索引文件
asset_index_url: str = client_manifest["assetIndex"]["url"]
print(f"正在获取资产索引文件“{asset_index_url.rsplit('/', 1)[-1]}”的内容……\n")
asset_index: Dict[str, Dict[str, str]] = get_response(asset_index_url).json()["objects"]

# 获取客户端JAR
client_url: str = client_manifest["downloads"]["client"]["url"]
client_sha1: str = client_manifest["downloads"]["client"]["sha1"]
client_path = LANG_DIR_FULL / "client.jar"
print(f"正在下载客户端Java归档“client.jar”（{client_sha1}）……")
get_file(client_url, "client.jar", client_path, client_sha1)

# 解压English (United States)语言文件
with ZipFile(client_path) as client:
    with client.open("assets/minecraft/lang/en_us.json") as content:
        with open(LANG_DIR_FULL / "en_us.json", "wb") as en:
            print("正在从client.jar解压语言文件“en_us.json”……")
            en.write(content.read())

# 删除客户端JAR
print("正在删除client.jar……\n")
client_path.unlink()

# 获取语言文件
language_files_list = [f"{_}.json" for _ in LANG_LIST if _ != "en_us"]
for lang in language_files_list:
    lang_asset = asset_index.get(f"minecraft/lang/{lang}")
    if lang_asset:
        file_hash = lang_asset["hash"]
        print(f"正在下载语言文件“{lang}”（{file_hash}）……")
        get_file(
            f"https://resources.download.minecraft.net/{file_hash[:2]}/{file_hash}",
            lang,
            LANG_DIR_FULL / lang,
            file_hash,
        )
    else:
        print(f"{lang}不存在。\n")

# 定义常量
PREFIXES: Tuple[str, ...] = (
    "block.",
    "item.minecraft.",
    "entity.minecraft.",
    "biome.",
    "effect.minecraft.",
    "enchantment.minecraft.",
    "trim_pattern.",
    "upgrade.",
    "filled_map",
)
INVALID_BLOCK_ITEM_ENTITY_PATTERN = re.compile(
    r"(block\.minecraft\.|item\.minecraft\.|entity\.minecraft\.)[^.]*\."
)
ITEM_EFFECT_PATTERN = re.compile(r"item\.minecraft\.[^.]*\.effect\.[^.]*")
ADVANCEMENTS_TITLE_PATTERN = re.compile(r"advancements\.(.*)\.title")
EXCLUSIONS: Set[str] = {
    "block.minecraft.set_spawn",
    "entity.minecraft.falling_block_type",
    "filled_map.id",
    "filled_map.level",
    "filled_map.locked",
    "filled_map.scale",
    "filled_map.unknown",
}


def is_valid_key(translation_key: str) -> bool:
    """
    判断是否为有效键名。

    Args:
        translation_key (str): 需要验证的键名

    Returns:
        bool: 如果键名有效，返回 True；否则返回 False
    """

    if ADVANCEMENTS_TITLE_PATTERN.match(translation_key):
        return True
    if not translation_key.startswith(PREFIXES):
        return False
    if translation_key in EXCLUSIONS or "pottery_shard" in translation_key:
        return False
    if ITEM_EFFECT_PATTERN.match(translation_key):
        return True
    if INVALID_BLOCK_ITEM_ENTITY_PATTERN.match(translation_key):
        return False
    return True


# 修改语言文件
for lang_name in LANG_LIST:
    with open(LANG_DIR_FULL / f"{lang_name}.json", "r", encoding="utf-8") as l:
        data: Dict[str, str] = json.load(l)
    edited_data: Dict[str, str] = {k: v for k, v in data.items() if is_valid_key(k)}
    with open(LANG_DIR_VALID / f"{lang_name}.json", "w", encoding="utf-8") as l:
        json.dump(edited_data, l, ensure_ascii=False, indent=4)
    print(f"已提取“{lang_name}.json”的有效字符串。")
