from __future__ import annotations

import csv
import re
import threading
from dataclasses import dataclass
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parent
TABLE_PATH = SKILL_ROOT / "data" / "ccb_handler_table.csv"
EXPECTED_HEADERS = ("序号", "部门名称", "职务/科室", "姓名", "办公号码", "工作职责")
_LEADERSHIP_TITLES = ("总经理", "副总经理", "主任", "副主任")
_CACHE_LOCK = threading.Lock()
_CACHE_KEY: tuple[int, int] | None = None
_CACHE_TABLE: "CCBHandlerTable | None" = None


def _compact_text(value: str) -> str:
    normalized = (value or "").replace("*", "x")
    return re.sub(r"\s+", " ", normalized.strip())


def _compact_search_text(value: str) -> str:
    normalized = (value or "").replace("*", "x")
    return re.sub(r"\s+", "", normalized.strip())


def _mask_person_name(value: str) -> str:
    normalized = _compact_text(value)
    if not normalized:
        return ""

    masked_chars: list[str] = []
    visible_char_count = 0
    for char in normalized:
        if char.isspace():
            masked_chars.append(char)
            continue
        if visible_char_count == 0:
            masked_chars.append(char)
        else:
            masked_chars.append("x")
        visible_char_count += 1
    return "".join(masked_chars)


def _strip_list_prefix(value: str) -> str:
    return re.sub(r"^\s*[0-9０-９]+[.．、]\s*", "", value or "").strip()


def _normalize_row(raw_row: list[str]) -> list[str]:
    trimmed = ["" if item is None else str(item).strip() for item in raw_row[: len(EXPECTED_HEADERS)]]
    if len(trimmed) < len(EXPECTED_HEADERS):
        trimmed.extend([""] * (len(EXPECTED_HEADERS) - len(trimmed)))
    return trimmed


def _is_leadership_role(role: str) -> bool:
    return any(keyword in role for keyword in _LEADERSHIP_TITLES)


@dataclass(frozen=True, slots=True)
class HandlerRecord:
    sequence: str
    department: str
    role: str
    owner_name: str
    office_phone: str
    responsibilities: str

    @property
    def role_display(self) -> str:
        role = self.role.strip()
        if not role:
            return "待补充岗"
        return role if role.endswith("岗") else f"{role}岗"

    @property
    def search_role(self) -> str:
        return _compact_search_text(self.role)

    @property
    def chain_role_display(self) -> str:
        role = self.role.strip()
        return role or "职务未明确"

    def responsibilities_excerpt(self, max_chars: int = 90, max_items: int = 2) -> str:
        raw_text = _compact_text(self.responsibilities)
        if not raw_text:
            return "未提供"

        numbered_parts = [
            _strip_list_prefix(item)
            for item in re.split(r"(?:(?<=。)|(?<=；))\s*|\s+(?=[0-9０-９]+[.．、])", raw_text)
            if _strip_list_prefix(item)
        ]
        selected_parts = numbered_parts[:max_items] if numbered_parts else [raw_text]
        excerpt = "；".join(part.rstrip("。；") for part in selected_parts if part)
        excerpt = excerpt or raw_text
        if len(excerpt) <= max_chars:
            return excerpt
        return excerpt[: max(0, max_chars - 3)].rstrip("，；。 ") + "..."


@dataclass(frozen=True, slots=True)
class HandlerChain:
    department_head: str
    supervising_head: str
    owner_name: str

    def render(self) -> str:
        supervising_head = (self.supervising_head or "").strip() or "分管通讯不确定"
        owner_name = (self.owner_name or "").strip() or "岗位负责人未明确"
        chain_members: list[str] = []
        for item in ((self.department_head or "").strip(), supervising_head, owner_name):
            normalized = (item or "").strip()
            if not normalized:
                continue
            if chain_members and chain_members[-1] == normalized:
                continue
            chain_members.append(normalized)
        return "—".join(chain_members) if chain_members else "岗位负责人未明确"


def _format_chain_member(record: HandlerRecord | None, *, use_role_display: bool) -> str:
    if record is None:
        return ""
    role = record.role_display if use_role_display else record.chain_role_display
    return f"{_mask_person_name(record.owner_name)}（{role}）"


@dataclass(frozen=True, slots=True)
class CCBHandlerTable:
    source_path: Path
    records: tuple[HandlerRecord, ...]

    def metrics(self) -> dict[str, object]:
        return {
            "table_path": str(self.source_path),
            "table_row_count": len(self.records),
        }

    def get_by_sequence(self, sequence: str) -> HandlerRecord | None:
        normalized = str(sequence or "").strip()
        if not normalized:
            return None
        for record in self.records:
            if record.sequence == normalized:
                return record
        return None

    def resolve_chain(self, record: HandlerRecord) -> HandlerChain:
        department_records = [item for item in self.records if item.department == record.department]
        department_head = self._find_department_head(department_records)
        supervising_head = self._find_supervising_head(record, department_records)
        if department_head is not None and department_head.sequence == record.sequence:
            department_head = None
        if department_head is not None and supervising_head is not None and department_head.sequence == supervising_head.sequence:
            department_head = None
        return HandlerChain(
            department_head=_format_chain_member(department_head, use_role_display=False),
            supervising_head=_format_chain_member(supervising_head, use_role_display=False),
            owner_name=_format_chain_member(record, use_role_display=True),
        )

    def render_lookup_context(self) -> str:
        rendered_rows: list[str] = []
        for record in self.records:
            chain = self.resolve_chain(record)
            rendered_rows.append(
                " | ".join(
                    [
                        f"序号={record.sequence}",
                        f"部门={record.department}",
                        f"岗位={record.role}",
                        f"负责人={_mask_person_name(record.owner_name)}",
                        f"办公号码={record.office_phone or '未提供'}",
                        f"部门总={chain.department_head or '未明确'}",
                        f"分管总={chain.supervising_head or '未明确'}",
                        f"工作职责={record.responsibilities}",
                    ]
                )
            )
        return "\n".join(rendered_rows)

    @staticmethod
    def _find_department_head(records: list[HandlerRecord]) -> HandlerRecord | None:
        if not records:
            return None

        def rank(item: HandlerRecord) -> tuple[int, str]:
            role = _compact_search_text(item.role)
            responsibilities = _compact_search_text(item.responsibilities)
            if ("主任" in role or "总经理" in role) and "全面工作" in responsibilities:
                return (0, item.sequence)
            if "主持全面" in responsibilities or "主持部门全面工作" in responsibilities:
                return (1, item.sequence)
            if "主任" in role or "总经理" in role:
                return (2, item.sequence)
            if ("副主任" in role or "副总经理" in role) and "主持" in responsibilities:
                return (3, item.sequence)
            return (9, item.sequence)

        candidates = [item for item in records if _is_leadership_role(item.role)]
        if not candidates:
            return None
        best = min(candidates, key=rank)
        return best if rank(best)[0] < 9 else None

    @staticmethod
    def _find_supervising_head(
        record: HandlerRecord,
        department_records: list[HandlerRecord],
    ) -> HandlerRecord | None:
        role_token = record.search_role
        if not role_token:
            return None

        candidates: list[tuple[int, str, HandlerRecord]] = []
        for item in department_records:
            if item.sequence == record.sequence:
                continue
            responsibilities = _compact_search_text(item.responsibilities)
            if role_token not in responsibilities:
                continue

            priority = 9
            if "分管" in responsibilities and _is_leadership_role(item.role):
                priority = 0
            elif "协管" in responsibilities and _is_leadership_role(item.role):
                priority = 1
            elif "分管" in responsibilities:
                priority = 2
            elif "协管" in responsibilities:
                priority = 3

            if priority < 9:
                candidates.append((priority, item.sequence, item))

        if not candidates:
            return None
        return min(candidates, key=lambda item: (item[0], item[1]))[2]


class CCBHandlerTableTool:
    def load(self) -> CCBHandlerTable:
        return load_handler_table()


def load_handler_table() -> CCBHandlerTable:
    global _CACHE_KEY, _CACHE_TABLE

    if not TABLE_PATH.exists():
        raise FileNotFoundError(f"CCB handler table not found: {TABLE_PATH}")

    stat = TABLE_PATH.stat()
    cache_key = (stat.st_mtime_ns, stat.st_size)

    with _CACHE_LOCK:
        if _CACHE_KEY == cache_key and _CACHE_TABLE is not None:
            return _CACHE_TABLE

        with TABLE_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            try:
                raw_header = next(reader)
            except StopIteration as exc:
                raise ValueError(f"CCB handler table is empty: {TABLE_PATH}") from exc

            header = tuple(_normalize_row(raw_header))
            if header != EXPECTED_HEADERS:
                raise ValueError(
                    f"Unexpected CCB handler table headers: {header!r}; expected {EXPECTED_HEADERS!r}"
                )

            records: list[HandlerRecord] = []
            for raw_row in reader:
                row = _normalize_row(raw_row)
                if not any(row):
                    continue
                record = HandlerRecord(
                    sequence=row[0],
                    department=_compact_text(row[1]),
                    role=_compact_text(row[2]),
                    owner_name=_mask_person_name(row[3]),
                    office_phone=_compact_text(row[4]),
                    responsibilities=_compact_text(row[5]),
                )
                if not any(
                    [
                        record.sequence,
                        record.department,
                        record.role,
                        record.owner_name,
                        record.office_phone,
                        record.responsibilities,
                    ]
                ):
                    continue
                records.append(record)

        if not records:
            raise ValueError(f"CCB handler table has no usable records: {TABLE_PATH}")

        _CACHE_KEY = cache_key
        _CACHE_TABLE = CCBHandlerTable(source_path=TABLE_PATH, records=tuple(records))
        return _CACHE_TABLE