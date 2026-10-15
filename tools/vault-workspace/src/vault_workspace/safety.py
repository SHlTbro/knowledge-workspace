"""Portable paths: reject ambiguous Windows names and every link component."""
from pathlib import Path, PurePosixPath
import re
import unicodedata

_DEVICE = re.compile(r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)", re.I)


def relative_path(value: str, *, allow_dot: bool = False) -> str:
    if allow_dot and value == ".":
        return value
    if not isinstance(value, str) or not value or len(value) > 220:
        raise ValueError("相对路径为空或过长")
    if value != unicodedata.normalize("NFC", value):
        raise ValueError("路径必须使用规范化Unicode")
    if "\\" in value or any(ord(c) < 32 or c in ':*?"<>|' for c in value):
        raise ValueError("路径包含不可移植字符")
    path = PurePosixPath(value)
    if path.is_absolute() or value != path.as_posix():
        raise ValueError("必须使用规范相对路径")
    for part in value.split("/"):
        if part in ("", ".", "..") or part.endswith((" ", ".")) or _DEVICE.match(part):
            raise ValueError("路径包含保留名称或越界片段")
        if part.casefold() in (".git", ".hg", ".svn"):
            raise ValueError("创建计划不能配置版本控制内部目录")
    return value


def under(root: Path, value: str, *, allow_dot: bool = False) -> Path:
    value = relative_path(value, allow_dot=allow_dot)
    root = Path(root).absolute()
    current = root
    for part in (() if value == "." else value.split("/")):
        if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
            raise ValueError("不允许通过链接访问")
        current = current / part
    if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
        raise ValueError("不允许通过链接访问")
    if not current.resolve().is_relative_to(root.resolve()):
        raise ValueError("路径越过授权目录")
    return current


def folder_name(value: str) -> str:
    relative_path(value)
    if "/" in value or value.startswith(".") or len(value) > 80:
        raise ValueError("库目录名必须是一个普通目录名")
    return value
