import sys
import threading
import queue
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

# Ensure project root is in PYTHONPATH so that `import src` works
sys.path.insert(0, str(Path(__file__).parent))

from src.log_parser import parse_file, parse_file_with_timestamps
from src.summarizer import find_log_files, merge_counts, top_n_problems
from src.anomaly_detector import aggregate_counts_by_minute, detect_anomalies
from src.code_linker import link_errors_to_code

class LogAnalyzerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI Log Analyzer")
        self.geometry("900x700")

        # Paths (set via file dialogs)
        self.logs_dir: Path | None = None
        self.code_dir: Path | None = None

        # Threading queue for UI updates
        self._queue = queue.Queue()

        # Wrap control variable (off by default for performance)
        self.wrap_var = tk.BooleanVar(value=False)

        # Build UI
        self.create_widgets()
        self.poll_queue()

    def create_widgets(self):
        # Directory selectors
        tk.Label(self, text="Logs Directory:").pack(anchor="w", padx=10, pady=(10, 0))
        tk.Button(self, text="Browse Logs...", command=self.select_logs_dir).pack(anchor="w", padx=10)

        tk.Label(self, text="Codebase Directory:").pack(anchor="w", padx=10, pady=(10, 0))
        tk.Button(self, text="Browse Codebase...", command=self.select_code_dir).pack(anchor="w", padx=10)

        # Controls: Analyze button, status, progress, wrap toggle
        control_frame = tk.Frame(self)
        control_frame.pack(fill="x", padx=10, pady=10)

        self.analyze_button = tk.Button(
            control_frame,
            text="Analyze",
            command=self.run_analysis,
            bg="#4CAF50",
            fg="white",
        )
        self.analyze_button.pack(side="left")

        self.status_label = tk.Label(control_frame, text="Idle")
        self.status_label.pack(side="left", padx=10)

        self.progress = ttk.Progressbar(control_frame, mode="indeterminate")
        self.progress.pack(side="left", fill="x", expand=True)

        wrap_check = tk.Checkbutton(
            control_frame,
            text="Word Wrap",
            variable=self.wrap_var,
            command=self.toggle_wrap,
            bg="#1e1e1e",
            fg="#d4d4d4",
            selectcolor="#1e1e1e",
        )
        wrap_check.pack(side="left", padx=10)

        # ScrolledText with dark theme, initial wrap off
        text_frame = tk.Frame(self)
        text_frame.pack(expand=True, fill="both", padx=10, pady=10)

        self.output = ScrolledText(
            text_frame,
            wrap=tk.NONE,
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="#d4d4d4",
            selectbackground="#264F78",
            undo=False,
            maxundo=0
        )
        self.output.pack(side="left", expand=True, fill="both")

        # Configure color tags
        self.output.tag_config('header', foreground='#569CD6', font=('TkDefaultFont', 12, 'bold'))
        self.output.tag_config('count', foreground='#DCDCAA')
        self.output.tag_config('msg', foreground='#D4D4D4')
        self.output.tag_config('anomaly', foreground='#F44747')
        self.output.tag_config('file', foreground='#9CDCFE')
        self.output.tag_config('snippet', foreground='#C586C0')
        self.output.tag_config('date', foreground='#B5CEA8')
        self.output.tag_config('time', foreground='#CE9178')

    def toggle_wrap(self):
        self.output.config(wrap=tk.WORD if self.wrap_var.get() else tk.NONE)

    def select_logs_dir(self):
        selected = filedialog.askdirectory(title="Select Logs Directory")
        if selected:
            self.logs_dir = Path(selected)
            self.output.insert(tk.END, f"Logs directory set to: {self.logs_dir}\n", 'msg')

    def select_code_dir(self):
        selected = filedialog.askdirectory(title="Select Codebase Directory")
        if selected:
            self.code_dir = Path(selected)
            self.output.insert(tk.END, f"Codebase directory set to: {self.code_dir}\n", 'msg')

    def run_analysis(self):
        if not self.logs_dir or not self.code_dir:
            messagebox.showwarning("Missing Directory", "Please select both logs and codebase directories.")
            return

        self.analyze_button.config(state='disabled')
        self.status_label.config(text="Starting analysis...")
        self.progress.start(50)
        self.output.delete('1.0', tk.END)

        threading.Thread(target=self._analysis_worker, daemon=True).start()

    def _analysis_worker(self):
        assert self.logs_dir and self.code_dir
        logs_dir = self.logs_dir
        code_dir = self.code_dir

        self._queue.put(('status', 'Scanning logs for top problems...'))
        all_counts: dict[str, int] = {}
        for log_file in find_log_files(logs_dir):
            counts = parse_file(log_file)
            merge_counts(all_counts, counts)
        top = top_n_problems(all_counts)
        self._queue.put(('top', top))

        self._queue.put(('status', 'Detecting anomalies...'))
        timestamps: list = []
        for log_file in find_log_files(logs_dir):
            timestamps += parse_file_with_timestamps(log_file)
        anomalies_df = []
        if timestamps:
            counts_df = aggregate_counts_by_minute(timestamps)
            anomalies_df, _ = detect_anomalies(counts_df, contamination=0.05)
        self._queue.put(('anomalies', anomalies_df))

        self._queue.put(('status', 'Linking errors to code...'))
        error_msgs = [err for err, _ in top]
        links = link_errors_to_code(error_msgs, code_dir)
        self._queue.put(('links', links))

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
        elif action == 'links':
            self._display_links(data)
        elif action == 'done':
            self._finish()

        self.after(10, self.poll_queue)

    def _display_top(self, top):
        self.output.insert(tk.END, "Top Problems Found:\n", 'header')
        for err, cnt in top:
            self.output.insert(tk.END, f" {cnt} ", 'count')
            self.output.insert(tk.END, "-> ")
            parts = err.split(' ', 2)
            if len(parts) >= 3:
                self.output.insert(tk.END, f"{parts[0]} ", 'date')
                self.output.insert(tk.END, f"{parts[1]} ", 'time')
                self.output.insert(tk.END, f"{parts[2]}\n", 'msg')
            else:
                self.output.insert(tk.END, f"{err}\n", 'msg')

    def _display_anomalies(self, anomalies_df):
        self.output.insert(tk.END, "\nAnomalous Time Windows:\n", 'header')
        if not getattr(anomalies_df, 'empty', True):
            for minute, row in anomalies_df.set_index('minute').iterrows():
                self.output.insert(tk.END, " • ")
                self.output.insert(tk.END, minute.strftime('%Y-%m-%d ') , 'date')
                self.output.insert(tk.END, minute.strftime('%H:%M:%S ') , 'time')
                self.output.insert(tk.END, f"-> {row['count']} errors\n", 'anomaly')
        else:
            self.output.insert(tk.END, " None\n", 'msg')

    def _display_links(self, links):
        self.output.insert(tk.END, "\nCode References for Top Errors:\n", 'header')
        for err, files in links.items():
            self.output.insert(tk.END, "\nError: ", 'header')
            self.output.insert(tk.END, f"{err}\n", 'msg')
            if not files:
                self.output.insert(tk.END, "  No matches found in code.\n", 'msg')
            else:
                for path, snippets in files.items():
                    self.output.insert(tk.END, f"  {path.relative_to(self.code_dir)}\n", 'file')
                    for snippet in snippets[:3]:
                        self.output.insert(tk.END, f"    • {snippet}\n", 'snippet')

    def _finish(self):
        self.progress.stop()
        self.analyze_button.config(state='normal')
        self.status_label.config(text="Idle")
        messagebox.showinfo("Analysis Complete", "Log analysis is finished.")

if __name__ == "__main__":
    app = LogAnalyzerGUI()
    app.mainloop()
