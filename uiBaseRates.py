# uiBaseRates.py - Base Rate Management Module for HRS
# Add, Update, Delete base rates with validation

import json
import os
import datetime as dt
import tkinter as tk
from tkinter import ttk, messagebox

from validation import validate_date, validate_base_rate

# ============== CONFIGURATION ==============
DATA_FILE = "hrs_data.json"
TODAY = dt.date.today
ISO = dt.date.fromisoformat

# ============== DATA FUNCTIONS ==============

def load_state():
    """Load state from JSON file."""
    if not os.path.exists(DATA_FILE):
        return {"base_rates": {}, "reservations": [], "last_locator": 4000}
    with open(DATA_FILE) as f:
        return json.load(f)


def save_state(state):
    """Save state to JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ============== BASE RATE APPLICATION ==============

class BaseRateApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ophelia's Oasis — Base Rate Management")
        self.geometry("700x550")
        self.minsize(600, 500)
        
        self.state_data = load_state()
        
        # Initialize base rates if empty
        if not self.state_data["base_rates"]:
            self._initialize_default_rates()
        
        self._build_ui()
        self._refresh_rates_list()
    
    def _initialize_default_rates(self):
        """Create default base rates for next 90 days."""
        t = TODAY()
        self.state_data["base_rates"] = {
            (t + dt.timedelta(days=i)).isoformat(): 280.0 + 10 * (i % 5)
            for i in range(90)
        }
        save_state(self.state_data)
    
    def _build_ui(self):
        """Build the user interface."""
        main = ttk.Frame(self, padding=15)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)
        
        # Title
        ttk.Label(
            main, text="Base Rate Management",
            font=("Segoe UI", 16, "bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 15))
        
        # === Add/Update Form ===
        form = ttk.LabelFrame(main, text="Add / Update Base Rate", padding=10)
        form.grid(row=1, column=0, sticky="ew", pady=(0, 15))
        form.columnconfigure(1, weight=1)
        
        # Date
        ttk.Label(form, text="Date (YYYY-MM-DD):").grid(row=0, column=0, sticky="w", pady=5)
        self.date_var = tk.StringVar(value=TODAY().isoformat())
        self.date_entry = ttk.Entry(form, textvariable=self.date_var, width=15)
        self.date_entry.grid(row=0, column=1, sticky="w", pady=5)
        
        # Rate
        ttk.Label(form, text="Rate ($):").grid(row=1, column=0, sticky="w", pady=5)
        self.rate_var = tk.StringVar(value="300.00")
        self.rate_entry = ttk.Entry(form, textvariable=self.rate_var, width=15)
        self.rate_entry.grid(row=1, column=1, sticky="w", pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(form)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(btn_frame, text="Add Rate", command=self._add_rate).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Update Rate", command=self._update_rate).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete Rate", command=self._delete_rate).pack(side="left", padx=5)
        
        # Status message
        self.status_var = tk.StringVar()
        self.status_lbl = ttk.Label(form, textvariable=self.status_var, foreground="blue")
        self.status_lbl.grid(row=3, column=0, columnspan=2, pady=(10, 0))
        
        # === Rates List ===
        list_frame = ttk.LabelFrame(main, text="Current Base Rates", padding=10)
        list_frame.grid(row=2, column=0, sticky="nsew")
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Filter
        filter_frame = ttk.Frame(list_frame)
        filter_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        ttk.Label(filter_frame, text="Filter Month:").pack(side="left")
        self.filter_var = tk.StringVar(value="All")
        months = ["All"] + [f"{TODAY().year}-{m:02d}" for m in range(1, 13)]
        ttk.Combobox(
            filter_frame, textvariable=self.filter_var,
            values=months, state="readonly", width=12
        ).pack(side="left", padx=5)
        ttk.Button(filter_frame, text="Apply", command=self._refresh_rates_list).pack(side="left")
        ttk.Button(filter_frame, text="Refresh", command=self._refresh_rates_list).pack(side="left", padx=5)
        
        # Treeview
        cols = ("Date", "Rate", "Day of Week")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=15)
        
        self.tree.heading("Date", text="Date")
        self.tree.heading("Rate", text="Rate ($)")
        self.tree.heading("Day of Week", text="Day")
        
        self.tree.column("Date", width=120, anchor="center")
        self.tree.column("Rate", width=100, anchor="center")
        self.tree.column("Day of Week", width=100, anchor="center")
        
        self.tree.grid(row=1, column=0, sticky="nsew")
        
        # Scrollbar
        ysb = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        ysb.grid(row=1, column=1, sticky="ns")
        
        # Bind selection
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        
        # Summary
        self.summary_var = tk.StringVar()
        ttk.Label(list_frame, textvariable=self.summary_var).grid(row=2, column=0, sticky="w", pady=(5, 0))
        
        # === Bulk Operations ===
        bulk_frame = ttk.LabelFrame(main, text="Bulk Operations", padding=10)
        bulk_frame.grid(row=3, column=0, sticky="ew", pady=(15, 0))
        
        ttk.Label(bulk_frame, text="Generate rates from:").pack(side="left")
        self.bulk_start = tk.StringVar(value=TODAY().isoformat())
        ttk.Entry(bulk_frame, textvariable=self.bulk_start, width=12).pack(side="left", padx=5)
        
        ttk.Label(bulk_frame, text="to:").pack(side="left")
        self.bulk_end = tk.StringVar(value=(TODAY() + dt.timedelta(days=30)).isoformat())
        ttk.Entry(bulk_frame, textvariable=self.bulk_end, width=12).pack(side="left", padx=5)
        
        ttk.Label(bulk_frame, text="Rate:").pack(side="left")
        self.bulk_rate = tk.StringVar(value="300.00")
        ttk.Entry(bulk_frame, textvariable=self.bulk_rate, width=10).pack(side="left", padx=5)
        
        ttk.Button(bulk_frame, text="Generate", command=self._bulk_generate).pack(side="left", padx=10)
    
    def _refresh_rates_list(self):
        """Refresh the rates list."""
        self.state_data = load_state()
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Filter
        filter_val = self.filter_var.get()
        
        # Sort dates
        sorted_dates = sorted(self.state_data["base_rates"].keys())
        
        count = 0
        total = 0.0
        
        for date_str in sorted_dates:
            # Apply filter
            if filter_val != "All" and not date_str.startswith(filter_val):
                continue
            
            rate = self.state_data["base_rates"][date_str]
            
            # Get day of week
            try:
                d = ISO(date_str)
                dow = d.strftime("%A")
            except:
                dow = ""
            
            self.tree.insert("", "end", iid=date_str, values=(date_str, f"${rate:.2f}", dow))
            count += 1
            total += rate
        
        # Update summary
        avg = total / count if count > 0 else 0
        self.summary_var.set(f"Showing {count} rates  |  Average: ${avg:.2f}")
    
    def _on_select(self, _evt=None):
        """Handle rate selection."""
        sel = self.tree.selection()
        if not sel:
            return
        
        date_str = sel[0]
        rate = self.state_data["base_rates"].get(date_str, 300.0)
        
        self.date_var.set(date_str)
        self.rate_var.set(f"{rate:.2f}")
    
    def _add_rate(self):
        """Add a new base rate."""
        # Validate date
        valid, err, date_obj = validate_date(self.date_var.get(), "Date")
        if not valid:
            self._show_error(err)
            return
        
        # Validate rate
        valid, err, rate = validate_base_rate(self.rate_var.get())
        if not valid:
            self._show_error(err)
            return
        
        date_str = date_obj.isoformat()
        
        # Check if already exists
        if date_str in self.state_data["base_rates"]:
            self._show_error(f"Rate already exists for {date_str}. Use 'Update Rate' to modify.")
            return
        
        # Add rate
        self.state_data["base_rates"][date_str] = rate
        save_state(self.state_data)
        
        self._show_success(f"Rate ${rate:.2f} added for {date_str}")
        self._refresh_rates_list()
    
    def _update_rate(self):
        """Update an existing base rate."""
        # Validate date
        valid, err, date_obj = validate_date(self.date_var.get(), "Date")
        if not valid:
            self._show_error(err)
            return
        
        # Validate rate
        valid, err, rate = validate_base_rate(self.rate_var.get())
        if not valid:
            self._show_error(err)
            return
        
        date_str = date_obj.isoformat()
        
        # Check if exists
        if date_str not in self.state_data["base_rates"]:
            self._show_error(f"No rate found for {date_str}. Use 'Add Rate' to create.")
            return
        
        # Update rate
        old_rate = self.state_data["base_rates"][date_str]
        self.state_data["base_rates"][date_str] = rate
        save_state(self.state_data)
        
        self._show_success(f"Rate for {date_str} updated: ${old_rate:.2f} → ${rate:.2f}")
        self._refresh_rates_list()
    
    def _delete_rate(self):
        """Delete a base rate."""
        # Validate date
        valid, err, date_obj = validate_date(self.date_var.get(), "Date")
        if not valid:
            self._show_error(err)
            return
        
        date_str = date_obj.isoformat()
        
        # Check if exists
        if date_str not in self.state_data["base_rates"]:
            self._show_error(f"No rate found for {date_str}.")
            return
        
        # Confirm
        if not messagebox.askyesno("Confirm Delete", f"Delete rate for {date_str}?"):
            return
        
        # Delete
        rate = self.state_data["base_rates"].pop(date_str)
        save_state(self.state_data)
        
        self._show_success(f"Rate ${rate:.2f} deleted for {date_str}")
        self._refresh_rates_list()
    
    def _bulk_generate(self):
        """Generate rates for a date range."""
        # Validate start date
        valid, err, start_obj = validate_date(self.bulk_start.get(), "Start date")
        if not valid:
            self._show_error(err)
            return
        
        # Validate end date
        valid, err, end_obj = validate_date(self.bulk_end.get(), "End date")
        if not valid:
            self._show_error(err)
            return
        
        # Validate rate
        valid, err, rate = validate_base_rate(self.bulk_rate.get())
        if not valid:
            self._show_error(err)
            return
        
        if end_obj <= start_obj:
            self._show_error("End date must be after start date.")
            return
        
        # Generate
        count = 0
        current = start_obj
        while current < end_obj:
            date_str = current.isoformat()
            if date_str not in self.state_data["base_rates"]:
                self.state_data["base_rates"][date_str] = rate
                count += 1
            current += dt.timedelta(days=1)
        
        save_state(self.state_data)
        self._show_success(f"Generated {count} new rates at ${rate:.2f}")
        self._refresh_rates_list()
    
    def _show_error(self, message):
        """Show error message."""
        self.status_var.set(f"❌ {message}")
        self.status_lbl.config(foreground="red")
    
    def _show_success(self, message):
        """Show success message."""
        self.status_var.set(f"✓ {message}")
        self.status_lbl.config(foreground="green")


# ============== MAIN ==============

if __name__ == "__main__":
    app = BaseRateApp()
    app.mainloop()
