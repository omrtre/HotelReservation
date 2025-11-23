# uiMakeReservation_enhanced.py - Enhanced Reservation Module for HRS
# With full input validation, credit card fields, address, and comments

import json
import os
import datetime as dt
import tkinter as tk
from tkinter import ttk, messagebox

from validation import (
    validate_guest_name, validate_address, validate_phone, validate_email,
    validate_date, validate_arrival_date, validate_number_of_days, validate_comments,
    validate_credit_card_number, validate_credit_card_expiry, validate_credit_card_type,
    validate_amount, trim_and_clean, format_phone_display, format_cc_masked
)

# ============== CONFIGURATION ==============
DATA_FILE = "hrs_data.json"
ROOM_COUNT = 45
TODAY = dt.date.today
ISO = dt.date.fromisoformat

RATE_MULT = {
    "Prepaid": 0.75,
    "60-Day": 0.85,
    "Conventional": 1.00,
    "Incentive": 0.80
}

ROOM_TYPES = ["Standard", "Deluxe", "Suite", "Penthouse"]
STATUSES = ["Booked", "In-House", "Checked-out", "Cancelled", "No-Show"]
RESERVATION_TYPES = ["Prepaid", "60-Day", "Conventional", "Incentive"]
CC_TYPES = ["Visa", "MasterCard", "American Express", "Discover"]

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


def daterange(start, end):
    """Generate dates from start to end (exclusive)."""
    while start < end:
        yield start
        start += dt.timedelta(days=1)


def base_rate(state, d):
    """Get base rate for a date."""
    return float(state["base_rates"].get(d.isoformat(), 300.0))


def occ_ratio(state, start, end):
    """Calculate occupancy ratio for date range."""
    res = [r for r in state["reservations"] 
           if r.get("status", "Booked") in ("Booked", "In-House")]
    if not res:
        return 0.0
    nightly = [
        sum(ISO(r["arrive"]) <= d < ISO(r["depart"]) for r in res)
        for d in daterange(start, end)
    ]
    return (sum(nightly) / len(nightly)) / ROOM_COUNT if nightly else 0.0


def rooms_available(state, start, end):
    """Calculate number of rooms available for each night."""
    res = [r for r in state["reservations"] 
           if r.get("status", "Booked") in ("Booked", "In-House")]
    availability = {}
    for d in daterange(start, end):
        occupied = sum(ISO(r["arrive"]) <= d < ISO(r["depart"]) for r in res)
        availability[d.isoformat()] = ROOM_COUNT - occupied
    return availability


def quote_total(state, arrive, depart, rtype):
    """Calculate quote for reservation."""
    start, end = ISO(arrive), ISO(depart)
    if end <= start:
        raise ValueError("Departure must be after arrival.")
    
    occ = occ_ratio(state, start, end)
    eligible = (start - TODAY()).days <= 30 and occ <= 0.60
    mult = RATE_MULT.get(rtype, 1.0)
    
    if rtype == "Incentive" and not eligible:
        mult = 1.0  # Falls back to conventional rate
    
    nightly = {
        d.isoformat(): round(base_rate(state, d) * mult, 2) 
        for d in daterange(start, end)
    }
    return round(sum(nightly.values()), 2), nightly, eligible, occ


def next_locator(state):
    """Generate next reservation locator."""
    state["last_locator"] += 1
    return f"OO{state['last_locator']}"


# ============== MAIN APPLICATION ==============

class ReservationApp(tk.Tk):
    def __init__(self, user_info=None):
        super().__init__()
        self.title("Ophelia's Oasis — Reservation System")
        self.user_info = user_info
        self.state_data = load_state()
        
        # Initialize base rates if empty
        if not self.state_data["base_rates"]:
            t = TODAY()
            self.state_data["base_rates"] = {
                (t + dt.timedelta(days=i)).isoformat(): 280.0 + 10 * (i % 5)
                for i in range(90)  # 90 days of rates
            }
            save_state(self.state_data)
        
        # Variables
        self._init_variables()
        
        # Build UI
        self._build_ui()
        
        # Initial data load
        self.refresh_res_list()
        self._update_nights_only()
    
    def _init_variables(self):
        """Initialize all form variables."""
        # Guest info
        self.guest = tk.StringVar()
        self.email = tk.StringVar()
        self.phone = tk.StringVar()
        self.address = tk.StringVar()
        self.comments = tk.StringVar()
        
        # Reservation info
        self.arr = tk.StringVar(value=(TODAY() + dt.timedelta(days=10)).isoformat())
        self.dep = tk.StringVar(value=(TODAY() + dt.timedelta(days=13)).isoformat())
        self.num_days = tk.StringVar(value="3")
        self.rtype = tk.StringVar(value="Conventional")
        self.room_type = tk.StringVar(value=ROOM_TYPES[0])
        self.status = tk.StringVar(value="Booked")
        self.nights_str = tk.StringVar(value="—")
        self.assigned_room = tk.StringVar(value="")
        
        # Credit card info
        self.cc_number = tk.StringVar()
        self.cc_expiry = tk.StringVar()
        self.cc_type = tk.StringVar(value=CC_TYPES[0])
        
        # Quote storage
        self.last_quote = None
        
        # Trace for auto-updates
        self.arr.trace_add("write", lambda *_: self._on_date_change())
        self.dep.trace_add("write", lambda *_: self._on_date_change())
        self.num_days.trace_add("write", lambda *_: self._on_days_change())
    
    def _build_ui(self):
        """Build the main user interface."""
        # Configure main window
        self.geometry("1100x700")
        self.minsize(1000, 600)
        
        # Main container
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(1, weight=1)
        
        # Title bar with user info
        title_frame = ttk.Frame(root)
        title_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))
        
        title = ttk.Label(
            title_frame, 
            text="Reservation — Create & Browse", 
            font=("Segoe UI", 16, "bold")
        )
        title.pack(side="left")
        
        if self.user_info:
            user_lbl = ttk.Label(
                title_frame,
                text=f"Logged in: {self.user_info.get('name', 'Unknown')} ({self.user_info.get('role', '')})",
                font=("Segoe UI", 10),
                foreground="gray"
            )
            user_lbl.pack(side="right")
        
        # LEFT: Create/Quote form
        self._build_form(root)
        
        # RIGHT: Reservations Browser
        self._build_browser(root)
    
    def _build_form(self, parent):
        """Build the reservation creation form."""
        form = ttk.LabelFrame(parent, text="Create / Quote Reservation", padding=10)
        form.grid(row=1, column=0, sticky="nsew", padx=(0, 8))
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)
        
        row = 0
        
        # === Guest Information Section ===
        ttk.Label(form, text="— Guest Information —", font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, columnspan=4, sticky="w", pady=(0, 5)
        )
        row += 1
        
        # Guest Name (required)
        ttk.Label(form, text="Guest Name *").grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.guest, width=30).grid(
            row=row, column=1, sticky="ew", pady=2, padx=(0, 10)
        )
        ttk.Label(form, text="(max 35 chars)", foreground="gray").grid(
            row=row, column=2, sticky="w"
        )
        row += 1
        
        # Email
        ttk.Label(form, text="Email *").grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.email, width=30).grid(
            row=row, column=1, sticky="ew", pady=2, padx=(0, 10)
        )
        ttk.Label(form, text="(max 40 chars)", foreground="gray").grid(
            row=row, column=2, sticky="w"
        )
        row += 1
        
        # Phone
        ttk.Label(form, text="Phone *").grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.phone, width=20).grid(
            row=row, column=1, sticky="w", pady=2
        )
        ttk.Label(form, text="(10-11 digits)", foreground="gray").grid(
            row=row, column=2, sticky="w"
        )
        row += 1
        
        # Address
        ttk.Label(form, text="Address *").grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.address, width=50).grid(
            row=row, column=1, columnspan=2, sticky="ew", pady=2
        )
        row += 1
        
        # Comments (optional)
        ttk.Label(form, text="Comments").grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.comments, width=50).grid(
            row=row, column=1, columnspan=2, sticky="ew", pady=2
        )
        ttk.Label(form, text="(optional, max 100)", foreground="gray").grid(
            row=row, column=3, sticky="w"
        )
        row += 1
        
        # Separator
        ttk.Separator(form, orient="horizontal").grid(
            row=row, column=0, columnspan=4, sticky="ew", pady=10
        )
        row += 1
        
        # === Reservation Details Section ===
        ttk.Label(form, text="— Reservation Details —", font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, columnspan=4, sticky="w", pady=(0, 5)
        )
        row += 1
        
        # Number of Days
        ttk.Label(form, text="Number of Days *").grid(row=row, column=0, sticky="w", pady=2)
        days_frame = ttk.Frame(form)
        days_frame.grid(row=row, column=1, sticky="w", pady=2)
        ttk.Entry(days_frame, textvariable=self.num_days, width=8).pack(side="left")
        ttk.Label(days_frame, text="(1-14)", foreground="gray").pack(side="left", padx=5)
        row += 1
        
        # Arrival Date
        ttk.Label(form, text="Arrival Date *").grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.arr, width=15).grid(
            row=row, column=1, sticky="w", pady=2
        )
        ttk.Label(form, text="(YYYY-MM-DD)", foreground="gray").grid(
            row=row, column=2, sticky="w"
        )
        row += 1
        
        # Departure Date
        ttk.Label(form, text="Departure Date *").grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.dep, width=15).grid(
            row=row, column=1, sticky="w", pady=2
        )
        ttk.Label(form, text="(auto-calculated)", foreground="gray").grid(
            row=row, column=2, sticky="w"
        )
        row += 1
        
        # Reservation Type
        ttk.Label(form, text="Reservation Type *").grid(row=row, column=0, sticky="w", pady=2)
        rtype_combo = ttk.Combobox(
            form, textvariable=self.rtype,
            values=RESERVATION_TYPES, state="readonly", width=15
        )
        rtype_combo.grid(row=row, column=1, sticky="w", pady=2)
        row += 1
        
        # Room Type
        ttk.Label(form, text="Room Type").grid(row=row, column=0, sticky="w", pady=2)
        ttk.Combobox(
            form, textvariable=self.room_type,
            values=ROOM_TYPES, state="readonly", width=15
        ).grid(row=row, column=1, sticky="w", pady=2)
        row += 1
        
        # Separator
        ttk.Separator(form, orient="horizontal").grid(
            row=row, column=0, columnspan=4, sticky="ew", pady=10
        )
        row += 1
        
        # === Credit Card Section ===
        ttk.Label(form, text="— Credit Card Information —", font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, columnspan=4, sticky="w", pady=(0, 5)
        )
        row += 1
        
        # CC Number
        ttk.Label(form, text="Card Number *").grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.cc_number, width=20).grid(
            row=row, column=1, sticky="w", pady=2
        )
        ttk.Label(form, text="(13-16 digits)", foreground="gray").grid(
            row=row, column=2, sticky="w"
        )
        row += 1
        
        # CC Expiry
        ttk.Label(form, text="Expiration *").grid(row=row, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.cc_expiry, width=10).grid(
            row=row, column=1, sticky="w", pady=2
        )
        ttk.Label(form, text="(MM-YYYY)", foreground="gray").grid(
            row=row, column=2, sticky="w"
        )
        row += 1
        
        # CC Type
        ttk.Label(form, text="Card Type *").grid(row=row, column=0, sticky="w", pady=2)
        ttk.Combobox(
            form, textvariable=self.cc_type,
            values=CC_TYPES, state="readonly", width=18
        ).grid(row=row, column=1, sticky="w", pady=2)
        row += 1
        
        # Separator
        ttk.Separator(form, orient="horizontal").grid(
            row=row, column=0, columnspan=4, sticky="ew", pady=10
        )
        row += 1
        
        # === Quote Section ===
        quote_frame = ttk.Frame(form)
        quote_frame.grid(row=row, column=0, columnspan=4, sticky="ew")
        
        ttk.Button(quote_frame, text="Get Quote", command=self.on_quote).pack(side="left")
        self.lbl_quote = ttk.Label(
            quote_frame, 
            text="Total: —  |  Incentive eligible: —  |  Occupancy: —%"
        )
        self.lbl_quote.pack(side="left", padx=10)
        row += 1
        
        # Nightly rates tree
        cols = ("Date", "Nightly Rate")
        self.tree = ttk.Treeview(form, columns=cols, show="headings", height=5)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=120, anchor="center")
        self.tree.grid(row=row, column=0, columnspan=4, sticky="nsew", pady=(5, 10))
        row += 1
        
        # Room availability display
        self.avail_lbl = ttk.Label(form, text="Room Availability: —", foreground="blue")
        self.avail_lbl.grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1
        
        # Save button
        btn_frame = ttk.Frame(form)
        btn_frame.grid(row=row, column=0, columnspan=4, sticky="e", pady=(10, 0))
        
        ttk.Button(btn_frame, text="Clear Form", command=self._clear_form).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Confirm & Save", command=self.on_save).pack(side="left")
    
    def _build_browser(self, parent):
        """Build the reservations browser panel."""
        right = ttk.LabelFrame(parent, text="Reservations Browser", padding=10)
        right.grid(row=1, column=1, sticky="nsew", padx=(8, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)
        
        # Toolbar
        tb = ttk.Frame(right)
        tb.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        ttk.Button(tb, text="Refresh", command=self.refresh_res_list).pack(side="left")
        ttk.Label(tb, text="  Search:").pack(side="left")
        self.search_var = tk.StringVar()
        ttk.Entry(tb, textvariable=self.search_var, width=15).pack(side="left", padx=2)
        ttk.Button(tb, text="Find", command=self.refresh_res_list).pack(side="left")
        
        # Table
        self.res_cols = (
            "Locator", "Guest", "Arrive", "Depart", "Nights", 
            "Room Type", "Res Type", "Status", "Room#"
        )
        self.res_tree = ttk.Treeview(right, columns=self.res_cols, show="headings", height=15)
        widths = [70, 120, 85, 85, 50, 80, 90, 80, 50]
        for c, w in zip(self.res_cols, widths):
            self.res_tree.heading(c, text=c)
            self.res_tree.column(c, width=w, anchor="center")
        self.res_tree.grid(row=1, column=0, sticky="nsew")
        
        # Scrollbar
        ysb = ttk.Scrollbar(right, orient="vertical", command=self.res_tree.yview)
        self.res_tree.configure(yscroll=ysb.set)
        ysb.grid(row=1, column=1, sticky="ns")
        
        self.res_tree.bind("<<TreeviewSelect>>", self.on_select_res)
        
        # Details panel
        details = ttk.LabelFrame(right, text="Selected Reservation", padding=10)
        details.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        details.columnconfigure(1, weight=1)
        
        self.d_lbl = ttk.Label(details, text="Select a reservation to see details.")
        self.d_lbl.grid(row=0, column=0, columnspan=6, sticky="w", pady=(0, 5))
        
        # Quick update controls
        ttk.Label(details, text="Status:").grid(row=1, column=0, sticky="w")
        self.d_status = tk.StringVar(value="Booked")
        ttk.Combobox(
            details, textvariable=self.d_status, 
            values=STATUSES, state="readonly", width=12
        ).grid(row=1, column=1, sticky="w", padx=(5, 15))
        
        ttk.Label(details, text="Room #:").grid(row=1, column=2, sticky="w")
        self.d_room = tk.StringVar()
        ttk.Entry(details, textvariable=self.d_room, width=8).grid(
            row=1, column=3, sticky="w", padx=(5, 15)
        )
        
        ttk.Button(
            details, text="Update Selected", command=self.update_selected
        ).grid(row=1, column=4, padx=5)
        
        ttk.Button(
            details, text="Cancel Reservation", command=self.cancel_selected
        ).grid(row=1, column=5, padx=5)
    
    # ============== EVENT HANDLERS ==============
    
    def _on_date_change(self):
        """Handle arrival/departure date changes."""
        self._update_nights_only()
    
    def _on_days_change(self):
        """Handle number of days change - update departure date."""
        try:
            days = int(self.num_days.get())
            if 1 <= days <= 14:
                arrive = ISO(self.arr.get())
                depart = arrive + dt.timedelta(days=days)
                self.dep.set(depart.isoformat())
        except (ValueError, Exception):
            pass
    
    def _calc_nights(self):
        """Calculate nights from dates."""
        try:
            return (ISO(self.dep.get()) - ISO(self.arr.get())).days
        except Exception:
            return None
    
    def _update_nights_only(self):
        """Update nights display."""
        n = self._calc_nights()
        self.nights_str.set(str(n) if n is not None and n >= 0 else "—")
        if n is not None and n > 0:
            self.num_days.set(str(n))
    
    def _clear_form(self):
        """Clear all form fields."""
        self.guest.set("")
        self.email.set("")
        self.phone.set("")
        self.address.set("")
        self.comments.set("")
        self.cc_number.set("")
        self.cc_expiry.set("")
        self.cc_type.set(CC_TYPES[0])
        self.rtype.set("Conventional")
        self.room_type.set(ROOM_TYPES[0])
        self.arr.set((TODAY() + dt.timedelta(days=10)).isoformat())
        self.dep.set((TODAY() + dt.timedelta(days=13)).isoformat())
        self.num_days.set("3")
        self.assigned_room.set("")
        self.last_quote = None
        self.lbl_quote.config(text="Total: —  |  Incentive eligible: —  |  Occupancy: —%")
        self.avail_lbl.config(text="Room Availability: —")
        for x in self.tree.get_children():
            self.tree.delete(x)
    
    def _validate_form(self):
        """Validate all form fields. Returns (is_valid, error_message)."""
        errors = []
        
        # Guest name
        valid, err = validate_guest_name(self.guest.get())
        if not valid:
            errors.append(f"Guest Name: {err}")
        
        # Email
        valid, err = validate_email(self.email.get())
        if not valid:
            errors.append(f"Email: {err}")
        
        # Phone
        valid, err, _ = validate_phone(self.phone.get())
        if not valid:
            errors.append(f"Phone: {err}")
        
        # Address
        valid, err = validate_address(self.address.get())
        if not valid:
            errors.append(f"Address: {err}")
        
        # Comments (optional)
        valid, err = validate_comments(self.comments.get())
        if not valid:
            errors.append(f"Comments: {err}")
        
        # Number of days
        valid, err, _ = validate_number_of_days(self.num_days.get())
        if not valid:
            errors.append(f"Number of Days: {err}")
        
        # Arrival date
        valid, err, _ = validate_arrival_date(self.arr.get(), self.rtype.get())
        if not valid:
            errors.append(f"Arrival Date: {err}")
        
        # Departure date
        valid, err, _ = validate_date(self.dep.get(), "Departure date")
        if not valid:
            errors.append(f"Departure Date: {err}")
        
        # Credit card number
        valid, err, _ = validate_credit_card_number(self.cc_number.get())
        if not valid:
            errors.append(f"Card Number: {err}")
        
        # Credit card expiry
        valid, err = validate_credit_card_expiry(self.cc_expiry.get())
        if not valid:
            errors.append(f"Card Expiry: {err}")
        
        # Credit card type
        valid, err = validate_credit_card_type(self.cc_type.get())
        if not valid:
            errors.append(f"Card Type: {err}")
        
        if errors:
            return False, "\n".join(errors)
        return True, None
    
    def on_quote(self):
        """Generate quote for reservation."""
        # Validate dates first
        valid, err, _ = validate_date(self.arr.get(), "Arrival date")
        if not valid:
            messagebox.showerror("Validation Error", err)
            return
        
        valid, err, _ = validate_date(self.dep.get(), "Departure date")
        if not valid:
            messagebox.showerror("Validation Error", err)
            return
        
        try:
            total, nightly, eligible, occ = quote_total(
                self.state_data, self.arr.get(), self.dep.get(), self.rtype.get()
            )
        except Exception as e:
            messagebox.showerror("Quote Error", str(e))
            return
        
        # Update display
        self.lbl_quote.config(
            text=f"Total: ${total:,.2f}  |  Incentive eligible: {'Yes' if eligible else 'No'}  |  Occupancy: {occ*100:.1f}%"
        )
        
        # Update nightly rates tree
        for x in self.tree.get_children():
            self.tree.delete(x)
        for d, amt in nightly.items():
            self.tree.insert("", "end", values=(d, f"${amt:,.2f}"))
        
        # Show room availability
        avail = rooms_available(self.state_data, ISO(self.arr.get()), ISO(self.dep.get()))
        min_avail = min(avail.values()) if avail else 0
        max_avail = max(avail.values()) if avail else 0
        self.avail_lbl.config(
            text=f"Room Availability: {min_avail}-{max_avail} rooms available (of {ROOM_COUNT} total)"
        )
        
        self.last_quote = (total, nightly, eligible, occ)
        
        # Update nights
        n = self._calc_nights()
        if n is not None and n >= 0:
            self.nights_str.set(str(n))
    
    def on_save(self):
        """Save the reservation."""
        # Validate form
        is_valid, errors = self._validate_form()
        if not is_valid:
            messagebox.showerror("Validation Errors", errors)
            return
        
        # Check if quoted
        if not self.last_quote:
            messagebox.showwarning("Quote Required", "Please get a quote first.")
            return
        
        total, nightly, eligible, occ = self.last_quote
        loc = next_locator(self.state_data)
        
        # Calculate advance payment based on type
        adv = 0.0
        adv_date = ""
        if self.rtype.get() in ("Prepaid", "60-Day"):
            adv = total
            adv_date = TODAY().isoformat()
        
        # Clean phone number
        _, _, cleaned_phone = validate_phone(self.phone.get())
        
        # Create reservation record
        reservation = {
            "locator": loc,
            "guest_name": trim_and_clean(self.guest.get()),
            "email": trim_and_clean(self.email.get()),
            "phone": cleaned_phone or self.phone.get().strip(),
            "address": trim_and_clean(self.address.get()),
            "comments": trim_and_clean(self.comments.get()),
            "arrive": self.arr.get(),
            "depart": self.dep.get(),
            "rtype": self.rtype.get(),
            "room_type": self.room_type.get(),
            "cc_on_file": True,
            "cc_last_four": self.cc_number.get()[-4:] if len(self.cc_number.get()) >= 4 else "",
            "cc_type": self.cc_type.get(),
            "cc_expiry": self.cc_expiry.get(),
            "paid_advance": round(adv, 2),
            "paid_advance_date": adv_date,
            "total_locked": round(total, 2),
            "snapshot": {"nightly": nightly},
            "assigned_room": self.assigned_room.get().strip(),
            "status": "Booked",
            "created_date": TODAY().isoformat(),
            "created_by": self.user_info.get('user_number', 'system') if self.user_info else 'system'
        }
        
        self.state_data["reservations"].append(reservation)
        save_state(self.state_data)
        
        messagebox.showinfo(
            "Reservation Saved",
            f"Reservation created successfully!\n\nLocator: {loc}\nGuest: {reservation['guest_name']}\nTotal: ${total:,.2f}"
        )
        
        self._clear_form()
        self.refresh_res_list()
    
    def refresh_res_list(self):
        """Refresh the reservations list."""
        self.res_tree.delete(*self.res_tree.get_children())
        self.state_data = load_state()
        
        q = (self.search_var.get() or "").strip().lower()
        
        for r in self.state_data["reservations"]:
            # Filter by search
            if q and q not in r.get("guest_name", "").lower() and q not in r.get("locator", "").lower():
                continue
            
            try:
                n = (ISO(r["depart"]) - ISO(r["arrive"])).days
            except Exception:
                n = ""
            
            self.res_tree.insert(
                "", "end", iid=r["locator"],
                values=(
                    r.get("locator", ""),
                    r.get("guest_name", ""),
                    r.get("arrive", ""),
                    r.get("depart", ""),
                    n,
                    r.get("room_type", ""),
                    r.get("rtype", ""),
                    r.get("status", ""),
                    r.get("assigned_room", "")
                )
            )
    
    def on_select_res(self, _evt=None):
        """Handle reservation selection."""
        sel = self.res_tree.selection()
        if not sel:
            return
        
        loc = sel[0]
        rec = next(
            (x for x in self.state_data["reservations"] if x.get("locator") == loc),
            None
        )
        if not rec:
            return
        
        # Update details display
        self.d_lbl.config(text=(
            f"Locator: {rec.get('locator', '')}  |  "
            f"Guest: {rec.get('guest_name', '')}  |  "
            f"Email: {rec.get('email', '')}  |  "
            f"Phone: {rec.get('phone', '')}\n"
            f"Arrive: {rec.get('arrive', '')} → Depart: {rec.get('depart', '')}  |  "
            f"Type: {rec.get('rtype', '')}  |  "
            f"Total: ${rec.get('total_locked', 0):,.2f}  |  "
            f"Paid: ${rec.get('paid_advance', 0):,.2f}"
        ))
        
        self.d_status.set(rec.get("status", "Booked"))
        self.d_room.set(rec.get("assigned_room", ""))
    
    def update_selected(self):
        """Update the selected reservation."""
        sel = self.res_tree.selection()
        if not sel:
            messagebox.showwarning("Update", "Select a reservation first.")
            return
        
        loc = sel[0]
        for r in self.state_data["reservations"]:
            if r.get("locator") == loc:
                old_status = r.get("status")
                r["status"] = self.d_status.get()
                r["assigned_room"] = self.d_room.get().strip()
                
                # Log status change
                if old_status != r["status"]:
                    r["status_changed_date"] = TODAY().isoformat()
                    r["status_changed_by"] = self.user_info.get('user_number', 'system') if self.user_info else 'system'
                
                save_state(self.state_data)
                self.refresh_res_list()
                messagebox.showinfo("Updated", f"Reservation {loc} updated successfully.")
                return
        
        messagebox.showerror("Error", "Reservation not found.")
    
    def cancel_selected(self):
        """Cancel the selected reservation."""
        sel = self.res_tree.selection()
        if not sel:
            messagebox.showwarning("Cancel", "Select a reservation first.")
            return
        
        loc = sel[0]
        
        if not messagebox.askyesno("Confirm Cancel", f"Cancel reservation {loc}?"):
            return
        
        for r in self.state_data["reservations"]:
            if r.get("locator") == loc:
                r["status"] = "Cancelled"
                r["cancelled_date"] = TODAY().isoformat()
                r["cancelled_by"] = self.user_info.get('user_number', 'system') if self.user_info else 'system'
                
                # Calculate cancellation fee based on policy
                rtype = r.get("rtype", "")
                if rtype in ("Prepaid", "60-Day"):
                    # Check if within 30 days
                    arrive = ISO(r.get("arrive", TODAY().isoformat()))
                    days_until = (arrive - TODAY()).days
                    if days_until <= 30:
                        r["cancellation_fee"] = r.get("total_locked", 0)
                    else:
                        r["cancellation_fee"] = 0
                elif rtype in ("Conventional", "Incentive"):
                    # First night charge
                    nightly = r.get("snapshot", {}).get("nightly", {})
                    if nightly:
                        first_night = list(nightly.values())[0]
                        r["cancellation_fee"] = first_night
                    else:
                        r["cancellation_fee"] = 0
                
                save_state(self.state_data)
                self.refresh_res_list()
                
                fee = r.get("cancellation_fee", 0)
                messagebox.showinfo(
                    "Cancelled",
                    f"Reservation {loc} cancelled.\nCancellation fee: ${fee:,.2f}"
                )
                return
        
        messagebox.showerror("Error", "Reservation not found.")


# ============== MAIN ==============

if __name__ == "__main__":
    app = ReservationApp()
    app.mainloop()
