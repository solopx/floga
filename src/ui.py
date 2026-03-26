import os
import logging
import threading
from collections import Counter
from datetime import datetime, time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkcalendar import DateEntry

try:
    import matplotlib
    matplotlib.use('TkAgg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    plt.ioff()
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("Matplotlib não instalado. Gráficos desabilitados.")

from typing import Dict, List

from log_engine import LogEngine, FilterCriteria


class UIStyle:
    BG_MAIN          = "#F0F2F7"
    BG_CARD          = "#FFFFFF"
    BG_TOOLBAR       = "#1E3148"
    BG_NAV           = "#EAF0F8"
    BG_STATUS        = "#E4ECF5"
    BG_BUTTON        = "#2B6CB0"
    BG_BUTTON_ACTIVE = "#1A56A0"
    BG_TBTN          = "#2D4A6E"
    BG_TBTN_ACTIVE   = "#3A5F85"
    BORDER_COLOR     = "#C8D5E0"
    SEPARATOR_COLOR  = "#D1DBE8"
    ACCENT           = BG_BUTTON
    SUCCESS          = "#276749"
    WARNING          = "#975A16"
    DANGER           = "#C53030"
    FG_MAIN          = "#1A2535"
    FG_ON_DARK       = "#EDF2F8"
    FG_MUTED         = "#718096"
    FG_STATUS        = "#4A5568"
    FG_BUTTON        = "#FFFFFF"
    FONT_NORMAL      = ('Segoe UI', 10)
    FONT_BOLD        = ('Segoe UI', 10, 'bold')
    FONT_SMALL       = ('Segoe UI', 9)
    FONT_MONO        = ('Consolas', 10)

    @staticmethod
    def apply_ttk_styles():
        style = ttk.Style()
        style.theme_use('clam')

        style.configure(
            "Treeview",
            background=UIStyle.BG_CARD,
            foreground=UIStyle.FG_MAIN,
            fieldbackground=UIStyle.BG_CARD,
            rowheight=26,
            bordercolor=UIStyle.BORDER_COLOR,
            font=UIStyle.FONT_NORMAL,
        )
        style.map(
            "Treeview",
            background=[("selected", UIStyle.ACCENT)],
            foreground=[("selected", UIStyle.FG_BUTTON)],
        )
        style.configure(
            "Treeview.Heading",
            background="#EDF2F8",
            foreground=UIStyle.FG_MAIN,
            font=UIStyle.FONT_BOLD,
            relief=tk.FLAT,
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#DDE7F2")],
        )
        style.configure(
            "TSpinbox",
            background=UIStyle.BG_CARD,
            foreground=UIStyle.FG_MAIN,
            fieldbackground=UIStyle.BG_CARD,
            insertcolor=UIStyle.FG_MAIN,
            arrowcolor=UIStyle.FG_MUTED,
        )

    @staticmethod
    def create_button(parent, text, command, **kwargs):
        return tk.Button(
            parent, text=text, command=command,
            bg=UIStyle.BG_BUTTON,
            fg=UIStyle.FG_BUTTON,
            font=UIStyle.FONT_NORMAL,
            relief=tk.FLAT,
            cursor='hand2',
            activebackground=UIStyle.BG_BUTTON_ACTIVE,
            activeforeground=UIStyle.FG_BUTTON,
            padx=12, pady=6,
            **kwargs
        )

    @staticmethod
    def create_toolbar_button(parent, text, command, **kwargs):
        return tk.Button(
            parent, text=text, command=command,
            bg=UIStyle.BG_TBTN,
            fg=UIStyle.FG_ON_DARK,
            font=UIStyle.FONT_NORMAL,
            relief=tk.FLAT,
            cursor='hand2',
            activebackground=UIStyle.BG_TBTN_ACTIVE,
            activeforeground=UIStyle.FG_ON_DARK,
            padx=12, pady=6,
            bd=0,
            **kwargs
        )

    @staticmethod
    def create_label(parent, text, bold=False, font=None, bg=None, fg=None, **kwargs):
        if font is None:
            font = UIStyle.FONT_BOLD if bold else UIStyle.FONT_NORMAL
        return tk.Label(
            parent, text=text,
            bg=bg if bg is not None else UIStyle.BG_MAIN,
            fg=fg if fg is not None else UIStyle.FG_MAIN,
            font=font,
            **kwargs
        )

    @staticmethod
    def create_entry(parent, textvariable, width=30, **kwargs):
        return tk.Entry(
            parent,
            textvariable=textvariable,
            font=UIStyle.FONT_NORMAL,
            bg=UIStyle.BG_CARD,
            fg=UIStyle.FG_MAIN,
            insertbackground=UIStyle.FG_MAIN,
            relief=tk.SOLID,
            bd=1,
            width=width,
            **kwargs
        )

    @staticmethod
    def create_frame(parent, **kwargs):
        return tk.Frame(parent, bg=UIStyle.BG_MAIN, **kwargs)


class SidebarView:
    WIDTH = 190

    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=UIStyle.BG_TOOLBAR, width=self.WIDTH)
        self.frame.pack_propagate(False)

        header = tk.Frame(self.frame, bg=UIStyle.BG_TOOLBAR, pady=18, padx=14)
        header.pack(fill=tk.X)
        tk.Label(
            header, text='FLogA',
            bg=UIStyle.BG_TOOLBAR, fg=UIStyle.FG_ON_DARK,
            font=('Segoe UI', 13, 'bold'),
        ).pack(anchor='w')
        tk.Label(
            header, text='Fortinet Log Analyzer',
            bg=UIStyle.BG_TOOLBAR, fg='#6B8CAE',
            font=('Segoe UI', 8),
        ).pack(anchor='w')

        tk.Frame(self.frame, bg=UIStyle.BG_TBTN_ACTIVE, height=1).pack(fill=tk.X)

        nav = tk.Frame(self.frame, bg=UIStyle.BG_TOOLBAR, pady=10)
        nav.pack(fill=tk.X)

        self.btn_load   = self._nav_btn(nav, 'Abrir Arquivo')
        self.btn_charts = self._nav_btn(nav, 'Gráficos')
        self.btn_csv    = self._nav_btn(nav, 'Exportar CSV')
        self.btn_json   = self._nav_btn(nav, 'Exportar JSON')

        tk.Frame(nav, bg=UIStyle.BG_TBTN_ACTIVE, height=1).pack(
            fill=tk.X, padx=14, pady=(6, 0)
        )
        self.btn_help = self._nav_btn(nav, 'Ajuda')

        self.charts_menu = tk.Menu(
            self.frame, tearoff=0,
            bg=UIStyle.BG_CARD, fg=UIStyle.FG_MAIN,
            activebackground=UIStyle.ACCENT,
            activeforeground=UIStyle.FG_BUTTON,
            font=UIStyle.FONT_NORMAL,
            bd=1, relief=tk.SOLID,
        )

        self.progress = ttk.Progressbar(
            self.frame, orient=tk.HORIZONTAL, mode='determinate'
        )
        self.progress.pack(side=tk.BOTTOM, fill=tk.X, padx=12, pady=(0, 8))

        footer = tk.Frame(self.frame, bg=UIStyle.BG_TOOLBAR, padx=14, pady=10)
        footer.pack(side=tk.BOTTOM, fill=tk.X)
        tk.Label(
            footer, text='V2',
            bg=UIStyle.BG_TOOLBAR, fg='#6B8CAE',
            font=UIStyle.FONT_SMALL,
        ).pack(anchor='w')

    def _nav_btn(self, parent, text):
        btn = tk.Button(
            parent, text=text,
            bg=UIStyle.BG_TOOLBAR,
            fg=UIStyle.FG_ON_DARK,
            font=UIStyle.FONT_NORMAL,
            relief=tk.FLAT,
            cursor='hand2',
            activebackground=UIStyle.BG_TBTN_ACTIVE,
            activeforeground=UIStyle.FG_ON_DARK,
            anchor='w',
            padx=14, pady=10,
            bd=0,
        )
        btn.pack(fill=tk.X)
        btn.bind('<Enter>', lambda e: btn.config(bg=UIStyle.BG_TBTN_ACTIVE))
        btn.bind('<Leave>', lambda e: btn.config(bg=UIStyle.BG_TOOLBAR))
        return btn


class FilterView:
    def __init__(self, parent):
        self.frame = tk.Frame(
            parent, bg=UIStyle.BG_CARD,
            highlightbackground=UIStyle.BORDER_COLOR,
            highlightthickness=1,
        )

        grid = tk.Frame(self.frame, bg=UIStyle.BG_CARD, padx=12, pady=10)
        grid.pack(fill=tk.X)
        grid.columnconfigure(0, weight=1)

        UIStyle.create_label(
            grid, 'Busca Geral', bold=True, bg=UIStyle.BG_CARD
        ).grid(row=0, column=0, sticky='w', pady=(0, 4))

        UIStyle.create_label(
            grid, 'Data/Hora Inicial', bold=True, bg=UIStyle.BG_CARD
        ).grid(row=0, column=2, sticky='w', padx=(12, 0), pady=(0, 4))

        UIStyle.create_label(
            grid, 'Data/Hora Final', bold=True, bg=UIStyle.BG_CARD
        ).grid(row=0, column=4, sticky='w', padx=(12, 0), pady=(0, 4))

        self.search_var = tk.StringVar()
        UIStyle.create_entry(grid, self.search_var, width=50).grid(
            row=1, column=0, sticky='ew', ipady=4
        )

        self._vsep(grid, column=1)
        self._vsep(grid, column=3)

        self.date_start, self.hour_start, self.min_start, self.sec_start = \
            self._create_datetime_controls(grid, row=1, column=2, default_time='00:00:00')

        self.date_end, self.hour_end, self.min_end, self.sec_end = \
            self._create_datetime_controls(grid, row=1, column=4, default_time='23:59:59')

        ctrl = tk.Frame(grid, bg=UIStyle.BG_CARD)
        ctrl.grid(row=0, column=5, rowspan=2, sticky='ns', padx=(16, 0))

        self.datetime_enabled = tk.BooleanVar(value=False)
        tk.Checkbutton(
            ctrl, text='Filtrar por periodo',
            variable=self.datetime_enabled,
            bg=UIStyle.BG_CARD,
            fg=UIStyle.FG_MAIN,
            activebackground=UIStyle.BG_CARD,
            selectcolor=UIStyle.BG_CARD,
            font=UIStyle.FONT_NORMAL,
        ).pack(anchor='w', pady=(0, 6))

        self.btn_clear = UIStyle.create_button(ctrl, 'Limpar Filtros', None)
        self.btn_clear.pack(fill=tk.X)

    def _vsep(self, parent, column):
        tk.Frame(
            parent, bg=UIStyle.SEPARATOR_COLOR, width=1
        ).grid(row=0, column=column, rowspan=2, sticky='ns', padx=10)

    def _create_datetime_controls(self, parent, row, column, default_time):
        container = tk.Frame(parent, bg=UIStyle.BG_CARD)
        container.grid(row=row, column=column, sticky='w', padx=(12, 0))

        date_entry = DateEntry(
            container, width=11, date_pattern='yyyy-mm-dd',
            background=UIStyle.BG_BUTTON,
            foreground=UIStyle.FG_BUTTON,
            borderwidth=1,
            font=UIStyle.FONT_NORMAL,
            headersbackground=UIStyle.BG_TOOLBAR,
            headersforeground=UIStyle.FG_ON_DARK,
            selectbackground=UIStyle.ACCENT,
            selectforeground=UIStyle.FG_BUTTON,
            normalbackground=UIStyle.BG_CARD,
            normalforeground=UIStyle.FG_MAIN,
            weekendbackground=UIStyle.BG_CARD,
            weekendforeground=UIStyle.FG_MAIN,
            othermonthbackground=UIStyle.BG_MAIN,
            othermonthforeground=UIStyle.FG_MUTED,
        )
        date_entry.pack(side=tk.LEFT, ipady=3)

        tk.Frame(container, bg=UIStyle.BG_CARD, width=8).pack(side=tk.LEFT)

        h, m, s = default_time.split(':')

        hour = ttk.Spinbox(container, from_=0, to=23, width=3,
                           format='%02.0f', font=UIStyle.FONT_NORMAL)
        hour.set(h)
        hour.pack(side=tk.LEFT, ipady=3)

        self._time_sep(container)

        minute = ttk.Spinbox(container, from_=0, to=59, width=3,
                             format='%02.0f', font=UIStyle.FONT_NORMAL)
        minute.set(m)
        minute.pack(side=tk.LEFT, ipady=3)

        self._time_sep(container)

        second = ttk.Spinbox(container, from_=0, to=59, width=3,
                             format='%02.0f', font=UIStyle.FONT_NORMAL)
        second.set(s)
        second.pack(side=tk.LEFT, ipady=3)

        return date_entry, hour, minute, second

    def _time_sep(self, container):
        tk.Label(
            container, text=':',
            bg=UIStyle.BG_CARD,
            fg=UIStyle.FG_MUTED,
            font=UIStyle.FONT_BOLD,
        ).pack(side=tk.LEFT, padx=1)


class TableView:
    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=UIStyle.BG_MAIN)

        container = tk.Frame(self.frame, bg=UIStyle.BG_CARD)
        container.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(container, show='headings', selectmode='extended')
        self.tree.tag_configure('critical', background="#FFE4E4", foreground="#9B2C2C")
        self.tree.tag_configure('warning',  background="#FEF3C7", foreground="#92400E")
        self.tree.tag_configure('notice',   background="#FDE8D8", foreground="#9A3412")
        self.tree.tag_configure('success',  background="#D1FAE5", foreground="#065F46")
        self.tree.tag_configure('info',     background="#DBEAFE", foreground="#1E40AF")
        self.tree.tag_configure('evenrow',  background=UIStyle.BG_CARD)
        self.tree.tag_configure('oddrow',   background="#F7FAFC")

        self.vsb = ttk.Scrollbar(container, orient='vertical',   command=self.tree.yview)
        self.hsb = ttk.Scrollbar(container, orient='horizontal', command=self.tree.xview)
        self.tree.configure(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)

        self.tree.grid(row=0, column=0, sticky='nsew')
        self.vsb.grid(row=0, column=1, sticky='ns')
        self.hsb.grid(row=1, column=0, sticky='ew')

        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)


class MetricsView:
    _LEVEL_COLORS = {
        'critical': '#C53030', 'alert': '#C53030', 'error': '#C53030',
        'emerg': '#C53030', 'emergency': '#C53030', 'crit': '#C53030',
        'high': '#E53E3E',
        'warning': '#D97706',
        'medium': '#DD6B20',
        'notice': '#CA8A04',
        'low': '#65A30D',
        'info': '#2B6CB0', 'information': '#2B6CB0', 'debug': '#718096',
    }
    _LEVEL_ORDER = [
        'critical', 'alert', 'error', 'emerg', 'emergency', 'crit',
        'high', 'warning', 'medium', 'notice', 'low',
        'info', 'information', 'debug',
    ]
    _FALLBACK_PALETTE = ['#6B46C1', '#B83280', '#0694A2', '#65A30D', '#1C64F2']

    def __init__(self, parent):
        self.frame = tk.Frame(parent, bg=UIStyle.BG_CARD, width=220)
        self.frame.pack_propagate(False)

        body = tk.Frame(self.frame, bg=UIStyle.BG_CARD, padx=12, pady=12)
        body.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            body, text='SEVERIDADE DOS EVENTOS',
            bg=UIStyle.BG_CARD, fg=UIStyle.FG_MUTED,
            font=('Segoe UI', 8, 'bold'),
        ).pack(anchor='w', pady=(0, 8))

        self._severity_frame = tk.Frame(body, bg=UIStyle.BG_CARD)
        self._severity_frame.pack(fill=tk.X)
        self._level_vars: Dict[str, tk.StringVar] = {}
        self._current_level_keys: List[str] = []

        tk.Frame(body, bg=UIStyle.BORDER_COLOR, height=1).pack(fill=tk.X, pady=12)

        tk.Label(
            body, text='PRINCIPAIS ORIGENS',
            bg=UIStyle.BG_CARD, fg=UIStyle.FG_MUTED,
            font=('Segoe UI', 8, 'bold'),
        ).pack(anchor='w', pady=(0, 6))

        self._origins_frame = tk.Frame(body, bg=UIStyle.BG_CARD)
        self._origins_frame.pack(fill=tk.X)

        tk.Frame(body, bg=UIStyle.BORDER_COLOR, height=1).pack(fill=tk.X, pady=12)

        tk.Label(
            body, text='PRINCIPAIS DESTINOS',
            bg=UIStyle.BG_CARD, fg=UIStyle.FG_MUTED,
            font=('Segoe UI', 8, 'bold'),
        ).pack(anchor='w', pady=(0, 6))

        self._dstips_frame = tk.Frame(body, bg=UIStyle.BG_CARD)
        self._dstips_frame.pack(fill=tk.X)

    def _sort_levels(self, levels):
        order_map = {lvl: i for i, lvl in enumerate(self._LEVEL_ORDER)}
        known = sorted([l for l in levels if l in order_map], key=lambda l: order_map[l])
        unknown = sorted([l for l in levels if l not in order_map])
        return known + unknown

    def _color_for(self, level, index):
        if level in self._LEVEL_COLORS:
            return self._LEVEL_COLORS[level]
        return self._FALLBACK_PALETTE[index % len(self._FALLBACK_PALETTE)]

    def _rebuild_severity_cards(self, sorted_levels):
        for w in self._severity_frame.winfo_children():
            w.destroy()
        self._level_vars.clear()
        for i, level in enumerate(sorted_levels):
            var = tk.StringVar(value='—')
            self._level_vars[level] = var
            self._make_metric_card(self._severity_frame, level.upper(), var,
                                   self._color_for(level, i))
        self._current_level_keys = sorted_levels

    def _make_metric_card(self, parent, name, var, color):
        card = tk.Frame(parent, bg=UIStyle.BG_CARD, pady=4)
        card.pack(fill=tk.X, pady=2)

        tk.Frame(card, bg=color, width=4).pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        info = tk.Frame(card, bg=UIStyle.BG_CARD)
        info.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(
            info, text=name,
            bg=UIStyle.BG_CARD, fg=UIStyle.FG_MUTED,
            font=('Segoe UI', 8, 'bold'),
        ).pack(anchor='w')
        tk.Label(
            info, textvariable=var,
            bg=UIStyle.BG_CARD, fg=UIStyle.FG_MAIN,
            font=('Segoe UI', 14, 'bold'),
        ).pack(anchor='w')

    def update(self, logs):
        level_counter = Counter()
        srcip_counter = Counter()
        dstip_counter = Counter()

        for log in logs:
            level = log.get('level', '').lower().strip()
            if level:
                level_counter[level] += 1

            srcip = log.get('srcip', '')
            if srcip:
                srcip_counter[srcip] += 1

            dstip = log.get('dstip', '')
            if dstip:
                dstip_counter[dstip] += 1

        sorted_levels = self._sort_levels(list(level_counter.keys()))

        if sorted_levels != self._current_level_keys:
            self._rebuild_severity_cards(sorted_levels)

        for level, var in self._level_vars.items():
            var.set(f'{level_counter.get(level, 0):,}')

        self._populate_ip_list(self._origins_frame, srcip_counter)
        self._populate_ip_list(self._dstips_frame, dstip_counter)

    def _populate_ip_list(self, frame, counter):
        for w in frame.winfo_children():
            w.destroy()
        for ip, count in counter.most_common(5):
            row = tk.Frame(frame, bg=UIStyle.BG_CARD)
            row.pack(fill=tk.X, pady=1)
            tk.Label(
                row, text=ip,
                bg=UIStyle.BG_CARD, fg=UIStyle.FG_MAIN,
                font=UIStyle.FONT_SMALL, anchor='w',
            ).pack(side=tk.LEFT)
            tk.Label(
                row, text=f'{count:,}',
                bg=UIStyle.BG_CARD, fg=UIStyle.ACCENT,
                font=('Segoe UI', 9, 'bold'),
            ).pack(side=tk.RIGHT)


class NavigationView:
    def __init__(self, parent):
        self.frame = tk.Frame(
            parent, bg=UIStyle.BG_NAV,
            highlightbackground=UIStyle.BORDER_COLOR,
            highlightthickness=1,
        )

        self.btn_prev = UIStyle.create_button(self.frame, '◀ Anterior', None)
        self.btn_prev.pack(side=tk.LEFT, padx=(8, 2), pady=5)

        self.btn_next = UIStyle.create_button(self.frame, 'Proxima ▶', None)
        self.btn_next.pack(side=tk.LEFT, padx=2, pady=5)

        self.label = tk.Label(
            self.frame,
            text='Pagina 1 / 1',
            bg=UIStyle.BG_NAV,
            fg=UIStyle.FG_STATUS,
            font=UIStyle.FONT_BOLD,
        )
        self.label.pack(side=tk.LEFT, padx=14)


class StatusView:
    def __init__(self, parent):
        self.var = tk.StringVar(value='Pronto')
        self.label = tk.Label(
            parent,
            textvariable=self.var,
            bd=0, anchor=tk.W,
            bg=UIStyle.BG_STATUS,
            fg=UIStyle.FG_STATUS,
            font=UIStyle.FONT_SMALL,
            padx=10, pady=4,
        )


class FLogAApp:
    PAGE_SIZE   = 3000
    DEBOUNCE_MS = 300
    APPNAME     = "FLogA - Fortinet Log Analyzer"
    APPVERSION  = "V2"

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(self.APPNAME + " " + self.APPVERSION)
        self.root.geometry('1600x900')
        self.root.configure(bg=UIStyle.BG_MAIN)

        UIStyle.apply_ttk_styles()

        self.engine = LogEngine()
        self.current_page = 0
        self.sort_state: Dict[str, bool] = {}
        self._debounce_id = None
        self._chart_windows = []
        self._base_status = 'Pronto'

        self._build_ui()
        self._connect_events()
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _build_ui(self):
        self.sidebar = SidebarView(self.root)
        self.sidebar.frame.pack(side=tk.LEFT, fill=tk.Y)

        content = tk.Frame(self.root, bg=UIStyle.BG_MAIN)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.filters = FilterView(content)
        self.filters.frame.pack(fill=tk.X, padx=10, pady=(8, 0))

        main = UIStyle.create_frame(content)
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=(6, 0))

        self.metrics = MetricsView(main)
        self.metrics.frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))

        self.table = TableView(main)
        self.table.frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.navigation = NavigationView(content)
        self.navigation.frame.pack(fill=tk.X, padx=10, pady=(4, 4))

        self.status = StatusView(content)
        self.status.label.pack(side=tk.BOTTOM, fill=tk.X)

        self.context_menu = tk.Menu(
            self.root, tearoff=0,
            bg=UIStyle.BG_CARD, fg=UIStyle.FG_MAIN,
            activebackground=UIStyle.ACCENT,
            activeforeground=UIStyle.FG_BUTTON,
            font=UIStyle.FONT_NORMAL,
        )
        self.context_menu.add_command(
            label='Copiar Linhas Selecionadas',
            command=self._copy_selection,
        )

    def _connect_events(self):
        self.sidebar.btn_load.config(command=self._load_file)
        self.sidebar.btn_csv.config(command=lambda: self._export('csv'))
        self.sidebar.btn_json.config(command=lambda: self._export('json'))
        self.sidebar.btn_help.config(command=self._show_help)

        self.sidebar.btn_charts.config(command=self._show_charts_menu)
        self.sidebar.charts_menu.add_command(
            label='Volume de Logs', command=self._show_volume_chart
        )
        self.sidebar.charts_menu.add_command(
            label='Heatmap de Logs (30min)', command=self._show_heatmap_chart
        )
        self.sidebar.charts_menu.add_separator()
        self.sidebar.charts_menu.add_command(
            label='Top 5 IPs de Origem',
            command=lambda: self._show_top_chart('srcip', 'Top 5 IPs de Origem', 5)
        )
        self.sidebar.charts_menu.add_command(
            label='Top 5 IPs de Destino',
            command=lambda: self._show_top_chart('dstip', 'Top 5 IPs de Destino', 5)
        )
        self.sidebar.charts_menu.add_command(
            label='Top 5 Acoes',
            command=lambda: self._show_top_chart('action', 'Top 5 Acoes', 5)
        )
        self.sidebar.charts_menu.add_command(
            label='Distribuicao de Niveis',
            command=self._plot_level_distribution
        )
        self.sidebar.charts_menu.add_command(
            label='Erros/Critical ao Longo do Tempo',
            command=self._plot_error_trend
        )

        self.filters.search_var.trace_add('write', self._on_search_change)
        self.filters.btn_clear.config(command=self._clear_filters)

        self.filters.date_start.bind('<<DateEntrySelected>>', self._on_datetime_change)
        self.filters.date_end.bind('<<DateEntrySelected>>',   self._on_datetime_change)

        for spinbox in [
            self.filters.hour_start, self.filters.min_start, self.filters.sec_start,
            self.filters.hour_end,   self.filters.min_end,   self.filters.sec_end,
        ]:
            for event in ('<KeyRelease>', '<<Increment>>', '<<Decrement>>'):
                spinbox.bind(event, self._on_datetime_change)

        self.filters.datetime_enabled.trace_add('write', lambda *_: self._apply_filters())

        self.table.tree.bind('<Double-1>', self._show_details)
        self.table.tree.bind('<Button-3>', self._show_context_menu)

        self.navigation.btn_prev.config(command=self._prev_page)
        self.navigation.btn_next.config(command=self._next_page)

    def _load_file(self):
        path = filedialog.askopenfilename(filetypes=[('Logs', '*.log;*.txt')])
        if not path:
            return

        self.sidebar.btn_load.config(state=tk.DISABLED)
        self.sidebar.progress.config(mode='indeterminate')
        self.sidebar.progress.start(10)
        self.status.var.set('Carregando arquivo...')

        def _worker():
            try:
                total, size = self.engine.load_file(path)
                self.root.after(0, lambda: self._on_load_complete(path, total, size))
            except Exception as e:
                self.root.after(0, lambda: self._on_load_error(e))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_load_complete(self, path: str, total: int, size: int):
        self.sidebar.progress.stop()
        self.sidebar.progress.config(mode='determinate')
        self.sidebar.btn_load.config(state=tk.NORMAL)

        self.table.tree.delete(*self.table.tree.get_children())
        self.table.tree['columns'] = self.engine.columns

        for col in self.engine.columns:
            self.sort_state[col] = True
            self.table.tree.heading(
                col, text=col.upper(),
                command=lambda c=col: self._sort_by_column(c)
            )
            width = 320 if col in ['msg', 'logdesc'] else 120
            self.table.tree.column(col, width=width, anchor='w', stretch=False)

        self._base_status = (
            f'{os.path.basename(path)}  |  {total:,} linhas  |  '
            f'{size / 1024 / 1024:.2f} MB'
        )
        self._apply_filters()

    def _on_load_error(self, e: Exception):
        self.sidebar.progress.stop()
        self.sidebar.progress.config(mode='determinate')
        self.sidebar.btn_load.config(state=tk.NORMAL)
        logging.exception(e)
        messagebox.showerror('Erro', str(e))

    def _export(self, fmt: str):
        if not self.engine.filtered_logs:
            messagebox.showwarning('Aviso', 'Nada para exportar.')
            return

        ext = f'.{fmt}'
        path = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[(f'Arquivo {fmt.upper()}', f'*{ext}')]
        )
        if not path:
            return

        try:
            if fmt == 'csv':
                self.engine.export_csv(path)
            else:
                self.engine.export_json(path)
            messagebox.showinfo('Exportacao concluida', f'Arquivo salvo em:\n{path}')
        except Exception as e:
            logging.exception(e)
            messagebox.showerror('Erro', str(e))

    def _on_search_change(self, *_):
        if self._debounce_id:
            self.root.after_cancel(self._debounce_id)
        self._debounce_id = self.root.after(self.DEBOUNCE_MS, self._apply_filters)

    def _on_datetime_change(self, *_):
        if self.filters.datetime_enabled.get():
            self._on_search_change()

    def _apply_filters(self):
        conditions = self.engine.parse_query(self.filters.search_var.get().strip())

        date_start = None
        date_end   = None

        if self.filters.datetime_enabled.get():
            try:
                date_start = datetime.combine(
                    self.filters.date_start.get_date(),
                    time(int(self.filters.hour_start.get()),
                         int(self.filters.min_start.get()),
                         int(self.filters.sec_start.get()))
                )
                date_end = datetime.combine(
                    self.filters.date_end.get_date(),
                    time(int(self.filters.hour_end.get()),
                         int(self.filters.min_end.get()),
                         int(self.filters.sec_end.get()))
                )
            except Exception as e:
                logging.error(f'Erro ao processar data/hora: {e}')

        criteria = FilterCriteria(
            conditions=conditions,
            date_start=date_start,
            date_end=date_end,
        )

        self.engine.apply_filter(criteria)
        self.current_page = 0
        self._refresh_table()
        self._update_stats()

    def _clear_filters(self):
        today = datetime.now().date()
        self.filters.search_var.set('')
        self.filters.datetime_enabled.set(False)
        self.filters.date_start.set_date(today)
        self.filters.date_end.set_date(today)
        self.filters.hour_start.set('00')
        self.filters.min_start.set('00')
        self.filters.sec_start.set('00')
        self.filters.hour_end.set('23')
        self.filters.min_end.set('59')
        self.filters.sec_end.set('59')
        self._apply_filters()

    def _sort_by_column(self, column: str):
        asc = self.sort_state.get(column, True)
        self.engine.sort_logs(column, asc)
        self.sort_state[column] = not asc

        for col in self.engine.columns:
            indicator = ' ▲' if (col == column and asc) else (' ▼' if col == column else '')
            self.table.tree.heading(col, text=col.upper() + indicator)

        self._refresh_table()

    def _refresh_table(self):
        tree = self.table.tree
        tree.config(yscrollcommand='', xscrollcommand='')
        tree.delete(*tree.get_children())

        page_logs = self.engine.get_page(self.current_page, self.PAGE_SIZE)

        for index, log in enumerate(page_logs):
            vals = [
                log.get(c, '').upper() if c == 'level' else log.get(c, '')
                for c in self.engine.columns
            ]
            level  = log.get('level',  '').lower()
            action = log.get('action', '').lower()

            base_tag = 'evenrow' if index % 2 == 0 else 'oddrow'

            if level in ('alert', 'critical', 'error', 'emerg', 'emergency', 'crit') \
                    or action in ('deny', 'block'):
                tag = ('critical', base_tag)
            elif level in ('warning', 'medium'):
                tag = ('warning', base_tag)
            elif level == 'notice':
                tag = ('notice', base_tag)
            elif level == 'high':
                tag = ('critical', base_tag)
            elif level == 'low':
                tag = ('info', base_tag)
            elif action in ('accept', 'allow', 'pass', 'permitted'):
                tag = ('success', base_tag)
            elif level in ('information', 'info', 'debug'):
                tag = ('info', base_tag)
            else:
                tag = base_tag

            tree.insert('', tk.END, values=vals, tags=tag)

        tree.config(
            yscrollcommand=self.table.vsb.set,
            xscrollcommand=self.table.hsb.set,
        )

        total       = len(self.engine.filtered_logs)
        total_pages = max(1, (total - 1) // self.PAGE_SIZE + 1)
        self.navigation.label.config(
            text=f'Pagina {self.current_page + 1} / {total_pages}'
        )

        query = self.filters.search_var.get().strip()
        datetime_active = self.filters.datetime_enabled.get()

        if not query and not datetime_active:
            self.status.var.set(self._base_status)
        else:
            filter_hint = f'  ·  [{query}]' if query else '  ·  [período]'
            self.status.var.set(f'{total:,} resultados{filter_hint}')

    def _update_stats(self):
        self.metrics.update(self.engine.filtered_logs)

    def _show_help(self):
        win = tk.Toplevel(self.root)
        win.title('Ajuda')
        win.geometry('700x580')
        win.configure(bg=UIStyle.BG_MAIN)
        win.resizable(False, False)

        header = tk.Frame(win, bg=UIStyle.BG_TOOLBAR, pady=14, padx=16)
        header.pack(fill=tk.X)
        tk.Label(
            header, text='Ajuda — FLogA - Fortinet Log Analyzer',
            bg=UIStyle.BG_TOOLBAR, fg=UIStyle.FG_ON_DARK,
            font=UIStyle.FONT_BOLD,
        ).pack(anchor='w')

        body = tk.Frame(win, bg=UIStyle.BG_MAIN, padx=16, pady=12)
        body.pack(fill=tk.BOTH, expand=True)

        txt = tk.Text(
            body,
            font=UIStyle.FONT_NORMAL,
            bg=UIStyle.BG_CARD, fg=UIStyle.FG_MAIN,
            relief=tk.FLAT, bd=0,
            wrap=tk.WORD, padx=14, pady=12,
            state=tk.NORMAL,
            cursor='arrow',
            tabs=('105', '415'),
        )
        vsb = ttk.Scrollbar(body, orient='vertical', command=txt.yview)
        txt.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        txt.pack(fill=tk.BOTH, expand=True)

        txt.tag_configure('heading', font=UIStyle.FONT_BOLD,
                          foreground=UIStyle.FG_MAIN, spacing1=14, spacing3=2)
        txt.tag_configure('rule',    font=('Segoe UI', 8),
                          foreground=UIStyle.BORDER_COLOR, spacing3=6)
        txt.tag_configure('code',    font=UIStyle.FONT_MONO,
                          foreground=UIStyle.ACCENT,
                          background=UIStyle.BG_NAV)
        txt.tag_configure('label',   font=UIStyle.FONT_BOLD,
                          foreground=UIStyle.FG_MAIN)
        txt.tag_configure('body',    font=UIStyle.FONT_NORMAL,
                          foreground=UIStyle.FG_MAIN, spacing1=2)
        txt.tag_configure('th',      font=UIStyle.FONT_BOLD,
                          foreground=UIStyle.FG_MUTED)
        txt.tag_configure('muted',   font=UIStyle.FONT_SMALL,
                          foreground=UIStyle.FG_MUTED, spacing1=4)
        txt.tag_configure('note',    font=UIStyle.FONT_SMALL,
                          foreground=UIStyle.FG_MUTED, spacing1=6, lmargin1=14, lmargin2=14)

        def ins(text, base='body'):
            parts = text.split('`')
            for i, part in enumerate(parts):
                if part:
                    txt.insert(tk.END, part, 'code' if i % 2 == 1 else base)

        def h(text):
            txt.insert(tk.END, text + '\n', 'heading')
            txt.insert(tk.END, '─' * 44 + '\n', 'rule')

        def labeled(label, text):
            txt.insert(tk.END, f'  {label}  ', 'label')
            ins(text + '\n')

        def gap():
            txt.insert(tk.END, '\n', 'body')

        h('Sintaxes de Busca')
        labeled('Busca Livre:', 'Digite qualquer `texto` para pesquisar em todos os campos simultaneamente.')
        labeled('Contém:    ', '`campo:valor` — Busca parcial (ex: `srcip:192.168` encontra 192.168.1.1).')
        labeled('Exato:     ', '  `campo==valor` — Busca o valor exato (ex: `level==high`).')
        labeled('Diferente: ', '`campo!=valor` — Exclui o valor da busca (ex: `action!=pass`).')
        gap()

        h('Operadores Lógicos')
        ins('Combine condições usando MAIÚSCULAS (obrigatório o uso de espaços entre eles):\n')
        gap()

        txt.insert(tk.END, '  Operador\t', 'th')
        txt.insert(tk.END, 'Descrição\t', 'th')
        txt.insert(tk.END, 'Exemplo\n', 'th')

        txt.insert(tk.END, '  AND\t', 'label')
        txt.insert(tk.END, 'Ambas as condições devem ser verdadeiras\t', 'body')
        txt.insert(tk.END, 'dstport:443 AND action:deny\n', 'code')

        txt.insert(tk.END, '  OR\t', 'label')
        txt.insert(tk.END, 'Pelo menos uma condição deve ser verdadeira\t', 'body')
        txt.insert(tk.END, 'level:error OR level:warning\n', 'code')

        gap()
        txt.insert(tk.END,
                   'Nota: As expressões são avaliadas da esquerda para a direita.\n',
                   'note')
        gap()

        h('Exemplos Práticos')
        examples = [
            ('level:critical',              'Filtra logs críticos (busca parcial).'),
            ('srcip:10.0 AND action:block', 'Bloqueios na rede 10.0.x.x.'),
            ('dstport==80 OR dstport==443', 'Tráfego HTTP ou HTTPS.'),
            ('user!=admin AND action:login', 'Logins de usuários comuns.'),
        ]
        for ex, desc in examples:
            txt.insert(tk.END, f'  {ex}', 'code')
            txt.insert(tk.END, f'  —  {desc}\n', 'body')

        txt.config(state=tk.DISABLED)

        btn_frame = tk.Frame(win, bg=UIStyle.BG_STATUS, pady=6)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)
        UIStyle.create_button(btn_frame, 'Fechar', win.destroy).pack(
            side=tk.RIGHT, padx=12, pady=2
        )

    def _prev_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self._refresh_table()

    def _next_page(self):
        max_page = max(0, (len(self.engine.filtered_logs) - 1) // self.PAGE_SIZE)
        if self.current_page < max_page:
            self.current_page += 1
            self._refresh_table()

    def _show_charts_menu(self):
        if not MATPLOTLIB_AVAILABLE:
            messagebox.showwarning(
                "Matplotlib nao disponivel",
                "Instale matplotlib para usar graficos:\npip install matplotlib",
            )
            return

        if not self.engine.filtered_logs:
            messagebox.showwarning("Aviso", "Nenhum log para gerar grafico.")
            return

        self.sidebar.charts_menu.post(
            self.sidebar.btn_charts.winfo_rootx() + self.sidebar.btn_charts.winfo_width(),
            self.sidebar.btn_charts.winfo_rooty(),
        )

    def _make_chart_window(self, title: str, geometry: str) -> tk.Toplevel:
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry(geometry)
        win.configure(bg=UIStyle.BG_MAIN)
        self._chart_windows.append(win)
        return win

    def _chart_btn_frame(self, win: tk.Toplevel) -> tk.Frame:
        frame = tk.Frame(win, bg=UIStyle.BG_STATUS, pady=4)
        frame.pack(fill=tk.X, side=tk.BOTTOM)
        return frame

    def _add_export_button(self, btn_frame: tk.Frame, fig) -> None:
        def export_image():
            filepath = filedialog.asksaveasfilename(
                defaultextension='.png',
                filetypes=[('PNG', '*.png'), ('JPEG', '*.jpg'), ('PDF', '*.pdf')]
            )
            if filepath:
                fig.savefig(filepath, dpi=300, bbox_inches='tight')
                messagebox.showinfo('Sucesso', f'Imagem salva em:\n{filepath}')

        UIStyle.create_button(btn_frame, 'Exportar Imagem', export_image).pack(
            side=tk.LEFT, padx=8, pady=4
        )

    def _on_chart_close(self, win: tk.Toplevel, fig) -> None:
        plt.close(fig)
        if win in self._chart_windows:
            self._chart_windows.remove(win)
        win.destroy()

    def _embed_canvas(self, fig, win: tk.Toplevel, btn_frame: tk.Frame) -> None:
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._add_export_button(btn_frame, fig)
        win.protocol("WM_DELETE_WINDOW", lambda: self._on_chart_close(win, fig))

    def _show_volume_chart(self):
        timeline_data = self.engine.get_timeline_data()
        if not timeline_data:
            messagebox.showinfo('Info', 'Dados insuficientes para volume.')
            return

        win       = self._make_chart_window('Volume de Logs', '1000x650')
        btn_frame = self._chart_btn_frame(win)

        fig, ax = plt.subplots(figsize=(11, 6))
        hours  = list(timeline_data.keys())
        counts = list(timeline_data.values())

        ax.plot(range(len(hours)), counts, marker='o', linewidth=2,
                markersize=5, color='#2B6CB0', markerfacecolor='#63B3ED')
        ax.fill_between(range(len(hours)), counts, alpha=0.15, color='#2B6CB0')
        ax.set_xlabel('Data/Hora', fontsize=11, fontweight='bold')
        ax.set_ylabel('Quantidade de Logs', fontsize=11, fontweight='bold')
        ax.set_title('Volume de Logs ao Longo do Tempo', fontsize=13, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')

        step = max(1, len(hours) // 10)
        ax.set_xticks(range(0, len(hours), step))
        ax.set_xticklabels([hours[i] for i in range(0, len(hours), step)],
                           rotation=45, ha='right', fontsize=9)
        plt.tight_layout()

        self._embed_canvas(fig, win, btn_frame)

    def _show_top_chart(self, field: str, title: str, limit: int = 5):
        top_data = self.engine.get_top_data(field, limit=limit)
        if not top_data:
            messagebox.showinfo('Info', f'Nenhum dado disponivel para {field}.')
            return

        win       = self._make_chart_window(title, '900x650')
        btn_frame = self._chart_btn_frame(win)

        fig, ax = plt.subplots(figsize=(10, 6))
        labels = [item[0] for item in top_data]
        values = [item[1] for item in top_data]

        palette = ['#2B6CB0', '#3182CE', '#4299E1', '#63B3ED', '#90CDF4']
        bars = ax.barh(range(len(labels)), values,
                       color=palette[:len(labels)], edgecolor='none')
        ax.invert_yaxis()
        ax.set_yticks(range(len(labels)))
        ax.set_yticklabels(labels, fontsize=10)
        ax.set_xlabel('Quantidade', fontsize=11, fontweight='bold')
        ax.set_title(title, fontsize=13, fontweight='bold')
        ax.grid(True, axis='x', alpha=0.3, linestyle='--')

        for i, (bar, value) in enumerate(zip(bars, values)):
            ax.text(value + max(values) * 0.01, i, f'{value:,}',
                    va='center', fontsize=10, fontweight='bold')
        plt.tight_layout()

        self._embed_canvas(fig, win, btn_frame)

    def _plot_error_trend(self):
        data = self.engine.get_error_time_series()
        if not data:
            messagebox.showinfo("Info", "Sem erros/criticos no periodo.")
            return

        win       = self._make_chart_window('Erros / Critical ao Longo do Tempo', '1000x600')
        btn_frame = self._chart_btn_frame(win)

        times  = list(data.keys())
        values = list(data.values())

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(range(len(times)), values, marker='o', linewidth=2,
                markersize=5, color='#C53030', markerfacecolor='#FC8181')
        ax.fill_between(range(len(times)), values, alpha=0.15, color='#C53030')
        ax.set_title('Erros / Critical ao Longo do Tempo', fontsize=13, fontweight='bold')
        ax.set_xlabel('Data/Hora', fontsize=11, fontweight='bold')
        ax.set_ylabel('Quantidade', fontsize=11, fontweight='bold')
        ax.grid(True, alpha=0.3, linestyle='--')

        step = max(1, len(times) // 10)
        ax.set_xticks(range(0, len(times), step))
        ax.set_xticklabels([times[i] for i in range(0, len(times), step)],
                           rotation=45, ha='right', fontsize=9)
        plt.tight_layout()

        self._embed_canvas(fig, win, btn_frame)

    def _plot_level_distribution(self):
        data = self.engine.get_level_counts()
        if not data:
            messagebox.showinfo("Info", "Sem dados para exibir.")
            return

        filtered = [(k, v) for k, v in data.items() if k and v > 0]
        if not filtered:
            messagebox.showinfo("Info", "Sem niveis validos.")
            return

        labels = [k for k, v in filtered]
        values = [v for k, v in filtered]

        win       = self._make_chart_window('Distribuicao de Niveis', '700x600')
        btn_frame = self._chart_btn_frame(win)

        palette = ['#2B6CB0', '#C53030', '#975A16', '#276749', '#6B46C1', '#B83280']
        fig, ax = plt.subplots(figsize=(7, 5))
        ax.set_title('Distribuicao de Niveis', fontsize=13, fontweight='bold')

        if len(labels) <= 6:
            ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90,
                   colors=palette[:len(labels)])
        else:
            ax.barh(labels, values, color=palette[:min(len(labels), 6)], edgecolor='none')
            ax.set_xlabel('Quantidade', fontsize=11, fontweight='bold')
            ax.grid(True, axis='x', alpha=0.3, linestyle='--')

        plt.tight_layout()

        self._embed_canvas(fig, win, btn_frame)

    def _show_heatmap_chart(self):
        interval_data = self.engine.get_30min_distribution()
        if not interval_data:
            messagebox.showinfo('Info', 'Dados insuficientes para heatmap.')
            return

        win       = self._make_chart_window('Heatmap de Logs (30min)', '1200x650')
        btn_frame = self._chart_btn_frame(win)

        fig, ax = plt.subplots(figsize=(14, 6))
        intervals = list(interval_data.keys())
        counts    = list(interval_data.values())

        max_count = max(counts) if counts else 1
        colors    = plt.cm.Blues([0.2 + 0.8 * (c / max_count) for c in counts])

        bars = ax.bar(range(len(intervals)), counts,
                      color=colors, edgecolor='none')

        for bar, count in zip(bars, counts):
            if count > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, count, f'{count:,}',
                        ha='center', va='bottom', fontsize=7, fontweight='bold')

        ax.set_xlabel('Data/Hora', fontsize=11, fontweight='bold')
        ax.set_ylabel('Quantidade de Logs', fontsize=11, fontweight='bold')
        ax.set_title('Distribuicao de Logs (intervalos de 30min)', fontsize=13, fontweight='bold')
        ax.set_xticks(range(len(intervals)))
        ax.set_xticklabels(intervals, rotation=90, ha='right', fontsize=7)
        ax.grid(True, axis='y', alpha=0.3, linestyle='--')

        if counts:
            avg = sum(counts) / len(counts)
            ax.axhline(y=avg, color='#C53030', linestyle='--', linewidth=1.5,
                       label=f'Media: {avg:.0f}', alpha=0.8)
            ax.legend(fontsize=10)

        plt.tight_layout()

        self._embed_canvas(fig, win, btn_frame)

    def _show_details(self, event):
        item_id = self.table.tree.identify_row(event.y)
        if not item_id:
            return

        win = tk.Toplevel(self.root)
        win.title('Inspecao de Log')
        win.geometry('560x680')
        win.configure(bg=UIStyle.BG_MAIN)

        header = tk.Frame(win, bg=UIStyle.BG_TOOLBAR, pady=10)
        header.pack(fill=tk.X)
        tk.Label(
            header, text='DETALHES DO REGISTRO',
            font=UIStyle.FONT_BOLD,
            bg=UIStyle.BG_TOOLBAR,
            fg=UIStyle.FG_ON_DARK,
        ).pack()

        txt = tk.Text(
            win,
            font=UIStyle.FONT_MONO,
            padx=12, pady=12,
            bg=UIStyle.BG_CARD,
            fg=UIStyle.FG_MAIN,
            insertbackground=UIStyle.FG_MAIN,
            relief=tk.FLAT,
        )
        txt.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        query  = self.filters.search_var.get().lower()
        values = self.table.tree.item(item_id)['values']

        txt.tag_configure('key',
                          foreground=UIStyle.ACCENT,
                          font=(UIStyle.FONT_MONO[0], UIStyle.FONT_MONO[1], 'bold'))
        txt.tag_configure('hl',  background='#FEF08A')
        txt.tag_configure('val', foreground=UIStyle.FG_MAIN)

        for k, v in zip(self.engine.columns, values):
            txt.insert(tk.END, f'{k.upper():<18}: ', 'key')
            val_tag = 'hl' if (query and query in str(v).lower()) else 'val'
            txt.insert(tk.END, f'{v}\n', val_tag)

        txt.config(state=tk.DISABLED)

    def _show_context_menu(self, event):
        if self.table.tree.selection():
            self.context_menu.post(event.x_root, event.y_root)

    def _copy_selection(self):
        selected = self.table.tree.selection()
        if not selected:
            return

        rows = ['\t'.join(self.engine.columns)]
        for item in selected:
            rows.append('\t'.join(map(str, self.table.tree.item(item)['values'])))

        self.root.clipboard_clear()
        self.root.clipboard_append('\n'.join(rows))
        messagebox.showinfo('Copiado', f'{len(selected)} linha(s) copiada(s).')

    def _on_closing(self):
        for win in self._chart_windows[:]:
            try:
                win.destroy()
            except Exception:
                pass

        if MATPLOTLIB_AVAILABLE:
            plt.close('all')

        if self._debounce_id:
            self.root.after_cancel(self._debounce_id)

        self.root.quit()
        self.root.destroy()
