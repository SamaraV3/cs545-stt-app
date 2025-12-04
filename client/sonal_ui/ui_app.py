import tkinter as tk
from tkinter import ttk, messagebox
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Protocol


# ===================== Reminder model =====================

@dataclass
class Reminder:
    id: int
    task: str
    time: datetime
    repeat: Optional[str] = None
    status: str = "scheduled"  # "scheduled", "completed", "cancelled"


# ===================== Repository interface & mock =====================

class ReminderRepository(Protocol):
    def get_reminders(self) -> List[Reminder]: ...
    def create_reminder(self, task: str, time: datetime, repeat: Optional[str] = None) -> Reminder: ...
    def delete_reminder(self, reminder_id: int) -> None: ...
    def update_reminder(self, reminder: Reminder) -> None: ...


class MockReminderRepository(ReminderRepository):
    """In-memory mock, like a Flutter MockReminderRepository."""

    def __init__(self):
        now = datetime.now()
        self._reminders: List[Reminder] = [
            Reminder(1, "Call mom", now.replace(hour=18, minute=0), None, "scheduled"),
            Reminder(2, "Take medicine", now.replace(hour=21, minute=30), "daily", "scheduled"),
        ]
        self._next_id = 3

    def get_reminders(self) -> List[Reminder]:
        return list(self._reminders)

    def create_reminder(self, task: str, time: datetime, repeat: Optional[str] = None) -> Reminder:
        r = Reminder(self._next_id, task, time, repeat, "scheduled")
        self._next_id += 1
        self._reminders.append(r)
        return r

    def delete_reminder(self, reminder_id: int) -> None:
        self._reminders = [r for r in self._reminders if r.id != reminder_id]

    def update_reminder(self, reminder: Reminder) -> None:
        for i, r in enumerate(self._reminders):
            if r.id == reminder.id:
                self._reminders[i] = reminder
                break


# ===================== Base screen =====================

class BaseScreen(ttk.Frame):
    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, **kwargs)
        self.app = app


# ===================== HOME SCREEN =====================

class HomeScreen(BaseScreen):
    """Shows pastel dashboard + list of reminders."""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, **kwargs)

        # Header bar
        header = ttk.Frame(self, style="HeaderBar.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="Reminder Dashboard", style="HeaderTitle.TLabel").pack(
            side="left", padx=16, pady=10
        )
        ttk.Button(
            header,
            text="Settings",
            style="Secondary.TButton",
            command=lambda: app.show_screen("settings"),
        ).pack(side="right", padx=16, pady=10)

        # Top stats (like little cards)
        stats = ttk.Frame(self, style="Body.TFrame")
        stats.pack(fill="x", padx=16, pady=(8, 0))
        self.total_var = tk.StringVar()
        self.sched_var = tk.StringVar()
        self.done_var = tk.StringVar()
        self._stat_card(stats, "Total", self.total_var).grid(row=0, column=0, padx=6, pady=6)
        self._stat_card(stats, "Scheduled", self.sched_var).grid(row=0, column=1, padx=6, pady=6)
        self._stat_card(stats, "Completed", self.done_var).grid(row=0, column=2, padx=6, pady=6)

        # Main card with table
        card = ttk.Frame(self, style="Card.TFrame", padding=12)
        card.pack(fill="both", expand=True, padx=16, pady=(8, 16))

        ttk.Label(card, text="Reminders", style="SectionTitle.TLabel").pack(anchor="w")

        columns = ("time", "task", "repeat", "status")
        self.tree = ttk.Treeview(
            card,
            columns=columns,
            show="headings",
            height=10,
            style="Reminders.Treeview",
        )
        for col, text in zip(columns, ["Time", "Task", "Repeat", "Status"]):
            self.tree.heading(col, text=text)
        self.tree.column("time", width=150, anchor="w")
        self.tree.column("task", width=280, anchor="w")
        self.tree.column("repeat", width=90, anchor="center")
        self.tree.column("status", width=90, anchor="center")

        self.tree.pack(fill="both", expand=True, pady=(4, 6))
        self.tree.bind("<Double-1>", lambda e: self.view_selected())

        # Buttons row
        btn_bar = ttk.Frame(card)
        btn_bar.pack(fill="x")

        ttk.Button(
            btn_bar, text="➕ Add", style="Accent.TButton", command=self.add
        ).pack(side="left", padx=4)
        ttk.Button(
            btn_bar, text="📝 Edit", command=self.view_selected
        ).pack(side="left", padx=4)
        ttk.Button(
            btn_bar, text="🗑 Delete", command=self.delete_selected
        ).pack(side="left", padx=4)

        self.status_label = ttk.Label(self, text="", style="Status.TLabel")
        self.status_label.pack(fill="x", padx=16, pady=(0, 8))

        self.refresh()

    def _stat_card(self, parent, label, var):
        f = ttk.Frame(parent, style="StatCard.TFrame", padding=8)
        ttk.Label(f, textvariable=var, style="StatNumber.TLabel").pack()
        ttk.Label(f, text=label, style="StatLabel.TLabel").pack()
        return f

    def refresh(self):
        # clear table
        for row in self.tree.get_children():
            self.tree.delete(row)

        reminders = self.app.repo.get_reminders()
        reminders.sort(key=lambda r: r.time)

        total = len(reminders)
        scheduled = len([r for r in reminders if r.status == "scheduled"])
        done = len([r for r in reminders if r.status == "completed"])

        self.total_var.set(str(total))
        self.sched_var.set(str(scheduled))
        self.done_var.set(str(done))

        for r in reminders:
            time_str = r.time.strftime("%Y-%m-%d %H:%M")
            self.tree.insert(
                "",
                "end",
                iid=str(r.id),
                values=(time_str, r.task, r.repeat or "-", r.status),
            )

        self.status_label.config(
            text=f"{total} reminder(s). Double-click a row or use Edit."
        )

    def _get_selected_reminder(self) -> Optional[Reminder]:
        sel = self.tree.selection()
        if not sel:
            return None
        rid = int(sel[0])
        for r in self.app.repo.get_reminders():
            if r.id == rid:
                return r
        return None

    def add(self):
        self.app.show_details(None)

    def view_selected(self):
        r = self._get_selected_reminder()
        if r is None:
            messagebox.showinfo(
                "No selection", "Please select a reminder to view or edit."
            )
            return
        self.app.show_details(r)

    def delete_selected(self):
        r = self._get_selected_reminder()
        if r is None:
            messagebox.showinfo(
                "No selection", "Please select a reminder to delete."
            )
            return
        if not messagebox.askyesno("Delete", f"Delete reminder '{r.task}'?"):
            return
        self.app.repo.delete_reminder(r.id)
        self.refresh()


# ===================== DETAILS SCREEN =====================

class DetailsScreen(BaseScreen):
    """Form screen to create or edit a reminder."""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, **kwargs)
        self.current: Optional[Reminder] = None

        header = ttk.Frame(self, style="HeaderBar.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="Reminder details", style="HeaderTitle.TLabel").pack(
            side="left", padx=16, pady=10
        )
        ttk.Button(
            header,
            text="← Back",
            style="Secondary.TButton",
            command=lambda: app.show_screen("home"),
        ).pack(side="right", padx=16, pady=10)

        card = ttk.Frame(self, style="Card.TFrame", padding=16)
        card.pack(fill="both", expand=True, padx=16, pady=(8, 16))

        form = ttk.Frame(card, style="Body.TFrame")
        form.pack(fill="x")

        ttk.Label(form, text="Task", style="FormLabel.TLabel").grid(
            row=0, column=0, sticky="e", padx=6, pady=6
        )
        self.task_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.task_var, width=40).grid(
            row=0, column=1, sticky="w"
        )

        ttk.Label(form, text="Time", style="FormLabel.TLabel").grid(
            row=1, column=0, sticky="e", padx=6, pady=6
        )
        self.time_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.time_var, width=25).grid(
            row=1, column=1, sticky="w"
        )
        ttk.Label(
            form, text="Format: YYYY-MM-DD HH:MM", style="Hint.TLabel"
        ).grid(row=2, column=1, sticky="w")

        ttk.Label(form, text="Repeat", style="FormLabel.TLabel").grid(
            row=3, column=0, sticky="e", padx=6, pady=6
        )
        self.repeat_var = tk.StringVar()
        repeat_box = ttk.Combobox(
            form,
            textvariable=self.repeat_var,
            width=20,
            values=["", "daily", "weekly", "weekdays"],
        )
        repeat_box.grid(row=3, column=1, sticky="w")

        ttk.Label(form, text="Status", style="FormLabel.TLabel").grid(
            row=4, column=0, sticky="e", padx=6, pady=6
        )
        self.status_var = tk.StringVar()
        status_box = ttk.Combobox(
            form,
            textvariable=self.status_var,
            width=20,
            values=["scheduled", "completed", "cancelled"],
            state="readonly",
        )
        status_box.grid(row=4, column=1, sticky="w")

        btn_bar = ttk.Frame(card, style="Body.TFrame")
        btn_bar.pack(fill="x", pady=(12, 0))
        ttk.Button(
            btn_bar, text="💾 Save", style="Accent.TButton", command=self.save
        ).pack(side="left", padx=4)

        self.feedback = ttk.Label(card, text="", style="Status.TLabel")
        self.feedback.pack(anchor="w", pady=(8, 0))

    def load(self, reminder: Optional[Reminder]):
        """Load data into the form. If reminder is None, new one."""
        self.current = reminder
        if reminder is None:
            self.task_var.set("")
            self.time_var.set(datetime.now().strftime("%Y-%m-%d %H:%M"))
            self.repeat_var.set("")
            self.status_var.set("scheduled")
        else:
            self.task_var.set(reminder.task)
            self.time_var.set(reminder.time.strftime("%Y-%m-%d %H:%M"))
            self.repeat_var.set(reminder.repeat or "")
            self.status_var.set(reminder.status)
        self.feedback.config(text="")

    def save(self):
        task = self.task_var.get().strip()
        time_str = self.time_var.get().strip()
        repeat = self.repeat_var.get().strip() or None
        status = self.status_var.get().strip() or "scheduled"

        if not task or not time_str:
            messagebox.showerror("Missing data", "Task and time are required.")
            return

        try:
            dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            messagebox.showerror(
                "Invalid time", "Use the format YYYY-MM-DD HH:MM."
            )
            return

        if self.current is None:
            new_r = self.app.repo.create_reminder(task, dt, repeat)
            self.current = new_r
            self.feedback.config(text=f"Created reminder #{new_r.id}")
        else:
            updated = Reminder(self.current.id, task, dt, repeat, status)
            self.app.repo.update_reminder(updated)
            self.current = updated
            self.feedback.config(text=f"Updated reminder #{updated.id}")

        # Refresh home screen table
        self.app.home_screen.refresh()


# ===================== SETTINGS SCREEN =====================

class SettingsScreen(BaseScreen):
    """Mock settings screen (safe word, channel, theme)."""

    def __init__(self, parent, app, **kwargs):
        super().__init__(parent, app, **kwargs)

        header = ttk.Frame(self, style="HeaderBar.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="Settings", style="HeaderTitle.TLabel").pack(
            side="left", padx=16, pady=10
        )
        ttk.Button(
            header,
            text="← Back",
            style="Secondary.TButton",
            command=lambda: app.show_screen("home"),
        ).pack(side="right", padx=16, pady=10)

        card = ttk.Frame(self, style="Card.TFrame", padding=16)
        card.pack(fill="both", expand=True, padx=16, pady=(8, 16))

        form = ttk.Frame(card, style="Body.TFrame")
        form.pack(fill="x")

        self.safe_word_var = tk.StringVar(value="memo")
        self.channel_var = tk.StringVar(value="voice")
        self.theme_var = tk.StringVar(value="light")

        ttk.Label(form, text="Safe word", style="FormLabel.TLabel").grid(
            row=0, column=0, sticky="e", padx=6, pady=6
        )
        ttk.Entry(form, textvariable=self.safe_word_var, width=20).grid(
            row=0, column=1, sticky="w"
        )

        ttk.Label(form, text="Notification channel", style="FormLabel.TLabel").grid(
            row=1, column=0, sticky="e", padx=6, pady=6
        )
        ttk.Combobox(
            form,
            textvariable=self.channel_var,
            width=22,
            values=["voice", "system notification", "both"],
        ).grid(row=1, column=1, sticky="w")

        ttk.Label(form, text="Theme", style="FormLabel.TLabel").grid(
            row=2, column=0, sticky="e", padx=6, pady=6
        )
        ttk.Combobox(
            form,
            textvariable=self.theme_var,
            width=22,
            values=["light", "dark"],
        ).grid(row=2, column=1, sticky="w")

        btn_bar = ttk.Frame(card, style="Body.TFrame")
        btn_bar.pack(fill="x", pady=(12, 0))
        ttk.Button(
            btn_bar,
            text="Save settings",
            style="Accent.TButton",
            command=self.save,
        ).pack(side="left", padx=4)

        self.feedback = ttk.Label(card, text="", style="Status.TLabel")
        self.feedback.pack(anchor="w", pady=(8, 0))

    def save(self):
        self.feedback.config(
            text=(
                f"Settings saved (safe word: '{self.safe_word_var.get()}', "
                f"channel: {self.channel_var.get()}, theme: {self.theme_var.get()})"
            )
        )


# ===================== MAIN APP & STYLES =====================

class ReminderUIApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Voice Reminder System – UI Prototype (Person 1)")
        self.root.geometry("820x520")
        self.root.minsize(760, 480)

        self._configure_style()

        self.repo: ReminderRepository = MockReminderRepository()

        container = ttk.Frame(root, style="Body.TFrame")
        container.pack(fill="both", expand=True)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)

        self.screens = {}
        self.home_screen = HomeScreen(container, self)
        self.details_screen = DetailsScreen(container, self)
        self.settings_screen = SettingsScreen(container, self)

        self.screens["home"] = self.home_screen
        self.screens["details"] = self.details_screen
        self.screens["settings"] = self.settings_screen

        for s in self.screens.values():
            s.grid(row=0, column=0, sticky="nsew")

        self.show_screen("home")

    def _configure_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        bg_main = "#DADFF5"    # lavender background
        bg_card = "#FFFFFF"
        header_bg = "#9BC6EE"  # light blue
        accent = "#2563EB"
        text_primary = "#111827"
        text_muted = "#6B7280"
        stat_bg = "#F9C8A8"    # peach cards

        style.configure("Body.TFrame", background=bg_main)

        style.configure("HeaderBar.TFrame", background=header_bg)
        style.configure(
            "HeaderTitle.TLabel",
            background=header_bg,
            foreground="white",
            font=("Segoe UI Semibold", 14),
        )

        style.configure("Card.TFrame", background=bg_card, relief="flat")

        style.configure(
            "SectionTitle.TLabel",
            background=bg_card,
            foreground=text_primary,
            font=("Segoe UI Semibold", 11),
        )
        style.configure(
            "FormLabel.TLabel",
            background=bg_card,
            foreground=text_primary,
        )
        style.configure(
            "Hint.TLabel",
            background=bg_card,
            foreground=text_muted,
            font=("Segoe UI", 8),
        )
        style.configure(
            "Status.TLabel",
            background=bg_main,
            foreground=text_muted,
            font=("Segoe UI", 9),
        )

        style.configure(
            "Accent.TButton",
            background=accent,
            foreground="white",
            font=("Segoe UI", 10, "bold"),
            padding=6,
            borderwidth=0,
        )
        style.map("Accent.TButton", background=[("active", "#1D4ED8")])

        style.configure(
            "Secondary.TButton",
            background="#E5E7EB",
            foreground=text_primary,
            padding=6,
            borderwidth=0,
        )
        style.map("Secondary.TButton", background=[("active", "#D1D5DB")])

        style.configure(
            "Reminders.Treeview",
            background="#FFFFFF",
            fieldbackground="#FFFFFF",
            rowheight=24,
        )
        style.configure(
            "Reminders.Treeview.Heading",
            background="#E5E7EB",
            foreground=text_primary,
            font=("Segoe UI Semibold", 9),
        )

        style.configure(
            "StatCard.TFrame",
            background=stat_bg,
            relief="flat",
        )
        style.configure(
            "StatNumber.TLabel",
            background=stat_bg,
            foreground=text_primary,
            font=("Segoe UI Bold", 16),
        )
        style.configure(
            "StatLabel.TLabel",
            background=stat_bg,
            foreground=text_muted,
            font=("Segoe UI", 9),
        )

        self.root.configure(bg=bg_main)

    def show_screen(self, name: str):
        self.screens[name].tkraise()

    def show_details(self, reminder: Optional[Reminder]):
        self.details_screen.load(reminder)
        self.show_screen("details")


def main():
    root = tk.Tk()
    app = ReminderUIApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
