import json
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import font as tkfont


DATA_FILE = Path.home() / ".today_checklist.json"


def load_data():
    """Read saved tasks from disk. Returns today's date and the task list."""
    today = date.today().isoformat()

    if not DATA_FILE.exists():
        return today, []

    try:
        saved = json.loads(DATA_FILE.read_text())
    except (json.JSONDecodeError, OSError):
        
        return today, []

    tasks = saved.get("tasks", [])

    if saved.get("date") != today:
        tasks = [t for t in tasks if not t.get("done")]

    return today, tasks


def save_data(tasks):
    """Write tasks to disk."""
    payload = {"date": date.today().isoformat(), "tasks": tasks}
    try:
        DATA_FILE.write_text(json.dumps(payload, indent=2))
    except OSError:
        pass  # Saving failed the app still works for this session.

BG = "#F5F6F4"      # page background
INK = "#1C1F1D"     # primary text
MUTED = "#8A918C"   # secondary text, checkbox outlines
ACCENT = "#2F6F5E"  # deep pine — used for completion only
RULE = "#E2E4E0"    # hairlines


def pick_font(root, candidates, size, weight="normal"):
    """Use the first font that exists on this computer."""
    available = set(tkfont.families(root))
    for name in candidates:
        if name in available:
            return tkfont.Font(family=name, size=size, weight=weight)
    return tkfont.Font(size=size, weight=weight)


class Checklist:
    def __init__(self, root):
        self.root = root
        _, self.tasks = load_data()

        root.title("Today")
        root.configure(bg=BG)
        root.geometry("380x560")
        root.minsize(320, 400)

        sans = ["Inter", "SF Pro Text", "Helvetica Neue", "Segoe UI",
                "DejaVu Sans", "Arial"]
        self.f_day = pick_font(root, sans, 22, "bold")
        self.f_date = pick_font(root, sans, 11)
        self.f_task = pick_font(root, sans, 13)
        self.f_task_done = pick_font(root, sans, 13)
        self.f_task_done.configure(overstrike=True)
        self.f_small = pick_font(root, sans, 10)

        self._build_header()
        self._build_input()
        self._build_list()
        self.render()

    def _build_header(self):
        head = tk.Frame(self.root, bg=BG)
        head.pack(fill="x", padx=28, pady=(28, 0))

        top = tk.Frame(head, bg=BG)
        top.pack(fill="x")

        today = date.today()
        tk.Label(top, text=today.strftime("%A"), font=self.f_day,
                 bg=BG, fg=INK).pack(side="left")

        self.count = tk.Label(top, text="", font=self.f_small,
                              bg=BG, fg=MUTED)
        self.count.pack(side="right", pady=(10, 0))

        tk.Label(head, text=today.strftime("%d %B").lstrip("0"),
                 font=self.f_date, bg=BG, fg=MUTED).pack(anchor="w")

        # The one flourish: a hairline that fills as you finish things.
        self.bar = tk.Canvas(head, height=2, bg=RULE,
                             highlightthickness=0, bd=0)
        self.bar.pack(fill="x", pady=(14, 0))
        self.bar.bind("<Configure>", lambda e: self.draw_progress())

    def draw_progress(self):
        self.bar.delete("fill")
        if not self.tasks:
            return
        done = sum(1 for t in self.tasks if t["done"])
        width = self.bar.winfo_width() * (done / len(self.tasks))
        self.bar.create_rectangle(0, 0, width, 2, fill=ACCENT,
                                  outline="", tags="fill")

    # -- input -------------------------------------------------------------

    def _build_input(self):
        wrap = tk.Frame(self.root, bg=BG)
        wrap.pack(fill="x", padx=28, pady=(18, 8))

        self.entry = tk.Entry(wrap, font=self.f_task, bg=BG, fg=INK,
                              relief="flat", insertbackground=INK,
                              highlightthickness=0, bd=0)
        self.entry.pack(fill="x", ipady=4)
        self.entry.insert(0, "")
        self.entry.bind("<Return>", lambda e: self.add_task())
        self.entry.focus_set()

        self.hint = tk.Label(wrap, text="Type a task, press Enter",
                             font=self.f_small, bg=BG, fg=MUTED)
        self.hint.pack(anchor="w", pady=(2, 0))

    # -- scrollable task list ---------------------------------------------

    def _build_list(self):
        holder = tk.Frame(self.root, bg=BG)
        holder.pack(fill="both", expand=True, padx=28, pady=(8, 24))

        self.canvas = tk.Canvas(holder, bg=BG, highlightthickness=0, bd=0)
        self.canvas.pack(side="left", fill="both", expand=True)

        self.list_frame = tk.Frame(self.canvas, bg=BG)
        self.window = self.canvas.create_window(
            (0, 0), window=self.list_frame, anchor="nw")

        self.list_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.window, width=e.width))

        # Mouse wheel scrolling (the event name differs per operating system)
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.bind_all(seq, self._on_scroll)

    def _on_scroll(self, event):
        if event.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-event.delta / 60), "units")

    # -- actions -----------------------------------------------------------

    def add_task(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.tasks.append({"text": text, "done": False})
        self.entry.delete(0, "end")
        self.commit()

    def toggle(self, index):
        self.tasks[index]["done"] = not self.tasks[index]["done"]
        self.commit()

    def remove(self, index):
        del self.tasks[index]
        self.commit()

    def commit(self):
        """Save to disk and redraw."""
        save_data(self.tasks)
        self.render()

    # -- drawing -----------------------------------------------------------

    def render(self):
        for widget in self.list_frame.winfo_children():
            widget.destroy()

        if not self.tasks:
            tk.Label(self.list_frame, text="Nothing yet. Add the first thing.",
                     font=self.f_small, bg=BG, fg=MUTED).pack(anchor="w",
                                                              pady=(12, 0))
        else:
            for i, task in enumerate(self.tasks):
                self._draw_row(i, task)

        done = sum(1 for t in self.tasks if t["done"])
        self.count.config(text=f"{done} of {len(self.tasks)}" if self.tasks else "")
        self.draw_progress()

    def _draw_row(self, index, task):
        row = tk.Frame(self.list_frame, bg=BG)
        row.pack(fill="x", pady=5)

        # Checkbox, drawn by hand so it looks the same everywhere.
        box = tk.Canvas(row, width=17, height=17, bg=BG,
                        highlightthickness=0, bd=0, cursor="hand2")
        box.pack(side="left", padx=(0, 12))
        if task["done"]:
            box.create_oval(1, 1, 16, 16, fill=ACCENT, outline=ACCENT)
            box.create_line(5, 9, 7.5, 12, 12, 5, fill="#FFFFFF", width=2)
        else:
            box.create_oval(1, 1, 16, 16, outline=MUTED, width=1)
        box.bind("<Button-1>", lambda e: self.toggle(index))

        label = tk.Label(row,
                         text=task["text"],
                         font=self.f_task_done if task["done"] else self.f_task,
                         bg=BG,
                         fg=MUTED if task["done"] else INK,
                         cursor="hand2",
                         anchor="w",
                         justify="left",
                         wraplength=250)
        label.pack(side="left", fill="x", expand=True)
        label.bind("<Button-1>", lambda e: self.toggle(index))

        delete = tk.Label(row, text="\u00d7", font=self.f_task,
                          bg=BG, fg=RULE, cursor="hand2")
        delete.pack(side="right", padx=(8, 0))
        delete.bind("<Button-1>", lambda e: self.remove(index))
        delete.bind("<Enter>", lambda e: delete.config(fg=INK))
        delete.bind("<Leave>", lambda e: delete.config(fg=RULE))


if __name__ == "__main__":
    window = tk.Tk()
    Checklist(window)
    window.mainloop()