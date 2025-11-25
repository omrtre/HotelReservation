# reservation_app.py
import json, os, datetime as dt, re
import tkinter as tk
from tkinter import ttk, messagebox

# --------- Constants ---------
DATA_FILE, ROOM_COUNT = "hrs_data.json", 45
TODAY = dt.date.today
ISO = dt.date.fromisoformat
RATE_MULT = {"Prepaid": 0.75, "60-Day": 0.85, "Conventional": 1.00, "Incentive": 0.80}
ROOM_TYPES = ["Standard", "Deluxe", "Suite", "Penthouse"]
STATUSES = ["Booked", "In-House", "Checked-out", "Cancelled", "Changing date"]
CARD_TYPES = ["Visa", "MasterCard", "AmEx", "Discover"]

# --------- Persistence ---------
def load_state():
    if not os.path.exists(DATA_FILE):
        return {"base_rates": {}, "reservations": [], "last_locator": 4000, "payment_reminders_sent": {}}
    with open(DATA_FILE) as f:
        data = json.load(f)
        if "payment_reminders_sent" not in data:
            data["payment_reminders_sent"] = {}
        if "last_locator" not in data:
            data["last_locator"] = 4000
        return data

def save_state(state):
    with open(DATA_FILE, "w") as f:
        json.dump(state, f, indent=2)

# --------- Pricing helpers ---------
def daterange(start, end):
    while start < end:
        yield start
        start += dt.timedelta(days=1)

def base_rate(state, d):
    return float(state["base_rates"].get(d.isoformat(), 300.0))

def occ_ratio(state, start, end, exclude_reservation_id=None):
    res = [r for r in state["reservations"] if r.get("status","Booked") in ("Booked","In-House")]
    if exclude_reservation_id:
        res = [r for r in res if r.get("reservation_id", r.get("locator")) != exclude_reservation_id]
    if not res: return 0.0
    nightly_counts = [sum(ISO(r["arrive"]) <= d < ISO(r["depart"]) for r in res) for d in daterange(start, end)]
    return (sum(nightly_counts)/len(nightly_counts))/ROOM_COUNT if nightly_counts else 0.0

def is_available_for(state, start, end, exclude_reservation_id=None):
    counts = []
    for d in daterange(start, end):
        occupied = sum(ISO(r["arrive"]) <= d < ISO(r["depart"]) and r.get("status") in ("Booked","In-House")
                       and r.get("reservation_id", r.get("locator")) != exclude_reservation_id
                       for r in state["reservations"])
        counts.append(occupied)
    if not counts:
        return True, ROOM_COUNT
    min_available = min(max(0, ROOM_COUNT - c) for c in counts)
    return min_available > 0, min_available

def quote_total(state, arrive, depart, rtype, original_cost=0.0, is_change=False):
    """
    Returns: (total, nightly_dict, eligible_bool, occ_ratio, change_note, penalty_amount)
    Change policy for Prepaid/60-Day: adjusted_total = 110% of new total (new_total * 1.10).
    change_cost = adjusted_total - original_cost
    penalty_amount = max(0, change_cost)
    """
    start, end = ISO(arrive), ISO(depart)
    if end <= start:
        raise ValueError("Departure must be after arrival.")
    occ = occ_ratio(state, start, end)
    eligible = (start - TODAY()).days <= 30 and occ <= 0.60
    mult = RATE_MULT.get(rtype, 1.0)
    if rtype == "Incentive" and not eligible:
        mult = 1.0
    nightly = {d.isoformat(): round(base_rate(state, d) * mult, 2) for d in daterange(start, end)}
    new_total = round(sum(nightly.values()), 2)
    change_note = ""
    penalty_amount = 0.0
    total = new_total

    if is_change and rtype in ["Prepaid", "60-Day"]:
        # Adjusted total is 110% of the new total
        new_110 = round(new_total * 1.10, 2)
        change_cost = round(new_110 - original_cost, 2)
        penalty_amount = round(change_cost if change_cost > 0 else 0.0, 2)
        change_note = (
            f"Change policy math: 110% of new total (${new_110:,.2f}) - original (${original_cost:,.2f}) "
            f"= ${change_cost:,.2f}; Adjusted total = ${new_110:,.2f}"
        )
        total = new_110

    return total, nightly, eligible, occ, change_note, penalty_amount

def next_locator(state):
    state["last_locator"] = int(state.get("last_locator", 4000)) + 1
    save_state(state)
    return f"OO{state['last_locator']}"

def run_daily_tasks(state):
    today = TODAY()
    tasks_performed = []

    # Payment reminders for 60-Day (45 days before arrival)
    for res in state["reservations"]:
        if res.get("status") == "Booked" and res.get("rtype") == "60-Day":
            arrive_date = ISO(res["arrive"])
            if (arrive_date - today).days == 45:
                loc = res.get("reservation_id", res.get("locator", "Unknown"))
                state["payment_reminders_sent"][loc] = today.isoformat()
                tasks_performed.append(f"Payment reminder sent for reservation {loc}")

    # Cancel 60-Day reservations with no paid_advance 30 days before arrival
    for res in state["reservations"]:
        if res.get("status") == "Booked" and res.get("rtype") == "60-Day":
            arrive_date = ISO(res["arrive"])
            if (arrive_date - today).days == 30 and float(res.get("paid_advance", 0.0)) == 0.0:
                res["status"] = "Cancelled"
                res["cancelled_date"] = today.isoformat()
                tasks_performed.append(f"60-Day reservation {res.get('reservation_id', res.get('locator','Unknown'))} cancelled (no payment 30 days before arrival)")

    # No-show penalties: yesterday arrivals not checked in
    yesterday = today - dt.timedelta(days=1)
    for res in state["reservations"]:
        if res.get("status") == "Booked" and ISO(res["arrive"]) == yesterday and not res.get("checked_in", False):
            first_night = list(res.get("snapshot", {}).get("nightly", {}).values())[0] if res.get("snapshot", {}).get("nightly") else base_rate(state, yesterday)
            res["no_show_penalty"] = first_night
            res["status"] = "Cancelled"
            res["cancellation_reason"] = "No-show"
            tasks_performed.append(f"No-show penalty applied to reservation {res.get('reservation_id', res.get('locator','Unknown'))}: ${first_night:.2f}")

    if tasks_performed:
        save_state(state)
    return tasks_performed

def mask_card(card_number: str) -> str:
    if not card_number or len(card_number) < 4:
        return "****"
    digits = "".join(ch for ch in card_number if ch.isdigit())
    if len(digits) < 4:
        return "****"
    return "*" * (len(digits) - 4) + digits[-4:]

# --------- Validation ---------
def is_valid_name(name): return bool(name) and len(name) <= 35
def is_valid_email(email): return bool(email) and len(email) <= 40 and "@" in email and "." in email
def is_valid_phone(phone): return phone.isdigit() and 10 <= len(phone) <= 11
def is_valid_address(addr): return bool(addr.strip())
def is_valid_card(card): return card.isdigit() and 13 <= len(card) <= 16
def is_valid_exp(exp_str):
    m = re.match(r"^(0[1-9]|1[0-2])-(\d{4})$", exp_str.strip())
    if not m: return False
    mm, yyyy = int(m.group(1)), int(m.group(2))
    try:
        next_month = dt.date(yyyy, mm, 28) + dt.timedelta(days=4)
        last_day = dt.date(next_month.year, next_month.month, 1) - dt.timedelta(days=1)
        return last_day >= TODAY()
    except: return False
def is_valid_date(date_str):
    try: ISO(date_str); return True
    except: return False
def is_valid_days(days_str):
    try:
        d = int(days_str)
        return 1 <= d <= 60
    except:
        return False

# --------- Status code mapping ---------
def status_code(rec):
    s = rec.get("status","Booked")
    return "X" if s=="Cancelled" else "I" if s=="In-House" else "O" if s=="Checked-out" else "B"

# --------- Login ---------
class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ophelia's Oasis — Staff Login")
        self.geometry("380x200")
        self.resizable(False, False)
        self.users = {"staff": "oasis2025", "manager": "orchid#9"}
        frame = ttk.Frame(self, padding=12); frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Username").grid(row=0, column=0, sticky="w", pady=(0,6))
        ttk.Label(frame, text="Password").grid(row=1, column=0, sticky="w")
        self.u = tk.StringVar(); self.p = tk.StringVar()
        ttk.Entry(frame, textvariable=self.u, width=24).grid(row=0, column=1, sticky="w")
        ttk.Entry(frame, textvariable=self.p, show="*", width=24).grid(row=1, column=1, sticky="w")
        self.msg = ttk.Label(frame, text="", foreground="red"); self.msg.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10,6))
        ttk.Button(frame, text="Login", command=self._login).grid(row=3, column=1, sticky="e")

    def _login(self):
        u, p = self.u.get().strip(), self.p.get().strip()
        if u in self.users and self.users[u] == p:
            self.destroy()
            app = ReservationApp(authorized_user=u)
            app.geometry("1100x820")
            app.mainloop()
        else:
            self.msg.config(text="Invalid credentials. Access denied.")

# --------- Main App ---------
class ReservationApp(tk.Tk):
    def __init__(self, authorized_user=""):
        super().__init__()
        self.title("Reservation — Create & Browse")
        self.authorized_user = authorized_user
        self.state_data = load_state()

        if not self.state_data["base_rates"]:
            t = TODAY()
            self.state_data["base_rates"] = {(t+dt.timedelta(days=i)).isoformat(): 280.0 + 10*(i % 5) for i in range(30)}
            save_state(self.state_data)

        # Form variables
        self.guest = tk.StringVar(); self.email = tk.StringVar(); self.phone = tk.StringVar()
        self.address = tk.StringVar(); self.comments = tk.StringVar()
        self.zipcode = tk.StringVar(); self.state = tk.StringVar()
        self.days = tk.StringVar(value="")  # REQUIRED Days field
        self.arr = tk.StringVar(value=(TODAY() + dt.timedelta(days=10)).isoformat())
        self.dep = tk.StringVar(value=(TODAY() + dt.timedelta(days=13)).isoformat())
        self.rtype = tk.StringVar(value="Conventional")
        self.room_type = tk.StringVar(value=ROOM_TYPES[0])
        self.status = tk.StringVar(value="Booked")
        self.nights_str = tk.StringVar(value="—")
        self.assigned_room = tk.StringVar(value="")
        self.cc_info = tk.StringVar(); self.cc_exp = tk.StringVar(); self.cc_type = tk.StringVar(value=CARD_TYPES[0])
        self.manual_res_id = tk.StringVar()
        self.auto_assign_res_id = tk.BooleanVar(value=True)
        self.search_res_id = tk.StringVar()
        # Payment update fields
        self.up_pay_date = tk.StringVar()
        self.up_pay_amt = tk.StringVar()

        self.last_quote = None; self.selected_reservation = None

        # Layout root
        root = ttk.Frame(self, padding=10); root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1); root.columnconfigure(1, weight=1); root.rowconfigure(1, weight=1)

        # Menu bar
        menubar = tk.Menu(self)
        self.config(menu=menubar)
        admin_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Admin", menu=admin_menu)
        admin_menu.add_command(label="Manage Base Rates", command=lambda: self.open_base_rate_admin())
        admin_menu.add_command(label="Reports", command=lambda: self.open_reports_window())

        # Title
        title_frame = ttk.Frame(root, padding=(4,0))
        title_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0,6))
        title_frame.columnconfigure(0, weight=1)
        ttk.Label(title_frame, text="Reservation — Create & Browse", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, sticky="w", padx=(4,0))
        ttk.Button(title_frame, text="Run Daily Tasks", command=self.run_daily_tasks_ui).grid(row=0, column=1, sticky="e")

        # LEFT: Create / Quote
        form = ttk.LabelFrame(root, text="Create / Quote Reservation", padding=(8,8))
        form.grid(row=1, column=0, sticky="nsew", padx=(0,8))
        for i in range(2): form.columnconfigure(i, weight=1)

        r = 0
        def row(label, var, width=28, required=False, padx_left=10):
            nonlocal r
            lab_text = f"{label}{' *' if required else ''}"
            ttk.Label(form, text=lab_text).grid(row=r, column=0, sticky="w", pady=2, padx=(padx_left,0))
            ttk.Entry(form, textvariable=var, width=width).grid(row=r, column=1, sticky="w", pady=2)
            r += 1

        # Guest info
        ttk.Label(form, text="Guest information", font=("Segoe UI", 10, "bold")).grid(row=r, column=0, columnspan=2, sticky="w", pady=(0,4), padx=(6,0)); r += 1
        row("Guest Name (max 35)", self.guest, required=True)
        row("Email (max 40)", self.email, required=True)
        row("Phone (10-11 digits)", self.phone, 20, required=True)
        row("Address", self.address, required=True)
        row("State", self.state, required=True)
        row("Zip code", self.zipcode, required=True)
        ttk.Label(form, text="Comments (optional)").grid(row=r, column=0, sticky="w", pady=2, padx=(10,0))
        ttk.Entry(form, textvariable=self.comments, width=28).grid(row=r, column=1, sticky="w", pady=2); r += 1

        # Reservation details
        ttk.Label(form, text="Reservation details", font=("Segoe UI", 10, "bold")).grid(row=r, column=0, columnspan=2, sticky="w", pady=(12,4), padx=(6,0)); r += 1

        # Manual Reservation ID controls
        ttk.Checkbutton(form, text="Auto assign Reservation ID", variable=self.auto_assign_res_id, command=self._toggle_manual_res_id).grid(row=r, column=0, sticky="w", padx=(10,0))
        self.ent_manual_res_id = ttk.Entry(form, textvariable=self.manual_res_id, width=18, state="disabled")
        self.ent_manual_res_id.grid(row=r, column=1, sticky="w", pady=2); r += 1

        # Number of days — manual entry (required)
        ttk.Label(form, text="Number of Days (1-60) *").grid(row=r, column=0, sticky="w", pady=2, padx=(10,0))
        ttk.Entry(form, textvariable=self.days, width=10).grid(row=r, column=1, sticky="w", pady=2); r += 1

        ttk.Label(form, text="Arrival (YYYY-MM-DD) *").grid(row=r, column=0, sticky="w", pady=2, padx=(10,0))
        ttk.Entry(form, textvariable=self.arr, width=16).grid(row=r, column=1, sticky="w", pady=2); r += 1

        ttk.Label(form, text="Departure (YYYY-MM-DD) *").grid(row=r, column=0, sticky="w", pady=2, padx=(10,0))
        ttk.Entry(form, textvariable=self.dep, width=16).grid(row=r, column=1, sticky="w", pady=2); r += 1

        ttk.Label(form, text="Reservation Type *").grid(row=r, column=0, sticky="w", pady=2, padx=(10,0))
        self.rtype_combo = ttk.Combobox(form, textvariable=self.rtype, values=["Prepaid", "60-Day", "Conventional", "Incentive"], state="readonly", width=16)
        self.rtype_combo.grid(row=r, column=1, sticky="w", pady=2); r += 1

        ttk.Label(form, text="Room Type").grid(row=r, column=0, sticky="w", pady=2, padx=(10,0))
        ttk.Combobox(form, textvariable=self.room_type, values=ROOM_TYPES, state="readonly", width=16).grid(row=r, column=1, sticky="w", pady=2); r += 1

        ttk.Label(form, text="Status").grid(row=r, column=0, sticky="w", pady=2, padx=(10,0))
        ttk.Combobox(form, textvariable=self.status, values=STATUSES, state="readonly", width=16).grid(row=r, column=1, sticky="w", pady=2); r += 1

        ttk.Label(form, text="Nights (auto)").grid(row=r, column=0, sticky="w", pady=2, padx=(10,0))
        ttk.Entry(form, textvariable=self.nights_str, state="readonly").grid(row=r, column=1, sticky="w", pady=2); r += 1

        ttk.Label(form, text="Assigned Room # (opt)").grid(row=r, column=0, sticky="w", pady=2, padx=(10,0))
        ttk.Entry(form, textvariable=self.assigned_room, width=10).grid(row=r, column=1, sticky="w", pady=2); r += 1

        # Credit card section
        ttk.Label(form, text="Credit card information", font=("Segoe UI", 10, "bold")).grid(row=r, column=0, columnspan=2, sticky="w", pady=(12,4), padx=(6,0)); r += 1
        cc_frame = ttk.LabelFrame(form, text="Required", padding=(8,6))
        cc_frame.grid(row=r, column=0, columnspan=2, sticky="ew", padx=(8,8), pady=(0,6)); r += 1
        cc_frame.columnconfigure(0, weight=0); cc_frame.columnconfigure(1, weight=1)

        cr = 0
        ttk.Label(cc_frame, text="Card Number *").grid(row=cr, column=0, sticky="w", pady=2, padx=(10,0))
        ttk.Entry(cc_frame, textvariable=self.cc_info, width=22).grid(row=cr, column=1, sticky="w", pady=2); cr += 1
        ttk.Label(cc_frame, text="Expiration (MM-YYYY) *").grid(row=cr, column=0, sticky="w", pady=2, padx=(10,0))
        ttk.Entry(cc_frame, textvariable=self.cc_exp, width=12).grid(row=cr, column=1, sticky="w", pady=2); cr += 1
        ttk.Label(cc_frame, text="Card Type *").grid(row=cr, column=0, sticky="w", pady=2, padx=(10,0))
        ttk.Combobox(cc_frame, textvariable=self.cc_type, values=CARD_TYPES, state="readonly", width=16).grid(row=cr, column=1, sticky="w", pady=2); cr += 1
        self.cc_msg = ttk.Label(cc_frame, text="", foreground="red")
        self.cc_msg.grid(row=cr, column=0, columnspan=2, sticky="w", pady=(6,0)); cr += 1

        # Controls
        ttk.Button(form, text="Get Quote", command=self.on_quote).grid(row=r, column=0, pady=(10,6), padx=(10,0), sticky="w")
        self.lbl_quote = ttk.Label(form, text="Total: —  | Incentive eligible: —  | Occupancy: —%")
        self.lbl_quote.grid(row=r, column=1, sticky="w", pady=(10,6)); r += 1

        ttk.Button(form, text="Verify Availability", command=self.verify_availability).grid(row=r, column=0, pady=(0,6), padx=(10,0), sticky="w")
        ttk.Button(form, text="Confirm & Save", command=self.on_save).grid(row=r, column=1, sticky="e", pady=(0,6)); r += 1

        # Nightly detail
        cols = ("Date", "Nightly Rate (locked)")
        self.tree = ttk.Treeview(form, columns=cols, show="headings", height=8)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=160 if c=="Date" else 180, anchor="center")
        self.tree.grid(row=r, column=0, columnspan=2, sticky="nsew", pady=(0,6)); r += 1
        form.rowconfigure(r-1, weight=1)

        # RIGHT: Browser
        right = ttk.LabelFrame(root, text="Reservations Browser", padding=(8,8))
        right.grid(row=1, column=1, sticky="nsew", padx=(8,0))
        for i in range(2): right.columnconfigure(i, weight=1)
        right.rowconfigure(1, weight=1)

        # Toolbar: add Reservation ID search box
        tb = ttk.Frame(right)
        tb.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(4,2))
        ttk.Button(tb, text="Refresh", command=self.refresh_res_list).pack(side="left")
        ttk.Label(tb, text="Search Guest:").pack(side="left", padx=(8,4))
        self.search_var = tk.StringVar()
        ttk.Entry(tb, textvariable=self.search_var, width=18).pack(side="left")
        ttk.Button(tb, text="Find", command=self.refresh_res_list).pack(side="left", padx=4)

        ttk.Label(tb, text="Reservation ID:").pack(side="left", padx=(12,4))
        ttk.Entry(tb, textvariable=self.search_res_id, width=14).pack(side="left")
        ttk.Button(tb, text="Find ID", command=self.search_by_reservation_id).pack(side="left", padx=4)

        # Table
        self.res_cols = ("Reservation ID","Guest","Arrive","Depart","Days","Nights","Room Type","Res Type","Status","Room#","Paid","Card (Last 4)","Code")
        self.res_tree = ttk.Treeview(right, columns=self.res_cols, show="headings", height=14)
        widths = [110, 160, 100, 100, 60, 60, 100, 110, 100, 70, 70, 110, 60]
        for c, w in zip(self.res_cols, widths):
            self.res_tree.heading(c, text=c)
            self.res_tree.column(c, width=w, anchor="center")
        self.res_tree.grid(row=1, column=0, columnspan=2, sticky="nsew")
        ysb = ttk.Scrollbar(right, orient="vertical", command=self.res_tree.yview)
        self.res_tree.configure(yscroll=ysb.set)
        ysb.grid(row=1, column=2, sticky="ns")
        self.res_tree.bind("<<TreeviewSelect>>", self.on_select_res)

        # Date change box
        date_change_frame = ttk.LabelFrame(right, text="Change Dates", padding=8)
        date_change_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6,4))
        date_change_frame.columnconfigure(1, weight=1)
        date_change_frame.columnconfigure(3, weight=1)

        ttk.Label(date_change_frame, text="Current Arrival:", font=("", 9, "bold")).grid(row=0, column=0, sticky="w", pady=2)
        self.curr_arr_label = ttk.Label(date_change_frame, text="—", foreground="blue", font=("", 9, "bold"))
        self.curr_arr_label.grid(row=0, column=1, sticky="w", pady=2, padx=(4,20))
        ttk.Label(date_change_frame, text="Current Departure:", font=("", 9, "bold")).grid(row=0, column=2, sticky="w", pady=2)
        self.curr_dep_label = ttk.Label(date_change_frame, text="—", foreground="blue", font=("", 9, "bold"))
        self.curr_dep_label.grid(row=0, column=3, sticky="w", pady=2, padx=(4,0))

        ttk.Label(date_change_frame, text="New Arrival:", font=("", 9, "bold")).grid(row=1, column=0, sticky="w", pady=2)
        self.d_new_arr = tk.StringVar()
        ttk.Entry(date_change_frame, textvariable=self.d_new_arr, width=12).grid(row=1, column=1, sticky="w", pady=2, padx=(4,20))
        ttk.Label(date_change_frame, text="New Departure:", font=("", 9, "bold")).grid(row=1, column=2, sticky="w", pady=2)
        self.d_new_dep = tk.StringVar()
        ttk.Entry(date_change_frame, textvariable=self.d_new_dep, width=12).grid(row=1, column=3, sticky="w", pady=2, padx=(4,0))

        btn_frame = ttk.Frame(date_change_frame)
        btn_frame.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(6,0))
        ttk.Button(btn_frame, text="Quote Date Change", command=self.quote_date_change).pack(side="left", padx=(0,8))
        ttk.Button(btn_frame, text="Apply Date Change", command=self.apply_date_change).pack(side="left")

        # Payment & Cancellation
        payment_frame = ttk.LabelFrame(right, text="Payment & Cancellation", padding=6)
        payment_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(4,0))
        ttk.Button(payment_frame, text="Process Prepayment", command=self.process_prepayment).pack(side="left", padx=(0,8))
        ttk.Button(payment_frame, text="Process Payment", command=self.process_payment).pack(side="left", padx=(0,8))
        ttk.Button(payment_frame, text="Generate Bill", command=self.generate_bill).pack(side="left", padx=(0,8))
        ttk.Button(payment_frame, text="Cancel Reservation", command=self.cancel_reservation).pack(side="left", padx=(0,8))
        ttk.Button(payment_frame, text="Check In Guest", command=self.check_in_guest).pack(side="left", padx=(0,8))
        ttk.Button(payment_frame, text="Check Out Guest", command=self.check_out_guest).pack(side="left")

        # Details
        details = ttk.LabelFrame(right, text="Reservation Details", padding=(8,8))
        details.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(4,0))
        details.columnconfigure(1, weight=1)
        self.d_lbl = ttk.Label(details, text="Select a reservation to see details.", anchor="w", wraplength=700, justify="left")
        self.d_lbl.grid(row=0, column=0, columnspan=5, sticky="ew", pady=(4,6))

        control_frame = ttk.Frame(details)
        control_frame.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(0,4))
        ttk.Label(control_frame, text="Status:").pack(side="left", padx=(0,4))
        self.d_status = tk.StringVar(value="Booked")
        ttk.Combobox(control_frame, textvariable=self.d_status, values=STATUSES, state="readonly", width=14).pack(side="left", padx=(0,20))
        ttk.Label(control_frame, text="Room #:").pack(side="left", padx=(0,4))
        self.d_room = tk.StringVar()
        ttk.Entry(control_frame, textvariable=self.d_room, width=8).pack(side="left", padx=(0,20))
        ttk.Button(control_frame, text="Update Selected", command=self.update_selected).pack(side="left")

        # Payment update panel (date + amount)
        update_pay = ttk.LabelFrame(details, text="Update Payment", padding=6)
        update_pay.grid(row=2, column=0, columnspan=5, sticky="ew", pady=(4,0))
        ttk.Label(update_pay, text="Payment Date (YYYY-MM-DD):").grid(row=0, column=0, sticky="w")
        ttk.Entry(update_pay, textvariable=self.up_pay_date, width=16).grid(row=0, column=1, sticky="w", padx=(6,18))
        ttk.Label(update_pay, text="Amount Paid:").grid(row=0, column=2, sticky="w")
        ttk.Entry(update_pay, textvariable=self.up_pay_amt, width=12).grid(row=0, column=3, sticky="w", padx=(6,18))
        ttk.Button(update_pay, text="Apply Payment", command=self._apply_payment_update).grid(row=0, column=4, sticky="e")

        # Initial populate
        self.refresh_res_list()

    # --------- Helpers ---------
    def _toggle_manual_res_id(self):
        if self.auto_assign_res_id.get():
            self.ent_manual_res_id.config(state="disabled")
            self.manual_res_id.set("")
        else:
            self.ent_manual_res_id.config(state="normal")

    def _calc_nights(self, arrive, depart):
        try:
            return (ISO(depart) - ISO(arrive)).days
        except Exception:
            return None

    def _apply_payment_update(self):
        if not self.selected_reservation:
            return messagebox.showwarning("Payment Update", "Select a reservation in the table.")
        rec = self.selected_reservation
        pay_date = self.up_pay_date.get().strip()
        pay_amt_str = self.up_pay_amt.get().strip()
        if not pay_date or not is_valid_date(pay_date):
            return messagebox.showerror("Payment Update", "Payment date must be YYYY-MM-DD.")
        try:
            pay_amt = float(pay_amt_str or "0")
            if pay_amt <= 0:
                return messagebox.showerror("Payment Update", "Amount Paid must be a positive number.")
        except:
            return messagebox.showerror("Payment Update", "Amount Paid must be a number.")
        payments = rec.setdefault("payments", [])
        payments.append({"date": pay_date, "amount": round(pay_amt, 2)})
        rec["paid_advance"] = round((rec.get("paid_advance", 0.0) + pay_amt), 2)
        rec["paid_advance_date"] = pay_date
        if rec["paid_advance"] >= rec.get("total_locked", 0.0):
            rec["fully_paid"] = True
        save_state(self.state_data)
        self.refresh_res_list()
        messagebox.showinfo("Payment Update", f"Payment applied for {rec.get('reservation_id', rec.get('locator'))}.\nPaid advance now ${rec['paid_advance']:,.2f} on {pay_date}.")

    # --------- Actions: Quote & Save ---------
    def on_quote(self):
        arr_str = self.arr.get().strip()
        dep_str = self.dep.get().strip()
        days_str = self.days.get().strip()

        if not is_valid_date(arr_str):
            return messagebox.showerror("Quote error", "Arrival date must be YYYY-MM-DD.")
        if (not dep_str) and is_valid_days(days_str):
            arr_d = ISO(arr_str)
            dep_d = arr_d + dt.timedelta(days=int(days_str))
            self.dep.set(dep_d.isoformat())
            dep_str = self.dep.get()
        if (not days_str) and is_valid_date(dep_str):
            try:
                span = (ISO(dep_str) - ISO(arr_str)).days
                if span <= 0:
                    return messagebox.showerror("Quote error", "Departure must be after arrival.")
                self.days.set(str(span))
            except Exception:
                return messagebox.showerror("Quote error", "Invalid departure date.")
        if not is_valid_days(self.days.get().strip()):
            return messagebox.showerror("Quote error", "Number of days must be an integer between 1 and 60.")
        if not is_valid_date(self.dep.get().strip()):
            return messagebox.showerror("Quote error", "Departure date must be YYYY-MM-DD.")
        try:
            arr_d = ISO(self.arr.get().strip()); dep_d = ISO(self.dep.get().strip())
            if dep_d <= arr_d:
                return messagebox.showerror("Quote error", "Departure must be after arrival.")
            span = (dep_d - arr_d).days
            self.nights_str.set(str(span))
            if span != int(self.days.get().strip()):
                messagebox.showwarning("Days mismatch", f"Nights from dates = {span}, but 'Number of Days' = {self.days.get().strip()}.")
            total, nightly, eligible, occ, _, _ = quote_total(self.state_data, self.arr.get(), self.dep.get(), self.rtype.get(), original_cost=0.0, is_change=False)
        except Exception as e:
            return messagebox.showerror("Quote error", str(e))

        self.lbl_quote.config(text=f"Total: ${total:,.2f} | Incentive eligible: {'Yes' if eligible else 'No'} | Occupancy: {occ*100:.1f}%")
        for x in self.tree.get_children(): self.tree.delete(x)
        for d, amt in nightly.items(): self.tree.insert("", "end", values=(d, f"${amt:,.2f}"))
        self.last_quote = (total, nightly, eligible, occ)

    def _validate_form(self):
        self.cc_msg.config(text="")
        if not is_valid_name(self.guest.get().strip()):
            return "Guest name is required and must be ≤ 35 characters."
        if not is_valid_email(self.email.get().strip()):
            return "Email is required, ≤ 40 characters, and must be valid."
        if not is_valid_phone(self.phone.get().strip()):
            return "Phone must be 10–11 digits."
        if not is_valid_address(self.address.get().strip()):
            return "Address is required."
        if not self.state.get().strip():
            return "State is required."
        if not self.zipcode.get().strip():
            return "Zip code is required."
        if not is_valid_date(self.arr.get().strip()):
            return "Arrival date must be YYYY-MM-DD."
        if self.dep.get().strip() and not is_valid_date(self.dep.get().strip()):
            return "Departure date must be YYYY-MM-DD."
        if not is_valid_days(self.days.get().strip()):
            return "Number of days must be an integer between 1 and 60."
        if not self.dep.get().strip():
            try:
                arr_d = ISO(self.arr.get().strip())
                dep_d = arr_d + dt.timedelta(days=int(self.days.get().strip()))
                self.dep.set(dep_d.isoformat())
            except Exception:
                return "Could not compute departure date from arrival + days."
        try:
            arr_d = ISO(self.arr.get().strip()); dep_d = ISO(self.dep.get().strip())
            if dep_d <= arr_d:
                return "Departure must be after arrival."
            span = (dep_d - arr_d).days
            if span != int(self.days.get().strip()):
                messagebox.showwarning("Days mismatch", f"Nights from dates = {span}, but 'Number of Days' = {self.days.get().strip()}. Using dates for calculations.")
                self.days.set(str(span))
        except:
            return "Arrival or Departure date invalid."

        if self.rtype.get().strip() not in RATE_MULT:
            return "Reservation type is required."
        if not is_valid_card(self.cc_info.get().strip()):
            self.cc_msg.config(text="Card number must be 13–16 digits (numeric only).")
            return "Card number must be 13–16 digits (numeric only)."
        if not is_valid_exp(self.cc_exp.get().strip()):
            self.cc_msg.config(text="Expiration must be MM-YYYY and not expired.")
            return "Expiration must be MM-YYYY and not expired."
        if self.cc_type.get().strip() not in CARD_TYPES:
            self.cc_msg.config(text="Please select a valid card type.")
            return "Please select a valid card type."
        if not self.auto_assign_res_id.get():
            manual = self.manual_res_id.get().strip()
            if not manual:
                return "Manual Reservation ID is empty. Enter an ID or enable auto assign."
            for r in self.state_data["reservations"]:
                existing_id = r.get("reservation_id", r.get("locator"))
                if existing_id == manual:
                    return f"Reservation ID {manual} already exists. Choose a different ID."
        return None

    def on_save(self):
        if not self.last_quote:
            return messagebox.showwarning("Save", "Please get a quote first.")
        err = self._validate_form()
        if err:
            return messagebox.showerror("Validation error", err)

        total, nightly, *_ = self.last_quote
        if self.auto_assign_res_id.get():
            res_id = next_locator(self.state_data)
        else:
            res_id = self.manual_res_id.get().strip()
            m = re.match(r"^OO(\d+)$", res_id)
            if m:
                num = int(m.group(1))
                if num > int(self.state_data.get("last_locator", 4000)):
                    self.state_data["last_locator"] = num
                    save_state(self.state_data)

        rtype = self.rtype.get()
        adv = total if rtype == "Prepaid" else 0.0
        n = self._calc_nights(self.arr.get(), self.dep.get())

        self.state_data["reservations"].append({
            "reservation_id": res_id,
            "locator": res_id,
            "guest_name": self.guest.get().strip(),
            "email": self.email.get().strip(),
            "phone": self.phone.get().strip(),
            "address": self.address.get().strip(),
            "state": self.state.get().strip(),
            "zip": self.zipcode.get().strip(),
            "comments": self.comments.get().strip(),
            "arrive": self.arr.get(),
            "depart": self.dep.get(),
            "days": int(self.days.get().strip()),
            "rtype": rtype,
            "room_type": self.room_type.get(),
            "cc_info": self.cc_info.get().strip(),
            "cc_exp": self.cc_exp.get().strip(),
            "cc_type": self.cc_type.get().strip(),
            "cc_on_file": True,
            "paid_advance": round(adv, 2),
            "paid_advance_date": TODAY().isoformat() if adv else "",
            "payments": ([{"date": TODAY().isoformat(), "amount": round(adv,2)}] if adv else []),
            "total_locked": round(total, 2),
            "snapshot": {"nightly": nightly},
            "assigned_room": self.assigned_room.get().strip(),
            "status": self.status.get(),
            "nights": n if n is not None else "",
            "checked_in": False,
            "checked_out": False,
            "fully_paid": True if rtype == "Prepaid" else False,
            "no_show_penalty": 0.0,
            "change_note": "",
            "created_date": TODAY().isoformat(),
            "created_by": self.authorized_user
        })
        save_state(self.state_data)
        messagebox.showinfo("Saved", f"Reservation saved.\nReservation ID: {res_id}" + (f"\nAdvance paid: ${adv:,.2f}" if adv else ""))
        self.refresh_res_list()

    # --------- Browser actions & reports ---------
    def refresh_res_list(self):
        self.res_tree.delete(*self.res_tree.get_children())
        self.state_data = load_state()
        q = (self.search_var.get() or "").strip().lower()
        q_id = (self.search_res_id.get() or "").strip()
        for r in self.state_data["reservations"]:
            guest_name = r.get("guest_name","").lower()
            res_id = r.get("reservation_id", r.get("locator",""))
            if q and q not in guest_name:
                continue
            if q_id and q_id not in str(res_id):
                continue
            try:
                n = (ISO(r["depart"]) - ISO(r["arrive"])).days
            except Exception:
                n = ""
            days = r.get("days", "")
            paid_status = "Yes" if r.get("paid_advance", 0) > 0 or r.get("rtype") in ["Conventional", "Incentive"] else "No"
            if r.get("rtype") == "60-Day" and r.get("paid_advance", 0) > 0:
                paid_status = "Yes"
            masked_card = mask_card(r.get("cc_info",""))
            self.res_tree.insert("", "end", iid=res_id, values=(
                res_id,
                r.get("guest_name",""),
                r.get("arrive",""),
                r.get("depart",""),
                days,
                n,
                r.get("room_type",""),
                r.get("rtype",""),
                r.get("status",""),
                r.get("assigned_room",""),
                paid_status,
                masked_card,
                status_code(r)
            ))

    def search_by_reservation_id(self):
        q_id = (self.search_res_id.get() or "").strip()
        if not q_id:
            return messagebox.showinfo("Search Reservation ID", "Enter a Reservation ID to search.")
        for r in self.state_data.get("reservations", []):
            res_id = r.get("reservation_id", r.get("locator",""))
            if str(res_id) == q_id:
                self.refresh_res_list()
                try:
                    self.res_tree.selection_set(res_id)
                    self.res_tree.see(res_id)
                    self.on_select_res()
                except Exception:
                    pass
                return
        self.refresh_res_list()
        messagebox.showinfo("Search Reservation ID", f"No exact match for '{q_id}'. Showing filtered list (partial matches).")

    def on_select_res(self, _evt=None):
        sel = self.res_tree.selection()
        if not sel:
            self.selected_reservation = None
            return
        res_id = sel[0]
        rec = next((x for x in self.state_data["reservations"] if x.get("reservation_id", x.get("locator"))==res_id), None)
        if not rec:
            self.selected_reservation = None
            return
        self.selected_reservation = rec

        details = (
            f"Reservation ID: {rec.get('reservation_id', rec.get('locator',''))}   |   Guest: {rec.get('guest_name','')}   |   "
            f"Arrive: {rec.get('arrive','')} → Depart: {rec.get('depart','')}   |   "
            f"Days: {rec.get('days','')}   |   Nights: {rec.get('nights','')}   |   "
            f"Room Type: {rec.get('room_type','')}   |   Res Type: {rec.get('rtype','')}   |   "
            f"Status: {rec.get('status','')} ({status_code(rec)})   |   Room#: {rec.get('assigned_room','')}   |   "
            f"Paid: ${rec.get('paid_advance',0):.2f}   |   Total: ${rec.get('total_locked',0):.2f}"
        )
        if rec.get('no_show_penalty', 0) > 0:
            details += f"   |   No-Show Penalty: ${rec.get('no_show_penalty',0):.2f}"
        if rec.get('fully_paid'):
            details += "   |   Fully Paid"
        masked_cc = mask_card(rec.get("cc_info", ""))
        if masked_cc.strip() and masked_cc != "****":
            details += f"   |   Card: {masked_cc}"
        if rec.get("change_note"):
            details += f"\nNotes: {rec.get('change_note')}"
        addr = rec.get("address","")
        st = rec.get("state","")
        zp = rec.get("zip","")
        if addr or st or zp:
            details += f"\nAddress: {addr} {st} {zp}"
        payments = rec.get("payments", [])
        if payments:
            pay_lines = " | Payments: " + ", ".join(f"{p['date']} ${p['amount']:,.2f}" for p in payments)
            details += pay_lines
        self.d_lbl.config(text=details)
        self.d_status.set(rec.get("status","Booked"))
        self.d_room.set(rec.get("assigned_room",""))
        self.curr_arr_label.config(text=rec.get("arrive","—"))
        self.curr_dep_label.config(text=rec.get("depart","—"))
        self.d_new_arr.set(rec.get("arrive",""))
        self.d_new_dep.set(rec.get("depart",""))

    def update_selected(self):
        sel = self.res_tree.selection()
        if not sel:
            return messagebox.showwarning("Update", "Select a reservation in the table.")
        res_id = sel[0]
        for r in self.state_data["reservations"]:
            if r.get("reservation_id", r.get("locator"))==res_id:
                r["status"] = self.d_status.get()
                r["assigned_room"] = self.d_room.get().strip()
                save_state(self.state_data)
                self.refresh_res_list()
                return messagebox.showinfo("Update", f"Reservation {res_id} updated.")
        messagebox.showerror("Update", "Could not find reservation in data.")

    # --------- Date change ---------
    def quote_date_change(self):
        if not self.selected_reservation:
            return messagebox.showwarning("Quote Date Change", "Select a reservation in the table.")
        rec = self.selected_reservation
        new_arrive = self.d_new_arr.get().strip()
        new_depart = self.d_new_dep.get().strip()
        if not is_valid_date(new_arrive) or not is_valid_date(new_depart):
            return messagebox.showerror("Date Change", "New arrival/departure must be YYYY-MM-DD.")
        if ISO(new_depart) <= ISO(new_arrive):
            return messagebox.showerror("Date Change", "Departure must be after arrival.")

        try:
            original_cost = rec.get("total_locked", 0.0)
            is_change = rec["rtype"] in ["Prepaid", "60-Day"]
            start = ISO(new_arrive); end = ISO(new_depart)
            available, min_avail = is_available_for(self.state_data, start, end, exclude_reservation_id=rec.get("reservation_id", rec.get("locator")))
            total, nightly, eligible, occ, change_note, penalty_amount = quote_total(
                self.state_data, new_arrive, new_depart, rec["rtype"],
                original_cost, is_change=is_change
            )
            nights = (ISO(new_depart) - ISO(new_arrive)).days
            difference = total - original_cost
            message = (
                f"Date Change Quote for {rec.get('reservation_id', rec.get('locator'))}:\n\n"
                f"Old: {rec['arrive']} to {rec['depart']} = ${original_cost:,.2f}\n"
                f"New: {new_arrive} to {new_depart} = ${total:,.2f}\n"
                f"Additional Cost: ${difference:,.2f}\n"
                f"Nights: {nights}\n"
                f"Incentive eligible: {'Yes' if eligible else 'No'}\n"
                f"Occupancy (avg): {occ*100:.1f}%\n"
                f"Availability: {'Yes' if available else 'No'} (min rooms available on span: {min_avail})"
            )
            if is_change:
                message += f"\n\n{change_note or 'Change policy applied.'}"
                if penalty_amount:
                    message += f"\nPenalty/extra charge due to change: ${penalty_amount:,.2f}"
            else:
                message += "\n\nNo date-change penalty for this reservation type."
            messagebox.showinfo("Date Change Quote", message)
        except Exception as e:
            messagebox.showerror("Quote Date Change Error", str(e))

    def apply_date_change(self):
        if not self.selected_reservation:
            return messagebox.showwarning("Apply Date Change", "Select a reservation in the table.")
        rec = self.selected_reservation
        new_arrive = self.d_new_arr.get().strip()
        new_depart = self.d_new_dep.get().strip()
        if not is_valid_date(new_arrive) or not is_valid_date(new_depart):
            return messagebox.showerror("Date Change", "New arrival/departure must be YYYY-MM-DD.")
        if ISO(new_depart) <= ISO(new_arrive):
            return messagebox.showerror("Date Change", "Departure must be after arrival.")

        try:
            original_cost = rec.get("total_locked", 0.0)
            is_change = rec["rtype"] in ["Prepaid", "60-Day"]
            start = ISO(new_arrive); end = ISO(new_depart)
            available, min_avail = is_available_for(self.state_data, start, end, exclude_reservation_id=rec.get("reservation_id", rec.get("locator")))
            if not available:
                return messagebox.showerror("Apply Date Change", f"Requested dates are not available. Minimum rooms available on span: {min_avail}.")
            total, nightly, eligible, occ, change_note, penalty_amount = quote_total(
                self.state_data, new_arrive, new_depart, rec["rtype"],
                original_cost, is_change=is_change
            )
            old_arrive, old_depart = rec["arrive"], rec["depart"]
            rec["arrive"] = new_arrive
            rec["depart"] = new_depart
            rec["total_locked"] = round(total, 2)
            rec["snapshot"] = {"nightly": nightly}
            rec["change_note"] = change_note
            if rec["status"] == "Changing date":
                rec["status"] = "Booked"
                self.d_status.set("Booked")
            save_state(self.state_data)
            self.curr_arr_label.config(text=new_arrive)
            self.curr_dep_label.config(text=new_depart)
            msg = (
                f"Date change applied to {rec.get('reservation_id', rec.get('locator'))}:\n\n"
                f"Old: {old_arrive} to {old_depart} (${original_cost:,.2f})\n"
                f"New: {new_arrive} to {new_depart} (${total:,.2f})\n"
                f"Additional cost: ${total - original_cost:,.2f}\n"
                f"Status: {rec['status']}"
            )
            if change_note:
                msg += f"\n\nNotes: {change_note}"
            if penalty_amount:
                msg += f"\n\nPenalty/extra charge due to change: ${penalty_amount:,.2f}"
            messagebox.showinfo("Date Change Applied", msg)
            self.refresh_res_list()
        except Exception as e:
            messagebox.showerror("Apply Date Change Error", str(e))

    # --------- Payment & Cancellation ---------
    def process_prepayment(self):
        if not self.selected_reservation:
            return messagebox.showwarning("Payment", "Select a reservation in the table.")
        rec = self.selected_reservation
        res_id = rec.get("reservation_id", rec.get("locator"))
        if rec.get("paid_advance", 0) >= rec.get("total_locked", 0):
            return messagebox.showinfo("Payment", f"Reservation {res_id} is already fully paid.")
        if rec["rtype"] in ["Conventional", "Incentive"]:
            return messagebox.showinfo("Payment", f"{rec['rtype']} reservations are paid at checkout, not in advance.")
        amount = rec["total_locked"] - rec.get("paid_advance", 0)
        if messagebox.askyesno("Process Prepayment", f"Process prepayment of ${amount:,.2f} for reservation {res_id}?\nGuest: {rec['guest_name']}"):
            payments = rec.setdefault("payments", [])
            payments.append({"date": TODAY().isoformat(), "amount": round(amount,2)})
            rec["paid_advance"] = rec["total_locked"]
            rec["paid_advance_date"] = TODAY().isoformat()
            rec["fully_paid"] = True
            save_state(self.state_data)
            self.refresh_res_list()
            messagebox.showinfo("Payment Processed", f"Prepayment of ${amount:,.2f} processed for {res_id}")

    def process_payment(self):
        if not self.selected_reservation:
            return messagebox.showwarning("Payment", "Select a reservation in the table.")
        rec = self.selected_reservation
        res_id = rec.get("reservation_id", rec.get("locator"))
        if rec.get("fully_paid"):
            return messagebox.showinfo("Payment", f"Reservation {res_id} is already fully paid.")
        if rec.get("status") == "Cancelled":
            return messagebox.showwarning("Payment", "Cannot process payment for a cancelled reservation.")
        amount_due = rec["total_locked"] - rec.get("paid_advance", 0)
        if amount_due <= 0:
            rec["fully_paid"] = True
            save_state(self.state_data)
            self.refresh_res_list()
            return messagebox.showinfo("Payment", f"No amount due. Marked {res_id} as fully paid.")
        if messagebox.askyesno("Process Payment", f"Process payment of ${amount_due:,.2f} for reservation {res_id}?\nGuest: {rec['guest_name']}"):
            payments = rec.setdefault("payments", [])
            payments.append({"date": TODAY().isoformat(), "amount": round(amount_due,2)})
            rec["paid_advance"] = rec["total_locked"]
            rec["paid_advance_date"] = TODAY().isoformat()
            rec["fully_paid"] = True
            save_state(self.state_data)
            self.refresh_res_list()
            messagebox.showinfo("Payment Processed", f"Payment of ${amount_due:,.2f} processed for {res_id}")

    def cancel_reservation(self):
        if not self.selected_reservation:
            return messagebox.showwarning("Cancellation", "Select a reservation in the table.")
        rec = self.selected_reservation
        res_id = rec.get("reservation_id", rec.get("locator"))
        rtype = rec["rtype"]
        if rec.get("status") == "Cancelled":
            return messagebox.showinfo("Cancellation", "Reservation is already cancelled.")
        if rec.get("checked_out"):
            return messagebox.showwarning("Cancellation", "Cannot cancel checked-out reservation.")

        if rtype in ["Prepaid", "60-Day"]:
            policy = "NO REFUND for cancellations"
        else:
            days_until_arrival = (ISO(rec["arrive"]) - TODAY()).days
            if days_until_arrival < 3:
                penalty_preview = list(rec.get('snapshot', {}).get('nightly', {}).values())[0] if rec.get('snapshot', {}).get('nightly') else base_rate(self.state_data, ISO(rec["arrive"]))
                policy = f"Charge first night (${penalty_preview:.2f}) as penalty"
            else:
                policy = "No penalty"

        if messagebox.askyesno("Cancel Reservation",
                               f"Cancel reservation {res_id}?\nGuest: {rec['guest_name']}\nType: {rtype}\nPolicy: {policy}\n\nAre you sure?"):
            if rtype in ["Prepaid", "60-Day"]:
                pass
            elif rtype in ["Conventional", "Incentive"]:
                days_until_arrival = (ISO(rec["arrive"]) - TODAY()).days
                if days_until_arrival < 3:
                    penalty = list(rec.get('snapshot', {}).get('nightly', {}).values())[0] if rec.get('snapshot', {}).get('nightly') else base_rate(self.state_data, ISO(rec["arrive"]))
                    rec["no_show_penalty"] = penalty
                    rec["paid_advance"] = max(rec.get("paid_advance", 0.0), penalty)
            rec["status"] = "Cancelled"
            rec["cancelled_date"] = TODAY().isoformat()
            save_state(self.state_data)
            self.refresh_res_list()
            messagebox.showinfo("Cancelled", f"Reservation {res_id} cancelled.\nPolicy applied: {policy}")

    def check_in_guest(self):
        if not self.selected_reservation:
            return messagebox.showwarning("Check In", "Select a reservation in the table.")
        rec = self.selected_reservation
        res_id = rec.get("reservation_id", rec.get("locator"))
        if rec["status"] == "In-House":
            return messagebox.showinfo("Check In", "Guest is already checked in.")
        if rec.get("status") == "Cancelled":
            return messagebox.showwarning("Check In", "Cannot check in a cancelled reservation.")
        if not rec.get("assigned_room"):
            return messagebox.showwarning("Check In", "Please assign a room number first.")
        rec["status"] = "In-House"
        rec["checked_in"] = True
        rec["check_in_date"] = TODAY().isoformat()
        save_state(self.state_data)
        self.refresh_res_list()
        messagebox.showinfo("Checked In", f"Guest {rec['guest_name']} checked into room {rec['assigned_room']}")

    def check_out_guest(self):
        if not self.selected_reservation:
            return messagebox.showwarning("Check Out", "Select a reservation in the table.")
        rec = self.selected_reservation
        res_id = rec.get("reservation_id", rec.get("locator"))
        if rec["status"] != "In-House":
            return messagebox.showwarning("Check Out", "Guest is not checked in.")
        final_payment = 0
        if rec["rtype"] in ["Conventional", "Incentive"]:
            final_payment = rec["total_locked"] - rec.get("paid_advance", 0)
        msg = f"Check out guest {rec['guest_name']} from room {rec['assigned_room']}?"
        if final_payment > 0:
            msg += f"\n\nFinal payment due: ${final_payment:,.2f}"
        if messagebox.askyesno("Check Out", msg):
            if final_payment > 0:
                payments = rec.setdefault("payments", [])
                payments.append({"date": TODAY().isoformat(), "amount": round(final_payment,2)})
                rec["paid_advance"] = rec["total_locked"]
                rec["paid_advance_date"] = TODAY().isoformat()
                rec["fully_paid"] = True
            rec["status"] = "Checked-out"
            rec["checked_out"] = True
            rec["check_out_date"] = TODAY().isoformat()
            save_state(self.state_data)
            self.refresh_res_list()
            messagebox.showinfo("Checked Out", f"Guest {rec['guest_name']} checked out." +
                                (f"\nFinal payment of ${final_payment:,.2f} processed." if final_payment > 0 else ""))

    def generate_bill(self):
        if not self.selected_reservation:
            return messagebox.showwarning("Bill", "Select a reservation in the table.")
        rec = self.selected_reservation
        res_id = rec.get("reservation_id", rec.get("locator"))
        guest = rec.get("guest_name","")
        arrive = rec.get("arrive",""); depart = rec.get("depart","")
        nights = self._calc_nights(arrive, depart) or 0
        nightly_rates = rec.get("snapshot", {}).get("nightly", {})
        total_locked = rec.get("total_locked", 0.0)
        paid = rec.get("paid_advance", 0.0)
        penalty = rec.get("no_show_penalty", 0.0)
        change_note = rec.get("change_note", "")
        payments = rec.get("payments", [])

        notes = []
        notes.append(f"Bill for reservation {res_id} — Guest: {guest}")
        notes.append(f"Stay: {arrive} → {depart} ({nights} nights)")
        if nightly_rates:
            notes.append("Nightly rates (locked):")
            for d, amt in nightly_rates.items():
                notes.append(f"  {d}: ${amt:,.2f}")
        else:
            notes.append("Nightly rates: not available")
        notes.append(f"Subtotal (total locked): ${total_locked:,.2f}")
        if change_note:
            notes.append(f"Date change notes: {change_note}")
        if penalty and rec.get("status") == "Cancelled":
            notes.append(f"Cancellation penalty: ${penalty:,.2f}")
        if payments:
            notes.append("Payments:")
            for p in payments:
                notes.append(f"  {p.get('date','')}  ${p.get('amount',0):,.2f}")
        elif paid:
            notes.append(f"Advance/previous payments: ${paid:,.2f} (date: {rec.get('paid_advance_date','')})")
        balance = max(0.0, total_locked - paid) + (penalty or 0.0)
        notes.append(f"Balance due: ${balance:,.2f}")
        messagebox.showinfo("Generated Bill", "\n".join(notes))

    def verify_availability(self):
        if not is_valid_date(self.arr.get().strip()) or not is_valid_days(self.days.get().strip()):
            return messagebox.showerror("Availability", "Enter valid Arrival (YYYY-MM-DD) and Number of Days.")
        start = ISO(self.arr.get().strip())
        end = start + dt.timedelta(days=int(self.days.get().strip()))
        available, min_avail = is_available_for(self.state_data, start, end)
        occ = occ_ratio(self.state_data, start, end)
        avg_occupied = round(occ * ROOM_COUNT, 1)
        avg_available = ROOM_COUNT - avg_occupied
        messagebox.showinfo("Availability", f"Average occupied rooms over the span: {avg_occupied}\nAverage available rooms: {avg_available}\nMinimum rooms available on span: {min_avail}\nAvailable: {'Yes' if available else 'No'}")

    def run_daily_tasks_ui(self):
        tasks = run_daily_tasks(self.state_data)
        if tasks:
            messagebox.showinfo("Daily Tasks Completed", "The following tasks were performed:\n\n• " + "\n• ".join(tasks))
        else:
            messagebox.showinfo("Daily Tasks", "No daily tasks needed to be performed.")
        self.refresh_res_list()

    # --------- Admin windows (base rates & reports) ---------
    def open_base_rate_admin(self):
        win = tk.Toplevel(self)
        win.title("Base Rates — Add / Update / Delete")
        win.geometry("480x380")
        tk.Label(win, text="Date (YYYY-MM-DD):").grid(row=0, column=0, sticky="w", padx=8, pady=(10,4))
        br_date = tk.Entry(win, width=16); br_date.grid(row=0, column=1, sticky="w")
        tk.Label(win, text="Rate:").grid(row=1, column=0, sticky="w", padx=8)
        br_rate = tk.Entry(win, width=12); br_rate.grid(row=1, column=1, sticky="w")

        out = tk.Text(win, height=12, width=52); out.grid(row=2, column=0, columnspan=3, padx=8, pady=8)
        def log(msg): out.insert("end", msg + "\n"); out.see("end")

        def add_rate():
            d = br_date.get().strip()
            s = br_rate.get().strip()
            if not is_valid_date(d):
                return log("Error: Date must be YYYY-MM-DD")
            try:
                r = float(s)
            except:
                return log("Error: Rate must be a number.")
            if d in self.state_data["base_rates"]:
                return log("Rate already exists for this date.")
            self.state_data["base_rates"][d] = r
            save_state(self.state_data)
            log(f"Added base rate {d} -> {r:.2f}")

        def update_rate():
            d = br_date.get().strip()
            s = br_rate.get().strip()
            if not is_valid_date(d):
                return log("Error: Date must be YYYY-MM-DD")
            try:
                r = float(s)
            except:
                return log("Error: Rate must be a number.")
            if d not in self.state_data["base_rates"]:
                return log("Error: Rate does not exist; cannot update.")
            self.state_data["base_rates"][d] = r
            save_state(self.state_data)
            log(f"Updated base rate {d} -> {r:.2f}")

        def delete_rate():
            d = br_date.get().strip()
            if not is_valid_date(d):
                return log("Error: Date must be YYYY-MM-DD")
            if d not in self.state_data["base_rates"]:
                return log("Error: Rate does not exist; nothing to delete.")
            del self.state_data["base_rates"][d]
            save_state(self.state_data)
            log(f"Deleted base rate {d}")

        tk.Button(win, text="Add", command=add_rate).grid(row=0, column=2, padx=8)
        tk.Button(win, text="Update", command=update_rate).grid(row=1, column=2, padx=8)
        tk.Button(win, text="Delete", command=delete_rate).grid(row=2, column=2, padx=8, sticky="n")

    def open_reports_window(self):
        win = tk.Toplevel(self)
        win.title("Reports")
        win.geometry("600x420")
        tk.Label(win, text="Reports & Admin Tasks", font=("Segoe UI", 12, "bold")).pack(pady=(8,6))
        btns = tk.Frame(win); btns.pack(pady=6)

        def print_bill_accommodation():
            if not self.selected_reservation:
                return messagebox.showwarning("Bill Accommodation", "Select a reservation first.")
            rec = self.selected_reservation
            res_id = rec.get("reservation_id", rec.get("locator"))
            fname = f"bill_{res_id}.txt"
            arrive = rec.get("arrive",""); depart = rec.get("depart","")
            nights = self._calc_nights(arrive, depart) or 0
            nightly_rates = rec.get("snapshot", {}).get("nightly", {})
            lines = [f"Accommodation Bill — {res_id} — Guest: {rec.get('guest_name','')}",
                     f"Stay: {arrive} → {depart} ({nights} nights)"]
            for d, amt in nightly_rates.items():
                lines.append(f"  {d}: ${amt:,.2f}")
            lines.append(f"Total: ${rec.get('total_locked',0.0):,.2f}")
            payments = rec.get("payments", [])
            if payments:
                lines.append("Payments:")
                for p in payments:
                    lines.append(f"  {p.get('date','')}  ${p.get('amount',0):,.2f}")
            with open(fname, "w") as f: f.write("\n".join(lines))
            messagebox.showinfo("Report", f"Printed {fname}")

        def daily_arrivals_report():
            today = TODAY().isoformat()
            fname = f"arrivals_{today}.txt"
            rows = [r for r in self.state_data["reservations"] if r.get("arrive")==today]
            rows.sort(key=lambda x: (x.get("assigned_room",""), x.get("guest_name","")))
            with open(fname, "w") as f:
                for r in rows:
                    f.write(f"{r.get('reservation_id', r.get('locator'))}\t{r.get('guest_name')}\tRoom {r.get('assigned_room','')}\n")
            messagebox.showinfo("Report", f"Printed {fname}")

        def daily_occupancy_report():
            today = TODAY()
            fname = f"occupancy_{today.isoformat()}.txt"
            occupied = sum(ISO(r["arrive"]) <= today < ISO(r["depart"]) and r.get("status") in ("Booked","In-House")
                           for r in self.state_data["reservations"])
            occ_pct = (occupied/ROOM_COUNT)*100 if ROOM_COUNT else 0
            with open(fname, "w") as f:
                f.write(f"Occupied rooms: {occupied}/{ROOM_COUNT}\nOccupancy: {occ_pct:.1f}%\n")
            messagebox.showinfo("Report", f"Printed {fname}")

        def expected_occupancy_report():
            start = TODAY(); horizon = 7
            fname = f"expected_occupancy_{start.isoformat()}.txt"
            lines = []
            for i in range(horizon):
                d = start + dt.timedelta(days=i)
                occ = sum(ISO(r["arrive"]) <= d < ISO(r["depart"]) and r.get("status") in ("Booked","In-House")
                          for r in self.state_data["reservations"])
                lines.append(f"{d.isoformat()}: {occ}/{ROOM_COUNT}")
            with open(fname, "w") as f: f.write("\n".join(lines))
            messagebox.showinfo("Report", f"Printed {fname}")

        def expected_room_income_report():
            start = TODAY(); horizon = 7
            fname = f"expected_income_{start.isoformat()}.txt"
            lines = []
            for i in range(horizon):
                d = start + dt.timedelta(days=i)
                total = 0.0
                for r in self.state_data["reservations"]:
                    if ISO(r["arrive"]) <= d < ISO(r["depart"]) and r.get("status") in ("Booked","In-House"):
                        base = base_rate(self.state_data, d)
                        mult = RATE_MULT.get(r.get("rtype","Conventional"), 1.0)
                        total += base * mult
                lines.append(f"{d.isoformat()}: ${total:,.2f}")
            with open(fname, "w") as f: f.write("\n".join(lines))
            messagebox.showinfo("Report", f"Printed {fname}")

        def incentive_report():
            fname = f"incentive_report_{TODAY().isoformat()}.txt"
            lines = []
            for r in self.state_data["reservations"]:
                if r.get("rtype") == "Incentive":
                    start = ISO(r["arrive"]); end = ISO(r["depart"])
                    eligible = (start - TODAY()).days <= 30 and occ_ratio(self.state_data, start, end) <= 0.60
                    lines.append(f"{r.get('reservation_id', r.get('locator'))} — Guest {r.get('guest_name')} — Eligible: {'Yes' if eligible else 'No'}")
            with open(fname, "w") as f: f.write("\n".join(lines))
            messagebox.showinfo("Report", f"Printed {fname}")

        def admin_assessment():
            tasks = run_daily_tasks(self.state_data)
            fname = f"admin_assessment_{TODAY().isoformat()}.txt"
            with open(fname, "w") as f: f.write("\n".join(tasks) if tasks else "No tasks performed.")
            messagebox.showinfo("Admin Assessment", f"Printed {fname}")

        tk.Button(btns, text="Print Bill Accommodation", command=print_bill_accommodation).grid(row=0, column=0, padx=6, pady=6, sticky="w")
        tk.Button(btns, text="Daily Arrivals Report", command=daily_arrivals_report).grid(row=0, column=1, padx=6, pady=6, sticky="w")
        tk.Button(btns, text="Daily Occupancy Report", command=daily_occupancy_report).grid(row=0, column=2, padx=6, pady=6, sticky="w")
        tk.Button(btns, text="Expected Occupancy", command=expected_occupancy_report).grid(row=1, column=0, padx=6, pady=6, sticky="w")
        tk.Button(btns, text="Expected Room Income", command=expected_room_income_report).grid(row=1, column=1, padx=6, pady=6, sticky="w")
        tk.Button(btns, text="Incentive Report", command=incentive_report).grid(row=1, column=2, padx=6, pady=6, sticky="w")
        tk.Button(btns, text="Admin Assessment (No-shows & 60-day reminders)", command=admin_assessment).grid(row=2, column=0, columnspan=3, padx=6, pady=8, sticky="w")

# --------- Entry point ---------
if __name__ == "__main__":
    login = LoginWindow()
    login.mainloop()




