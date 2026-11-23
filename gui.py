import copy
import csv
import os
from datetime import datetime

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import reports
import seed
from insights import InsightsEngine
from main import DATA_DIR, EXPORT_DIR, load_config, save_config
from models import Trip
from service import ItineraryService
from sqlite_storage import create_storage, storage_label
from storage import Storage
from validation import CATEGORIES, STATUSES, validate_trip

COLUMNS = [
    ("ID", "id", 55),
    ("Destination", "destination", 190),
    ("Start", "start_date", 110),
    ("End", "end_date", 110),
    ("Category", "category", 100),
    ("Cost", "estimated_cost", 100),
    ("Status", "status", 110),
    ("Timing", "timing", 100),
]

TAG_COLORS = {
    "Overdue": "#c62828",
    "Ongoing": "#2e7d32",
    "Upcoming": "#1565c0",
    "Completed": "#616161",
    "Cancelled": "#9e9e9e",
    "Invalid": "#c62828",
}

EXPORT_TYPES = {
    "Markdown": ("md", [("Markdown files", "*.md")]),
    "CSV": ("csv", [("CSV files", "*.csv")]),
    "Audit log": ("txt", [("Text files", "*.txt")]),
    "JSON": ("json", [("JSON files", "*.json")]),
}


class TripDialog(tk.Toplevel):
    def __init__(self, parent, trip=None):
        super().__init__(parent)
        self.title("Edit Trip" if trip else "Add Trip")
        self.transient(parent)
        self.grab_set()
        self.resizable(False, False)
        self.result = None
        form = ttk.Frame(self, padding=16)
        form.grid(row=0, column=0, sticky="nsew")
        row = 0

        self.destination = tk.StringVar(value=trip.destination if trip else "")
        self._label(form, "Destination *", row)
        ttk.Entry(form, textvariable=self.destination, width=42).grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        self.start = tk.StringVar(value=trip.start_date if trip else "")
        self._label(form, "Start date * (YYYY-MM-DD)", row)
        ttk.Entry(form, textvariable=self.start, width=42).grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        self.end = tk.StringVar(value=trip.end_date if trip else "")
        self._label(form, "End date * (YYYY-MM-DD)", row)
        ttk.Entry(form, textvariable=self.end, width=42).grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        self.category = tk.StringVar(value=trip.category if trip else CATEGORIES[0])
        self._label(form, "Category *", row)
        ttk.Combobox(form, textvariable=self.category, values=CATEGORIES, state="readonly", width=39).grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        self.cost = tk.StringVar(value=f"{trip.estimated_cost:.2f}" if trip else "0.00")
        self._label(form, "Estimated cost *", row)
        ttk.Entry(form, textvariable=self.cost, width=42).grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        self.status = tk.StringVar(value=trip.status if trip else STATUSES[0])
        self._label(form, "Status *", row)
        ttk.Combobox(form, textvariable=self.status, values=STATUSES, state="readonly", width=39).grid(row=row, column=1, sticky="ew", pady=3)
        row += 1

        self._label(form, "Notes", row)
        self.notes = tk.Text(form, width=40, height=4, wrap="word")
        self.notes.grid(row=row, column=1, sticky="ew", pady=3)
        if trip:
            self.notes.insert("1.0", trip.notes)
        row += 1

        buttons = ttk.Frame(form)
        buttons.grid(row=row, column=0, columnspan=2, pady=(12, 0))
        ttk.Button(buttons, text="Save", command=self.apply).pack(side="left", padx=6)
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left", padx=6)

        self.bind("<Return>", lambda _: self.apply())
        self.bind("<Escape>", lambda _: self.destroy())
        self.after(100, lambda: self.destination.set(self.destination.get()))

    @staticmethod
    def _label(parent, text, row):
        ttk.Label(parent, text=text).grid(row=row, column=0, sticky="w", pady=3, padx=(0, 10))

    def apply(self):
        fields = {
            "destination": self.destination.get().strip(),
            "start_date": self.start.get().strip(),
            "end_date": self.end.get().strip(),
            "category": self.category.get(),
            "notes": self.notes.get("1.0", "end").strip(),
            "estimated_cost": self.cost.get().strip(),
            "status": self.status.get(),
        }
        errors = validate_trip(fields)
        if errors:
            messagebox.showerror("Invalid input", "\n".join("- " + item for item in errors), parent=self)
            return
        fields["estimated_cost"] = float(fields["estimated_cost"])
        self.result = fields
        self.destroy()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Travel Itinerary Organizer")
        self.geometry("1150x680")
        self.minsize(920, 560)
        self.configure(bg="#f4f6f8")

        config = load_config()
        self.config = config
        self.fmt = config.get("format", "json")
        self.cost_limit = float(config.get("cost_limit", 10000.0))
        self.storage = create_storage(config, DATA_DIR)
        self.service = ItineraryService(self.storage, self.cost_limit)

        self.keyword = tk.StringVar()
        self.category = tk.StringVar(value="All")
        self.status = tk.StringVar(value="All")
        self.export_kind = tk.StringVar(value="Markdown")
        self.history = []
        self.future = []

        self._build_header()
        self._build_toolbar()
        self._build_notebook()
        self._build_statusbar()
        self.refresh()
        self.bind_all("<Control-z>", lambda event: self.undo())
        self.bind_all("<Control-y>", lambda event: self.redo())

    def _build_header(self):
        header = ttk.Frame(self, padding=(14, 10))
        header.pack(fill="x")
        ttk.Label(header, text="Travel Itinerary Organizer", font=("Segoe UI", 16, "bold")).pack(side="left")
        ttk.Label(header, text="  StudentLife Hack - Project #52", foreground="#607d8b").pack(side="left")

    def _build_toolbar(self):
        bar = ttk.Frame(self, padding=(10, 4))
        bar.pack(fill="x")
        actions = [
            ("Undo", self.undo),
            ("Redo", self.redo),
            ("Add", self.add_trip),
            ("Edit", self.edit_trip),
            ("Delete", self.delete_trip),
            ("Import CSV", self.import_csv),
            ("Seed data", self.seed_data),
            ("Toggle storage", self.toggle_storage),
            ("DB backend", self.toggle_backend),
            ("Refresh", self.refresh),
        ]
        for label, command in actions:
            ttk.Button(bar, text=label, command=command).pack(side="left", padx=3)
        ttk.Frame(bar, width=18).pack(side="left")
        ttk.Label(bar, text="Export:").pack(side="left")
        ttk.Combobox(bar, textvariable=self.export_kind, values=list(EXPORT_TYPES), state="readonly", width=12).pack(side="left", padx=3)
        ttk.Button(bar, text="Export report", command=self.export_report).pack(side="left", padx=3)

    def _build_notebook(self):
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=6)

        self.trips_tab = ttk.Frame(self.notebook)
        self.summary_tab = ttk.Frame(self.notebook)
        self.warnings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.trips_tab, text="Trips")
        self.notebook.add(self.summary_tab, text="Summary & Analytics")
        self.notebook.add(self.warnings_tab, text="Warnings")

        self._build_trips_tab()
        self._build_summary_tab()
        self._build_warnings_tab()

    def _build_trips_tab(self):
        filt = ttk.Frame(self.trips_tab, padding=(8, 8))
        filt.pack(fill="x")
        ttk.Label(filt, text="Keyword:").pack(side="left", padx=(0, 4))
        ttk.Entry(filt, textvariable=self.keyword, width=26).pack(side="left", padx=3)
        ttk.Label(filt, text="Category:").pack(side="left", padx=(12, 4))
        ttk.Combobox(filt, textvariable=self.category, values=["All"] + CATEGORIES, state="readonly", width=13).pack(side="left", padx=3)
        ttk.Label(filt, text="Status:").pack(side="left", padx=(12, 4))
        ttk.Combobox(filt, textvariable=self.status, values=["All"] + STATUSES, state="readonly", width=13).pack(side="left", padx=3)
        ttk.Button(filt, text="Search", command=self.search).pack(side="left", padx=(12, 3))
        ttk.Button(filt, text="Clear", command=self.clear_filter).pack(side="left", padx=3)

        frame = ttk.Frame(self.trips_tab, padding=(8, 0, 8, 8))
        frame.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(frame, columns=[key for _, key, _ in COLUMNS], show="headings", selectmode="browse")
        for text, key, width in COLUMNS:
            self.tree.heading(key, text=text, command=lambda k=key: self.sort_by(k))
            self.tree.column(key, width=width, anchor="center" if key in ("id", "start_date", "end_date", "estimated_cost", "timing") else "w")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        for name, color in TAG_COLORS.items():
            self.tree.tag_configure(name, foreground=color)
        self.tree.bind("<Double-1>", lambda _: self.edit_trip())
        self.tree.bind("<Delete>", lambda _: self.delete_trip())

    def _build_summary_tab(self):
        frame = ttk.Frame(self.summary_tab, padding=12)
        frame.pack(fill="both", expand=True)
        self.summary_text = tk.Text(frame, wrap="none", font=("Consolas", 10), bg="#ffffff", relief="solid", padx=12, pady=12)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.summary_text.yview)
        self.summary_text.configure(yscrollcommand=scroll.set)
        self.summary_text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _build_warnings_tab(self):
        frame = ttk.Frame(self.warnings_tab, padding=(8, 8))
        frame.pack(fill="both", expand=True)
        self.warning_tree = ttk.Treeview(frame, columns=("id", "destination", "detail"), show="headings")
        self.warning_tree.heading("id", text="ID")
        self.warning_tree.heading("destination", text="Destination")
        self.warning_tree.heading("detail", text="Warning")
        self.warning_tree.column("id", width=70, anchor="center")
        self.warning_tree.column("destination", width=220)
        self.warning_tree.column("detail", width=620)
        scroll = ttk.Scrollbar(frame, orient="vertical", command=self.warning_tree.yview)
        self.warning_tree.configure(yscrollcommand=scroll.set)
        self.warning_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def _build_statusbar(self):
        self.statusbar = ttk.Label(self, text="", anchor="w", padding=(12, 5), foreground="#455a64")
        self.statusbar.pack(fill="x")

    def _snapshot(self):
        return copy.deepcopy([trip.to_dict() for trip in self.service.trips])

    def _push_history(self):
        self.history.append(self._snapshot())
        if len(self.history) > 30:
            self.history.pop(0)
        self.future.clear()

    def undo(self):
        if not self.history:
            return
        self.future.append(self._snapshot())
        self.service.replace_all([Trip.from_dict(row) for row in self.history.pop()])
        self.refresh()
        messagebox.showinfo("Undo", "Last change reverted.")

    def redo(self):
        if not self.future:
            return
        self.history.append(self._snapshot())
        self.service.replace_all([Trip.from_dict(row) for row in self.future.pop()])
        self.refresh()
        messagebox.showinfo("Redo", "Change reapplied.")

    def refresh(self):
        self._fill_tree(sorted(self.service.trips, key=lambda t: t.id))
        self._fill_summary()
        self._fill_warnings()
        self._set_status()

    def _fill_tree(self, trips):
        self.tree.delete(*self.tree.get_children())
        for trip in trips:
            timing = trip.timing()
            values = (
                trip.id, trip.destination, trip.start_date, trip.end_date,
                trip.category, f"{trip.estimated_cost:.2f}", trip.status, timing,
            )
            self.tree.insert("", "end", values=values, tags=(timing,))
        self._set_status()

    def _fill_summary(self):
        data = self.service.summary()
        lines = ["TRAVEL ITINERARY ORGANIZER - SUMMARY", "=" * 50, ""]
        lines += [line.strip() for line in reports.summary_lines(data)]
        for title, key in (("BY CATEGORY", "by_category"), ("BY STATUS", "by_status"), ("BY TIMING", "by_timing")):
            lines += ["", title, "-" * 50]
            lines += [line.strip() for line in reports.bar_chart(data[key], width=30)]
        lines += ["", "HIGHEST ESTIMATED COSTS", "-" * 50]
        for trip in data["top_costs"]:
            lines.append(f"  {trip.destination:<24} {trip.estimated_cost:>10.2f}")
        insights = InsightsEngine(self.service).report()
        lines += ["", "SMART INSIGHTS", "-" * 50]
        for month, total in insights["monthly_spend"]:
            lines.append(f"  {month} spend: {total:.2f}")
        lines.append(f"  Upcoming (30 days): {len(insights['upcoming'])}")
        lines.append(f"  Forecast spend: {insights['forecast']:.2f}")
        lines.append(f"  Projected next-month spend: {insights['projected_spend']:.2f}")
        lines.append(f"  Cost anomalies: {len(insights['anomalies'])}")
        self.summary_text.configure(state="normal")
        self.summary_text.delete("1.0", "end")
        self.summary_text.insert("1.0", "\n".join(lines))
        self.summary_text.configure(state="disabled")

    def _fill_warnings(self):
        self.warning_tree.delete(*self.warning_tree.get_children())
        for trip, message in self.service.warnings():
            self.warning_tree.insert("", "end", values=(trip.id, trip.destination, message))

    def _set_status(self, showing=None):
        shown = showing if showing is not None else len(self.tree.get_children())
        self.statusbar.configure(
            text=f"  Records: {len(self.service.trips)}   Showing: {shown}   Storage: {storage_label(self.config)}   Cost limit: {self.cost_limit:.2f}"
        )

    def sort_by(self, key):
        items = list(self.service.trips)
        reverse = getattr(self, "_sort_reverse", {}).get(key, False)
        if key == "estimated_cost":
            items.sort(key=lambda t: t.estimated_cost, reverse=reverse)
        elif key == "id":
            items.sort(key=lambda t: t.id, reverse=reverse)
        else:
            items.sort(key=lambda t: str(getattr(t, key, "")).lower(), reverse=reverse)
        state = getattr(self, "_sort_reverse", {})
        state[key] = not reverse
        self._sort_reverse = state
        self._fill_tree(items)

    def selected_trip(self):
        selection = self.tree.selection()
        if not selection:
            return None
        values = self.tree.item(selection[0], "values")
        return self.service.find(int(values[0]))

    def add_trip(self):
        dialog = TripDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            self._push_history()
            trip = self.service.add(dialog.result)
            self.refresh()
            messagebox.showinfo("Saved", f"Trip #{trip.id} added to {trip.destination}.")

    def edit_trip(self):
        trip = self.selected_trip()
        if not trip:
            messagebox.showwarning("No selection", "Select a trip in the table first.")
            return
        dialog = TripDialog(self, trip)
        self.wait_window(dialog)
        if dialog.result:
            self._push_history()
            self.service.update(trip.id, dialog.result)
            self.refresh()
            messagebox.showinfo("Saved", f"Trip #{trip.id} updated.")

    def delete_trip(self):
        trip = self.selected_trip()
        if not trip:
            messagebox.showwarning("No selection", "Select a trip in the table first.")
            return
        if messagebox.askyesno("Delete", f"Delete trip #{trip.id} - {trip.destination}?"):
            self._push_history()
            self.service.delete(trip.id)
            self.refresh()

    def search(self):
        category = None if self.category.get() == "All" else self.category.get()
        status = None if self.status.get() == "All" else self.status.get()
        results = self.service.search(self.keyword.get(), category, status)
        self._fill_tree(sorted(results, key=lambda t: t.id))
        self._set_status(showing=len(results))

    def clear_filter(self):
        self.keyword.set("")
        self.category.set("All")
        self.status.set("All")
        self.refresh()

    def export_report(self):
        kind = self.export_kind.get()
        extension, filetypes = EXPORT_TYPES[kind]
        initial = f"itinerary_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{extension}"
        path = filedialog.asksaveasfilename(
            initialdir=EXPORT_DIR, initialfile=initial, defaultextension=f".{extension}",
            filetypes=filetypes, title=f"Export {kind} report",
        )
        if not path:
            return
        summary = self.service.summary()
        trips = list(self.service.trips)
        warnings = self.service.warnings()
        if kind == "Markdown":
            reports.export_markdown(summary, trips, warnings, path)
        elif kind == "CSV":
            reports.export_csv(trips, path)
        elif kind == "Audit log":
            reports.export_audit(summary, trips, warnings, path)
        else:
            reports.export_json(trips, path)
        messagebox.showinfo("Exported", f"Report saved to:\n{path}")

    def import_csv(self):
        path = filedialog.askopenfilename(
            initialdir=DATA_DIR, filetypes=[("CSV files", "*.csv"), ("All files", "*.*")], title="Import CSV",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
        except (OSError, csv.Error) as exc:
            messagebox.showerror("Import failed", str(exc))
            return
        valid, errors = [], []
        next_id = self.service.next_id()
        for line, row in enumerate(rows, start=2):
            problems = validate_trip(row)
            if problems:
                errors.append((line, "; ".join(problems)))
                continue
            row["id"] = next_id
            row["estimated_cost"] = float(row["estimated_cost"])
            row["created_at"] = datetime.now().isoformat(timespec="seconds")
            valid.append(Trip.from_dict(row))
            next_id += 1
        if valid:
            self._push_history()
            self.service.replace_all(list(self.service.trips) + valid)
            self.refresh()
        detail = f"Imported: {len(valid)}\nRejected: {len(errors)}"
        if errors:
            detail += "\n\n" + "\n".join(f"Row {line}: {reason}" for line, reason in errors[:10])
            if len(errors) > 10:
                detail += f"\n... and {len(errors) - 10} more"
        messagebox.showinfo("Import complete", detail)

    def seed_data(self):
        rows = seed.generate(40)
        seed.write_samples(rows, DATA_DIR)
        if messagebox.askyesno("Seed data", "Replace the current dataset with 40 sample records?"):
            self._push_history()
            self.service.replace_all([Trip.from_dict(row) for row in rows])
        elif messagebox.askyesno("Seed data", "Append the 40 sample records instead?"):
            self._push_history()
            starting = self.service.next_id()
            for offset, row in enumerate(rows):
                row["id"] = starting + offset
            self.service.replace_all(list(self.service.trips) + [Trip.from_dict(row) for row in rows])
        else:
            return
        self.refresh()
        messagebox.showinfo("Seed complete", f"Dataset now has {len(self.service.trips)} records.")

    def toggle_backend(self):
        new_backend = "sqlite" if self.config.get("backend", "file") != "sqlite" else "file"
        target = create_storage({"backend": new_backend, "format": self.fmt}, DATA_DIR)
        target.save(self.service.trips)
        self.config["backend"] = new_backend
        self.storage = target
        self.service = ItineraryService(self.storage, self.cost_limit)
        save_config(self.config)
        self.refresh()
        messagebox.showinfo("Database backend", f"Backend switched to {storage_label(self.config)}; data preserved.")

    def toggle_storage(self):
        new_fmt = "csv" if self.fmt == "json" else "json"
        target = Storage(os.path.join(DATA_DIR, f"itinerary.{new_fmt}"), new_fmt)
        target.save(self.service.trips)
        self.fmt = new_fmt
        self.storage = target
        self.service = ItineraryService(self.storage, self.cost_limit)
        self.config["format"] = new_fmt
        save_config(self.config)
        self.refresh()
        messagebox.showinfo("Storage", f"Storage switched to {new_fmt.upper()}; data preserved.")


def launch():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    launch()
