"""
扫描目录并解析 SKILL.md

职责：
1. 扫描 skill 目录
2. 解析 frontmatter
3. 生成 SkillEntry
4. 提供 skill 正文读取能力，供 runtime.py 后续复用

创建时间：2026/5/2
开发人：zcry
"""
from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

from app.models.dto.skill.skill import SkillEntry, SkillFrontmatter, SkillScope


class SkillLoader:
    """
    skill 加载器

    目录约定：
    - system:   app/skills/system/<skill_name>/SKILL.md
    - internal: app/skills/internal/<agent_name>/<skill_name>/SKILL.md

    设计说明：
    - 默认支持宽松加载：坏 skill 记录 warning 后跳过
    - strict=True 时：遇到坏 skill 直接抛异常
    - frontmatter 先只支持 MVP 所需字段，不追求完整 YAML 兼容
    """

    SYSTEM_DIR_NAME = "system"
    INTERNAL_DIR_NAME = "internal"
    SKILL_FILE_NAME = "SKILL.md"

    def __init__(self, skills_root: str | Path) -> None:
        self.skills_root = Path(skills_root).resolve()
        self.logger = logging.getLogger(self.__class__.__name__)

    # ============================================================
    # Public API
    # ============================================================

    def load_all(self, *, strict: bool = False) -> list[SkillEntry]:
        """
        加载所有 skills

        返回结果按：
        1. scope
        2. owner_agent
        3. name
        排序，保证稳定输出。
        """
        entries: list[SkillEntry] = []

        for skill_file in self.discover_skill_files():
            try:
                entry = self.load_file(skill_file)
            except Exception as exc:
                if strict:
                    raise
                self.logger.warning(
                    "skip invalid skill file: path=%s error=%s",
                    skill_file,
                    exc,
                )
                continue
            entries.append(entry)

        return sorted(
            entries,
            key=lambda item: (
                item.scope,
                item.owner_agent or "",
                item.name,
                item.file_path,
            ),
        )

    def load_file(self, skill_file: str | Path) -> SkillEntry:
        """
        加载单个 SKILL.md 并解析为 SkillEntry
        """
        path = Path(skill_file).resolve()

        if not path.exists():
            raise FileNotFoundError(f"skill file not found: {path}")

        if path.name != self.SKILL_FILE_NAME:
            raise ValueError(f"invalid skill file name: {path.name}")

        scope, owner_agent, base_dir = self._resolve_skill_location(path)
        raw_text = path.read_text(encoding="utf-8")
        frontmatter_data, _ = self._split_frontmatter(raw_text)
        frontmatter = SkillFrontmatter.model_validate(frontmatter_data)

        return SkillEntry.from_frontmatter(
            frontmatter=frontmatter,
            file_path=str(path),
            base_dir=str(base_dir),
            scope=scope,
            owner_agent=owner_agent,
        )

    def discover_skill_files(self) -> list[Path]:
        """
        发现 skills_root 下所有符合约定的 SKILL.md
        """
        if not self.skills_root.exists():
            return []

        discovered: list[Path] = []

        system_root = self.skills_root / self.SYSTEM_DIR_NAME
        if system_root.exists():
            discovered.extend(self._discover_system_skill_files(system_root))

        internal_root = self.skills_root / self.INTERNAL_DIR_NAME
        if internal_root.exists():
            discovered.extend(self._discover_internal_skill_files(internal_root))

        return sorted({path.resolve() for path in discovered})

    def read_skill_body(self, skill_file: str | Path) -> str:
        """
        读取 skill markdown 正文

        这个方法后续 runtime.py 在 apply_skill(...) 时会直接复用
        """
        path = Path(skill_file).resolve()
        raw_text = path.read_text(encoding="utf-8")
        _, body = self._split_frontmatter(raw_text)
        return body.strip()

    # ============================================================
    # Discover helpers
    # ============================================================

    def _discover_system_skill_files(self, system_root: Path) -> list[Path]:
        """
        发现 system skills：
        app/skills/system/<skill_name>/SKILL.md
        """
        files: list[Path] = []

        for child in system_root.iterdir():
            if not child.is_dir():
                continue
            skill_file = child / self.SKILL_FILE_NAME
            if skill_file.is_file():
                files.append(skill_file)

        return files

    def _discover_internal_skill_files(self, internal_root: Path) -> list[Path]:
        """
        发现 internal skills：
        app/skills/internal/<agent_name>/<skill_name>/SKILL.md
        """
        files: list[Path] = []

        for agent_dir in internal_root.iterdir():
            if not agent_dir.is_dir():
                continue

            for skill_dir in agent_dir.iterdir():
                if not skill_dir.is_dir():
                    continue

                skill_file = skill_dir / self.SKILL_FILE_NAME
                if skill_file.is_file():
                    files.append(skill_file)

        return files

    # ============================================================
    # Location resolution
    # ============================================================

    def _resolve_skill_location(
        self,
        skill_file: Path,
    ) -> tuple[SkillScope, str | None, Path]:
        """
        根据文件路径解析：
        - scope
        - owner_agent
        - base_dir
        """
        try:
            relative = skill_file.relative_to(self.skills_root)
        except ValueError as exc:
            raise ValueError(
                f"skill file is outside skills_root: file={skill_file} root={self.skills_root}"
            ) from exc

        parts = relative.parts

        # system/<skill>/SKILL.md
        if len(parts) == 3 and parts[0] == self.SYSTEM_DIR_NAME and parts[2] == self.SKILL_FILE_NAME:
            return "system", None, skill_file.parent

        # internal/<agent>/<skill>/SKILL.md
        if (
            len(parts) == 4
            and parts[0] == self.INTERNAL_DIR_NAME
            and parts[3] == self.SKILL_FILE_NAME
        ):
            owner_agent = parts[1].strip()
            if not owner_agent:
                raise ValueError(f"invalid internal skill owner in path: {skill_file}")
            return "internal", owner_agent, skill_file.parent

        raise ValueError(
            "invalid skill path layout. expected one of: "
            "system/<skill>/SKILL.md or internal/<agent>/<skill>/SKILL.md"
        )

    # ============================================================
    # Frontmatter parsing
    # ============================================================

    def _split_frontmatter(self, raw_text: str) -> tuple[dict[str, Any], str]:
        """
        拆分 frontmatter 和 markdown body

        规则：
        - 如果文件以 --- 开头，则解析 frontmatter，直到下一个 ---
        - 否则认为没有 frontmatter

        返回：
        - frontmatter_data
        - markdown_body
        """
        text = raw_text.lstrip("\ufeff")
        lines = text.splitlines()

        if not lines or lines[0].strip() != "---":
            return {}, text

        closing_index: int | None = None
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                closing_index = index
                break

        if closing_index is None:
            raise ValueError("frontmatter starts with '---' but closing '---' is missing")

        frontmatter_lines = lines[1:closing_index]
        body_lines = lines[closing_index + 1 :]

        frontmatter_data = self._parse_frontmatter_lines(frontmatter_lines)
        body = "\n".join(body_lines)

        return frontmatter_data, body

    def _parse_frontmatter_lines(self, lines: list[str]) -> dict[str, Any]:
        """
        解析一个受限版 YAML frontmatter

        当前支持：
        - key: value
        - key:
            - item1
            - item2
        - 布尔值 true/false
        - 简单 inline list: [a, b] / ["a", "b"]
        """
        data: dict[str, Any] = {}
        index = 0

        while index < len(lines):
            line = lines[index]
            stripped = line.strip()

            if not stripped or stripped.startswith("#"):
                index += 1
                continue

            if stripped.startswith("- "):
                raise ValueError(f"unexpected list item without key: {line}")

            if ":" not in line:
                raise ValueError(f"invalid frontmatter line: {line}")

            raw_key, raw_value = line.split(":", 1)
            key = raw_key.strip()
            value = raw_value.strip()

            if not key:
                raise ValueError(f"invalid frontmatter key in line: {line}")

            if value:
                data[key] = self._parse_scalar_value(value)
                index += 1
                continue

            # 处理 key:\n  - item 的情况
            list_items: list[str] = []
            lookahead = index + 1

            while lookahead < len(lines):
                next_line = lines[lookahead]
                next_stripped = next_line.strip()

                if not next_stripped:
                    lookahead += 1
                    continue

                if next_line.startswith((" ", "\t")) and next_stripped.startswith("- "):
                    list_items.append(next_stripped[2:].strip())
                    lookahead += 1
                    continue

                break

            if list_items:
                data[key] = list_items
                index = lookahead
                continue

            data[key] = ""
            index += 1

        return data

    def _parse_scalar_value(self, raw: str) -> Any:
        """
        解析单个 frontmatter value

        支持：
        - true / false
        - quoted string
        - inline list
        - plain string
        """
        lowered = raw.lower()

        if lowered == "true":
            return True
        if lowered == "false":
            return False

        if raw.startswith("[") and raw.endswith("]"):
            return self._parse_inline_list(raw)

        if (raw.startswith('"') and raw.endswith('"')) or (
            raw.startswith("'") and raw.endswith("'")
        ):
            try:
                parsed = ast.literal_eval(raw)
            except Exception:
                return raw[1:-1].strip()
            return parsed

        return raw

    def _parse_inline_list(self, raw: str) -> list[str]:
        """
        解析 inline list

        支持两类：
        - [a, b]
        - ["a", "b"]
        """
        try:
            parsed = ast.literal_eval(raw)
        except Exception:
            parsed = None

        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]

        inner = raw[1:-1].strip()
        if not inner:
            return []

        return [part.strip().strip("'\"") for part in inner.split(",") if part.strip()]
