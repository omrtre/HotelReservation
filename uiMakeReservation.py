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

def occ_ratio(state, start, end):
    res = [r for r in state["reservations"] if r.get("status","Booked") in ("Booked","In-House")]
    if not res: return 0.0
    nightly_counts = [sum(ISO(r["arrive"]) <= d < ISO(r["depart"]) for r in res) for d in daterange(start, end)]
    return (sum(nightly_counts)/len(nightly_counts))/ROOM_COUNT if nightly_counts else 0.0

def quote_total(state, arrive, depart, rtype, original_cost=0.0, is_change=False):
    start, end = ISO(arrive), ISO(depart)
    if end <= start:
        raise ValueError("Departure must be after arrival.")

    occ = occ_ratio(state, start, end)
    eligible = (start - TODAY()).days <= 30 and occ <= 0.60
    mult = RATE_MULT.get(rtype, 1.0)
    if rtype == "Incentive" and not eligible:
        mult = 1.0

    nightly = {d.isoformat(): round(base_rate(state, d) * mult, 2) for d in daterange(start, end)}
    total = round(sum(nightly.values()), 2)

    change_note = ""
    if is_change and rtype in ["Prepaid", "60-Day"]:
        new_110 = round(total * 1.10, 2)
        change_cost = round(new_110 - original_cost, 2)
        adjusted_total = max(original_cost, change_cost) if change_cost > 0 else original_cost
        change_note = (
            f"Change policy math: 110% of new total (${new_110:,.2f}) - original (${original_cost:,.2f}) "
            f"= ${change_cost:,.2f}; Adjusted total = ${adjusted_total:,.2f}"
        )
        total = adjusted_total

    return total, nightly, eligible, occ, change_note

def next_locator(state):
    state["last_locator"] += 1
    return f"OO{state['last_locator']}"

def run_daily_tasks(state):
    today = TODAY()
    tasks_performed = []

    # Payment reminders for 60-Day (45 days before arrival)
    for res in state["reservations"]:
        if res.get("status") == "Booked" and res.get("rtype") == "60-Day":
            arrive_date = ISO(res["arrive"])
            if (arrive_date - today).days == 45:
                loc = res.get("locator", "Unknown")
                state["payment_reminders_sent"][loc] = today.isoformat()
                tasks_performed.append(f"Payment reminder sent for reservation {loc}")

    # No-show penalties: yesterday arrivals not checked in
    yesterday = today - dt.timedelta(days=1)
    for res in state["reservations"]:
        if res.get("status") == "Booked" and ISO(res["arrive"]) == yesterday and not res.get("checked_in", False):
            first_night = list(res.get("snapshot", {}).get("nightly", {}).values())[0] if res.get("snapshot", {}).get("nightly") else base_rate(state, yesterday)
            res["no_show_penalty"] = first_night
            res["status"] = "Cancelled"
            res["cancellation_reason"] = "No-show"
            tasks_performed.append(f"No-show penalty applied to reservation {res.get('locator','Unknown')}: ${first_night:.2f}")

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

# --------- Login ---------
class LoginWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ophelia's Oasis — Staff Login")
        self.geometry("380x200")
        self.resizable(False, False)
        self.users = {"staff": "oasis2025", "manager": "orchid#9"}  # Update as needed

        frame = ttk.Frame(self, padding=12)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Username").grid(row=0, column=0, sticky="w", pady=(0,6))
        ttk.Label(frame, text="Password").grid(row=1, column=0, sticky="w")
        self.u = tk.StringVar(); self.p = tk.StringVar()
        ttk.Entry(frame, textvariable=self.u, width=24).grid(row=0, column=1, sticky="w")
        ttk.Entry(frame, textvariable=self.p, show="*", width=24).grid(row=1, column=1, sticky="w")
        self.msg = ttk.Label(frame, text="", foreground="red")
        self.msg.grid(row=2, column=0, columnspan=2, sticky="w", pady=(10,6))
        ttk.Button(frame, text="Login", command=self._login).grid(row=3, column=1, sticky="e")

    def _login(self):
        u, p = self.u.get().strip(), self.p.get().strip()
        if u in self.users and self.users[u] == p:
            self.destroy()
            app = ReservationApp(authorized_user=u)
            app.geometry("1000x750")
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
        self.arr = tk.StringVar(value=(TODAY() + dt.timedelta(days=10)).isoformat())
        self.dep = tk.StringVar(value=(TODAY() + dt.timedelta(days=13)).isoformat())  # Manual entry
        self.rtype = tk.StringVar(value="Conventional")
        self.room_type = tk.StringVar(value=ROOM_TYPES[0])
        self.status = tk.StringVar(value="Booked")
        self.nights_str = tk.StringVar(value="—")
        self.assigned_room = tk.StringVar(value="")
        self.cc_info = tk.StringVar(); self.cc_exp = tk.StringVar(); self.cc_type = tk.StringVar(value=CARD_TYPES[0])
        self.last_quote = None; self.selected_reservation = None

        # Layout root
        root = ttk.Frame(self, padding=10); root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1); root.columnconfigure(1, weight=1); root.rowconfigure(1, weight=1)

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
        ttk.Label(form, text="Comments (optional)").grid(row=r, column=0, sticky="w", pady=2, padx=(10,0))
        ttk.Entry(form, textvariable=self.comments, width=28).grid(row=r, column=1, sticky="w", pady=2); r += 1

        # Reservation details
        ttk.Label(form, text="Reservation details", font=("Segoe UI", 10, "bold")).grid(row=r, column=0, columnspan=2, sticky="w", pady=(12,4), padx=(6,0)); r += 1
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

        # Credit card section (highlighted)
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

        # Quote
        ttk.Button(form, text="Get Quote", command=self.on_quote).grid(row=r, column=0, pady=(10,6), padx=(10,0), sticky="w")
        self.lbl_quote = ttk.Label(form, text="Total: —  | Incentive eligible: —  | Occupancy: —%")
        self.lbl_quote.grid(row=r, column=1, sticky="w", pady=(10,6)); r += 1

        # Nightly detail
        cols = ("Date", "Nightly Rate (locked)")
        self.tree = ttk.Treeview(form, columns=cols, show="headings", height=7)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=160 if c=="Date" else 180, anchor="center")
        self.tree.grid(row=r, column=0, columnspan=2, sticky="nsew", pady=(0,6)); r += 1

        # Save
        ttk.Button(form, text="Confirm & Save", command=self.on_save).grid(row=r, column=1, sticky="e", pady=(6,0))
        form.rowconfigure(r-1, weight=1)

        # RIGHT: Browser
        right = ttk.LabelFrame(root, text="Reservations Browser", padding=(8,8))
        right.grid(row=1, column=1, sticky="nsew", padx=(8,0))
        for i in range(2): right.columnconfigure(i, weight=1)
        right.rowconfigure(1, weight=1)

        # Toolbar
        tb = ttk.Frame(right)
        tb.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(4,2))
        ttk.Button(tb, text="Refresh", command=self.refresh_res_list).pack(side="left")
        ttk.Label(tb, text="Search Guest:").pack(side="left", padx=(8,4))
        self.search_var = tk.StringVar()
        ttk.Entry(tb, textvariable=self.search_var, width=18).pack(side="left")
        ttk.Button(tb, text="Find", command=self.refresh_res_list).pack(side="left", padx=4)

        # Table
        self.res_cols = ("Locator","Guest","Arrive","Depart","Nights","Room Type","Res Type","Status","Room#","Paid","Card (Last 4)")
        self.res_tree = ttk.Treeview(right, columns=self.res_cols, show="headings", height=12)
        widths = [80, 140, 90, 90, 60, 100, 100, 90, 60, 60, 110]
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

        # Initial populate
        self.refresh_res_list()

    # --------- Helpers ---------
    def _calc_nights(self, arrive, depart):
        try:
            return (ISO(depart) - ISO(arrive)).days
        except Exception:
            return None

    # --------- Actions: Quote & Save ---------
    def on_quote(self):
        # Validate dates first for a proper quote
        if not is_valid_date(self.arr.get().strip()):
            return messagebox.showerror("Quote error", "Arrival date must be YYYY-MM-DD.")
        if not is_valid_date(self.dep.get().strip()):
            return messagebox.showerror("Quote error", "Departure date must be YYYY-MM-DD.")
        if ISO(self.dep.get()) <= ISO(self.arr.get()):
            return messagebox.showerror("Quote error", "Departure must be after arrival.")

        try:
            total, nightly, eligible, occ, _ = quote_total(self.state_data, self.arr.get(), self.dep.get(), self.rtype.get(), original_cost=0.0, is_change=False)
        except Exception as e:
            return messagebox.showerror("Quote error", str(e))

        self.lbl_quote.config(text=f"Total: ${total:,.2f} | Incentive eligible: {'Yes' if eligible else 'No'} | Occupancy: {occ*100:.1f}%")
        for x in self.tree.get_children(): self.tree.delete(x)
        for d, amt in nightly.items(): self.tree.insert("", "end", values=(d, f"${amt:,.2f}"))
        self.last_quote = (total, nightly, eligible, occ)

        n = self._calc_nights(self.arr.get(), self.dep.get())
        self.nights_str.set(str(n) if n is not None and n >= 0 else "—")

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
        if not is_valid_date(self.arr.get().strip()):
            return "Arrival date must be YYYY-MM-DD."
        if not is_valid_date(self.dep.get().strip()):
            return "Departure date must be YYYY-MM-DD."
        try:
            if ISO(self.dep.get()) <= ISO(self.arr.get()):
                return "Departure must be after arrival."
        except:
            return "Departure date is invalid."
        if self.rtype.get().strip() not in RATE_MULT:
            return "Reservation type is required."
        # Card validations with inline message
        if not is_valid_card(self.cc_info.get().strip()):
            self.cc_msg.config(text="Card number must be 13–16 digits (numeric only).")
            return "Card number must be 13–16 digits (numeric only)."
        if not is_valid_exp(self.cc_exp.get().strip()):
            self.cc_msg.config(text="Expiration must be MM-YYYY and not expired.")
            return "Expiration must be MM-YYYY and not expired."
        if self.cc_type.get().strip() not in CARD_TYPES:
            self.cc_msg.config(text="Please select a valid card type.")
            return "Please select a valid card type."
        return None

    def on_save(self):
        if not self.last_quote:
            return messagebox.showwarning("Save", "Please get a quote first.")
        err = self._validate_form()
        if err:
            return messagebox.showerror("Validation error", err)

        total, nightly, *_ = self.last_quote
        loc = next_locator(self.state_data)
        rtype = self.rtype.get()
        adv = total if rtype == "Prepaid" else 0.0
        n = self._calc_nights(self.arr.get(), self.dep.get())

        self.state_data["reservations"].append({
            "locator": loc,
            "guest_name": self.guest.get().strip(),
            "email": self.email.get().strip(),
            "phone": self.phone.get().strip(),
            "address": self.address.get().strip(),
            "comments": self.comments.get().strip(),
            "arrive": self.arr.get(),
            "depart": self.dep.get(),
            "rtype": rtype,
            "room_type": self.room_type.get(),
            "cc_info": self.cc_info.get().strip(),
            "cc_exp": self.cc_exp.get().strip(),
            "cc_type": self.cc_type.get().strip(),
            "cc_on_file": True,
            "paid_advance": round(adv, 2),
            "paid_advance_date": TODAY().isoformat() if adv else "",
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
        messagebox.showinfo("Saved", f"Reservation saved.\nLocator: {loc}" + (f"\nAdvance paid: ${adv:,.2f}" if adv else ""))
        self.refresh_res_list()

    # --------- Browser actions ---------
    def refresh_res_list(self):
        self.res_tree.delete(*self.res_tree.get_children())
        self.state_data = load_state()
        q = (self.search_var.get() or "").strip().lower()
        for r in self.state_data["reservations"]:
            if q and q not in r.get("guest_name","").lower():
                continue
            try:
                n = (ISO(r["depart"]) - ISO(r["arrive"])).days
            except Exception:
                n = ""
            paid_status = "Yes" if r.get("paid_advance", 0) > 0 or r.get("rtype") in ["Conventional", "Incentive"] else "No"
            if r.get("rtype") == "60-Day" and r.get("paid_advance", 0) > 0:
                paid_status = "Yes"
            masked_card = mask_card(r.get("cc_info",""))
            self.res_tree.insert("", "end", iid=r["locator"], values=(
                r.get("locator",""),
                r.get("guest_name",""),
                r.get("arrive",""),
                r.get("depart",""),
                n,
                r.get("room_type",""),
                r.get("rtype",""),
                r.get("status",""),
                r.get("assigned_room",""),
                paid_status,
                masked_card
            ))

    def on_select_res(self, _evt=None):
        sel = self.res_tree.selection()
        if not sel:
            self.selected_reservation = None
            return
        loc = sel[0]
        rec = next((x for x in self.state_data["reservations"] if x.get("locator")==loc), None)
        if not rec:
            self.selected_reservation = None
            return
        self.selected_reservation = rec

        details = (
            f"Locator: {rec.get('locator','')}   |   Guest: {rec.get('guest_name','')}   |   "
            f"Arrive: {rec.get('arrive','')} → Depart: {rec.get('depart','')}   |   "
            f"Room Type: {rec.get('room_type','')}   |   Res Type: {rec.get('rtype','')}   |   "
            f"Status: {rec.get('status','')}   |   Room#: {rec.get('assigned_room','')}   |   "
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
        loc = sel[0]
        for r in self.state_data["reservations"]:
            if r.get("locator")==loc:
                r["status"] = self.d_status.get()
                r["assigned_room"] = self.d_room.get().strip()
                save_state(self.state_data)
                self.refresh_res_list()
                return messagebox.showinfo("Update", f"Reservation {loc} updated.")
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
            total, nightly, eligible, occ, change_note = quote_total(
                self.state_data, new_arrive, new_depart, rec["rtype"],
                original_cost, is_change=is_change
            )
            nights = (ISO(new_depart) - ISO(new_arrive)).days
            difference = total - original_cost
            message = (
                f"Date Change Quote for {rec['locator']}:\n\n"
                f"Old: {rec['arrive']} to {rec['depart']} = ${original_cost:,.2f}\n"
                f"New: {new_arrive} to {new_depart} = ${total:,.2f}\n"
                f"Additional Cost: ${difference:,.2f}\n"
                f"Nights: {nights}\n"
                f"Incentive eligible: {'Yes' if eligible else 'No'}\n"
                f"Occupancy: {occ*100:.1f}%"
            )
            message += f"\n\n{change_note or 'No date-change penalty for this reservation type.'}" if is_change else "\n\nNo date-change penalty for this reservation type."
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
            total, nightly, _, _, change_note = quote_total(
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
                f"Date change applied to {rec['locator']}:\n\n"
                f"Old: {old_arrive} to {old_depart} (${original_cost:,.2f})\n"
                f"New: {new_arrive} to {new_depart} (${total:,.2f})\n"
                f"Additional cost: ${total - original_cost:,.2f}\n"
                f"Status: {rec['status']}"
            )
            if change_note:
                msg += f"\n\nNotes: {change_note}"
            messagebox.showinfo("Date Change Applied", msg)
            self.refresh_res_list()
        except Exception as e:
            messagebox.showerror("Apply Date Change Error", str(e))

    # --------- Payment & Cancellation ---------
    def process_prepayment(self):
        if not self.selected_reservation:
            return messagebox.showwarning("Payment", "Select a reservation in the table.")
        rec = self.selected_reservation
        loc = rec["locator"]
        if rec.get("paid_advance", 0) >= rec.get("total_locked", 0):
            return messagebox.showinfo("Payment", f"Reservation {loc} is already fully paid.")
        if rec["rtype"] in ["Conventional", "Incentive"]:
            return messagebox.showinfo("Payment", f"{rec['rtype']} reservations are paid at checkout, not in advance.")
        amount = rec["total_locked"] - rec.get("paid_advance", 0)
        if messagebox.askyesno("Process Payment", f"Process payment of ${amount:,.2f} for reservation {loc}?\nGuest: {rec['guest_name']}"):
            rec["paid_advance"] = rec["total_locked"]
            rec["paid_advance_date"] = TODAY().isoformat()
            rec["fully_paid"] = True
            save_state(self.state_data)
            self.refresh_res_list()
            messagebox.showinfo("Payment Processed", f"Payment of ${amount:,.2f} processed for {loc}")

    def process_payment(self):
        if not self.selected_reservation:
            return messagebox.showwarning("Payment", "Select a reservation in the table.")
        rec = self.selected_reservation
        loc = rec["locator"]
        if rec.get("fully_paid"):
            return messagebox.showinfo("Payment", f"Reservation {loc} is already fully paid.")
        if rec.get("status") == "Cancelled":
            return messagebox.showwarning("Payment", "Cannot process payment for a cancelled reservation.")
        amount_due = rec["total_locked"] - rec.get("paid_advance", 0)
        if amount_due <= 0:
            rec["fully_paid"] = True
            save_state(self.state_data)
            self.refresh_res_list()
            return messagebox.showinfo("Payment", f"No amount due. Marked {loc} as fully paid.")
        if messagebox.askyesno("Process Payment", f"Process payment of ${amount_due:,.2f} for reservation {loc}?\nGuest: {rec['guest_name']}"):
            rec["paid_advance"] = rec["total_locked"]
            rec["paid_advance_date"] = TODAY().isoformat()
            rec["fully_paid"] = True
            save_state(self.state_data)
            self.refresh_res_list()
            messagebox.showinfo("Payment Processed", f"Payment of ${amount_due:,.2f} processed for {loc}")

    def cancel_reservation(self):
        if not self.selected_reservation:
            return messagebox.showwarning("Cancellation", "Select a reservation in the table.")
        rec = self.selected_reservation
        loc = rec["locator"]
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
                               f"Cancel reservation {loc}?\nGuest: {rec['guest_name']}\nType: {rtype}\nPolicy: {policy}\n\nAre you sure?"):
            if rtype in ["Prepaid", "60-Day"]:
                pass
            elif rtype in ["Conventional", "Incentive"]:
                days_until_arrival = (ISO(rec["arrive"]) - TODAY()).days
                if days_until_arrival < 3:
                    penalty = list(rec.get('snapshot', {}).get('nightly', {}).values())[0] if rec.get('snapshot', {}).get('nightly') else base_rate(self.state_data, ISO(rec["arrive"]))
                    rec["no_show_penalty"] = penalty
                    rec["paid_advance"] = penalty
            rec["status"] = "Cancelled"
            rec["cancelled_date"] = TODAY().isoformat()
            save_state(self.state_data)
            self.refresh_res_list()
            messagebox.showinfo("Cancelled", f"Reservation {loc} cancelled.\nPolicy applied: {policy}")

    def check_in_guest(self):
        if not self.selected_reservation:
            return messagebox.showwarning("Check In", "Select a reservation in the table.")
        rec = self.selected_reservation
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
        if rec["status"] != "In-House":
            return messagebox.showwarning("Check Out", "Guest is not checked in.")
        final_payment = 0
        if rec["rtype"] in ["Conventional", "Incentive"]:
            final_payment = rec["total_locked"] - rec.get("paid_advance", 0)
        msg = f"Check out guest {rec['guest_name']} from room {rec['assigned_room']}?"
        if final_payment > 0:
            msg += f"\n\nFinal payment due: ${final_payment:,.2f}"
        if messagebox.askyesno("Check Out", msg):
            rec["status"] = "Checked-out"
            rec["checked_out"] = True
            rec["check_out_date"] = TODAY().isoformat()
            if final_payment > 0:
                rec["paid_advance"] = rec["total_locked"]
                rec["fully_paid"] = True
            save_state(self.state_data)
            self.refresh_res_list()
            messagebox.showinfo("Checked Out", f"Guest {rec['guest_name']} checked out." +
                                (f"\nFinal payment of ${final_payment:,.2f} processed." if final_payment > 0 else ""))

    def generate_bill(self):
        if not self.selected_reservation:
            return messagebox.showwarning("Bill", "Select a reservation in the table.")
        rec = self.selected_reservation
        loc = rec.get("locator","Unknown")
        guest = rec.get("guest_name","")
        arrive = rec.get("arrive",""); depart = rec.get("depart","")
        nights = self._calc_nights(arrive, depart) or 0
        nightly_rates = rec.get("snapshot", {}).get("nightly", {})
        total_locked = rec.get("total_locked", 0.0)
        paid = rec.get("paid_advance", 0.0)
        penalty = rec.get("no_show_penalty", 0.0)
        change_note = rec.get("change_note", "")

        notes = []
        notes.append(f"Bill for reservation {loc} — Guest: {guest}")
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
        if paid:
            notes.append(f"Advance/previous payments: ${paid:,.2f}")
        balance = max(0.0, total_locked - paid) + (penalty or 0.0)
        notes.append(f"Balance due: ${balance:,.2f}")
        messagebox.showinfo("Generated Bill", "\n".join(notes))

    def run_daily_tasks_ui(self):
        tasks = run_daily_tasks(self.state_data)
        if tasks:
            messagebox.showinfo("Daily Tasks Completed", "The following tasks were performed:\n\n• " + "\n• ".join(tasks))
        else:
            messagebox.showinfo("Daily Tasks", "No daily tasks needed to be performed.")
        self.refresh_res_list()

# --------- Entry point ---------
if __name__ == "__main__":
    login = LoginWindow()
    login.mainloop()
