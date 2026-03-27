import importlib.util
import logging
import tkinter as tk
from tkinter import filedialog, messagebox

MATPLOTLIB_AVAILABLE = importlib.util.find_spec('matplotlib') is not None

plt = None
FigureCanvasTkAgg = None
_mpl_initialized = False


def _init_mpl():
    global plt, FigureCanvasTkAgg, _mpl_initialized
    if _mpl_initialized:
        return
    _mpl_initialized = True
    try:
        import matplotlib
        matplotlib.use('TkAgg')
        import matplotlib.pyplot as _plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg as _FCA
        _plt.ioff()
        plt = _plt
        FigureCanvasTkAgg = _FCA
    except Exception:
        pass


class ChartsMixin:

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

        _init_mpl()

        self.sidebar.charts_menu.post(
            self.sidebar.btn_charts.winfo_rootx() + self.sidebar.btn_charts.winfo_width(),
            self.sidebar.btn_charts.winfo_rooty(),
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

        max_val = max(values) if values else 1
        colors  = plt.cm.RdYlGn_r([0.05 + 0.95 * (v / max_val) for v in values])
        bars = ax.barh(range(len(labels)), values,
                       color=colors, edgecolor='none')
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
            max_val  = max(values) if values else 1
            colors   = plt.cm.RdYlGn_r([0.05 + 0.95 * (v / max_val) for v in values])
            ax.barh(labels, values, color=colors, edgecolor='none')
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
        colors    = plt.cm.RdYlGn_r([0.05 + 0.95 * (c / max_count) for c in counts])

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

    def _cleanup_charts(self):
        for win in self._chart_windows[:]:
            try:
                win.destroy()
            except Exception:
                pass
        if plt is not None:
            plt.close('all')
