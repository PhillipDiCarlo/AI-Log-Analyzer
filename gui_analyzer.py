import sys
import threading
import queue
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).parent))

from src.log_parser import parse_file, parse_file_with_timestamps
from src.summarizer import find_log_files, merge_counts, top_n_problems
from src.anomaly_detector import aggregate_counts_by_minute, detect_anomalies
from src.code_linker import link_errors_to_code
from src.semantic_linker import SemanticCodeLinker

class LogAnalyzerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Log Analyzer")
        self.geometry("900x820")

        # Paths
        self.logs_dir: Path | None = None
        self.code_dir: Path | None = None

        # Thread-safe queue
        self._queue: queue.Queue = queue.Queue()
        self.wrap_var = tk.BooleanVar(value=False)

        # For plotting
        self._last_counts_df = None
        self._last_anomalies = None

        # Semantic indexer
        self.semantic = SemanticCodeLinker()

        self._build_ui()
        self.poll_queue()

    def _build_ui(self):
        # Directory selectors
        tk.Label(self, text="Logs Directory:").pack(anchor="w", padx=10, pady=(10,0))
        tk.Button(self, text="Browse Logs...", command=self.select_logs_dir).pack(anchor="w", padx=10)
        tk.Label(self, text="Codebase Directory:").pack(anchor="w", padx=10, pady=(5,0))
        tk.Button(self, text="Browse Codebase...", command=self.select_code_dir).pack(anchor="w", padx=10)

        # Controls
        ctrl = tk.Frame(self)
        ctrl.pack(fill="x", padx=10, pady=10)
        self.analyze_button = tk.Button(ctrl, text="Analyze", command=self.run_analysis, bg="#4CAF50", fg="white")
        self.analyze_button.pack(side="left")
        self.status_label = tk.Label(ctrl, text="Idle")
        self.status_label.pack(side="left", padx=10)
        self.progress = ttk.Progressbar(ctrl, mode="indeterminate")
        self.progress.pack(side="left", fill="x", expand=True, padx=(0,10))
        tk.Checkbutton(ctrl, text="Word Wrap", variable=self.wrap_var,
                       command=self.toggle_wrap, bg="#1e1e1e", fg="#d4d4d4", selectcolor="#1e1e1e").pack(side="left")

        # Text output
        self.output = ScrolledText(
            self, wrap=tk.NONE, bg="#1e1e1e", fg="#d4d4d4",
            insertbackground="#d4d4d4", selectbackground="#264F78",
            undo=False, maxundo=0
        )
        self.output.pack(expand=True, fill="both", padx=10, pady=(0,10))

        # Chart area
        self.chart_frame = tk.Frame(self)
        self.chart_frame.pack(fill="x", padx=10, pady=(0,10))

        # Text tags
        tags = {
            'header':('#569CD6', ('TkDefaultFont',12,'bold')),
            'count':'#DCDCAA', 'msg':'#D4D4D4', 'anomaly':'#F44747',
            'file':'#9CDCFE','snippet':'#C586C0','date':'#B5CEA8','time':'#CE9178'
        }
        for tag, cfg in tags.items():
            if isinstance(cfg, tuple):
                self.output.tag_config(tag, foreground=cfg[0], font=cfg[1])
            else:
                self.output.tag_config(tag, foreground=cfg)

        # Kick off semantic index build with progress callback
        threading.Thread(
            target=lambda: self.semantic.build_index(
                self.code_dir or Path('.'),
                rebuild=False,
                progress_cb=lambda pct: self._queue.put(('status', f'Indexing: {pct}%'))
            ),
            daemon=True
        ).start()

    def select_logs_dir(self):
        path = filedialog.askdirectory(title="Select Logs Directory")
        if path:
            self.logs_dir = Path(path)
            self.output.insert(tk.END, f"Logs directory set to: {path}\n", 'msg')

    def select_code_dir(self):
        path = filedialog.askdirectory(title="Select Codebase Directory")
        if path:
            self.code_dir = Path(path)
            self.output.insert(tk.END, f"Codebase directory set to: {path}\n", 'msg')

    def toggle_wrap(self):
        self.output.config(wrap=tk.WORD if self.wrap_var.get() else tk.NONE)

    def run_analysis(self):
        if not self.logs_dir or not self.code_dir:
            messagebox.showwarning("Missing Directory", "Please select both logs and codebase directories.")
            return

        self.analyze_button.config(state='disabled')
        self.status_label.config(text="Starting analysis...")
        self.progress.start(50)
        self.output.delete('1.0', tk.END)
        for w in self.chart_frame.winfo_children():
            w.destroy()

        threading.Thread(target=self._analysis_worker, daemon=True).start()

    def _analysis_worker(self):
        assert self.logs_dir and self.code_dir
        logs = self.logs_dir
        code = self.code_dir

        # Phase 1: top problems
        self._queue.put(('status', 'Scanning logs for top problems...'))
        all_counts = {}
        for f in find_log_files(logs):
            merge_counts(all_counts, parse_file(f))
        top = top_n_problems(all_counts)
        self._queue.put(('top', top))

        # Phase 2: anomalies
        self._queue.put(('status', 'Detecting anomalies...'))
        ts = []
        for f in find_log_files(logs):
            ts += parse_file_with_timestamps(f)
        if ts:
            df = aggregate_counts_by_minute(ts)
            anoms, _ = detect_anomalies(df, contamination=0.05)
            self._last_counts_df = df
            self._last_anomalies = anoms
            self._queue.put(('anomalies', anoms))
            self._queue.put(('plot_data', df))
        else:
            self._queue.put(('anomalies', []))

        # Phase 3: code linking & semantic
        self._queue.put(('status', 'Linking errors to code...'))
        errs = [e for e, _ in top]
        kw_links = link_errors_to_code(errs, code)
        self._queue.put(('links', kw_links))

        # Ensure semantic index built
        if self.semantic.index is None:
            self.semantic.build_index(code)

        sem_links = {e: self.semantic.query(e, top_k=5) for e in errs}
        self._queue.put(('semantic_links', sem_links))

        self._queue.put(('done', None))

    def poll_queue(self):
        try:
            action, data = self._queue.get_nowait()
        except queue.Empty:
            self.after(100, self.poll_queue)
            return

        if action == 'status':
            self.status_label.config(text=data)
        elif action == 'top':
            self._display_top(data)
        elif action == 'anomalies':
            self._display_anomalies(data)
        elif action == 'plot_data':
            self._show_plot(data)
        elif action == 'links':
            self._display_links(data)
        elif action == 'semantic_links':
            self._display_semantic_links(data)
        elif action == 'done':
            self._finish()

        self.after(10, self.poll_queue)

    def _display_top(self, top):
        self.output.insert(tk.END, "Top Problems Found:\n", 'header')
        for err, cnt in top:
            self.output.insert(tk.END, f" {cnt} ", 'count')
            self.output.insert(tk.END, "-> ")
            parts = err.split(' ',2)
            if len(parts)>=3:
                self.output.insert(tk.END, f"{parts[0]} ",'date')
                    
            else:
                self.output.insert(tk.END, f"{err}\n",'msg')

    def _display_anomalies(self, anoms):
        self.output.insert(tk.END, "\nAnomalous Time Windows:\n", 'header')
        if anoms is not None and hasattr(anoms,'empty') and not anoms.empty:
            for m, r in anoms.set_index('minute').iterrows():
                self.output.insert(tk.END, " • ")
                self.output.insert(tk.END, m.strftime('%Y-%m-%d '),'date')
                self.output.insert(tk.END, m.strftime('%H:%M:%S '),'time')
                self.output.insert(tk.END, f"-> {r['count']} errors\n",'anomaly')
        else:
            self.output.insert(tk.END, " None\n",'msg')

    def _show_plot(self, df):
        for w in self.chart_frame.winfo_children():
            w.destroy()

        fig, ax = plt.subplots(figsize=(8,2), dpi=100)
        ax.plot(df['minute'], df['count'], label='Error Count')
        if self._last_anomalies is not None and not self._last_anomalies.empty:
            ax.scatter(self._last_anomalies['minute'], self._last_anomalies['count'],
                       color='red', label='Anomaly')
        ax.set_title('Errors Over Time')
        ax.set_ylabel('Count')
        ax.set_xlabel('Time')
        ax.legend()
        fig.autofmt_xdate()
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def _display_links(self, links):
        self.output.insert(tk.END, "\nCode References (keywords):\n", 'header')
        for err, mapping in links.items():
            self.output.insert(tk.END, f"\nError: {err}\n", 'header')
            if not mapping:
                self.output.insert(tk.END, "  No keyword matches.\n",'msg')
            for path, lines in mapping.items():
                self.output.insert(tk.END, f"  {path.relative_to(self.code_dir)}\n",'file')
                for s in lines[:3]:
                    self.output.insert(tk.END, f"    • {s}\n",'snippet')

    def _display_semantic_links(self, results):
        self.output.insert(tk.END, "\nCode References (semantic):\n", 'header')
        for err, recs in results.items():
            self.output.insert(tk.END, f"\nError: {err}\n", 'header')
            if not recs:
                self.output.insert(tk.END, "  No semantic matches.\n",'msg')
            for file, ln, snip, dist in recs:
                rel = file.relative_to(self.code_dir)
                self.output.insert(tk.END, f"  {rel}:{ln} [{dist:.2f}]\n",'file')
                self.output.insert(tk.END, f"    {snip}\n",'snippet')

    def _finish(self):
        self.progress.stop()
        self.analyze_button.config(state='normal')
        self.status_label.config(text="Idle")
        messagebox.showinfo("Analysis Complete", "Log analysis is finished.")

if __name__ == "__main__":
    app = LogAnalyzerGUI()
    app.mainloop()

