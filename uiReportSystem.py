import tkinter as tk
from tkinter import ttk
from datetime import date

# ---------------------------
# Helpers / sample data
# ---------------------------
REPORT_TYPES = [
    "Expected Occupancy",
    "Expected Room Income",
    "Incentive Discount",
    "Daily Arrivals",
    "Daily Occupancy"
]

HOTELS = [
    "All Hotels",
    "Ophelia Oasis",
    "Richard Royale",
    "Flynn's Fortune",
]

BOOKING_SOURCES = ["All", "Online", "Phone", "Walk-in"]
ROOM_TYPES = ["All", "Standard", "Deluxe", "Suite", "Penthouse"]
CUSTOMER_TYPES = ["All", "Individual", "Corporate", "Group", "Loyalty Member"]
PAYMENT_METHODS = ["All", "Card", "Cash", "Online", "On Account"]

YEARS = [str(y) for y in range(2018, date.today().year + 1)]
MONTHS = [
    ("01", "January"), ("02", "February"), ("03", "March"), ("04", "April"),
    ("05", "May"), ("06", "June"), ("07", "July"), ("08", "August"),
    ("09", "September"), ("10", "October"), ("11", "November"), ("12", "December")
]

def current_year_str():
    return str(date.today().year)

def current_month_str():
    return f"{date.today().month:02d}"

# ---------------------------
# App
# ---------------------------
m = tk.Tk()
m.title("Hotel Reservation System")
m.geometry("1000x640")
m.minsize(900, 580)


# Global Grid: 2 columns (left: Report + Filters, right: Preview)
m.columnconfigure(0, weight=1, uniform="col")
m.columnconfigure(1, weight=1, uniform="col")
m.rowconfigure(1, weight=1)  # main content area (row 1)
m.rowconfigure(0, weight=0)  # title row

style = ttk.Style()
style.configure("Header.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
style.configure("Header.TLabelframe", padding=(10, 10))


# ---------------------------
# Main Title Row
# ---------------------------
title_frame = ttk.Frame(m)
title_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12, 0))
title_frame.columnconfigure(0, weight=1)

main_title = ttk.Label(
    title_frame,
    text="Reservation — Generate Report",
    font=("Segoe UI", 18, "bold")
)
main_title.grid(row=0, column=0, sticky="w")

separator = ttk.Separator(title_frame, orient="horizontal")
separator.grid(row=1, column=0, sticky="ew", pady=(6, 0))

# ---------------------------
# Report Section (Frame)
# ---------------------------
report_frame = ttk.LabelFrame(m, text="Generate Report", style="Header.TLabelframe")
report_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=12)
for i in range(4):
    report_frame.columnconfigure(i, weight=1)

# Hotel (Combobox)
ttk.Label(report_frame, text="Hotel").grid(row=0, column=0, sticky="w", padx=8, pady=(10, 4))
hotel_var = tk.StringVar(value=HOTELS[0])
hotel_cb = ttk.Combobox(report_frame, textvariable=hotel_var, values=HOTELS, state="readonly")
hotel_cb.grid(row=0, column=1, sticky="ew", padx=8, pady=(10, 4))

# Report Type (Combobox)
ttk.Label(report_frame, text="Report Type").grid(row=0, column=2, sticky="w", padx=8, pady=(10, 4))
report_type_var = tk.StringVar(value=REPORT_TYPES[0])
report_type_cb = ttk.Combobox(report_frame, textvariable=report_type_var, values=REPORT_TYPES, state="readonly")
report_type_cb.grid(row=0, column=3, sticky="ew", padx=8, pady=(10, 4))

# Range Type (Month / Custom)
ttk.Label(report_frame, text="Range").grid(row=1, column=0, sticky="w", padx=8, pady=4)
range_type_var = tk.StringVar(value="By Month")
range_type_cb = ttk.Combobox(report_frame, textvariable=range_type_var,
                             values=["By Month", "Custom Dates"], state="readonly")
range_type_cb.grid(row=1, column=1, sticky="ew", padx=8, pady=4)

# Month / Year selectors (for "By Month")
ttk.Label(report_frame, text="Month").grid(row=1, column=2, sticky="w", padx=8, pady=4)
month_var = tk.StringVar(value=current_month_str())
month_cb = ttk.Combobox(report_frame, textvariable=month_var,
                        values=[code for code, name in MONTHS], width=6, state="readonly")
month_cb.grid(row=1, column=3, sticky="w", padx=8, pady=4)

ttk.Label(report_frame, text="Year").grid(row=2, column=2, sticky="w", padx=8, pady=4)
year_var = tk.StringVar(value=current_year_str())
year_cb = ttk.Combobox(report_frame, textvariable=year_var, values=YEARS, width=8, state="readonly")
year_cb.grid(row=2, column=3, sticky="w", padx=8, pady=4)

# Custom date range (Entries to keep zero-dependency) — ISO YYYY-MM-DD
# If you install tkcalendar: from tkcalendar import DateEntry and replace with DateEntry(report_frame, ...)
ttk.Label(report_frame, text="Start Date (YYYY-MM-DD)").grid(row=2, column=0, sticky="w", padx=8, pady=4)
start_date_var = tk.StringVar(value=f"{current_year_str()}-{current_month_str()}-01")
start_date_entry = ttk.Entry(report_frame, textvariable=start_date_var)
start_date_entry.grid(row=2, column=1, sticky="ew", padx=8, pady=4)

ttk.Label(report_frame, text="End Date (YYYY-MM-DD)").grid(row=3, column=0, sticky="w", padx=8, pady=(4, 10))
end_date_var = tk.StringVar(value=str(date.today()))
end_date_entry = ttk.Entry(report_frame, textvariable=end_date_var)
end_date_entry.grid(row=3, column=1, sticky="ew", padx=8, pady=(4, 10))

# Output
ttk.Label(report_frame, text="Output").grid(row=4, column=0, sticky="w", padx=8, pady=(4, 10))
output_var = tk.StringVar(value="Preview")
output_cb = ttk.Combobox(report_frame, textvariable=output_var,
                         values=["Preview", "PDF", "Excel (XLSX)", "CSV"], state="readonly")
output_cb.grid(row=4, column=1, sticky="ew", padx=8, pady=(4, 10))

# Comparison toggle
compare_var = tk.BooleanVar(value=False)
compare_chk = ttk.Checkbutton(report_frame, text="Compare with previous period", variable=compare_var)
compare_chk.grid(row=3, column=2, columnspan=2, sticky="w", padx=8, pady=(4, 10))

# ---------------------------
# Filters Section (Frame)
# ---------------------------
filters_frame = ttk.LabelFrame(m, text="Filters", style="Header.TLabelframe")
filters_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(200, 12))  # stacked below Report
filters_frame.columnconfigure(1, weight=1)

# Booking Source
ttk.Label(filters_frame, text="Booking Source").grid(row=0, column=0, sticky="w", padx=8, pady=(10, 4))
source_var = tk.StringVar(value=BOOKING_SOURCES[0])
source_cb = ttk.Combobox(filters_frame, textvariable=source_var, values=BOOKING_SOURCES, state="readonly")
source_cb.grid(row=0, column=1, sticky="ew", padx=8, pady=(10, 4))

# Room Type
ttk.Label(filters_frame, text="Room Type").grid(row=1, column=0, sticky="w", padx=8, pady=4)
room_var = tk.StringVar(value=ROOM_TYPES[0])
room_cb = ttk.Combobox(filters_frame, textvariable=room_var, values=ROOM_TYPES, state="readonly")
room_cb.grid(row=1, column=1, sticky="ew", padx=8, pady=4)

# Customer Type
ttk.Label(filters_frame, text="Customer Type").grid(row=2, column=0, sticky="w", padx=8, pady=4)
cust_var = tk.StringVar(value=CUSTOMER_TYPES[0])
cust_cb = ttk.Combobox(filters_frame, textvariable=cust_var, values=CUSTOMER_TYPES, state="readonly")
cust_cb.grid(row=2, column=1, sticky="ew", padx=8, pady=4)

# Status (multi-select via checkbuttons to keep it simple)
status_frame = ttk.Frame(filters_frame)
status_frame.grid(row=3, column=0, columnspan=2, sticky="ew", padx=8, pady=(4, 10))
ttk.Label(status_frame, text="Status: ").grid(row=0, column=0, sticky="w", padx=(0, 8))

status_vals = {
    "Checked-in": tk.BooleanVar(value=True),
    "Checked-out": tk.BooleanVar(value=True),
    "Cancelled": tk.BooleanVar(value=False),
    "No-show": tk.BooleanVar(value=False),
}
col = 1
for label, var in status_vals.items():
    ttk.Checkbutton(status_frame, text=label, variable=var).grid(row=0, column=col, sticky="w", padx=6)
    col += 1

# ---------------------------
# Preview Section (Frame)
# ---------------------------
preview_frame = ttk.LabelFrame(m, text="Preview", style="Header.TLabelframe")
preview_frame.grid(row=1, column=1, sticky="nsew", padx=12, pady=12)
preview_frame.rowconfigure(0, weight=1)
preview_frame.columnconfigure(0, weight=1)

# A Treeview as a tabular preview
columns = ("Date", "Room Type", "Booking Type", "Status")
preview_tv = ttk.Treeview(preview_frame, columns=columns, show="headings", height=20)
for c in columns:
    preview_tv.heading(c, text=c.upper())
    preview_tv.column(c, width=150, anchor="center")
preview_tv.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)

# Scrollbars
vsb = ttk.Scrollbar(preview_frame, orient="vertical", command=preview_tv.yview)
hsb = ttk.Scrollbar(preview_frame, orient="horizontal", command=preview_tv.xview)
preview_tv.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
vsb.grid(row=0, column=1, sticky="ns")
hsb.grid(row=1, column=0, sticky="ew")

# ---------------------------
# Buttons Row
# ---------------------------
buttons_frame = ttk.Frame(m)
buttons_frame.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=(0, 12))
buttons_frame.columnconfigure(0, weight=1)
buttons_frame.columnconfigure(1, weight=0)
buttons_frame.columnconfigure(2, weight=0)
buttons_frame.columnconfigure(3, weight=0)

def normalize_date_range():
    """
    Return (start_date_str, end_date_str) depending on range type.
    For 'By Month', build the first and last day string.
    For 'Custom Dates', use the entry values.
    """
    if range_type_var.get() == "By Month":
        y = int(year_var.get())
        mcode = int(month_var.get())
        # Compute last day of month
        if mcode in (1,3,5,7,8,10,12):
            last_day = 31
        elif mcode == 2:
            # leap year:
            last_day = 29 if (y % 400 == 0 or (y % 4 == 0 and y % 100 != 0)) else 28
        else:
            last_day = 30
        start = f"{y}-{mcode:02d}-01"
        end = f"{y}-{mcode:02d}-{last_day:02d}"
        return start, end
    else:
        return start_date_var.get().strip(), end_date_var.get().strip()

def collect_status_filter():
    active = [label for label, var in status_vals.items() if var.get()]
    return active

def generate_report():
    # Clear preview
    for item in preview_tv.get_children():
        preview_tv.delete(item)

    start_str, end_str = normalize_date_range()
    status_active = collect_status_filter()

    # Here you’d call your backend/report engine with these parameters:
    params = {
        "hotel": hotel_var.get(),
        "report_type": report_type_var.get(),
        "range_type": range_type_var.get(),
        "start_date": start_str,
        "end_date": end_str,
        "output": output_var.get(),
        "compare": compare_var.get(),
        "filters": {
            "booking_source": source_var.get(),
            "room_type": room_var.get(),
            "customer_type": cust_var.get(),
            "status": status_active
        }
    }

    # --- Demo data (replace with real query results) ---
    # Shape the preview columns per report type if you want.
    sample_rows = [
        ("2025-10-01", "Deluxe", "Website", "Checked-in"),
        ("2025-10-02", "Suite", "Walk-in", "Checked-out"),
        ("2025-10-03", "Standard", "Walk-in", "Cancelled"),
        ("2025-10-04", "Penthouse", "Corporate", "No-show"),
    ]
    for r in sample_rows:
        preview_tv.insert("", "end", values=r)

    # If exporting, dispatch to the right handler:
    if output_var.get() in ("PDF", "Excel (XLSX)", "CSV"):
        m.bell()  # stub feedback
        print(f"[Export] Would export {report_type_var.get()} as {output_var.get()} with params:", params)
    else:
        print("[Preview] Parameters:", params)

def clear_preview():
    for item in preview_tv.get_children():
        preview_tv.delete(item)

preview_btn = ttk.Button(buttons_frame, text="Preview / Generate", command=generate_report)
preview_btn.grid(row=0, column=1, sticky="e", padx=6)

clear_btn = ttk.Button(buttons_frame, text="Clear Preview", command=clear_preview)
clear_btn.grid(row=0, column=2, sticky="e", padx=6)

close_btn = ttk.Button(buttons_frame, text="Close", command=m.destroy)
close_btn.grid(row=0, column=3, sticky="e", padx=6)

# Behavior: enable/disable Month/Year vs Custom date entries
def update_range_controls(*_):
    is_month = (range_type_var.get() == "By Month")
    state_month = "readonly" if is_month else "disabled"
    state_year = "readonly" if is_month else "disabled"
    state_custom = "normal" if not is_month else "disabled"

    month_cb.config(state=state_month)
    year_cb.config(state=state_year)
    start_date_entry.config(state=state_custom)
    end_date_entry.config(state=state_custom)

range_type_var.trace_add("write", update_range_controls)
update_range_controls()

# Nice theme spacing
#style = ttk.Style()
#try:
#   style.theme_use("clam")
#except tk.TclError:
#   pass
#style.configure("Treeview", rowheight=26)

m.mainloop()
