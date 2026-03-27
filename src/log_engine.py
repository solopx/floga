import re
import os
import csv
import json
import logging
from collections import Counter
from typing import Dict, List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass


logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')


@dataclass
class FieldCondition:
    field: Optional[str]
    operator: str
    value: str
    connector: str


@dataclass
class FilterCriteria:
    conditions: List[FieldCondition]
    date_start: Optional[datetime]
    date_end: Optional[datetime]


class LogEngine:
    LOG_PATTERN = re.compile(r'(\w+)=((?:".*?")|\S+)')
    DATE_FORMATS = ('%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y')
    _HOUR_FMT   = '%Y-%m-%d %H:00'
    _TOKEN_RE   = re.compile(r'\s+(AND|OR)\s+', re.IGNORECASE)
    _FIELD_RE   = re.compile(r'^(\w+)(==|!=|:)(.+)$')

    def __init__(self):
        self.all_logs: List[Dict[str, str]] = []
        self.filtered_logs: List[Dict[str, str]] = []
        self.columns: List[str] = []

    def parse_line(self, line: str) -> Dict[str, str]:
        parsed = {}
        for key, value in self.LOG_PATTERN.findall(line):
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            parsed[key] = value
        return parsed

    def load_file(self, filepath: str, progress_cb=None) -> Tuple[int, int]:
        self.all_logs.clear()
        all_keys = set()
        size = os.path.getsize(filepath)
        total_lines = 0
        valid_lines = 0
        _CHUNK = 50_000

        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.replace('\x00', '').strip()
                if not line:
                    continue
                total_lines += 1
                data = self.parse_line(line)
                if data:
                    valid_lines += 1
                all_keys.update(data.keys())
                data['_dt'] = self.parse_log_datetime(data)
                self.all_logs.append(data)
                if progress_cb and total_lines % _CHUNK == 0:
                    progress_cb(f.buffer.tell() / size)

        if total_lines > 0 and valid_lines == 0:
            raise ValueError(
                'O arquivo não contém entradas no formato key=value.\n\n'
                'Esta aplicação suporta apenas logs  no formato:\n'
                '  chave=valor chave="valor com espaços" ...\n\n'
                'Verifique se o arquivo selecionado é um arquivo log válido.'
            )

        priority = ['date', 'time', 'user', 'srcip', 'dstip',
                    'action', 'status', 'level', 'msg']
        self.columns = [c for c in priority if c in all_keys]
        self.columns += [c for c in sorted(all_keys) if c not in self.columns]

        return len(self.all_logs), size

    def parse_query(self, query: str) -> List[FieldCondition]:
        if not query.strip():
            return []

        parts = self._TOKEN_RE.split(query.strip())
        conditions: List[FieldCondition] = []
        pending_connector = 'AND'

        for part in parts:
            upper = part.strip().upper()
            if upper in ('AND', 'OR'):
                pending_connector = upper
                continue
            token = part.strip()
            if not token:
                continue
            m = self._FIELD_RE.match(token)
            if m:
                field, op, val = m.group(1), m.group(2), m.group(3)
                if op == '==':
                    operator = 'eq'
                elif op == '!=':
                    operator = 'neq'
                else:
                    operator = 'contains'
                cond = FieldCondition(field=field.lower(), operator=operator,
                                      value=val.lower(), connector=pending_connector)
            else:
                cond = FieldCondition(field=None, operator='contains',
                                      value=token.lower(), connector=pending_connector)
            conditions.append(cond)
            pending_connector = 'AND'

        return conditions

    def parse_log_datetime(self, log: Dict[str, str]) -> Optional[datetime]:
        log_date = log.get('date', '').strip()
        log_time = log.get('time', '').strip()
        if not log_date or not log_time:
            return None

        for fmt in self.DATE_FORMATS:
            try:
                return datetime.strptime(f'{log_date} {log_time}',
                                         f'{fmt} %H:%M:%S')
            except ValueError:
                continue
        return None

    def _eval_condition(self, cond: FieldCondition, log: dict) -> bool:
        if cond.field is None:
            return any(cond.value in str(v).lower() for k, v in log.items() if k != '_dt')
        raw = log.get(cond.field)
        if raw is None:
            return False
        field_val = str(raw).lower()
        if cond.operator == 'contains':
            return cond.value in field_val
        if cond.operator == 'eq':
            return field_val == cond.value
        if cond.operator == 'neq':
            return field_val != cond.value
        return False

    def apply_filter(self, criteria: FilterCriteria) -> int:
        self.filtered_logs.clear()

        for log in self.all_logs:
            if criteria.date_start or criteria.date_end:
                log_dt = log['_dt'] if '_dt' in log else self.parse_log_datetime(log)
                if log_dt is None:
                    continue
                if criteria.date_start and log_dt < criteria.date_start:
                    continue
                if criteria.date_end and log_dt > criteria.date_end:
                    continue

            if criteria.conditions:
                result = self._eval_condition(criteria.conditions[0], log)
                for cond in criteria.conditions[1:]:
                    ev = self._eval_condition(cond, log)
                    result = (result and ev) if cond.connector == 'AND' else (result or ev)
                if not result:
                    continue

            self.filtered_logs.append(log)

        return len(self.filtered_logs)

    def get_page(self, page_num: int, page_size: int) -> List[Dict[str, str]]:
        start = page_num * page_size
        end = start + page_size
        return self.filtered_logs[start:end]

    def sort_logs(self, column: str, ascending: bool = True):
        try:
            self.filtered_logs.sort(
                key=lambda x: float(x.get(column, 0)),
                reverse=not ascending
            )
        except ValueError:
            self.filtered_logs.sort(
                key=lambda x: str(x.get(column, '')).lower(),
                reverse=not ascending
            )

    def export_csv(self, filepath: str):
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(self.columns)
            for log in self.filtered_logs:
                writer.writerow([log.get(c, '') for c in self.columns])

    def export_json(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            data = [{k: v for k, v in log.items() if k != '_dt'} for log in self.filtered_logs]
            json.dump(data, f, indent=2)

    def get_timeline_data(self) -> Dict[str, int]:
        timeline = Counter()
        for log in self.filtered_logs:
            log_dt = log['_dt'] if '_dt' in log else self.parse_log_datetime(log)
            if log_dt:
                timeline[log_dt.strftime(self._HOUR_FMT)] += 1
        return dict(sorted(timeline.items()))

    def get_top_data(self, field: str, limit: int = 10) -> List[Tuple[str, int]]:
        counter = Counter(log.get(field, '-') for log in self.filtered_logs)
        return counter.most_common(limit)

    def get_30min_distribution(self) -> Dict[str, int]:
        intervals = Counter()
        for log in self.filtered_logs:
            log_dt = log['_dt'] if '_dt' in log else self.parse_log_datetime(log)
            if log_dt:
                minute_interval = '00-30' if log_dt.minute < 30 else '30-00'
                key = f'{log_dt.hour:02d}:{minute_interval}'
                intervals[key] += 1
        return dict(sorted(intervals.items()))

    def get_level_counts(self) -> Counter:
        return Counter(log.get('level', 'unknown') for log in self.filtered_logs)

    def group_by(self, field: str) -> List[Tuple[str, int]]:
        counter = Counter(
            log.get(field, '') for log in self.filtered_logs if log.get(field)
        )
        return counter.most_common()

    def get_error_time_series(self) -> Dict[str, int]:
        counter = Counter()
        for log in self.filtered_logs:
            level = log.get('level', '').lower()
            if level in ('error', 'critical', 'alert'):
                dt = log['_dt'] if '_dt' in log else self.parse_log_datetime(log)
                if dt:
                    counter[dt.strftime(self._HOUR_FMT)] += 1
        return dict(sorted(counter.items()))
