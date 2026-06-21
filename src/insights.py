from collections import Counter, defaultdict

BLOCK_ACTIONS = {'deny', 'block', 'drop', 'blocked', 'denied'}
CRITICAL_LEVELS = {'critical', 'alert', 'error', 'emerg', 'emergency', 'crit'}
PORT_SCAN_THRESHOLD = 10

_SERVICE_MAP = {
    'Web':    {'http', 'https', 'http_proxy', 'ssl', 'web'},
    'DNS':    {'dns'},
    'SSH':    {'ssh'},
    'RDP':    {'rdp', 'ms-rdp', 'microsoft-rdp'},
    'ICMP':   {'icmp', 'ping'},
    'FTP':    {'ftp', 'ftp-data'},
    'SMTP':   {'smtp', 'smtps', 'submission'},
    'Email':  {'imap', 'imaps', 'pop3', 'pop3s'},
    'SMB':    {'smb', 'netbios-ssn', 'microsoft-ds'},
    'Telnet': {'telnet'},
    'NTP':    {'ntp'},
    'SNMP':   {'snmp'},
    'LDAP':   {'ldap', 'ldaps'},
    'VPN':    {'ipsec', 'isakmp', 'openvpn', 'l2tp', 'pptp', 'ssl-vpn'},
}

_PORT_MAP = {
    '80': 'Web', '443': 'Web', '8080': 'Web', '8443': 'Web',
    '53':  'DNS',
    '22':  'SSH',
    '3389': 'RDP',
    '21': 'FTP', '20': 'FTP',
    '25': 'SMTP', '465': 'SMTP', '587': 'SMTP',
    '143': 'Email', '993': 'Email', '110': 'Email', '995': 'Email',
    '445': 'SMB', '139': 'SMB',
    '23':  'Telnet',
    '123': 'NTP',
    '161': 'SNMP', '162': 'SNMP',
    '389': 'LDAP', '636': 'LDAP',
    '500': 'VPN', '1701': 'VPN', '1194': 'VPN', '4500': 'VPN',
}

_TYPE_DESC = {
    'Web':    'TCP/80, 443',
    'DNS':    'UDP/53',
    'SSH':    'TCP/22',
    'RDP':    'TCP/3389',
    'ICMP':   'proto ICMP',
    'FTP':    'TCP/21',
    'SMTP':   'TCP/25, 587',
    'Email':  'TCP/143, 993',
    'SMB':    'TCP/445',
    'Telnet': 'TCP/23',
    'NTP':    'UDP/123',
    'SNMP':   'UDP/161',
    'LDAP':   'TCP/389',
    'VPN':    'UDP/500, 4500',
}


def get_insights(filtered_logs: list, timeline_data: dict) -> dict:
    return {
        'summary':          _insight_summary(filtered_logs),
        'traffic_types':    _insight_traffic_types(filtered_logs),
        'top_blockers':     _insight_top_blockers(filtered_logs),
        'peak_hour':        _insight_peak_hour(timeline_data),
        'unusual_services': _insight_unusual_services(filtered_logs),
        'port_scan':        _insight_port_scan_suspects(filtered_logs),
        'criticality':      _insight_criticality(filtered_logs),
    }


def _insight_traffic_types(logs: list) -> list:
    counter = Counter()
    for log in logs:
        svc = log.get('service', '').lower().strip()
        port = log.get('dstport', '').strip()
        proto = log.get('proto', '').lower().strip()

        label = None
        if svc:
            for name, keywords in _SERVICE_MAP.items():
                if svc in keywords:
                    label = name
                    break
        if label is None and port:
            label = _PORT_MAP.get(port)
        if label is None and proto == 'icmp':
            label = 'ICMP'
        if label is None and svc:
            label = svc.upper()

        if label:
            counter[label] += 1

    return [(label, count, _TYPE_DESC.get(label, '')) for label, count in counter.most_common(10)]


def _insight_summary(logs: list) -> dict:
    total = len(logs)
    if total == 0:
        return {'total': 0, 'period': None, 'block_pct': 0.0}

    dts = [l['_dt'] for l in logs if l.get('_dt')]
    period = None
    if dts:
        first = min(dts)
        last  = max(dts)
        period = (first.strftime('%Y-%m-%d %H:%M'), last.strftime('%Y-%m-%d %H:%M'))

    block_count = sum(
        1 for l in logs if l.get('action', '').lower() in BLOCK_ACTIONS
    )
    return {
        'total': total,
        'period': period,
        'block_pct': block_count / total * 100,
        'block_count': block_count,
    }


def _insight_top_blockers(logs: list) -> list:
    block_logs = [l for l in logs if l.get('action', '').lower() in BLOCK_ACTIONS]
    total_blocks = len(block_logs)
    if total_blocks == 0:
        return []

    counter = Counter(l.get('srcip', '') for l in block_logs if l.get('srcip'))
    result = []
    for ip, count in counter.most_common(3):
        result.append({
            'ip':    ip,
            'count': count,
            'pct':   count / total_blocks * 100,
        })
    return result


def _insight_peak_hour(timeline_data: dict) -> dict:
    if not timeline_data:
        return {}

    counts = list(timeline_data.values())
    avg = sum(counts) / len(counts)
    peak_hour = max(timeline_data, key=timeline_data.get)
    peak_count = timeline_data[peak_hour]
    diff_pct = (peak_count - avg) / max(avg, 1) * 100

    return {
        'hour':      peak_hour,
        'count':     peak_count,
        'avg':       avg,
        'diff_pct':  diff_pct,
    }


def _insight_unusual_services(logs: list) -> list:
    block_logs = [l for l in logs if l.get('action', '').lower() in BLOCK_ACTIONS]
    if not block_logs:
        return []

    all_services = Counter(
        l.get('service', '') for l in logs if l.get('service')
    )
    top10 = {svc for svc, _ in all_services.most_common(10)}

    unusual = Counter(
        l.get('service', '') for l in block_logs
        if l.get('service') and l['service'] not in top10
    )
    return [svc for svc, _ in unusual.most_common(10)]


def _insight_port_scan_suspects(logs: list) -> list:
    ip_ports = defaultdict(set)
    for log in logs:
        ip   = log.get('srcip')
        port = log.get('dstport')
        if ip and port:
            ip_ports[ip].add(port)

    suspects = [
        (ip, len(ports))
        for ip, ports in ip_ports.items()
        if len(ports) >= PORT_SCAN_THRESHOLD
    ]
    suspects.sort(key=lambda x: -x[1])
    return suspects[:10]


def _insight_criticality(logs: list) -> dict:
    total = len(logs)
    if total == 0:
        return {'pct_critical': 0.0, 'trend': 'sem dados'}

    def _pct_crit(subset):
        if not subset:
            return 0.0
        return sum(
            1 for l in subset
            if l.get('level', '').lower() in CRITICAL_LEVELS
        ) / len(subset) * 100

    pct_total = _pct_crit(logs)

    chronological = sorted((l for l in logs if l.get('_dt')), key=lambda l: l['_dt'])
    if len(chronological) < 2:
        return {
            'pct_critical': pct_total,
            'trend':        'sem dados',
            'pct_first':    0.0,
            'pct_second':   0.0,
        }

    mid = len(chronological) // 2
    first_half  = chronological[:mid]
    second_half = chronological[mid:]

    pct_first  = _pct_crit(first_half)
    pct_second = _pct_crit(second_half)

    if pct_first == 0:
        trend = 'crescente' if pct_second > 0 else 'estável'
    else:
        diff = (pct_second - pct_first) / pct_first * 100
        if diff > 20:
            trend = 'crescente'
        elif diff < -20:
            trend = 'decrescente'
        else:
            trend = 'estável'

    return {
        'pct_critical': pct_total,
        'trend':        trend,
        'pct_first':    pct_first,
        'pct_second':   pct_second,
    }
