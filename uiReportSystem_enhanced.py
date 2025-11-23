# uiReportSystem_enhanced.py - Enhanced Report System for HRS
# Generates actual reports from reservation data

import json
import os
import datetime as dt
import tkinter as tk
from tkinter import ttk, messagebox

# ============== CONFIGURATION ==============
DATA_FILE = "hrs_data.json"
TODAY = dt.date.today
ISO = dt.date.fromisoformat
ROOM_COUNT = 45

REPORT_TYPES = [
    "Daily Arrivals",
    "Daily Departures", 
    "Daily Occupancy",
    "Expected Occupancy (30-day)",
    "Expected Room Income (30-day)",
    "Incentive Discount Report",
    "Bill Accommodation Summary",
]

# ============== DATA FUNCTIONS ==============

def load_state():
    """Load state from JSON file."""
    if not os.path.exists(DATA_FILE):
        return {"base_rates": {}, "reservations": [], "last_locator": 4000}
    with open(DATA_FILE) as f:
        return json.load(f)


def daterange(start, end):
    """Generate dates from start to end (exclusive)."""
    while start < end:
        yield start
        start += dt.timedelta(days=1)


# ============== REPORT GENERATORS ==============

def generate_daily_arrivals(state, report_date):
    """Generate daily arrivals report for a specific date."""
    date_str = report_date.isoformat()
    
    arrivals = [
        r for r in state["reservations"]
        if r.get("arrive") == date_str and r.get("status") in ("Booked", "In-House")
    ]
    
    # Sort by guest name
    arrivals.sort(key=lambda x: x.get("guest_name", ""))
    
    report = {
        "title": f"Daily Arrivals Report - {date_str}",
        "date": date_str,
        "columns": ["Locator", "Guest Name", "Room Type", "Res Type", "Nights", "Room #", "Total"],
        "data": [],
        "summary": {}
    }
    
    total_revenue = 0
    for r in arrivals:
        try:
            nights = (ISO(r["depart"]) - ISO(r["arrive"])).days
        except:
            nights = 0
        
        total = r.get("total_locked", 0)
        total_revenue += total
        
        report["data"].append([
            r.get("locator", ""),
            r.get("guest_name", ""),
            r.get("room_type", ""),
            r.get("rtype", ""),
            nights,
            r.get("assigned_room", "N/A"),
            f"${total:,.2f}"
        ])
    
    report["summary"] = {
        "Total Arrivals": len(arrivals),
        "Total Expected Revenue": f"${total_revenue:,.2f}"
    }
    
    return report


def generate_daily_departures(state, report_date):
    """Generate daily departures report."""
    date_str = report_date.isoformat()
    
    departures = [
        r for r in state["reservations"]
        if r.get("depart") == date_str and r.get("status") in ("In-House", "Checked-out")
    ]
    
    departures.sort(key=lambda x: x.get("guest_name", ""))
    
    report = {
        "title": f"Daily Departures Report - {date_str}",
        "date": date_str,
        "columns": ["Locator", "Guest Name", "Room #", "Res Type", "Status", "Balance Due"],
        "data": [],
        "summary": {}
    }
    
    total_balance = 0
    for r in departures:
        total = r.get("total_locked", 0)
        paid = r.get("paid_advance", 0)
        balance = total - paid
        total_balance += balance
        
        report["data"].append([
            r.get("locator", ""),
            r.get("guest_name", ""),
            r.get("assigned_room", ""),
            r.get("rtype", ""),
            r.get("status", ""),
            f"${balance:,.2f}"
        ])
    
    report["summary"] = {
        "Total Departures": len(departures),
        "Total Balance Due": f"${total_balance:,.2f}"
    }
    
    return report


def generate_daily_occupancy(state, report_date):
    """Generate daily occupancy report."""
    date_str = report_date.isoformat()
    
    # Count occupied rooms for this date
    occupied = [
        r for r in state["reservations"]
        if r.get("status") in ("Booked", "In-House")
        and r.get("arrive") <= date_str < r.get("depart", "9999-12-31")
    ]
    
    occupied_count = len(occupied)
    available_count = ROOM_COUNT - occupied_count
    occupancy_pct = (occupied_count / ROOM_COUNT) * 100 if ROOM_COUNT > 0 else 0
    
    report = {
        "title": f"Daily Occupancy Report - {date_str}",
        "date": date_str,
        "columns": ["Room #", "Guest Name", "Locator", "Res Type", "Arrive", "Depart"],
        "data": [],
        "summary": {}
    }
    
    # Sort by room number
    occupied.sort(key=lambda x: x.get("assigned_room", "ZZZ"))
    
    for r in occupied:
        report["data"].append([
            r.get("assigned_room", "N/A"),
            r.get("guest_name", ""),
            r.get("locator", ""),
            r.get("rtype", ""),
            r.get("arrive", ""),
            r.get("depart", "")
        ])
    
    report["summary"] = {
        "Total Rooms": ROOM_COUNT,
        "Occupied Rooms": occupied_count,
        "Available Rooms": available_count,
        "Occupancy Rate": f"{occupancy_pct:.1f}%"
    }
    
    return report


def generate_expected_occupancy(state, start_date, days=30):
    """Generate expected occupancy report for next N days."""
    report = {
        "title": f"Expected Occupancy Report - Next {days} Days",
        "date": start_date.isoformat(),
        "columns": ["Date", "Day", "Occupied", "Available", "Occupancy %"],
        "data": [],
        "summary": {}
    }
    
    total_occupied = 0
    end_date = start_date + dt.timedelta(days=days)
    
    for d in daterange(start_date, end_date):
        date_str = d.isoformat()
        dow = d.strftime("%A")[:3]
        
        # Count reservations for this date
        occupied = sum(
            1 for r in state["reservations"]
            if r.get("status") in ("Booked", "In-House")
            and r.get("arrive", "9999-12-31") <= date_str < r.get("depart", "0000-01-01")
        )
        
        available = ROOM_COUNT - occupied
        pct = (occupied / ROOM_COUNT) * 100 if ROOM_COUNT > 0 else 0
        total_occupied += occupied
        
        report["data"].append([
            date_str,
            dow,
            occupied,
            available,
            f"{pct:.1f}%"
        ])
    
    avg_occupancy = (total_occupied / days / ROOM_COUNT) * 100 if days > 0 and ROOM_COUNT > 0 else 0
    
    report["summary"] = {
        "Period": f"{days} days",
        "Average Occupancy": f"{avg_occupancy:.1f}%",
        "Total Room-Nights Available": days * ROOM_COUNT,
        "Total Room-Nights Booked": total_occupied
    }
    
    return report


def generate_expected_income(state, start_date, days=30):
    """Generate expected room income report for next N days."""
    report = {
        "title": f"Expected Room Income Report - Next {days} Days",
        "date": start_date.isoformat(),
        "columns": ["Date", "Expected Revenue", "Reservations", "Avg Rate"],
        "data": [],
        "summary": {}
    }
    
    total_revenue = 0
    end_date = start_date + dt.timedelta(days=days)
    
    for d in daterange(start_date, end_date):
        date_str = d.isoformat()
        
        # Find all reservations that include this date
        daily_revenue = 0
        res_count = 0
        
        for r in state["reservations"]:
            if r.get("status") not in ("Booked", "In-House"):
                continue
            
            arrive = r.get("arrive", "9999-12-31")
            depart = r.get("depart", "0000-01-01")
            
            if arrive <= date_str < depart:
                nightly = r.get("snapshot", {}).get("nightly", {})
                if date_str in nightly:
                    daily_revenue += nightly[date_str]
                    res_count += 1
        
        avg_rate = daily_revenue / res_count if res_count > 0 else 0
        total_revenue += daily_revenue
        
        report["data"].append([
            date_str,
            f"${daily_revenue:,.2f}",
            res_count,
            f"${avg_rate:,.2f}"
        ])
    
    report["summary"] = {
        "Period": f"{days} days",
        "Total Expected Revenue": f"${total_revenue:,.2f}",
        "Average Daily Revenue": f"${total_revenue/days:,.2f}" if days > 0 else "$0.00"
    }
    
    return report


def generate_incentive_report(state, start_date, days=30):
    """Generate incentive discount impact report."""
    report = {
        "title": f"Incentive Discount Report - Next {days} Days",
        "date": start_date.isoformat(),
        "columns": ["Locator", "Guest", "Arrive", "Depart", "Full Rate", "Discounted", "Savings"],
        "data": [],
        "summary": {}
    }
    
    total_full = 0
    total_discounted = 0
    
    end_date = start_date + dt.timedelta(days=days)
    
    incentive_res = [
        r for r in state["reservations"]
        if r.get("rtype") == "Incentive"
        and r.get("status") in ("Booked", "In-House")
        and ISO(r.get("arrive", "9999-12-31")) < end_date
    ]
    
    for r in incentive_res:
        nightly = r.get("snapshot", {}).get("nightly", {})
        discounted = sum(nightly.values())
        
        # Calculate what full rate would have been
        full_rate = discounted / 0.80 if discounted > 0 else 0  # Incentive is 80%
        savings = full_rate - discounted
        
        total_full += full_rate
        total_discounted += discounted
        
        report["data"].append([
            r.get("locator", ""),
            r.get("guest_name", ""),
            r.get("arrive", ""),
            r.get("depart", ""),
            f"${full_rate:,.2f}",
            f"${discounted:,.2f}",
            f"${savings:,.2f}"
        ])
    
    total_savings = total_full - total_discounted
    discount_pct = (total_savings / total_full * 100) if total_full > 0 else 0
    
    report["summary"] = {
        "Total Incentive Reservations": len(incentive_res),
        "Revenue at Full Rate": f"${total_full:,.2f}",
        "Actual Revenue": f"${total_discounted:,.2f}",
        "Total Discount Given": f"${total_savings:,.2f}",
        "Average Discount": f"{discount_pct:.1f}%"
    }
    
    return report


def generate_bill_summary(state, start_date, end_date):
    """Generate bill accommodation summary for date range."""
    report = {
        "title": f"Bill Accommodation Summary",
        "date": f"{start_date.isoformat()} to {end_date.isoformat()}",
        "columns": ["Locator", "Guest", "Check-Out", "Room", "Nights", "Total", "Status"],
        "data": [],
        "summary": {}
    }
    
    # Find checked-out reservations in date range
    checkouts = [
        r for r in state["reservations"]
        if r.get("status") == "Checked-out"
        and start_date.isoformat() <= r.get("check_out_date", r.get("depart", "")) <= end_date.isoformat()
    ]
    
    total_revenue = 0
    
    for r in checkouts:
        try:
            nights = (ISO(r["depart"]) - ISO(r["arrive"])).days
        except:
            nights = 0
        
        total = r.get("total_locked", 0)
        total_revenue += total
        
        report["data"].append([
            r.get("locator", ""),
            r.get("guest_name", ""),
            r.get("check_out_date", r.get("depart", "")),
            r.get("assigned_room", ""),
            nights,
            f"${total:,.2f}",
            r.get("status", "")
        ])
    
    report["summary"] = {
        "Total Check-Outs": len(checkouts),
        "Total Revenue": f"${total_revenue:,.2f}",
        "Average Bill": f"${total_revenue/len(checkouts):,.2f}" if checkouts else "$0.00"
    }
    
    return report


# ============== REPORT APPLICATION ==============

class ReportApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ophelia's Oasis — Report System")
        self.geometry("1000x700")
        self.minsize(900, 600)
        
        self.state_data = load_state()
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the user interface."""
        main = ttk.Frame(self, padding=15)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=0)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(1, weight=1)
        
        # Title
        ttk.Label(
            main, text="Report Generator",
            font=("Segoe UI", 16, "bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 15))
        
        # === Left: Report Options ===
        left = ttk.LabelFrame(main, text="Report Options", padding=10)
        left.grid(row=1, column=0, sticky="ns", padx=(0, 15))
        
        # Report Type
        ttk.Label(left, text="Report Type:").grid(row=0, column=0, sticky="w", pady=5)
        self.report_type_var = tk.StringVar(value=REPORT_TYPES[0])
        report_combo = ttk.Combobox(
            left, textvariable=self.report_type_var,
            values=REPORT_TYPES, state="readonly", width=28
        )
        report_combo.grid(row=1, column=0, sticky="w", pady=(0, 10))
        
        # Date Selection
        ttk.Label(left, text="Report Date:").grid(row=2, column=0, sticky="w", pady=5)
        self.date_var = tk.StringVar(value=TODAY().isoformat())
        ttk.Entry(left, textvariable=self.date_var, width=15).grid(row=3, column=0, sticky="w", pady=(0, 10))
        
        # Date Range (for some reports)
        ttk.Label(left, text="End Date (if range):").grid(row=4, column=0, sticky="w", pady=5)
        self.end_date_var = tk.StringVar(value=(TODAY() + dt.timedelta(days=30)).isoformat())
        ttk.Entry(left, textvariable=self.end_date_var, width=15).grid(row=5, column=0, sticky="w", pady=(0, 10))
        
        # Days (for forecast reports)
        ttk.Label(left, text="Forecast Days:").grid(row=6, column=0, sticky="w", pady=5)
        self.days_var = tk.StringVar(value="30")
        ttk.Entry(left, textvariable=self.days_var, width=10).grid(row=7, column=0, sticky="w", pady=(0, 15))
        
        # Generate Button
        ttk.Button(
            left, text="Generate Report",
            command=self._generate_report
        ).grid(row=8, column=0, sticky="ew", pady=10)
        
        # Export Buttons
        ttk.Separator(left, orient="horizontal").grid(row=9, column=0, sticky="ew", pady=10)
        
        ttk.Button(
            left, text="Export to Text File",
            command=self._export_text
        ).grid(row=10, column=0, sticky="ew", pady=5)
        
        ttk.Button(
            left, text="Print Preview",
            command=self._print_preview
        ).grid(row=11, column=0, sticky="ew", pady=5)
        
        # === Right: Report Display ===
        right = ttk.LabelFrame(main, text="Report Output", padding=10)
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        
        # Report Title
        self.report_title_var = tk.StringVar(value="Select a report type and click Generate")
        ttk.Label(
            right, textvariable=self.report_title_var,
            font=("Segoe UI", 12, "bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))
        
        # Report Table
        self.tree = ttk.Treeview(right, show="headings", height=20)
        self.tree.grid(row=1, column=0, sticky="nsew")
        
        # Scrollbars
        ysb = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        xsb = ttk.Scrollbar(right, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=ysb.set, xscroll=xsb.set)
        ysb.grid(row=1, column=1, sticky="ns")
        xsb.grid(row=2, column=0, sticky="ew")
        
        # Summary Frame
        self.summary_frame = ttk.LabelFrame(right, text="Summary", padding=10)
        self.summary_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        
        self.summary_text = tk.Text(self.summary_frame, height=4, wrap="word")
        self.summary_text.pack(fill="x")
        self.summary_text.config(state="disabled")
        
        # Store current report
        self.current_report = None
    
    def _generate_report(self):
        """Generate the selected report."""
        self.state_data = load_state()
        
        report_type = self.report_type_var.get()
        
        try:
            report_date = ISO(self.date_var.get())
        except:
            messagebox.showerror("Error", "Invalid report date. Use YYYY-MM-DD format.")
            return
        
        try:
            days = int(self.days_var.get())
        except:
            days = 30
        
        # Generate report based on type
        if report_type == "Daily Arrivals":
            report = generate_daily_arrivals(self.state_data, report_date)
        elif report_type == "Daily Departures":
            report = generate_daily_departures(self.state_data, report_date)
        elif report_type == "Daily Occupancy":
            report = generate_daily_occupancy(self.state_data, report_date)
        elif report_type == "Expected Occupancy (30-day)":
            report = generate_expected_occupancy(self.state_data, report_date, days)
        elif report_type == "Expected Room Income (30-day)":
            report = generate_expected_income(self.state_data, report_date, days)
        elif report_type == "Incentive Discount Report":
            report = generate_incentive_report(self.state_data, report_date, days)
        elif report_type == "Bill Accommodation Summary":
            try:
                end_date = ISO(self.end_date_var.get())
            except:
                end_date = report_date + dt.timedelta(days=30)
            report = generate_bill_summary(self.state_data, report_date, end_date)
        else:
            messagebox.showerror("Error", "Unknown report type.")
            return
        
        self.current_report = report
        self._display_report(report)
    
    def _display_report(self, report):
        """Display report in the UI."""
        # Update title
        self.report_title_var.set(report["title"])
        
        # Clear tree
        self.tree.delete(*self.tree.get_children())
        
        # Configure columns
        columns = report["columns"]
        self.tree["columns"] = columns
        
        for col in columns:
            self.tree.heading(col, text=col)
            # Set column width based on content
            width = max(80, len(col) * 10)
            self.tree.column(col, width=width, anchor="center")
        
        # Add data
        for row in report["data"]:
            self.tree.insert("", "end", values=row)
        
        # Update summary
        self.summary_text.config(state="normal")
        self.summary_text.delete("1.0", "end")
        
        summary_lines = []
        for key, value in report["summary"].items():
            summary_lines.append(f"{key}: {value}")
        
        self.summary_text.insert("1.0", "   |   ".join(summary_lines))
        self.summary_text.config(state="disabled")
    
    def _export_text(self):
        """Export report to text file."""
        if not self.current_report:
            messagebox.showwarning("Warning", "Generate a report first.")
            return
        
        report = self.current_report
        
        # Build text content
        lines = [
            "=" * 80,
            f"  {report['title']}",
            f"  Generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 80,
            ""
        ]
        
        # Column headers
        header = "  ".join(f"{col:<15}" for col in report["columns"])
        lines.append(header)
        lines.append("-" * len(header))
        
        # Data rows
        for row in report["data"]:
            line = "  ".join(f"{str(val):<15}" for val in row)
            lines.append(line)
        
        # Summary
        lines.append("")
        lines.append("-" * 80)
        lines.append("SUMMARY:")
        for key, value in report["summary"].items():
            lines.append(f"  {key}: {value}")
        lines.append("=" * 80)
        
        # Save to file
        filename = f"report_{report['title'].replace(' ', '_').replace('/', '-')}_{TODAY().isoformat()}.txt"
        with open(filename, "w") as f:
            f.write("\n".join(lines))
        
        messagebox.showinfo("Exported", f"Report saved to: {filename}")
    
    def _print_preview(self):
        """Show print preview in a new window."""
        if not self.current_report:
            messagebox.showwarning("Warning", "Generate a report first.")
            return
        
        report = self.current_report
        
        # Create preview window
        preview = tk.Toplevel(self)
        preview.title(f"Print Preview - {report['title']}")
        preview.geometry("700x500")
        
        # Text widget
        text = tk.Text(preview, wrap="none", font=("Courier New", 10))
        text.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Build content
        lines = [
            "=" * 70,
            f"  OPHELIA'S OASIS HOTEL",
            f"  {report['title']}",
            f"  Generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "=" * 70,
            ""
        ]
        
        # Column headers
        header = " | ".join(f"{col:<12}" for col in report["columns"])
        lines.append(header)
        lines.append("-" * len(header))
        
        # Data
        for row in report["data"]:
            line = " | ".join(f"{str(val):<12}" for val in row)
            lines.append(line)
        
        # Summary
        lines.append("")
        lines.append("=" * 70)
        lines.append("SUMMARY")
        lines.append("-" * 70)
        for key, value in report["summary"].items():
            lines.append(f"  {key}: {value}")
        lines.append("=" * 70)
        
        text.insert("1.0", "\n".join(lines))
        text.config(state="disabled")


# ============== MAIN ==============

if __name__ == "__main__":
    app = ReportApp()
    app.mainloop()
