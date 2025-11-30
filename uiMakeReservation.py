# reservation_app.py
import json, os, datetime as dt
import tkinter as tk
from tkinter import ttk, messagebox

DATA_FILE, ROOM_COUNT = "hrs_data.json", 45
TODAY = dt.date.today
ISO = dt.date.fromisoformat
RATE_MULT = {"Prepaid": 0.75, "60-Day": 0.85, "Conventional": 1.00, "Incentive": 0.80}
ROOM_TYPES = ["Standard", "Deluxe", "Suite", "Penthouse"]
STATUSES = ["Booked", "In-House", "Checked-out", "Cancelled"]

def load_state():
    if not os.path.exists(DATA_FILE):
        return {"base_rates": {}, "reservations": [], "last_locator": 4000}
    with open(DATA_FILE) as f: return json.load(f)

def save_state(state):
    with open(DATA_FILE, "w") as f: json.dump(state, f, indent=2)

def daterange(start, end):
    while start < end:
        yield start
        start += dt.timedelta(days=1)

def base_rate(state, d):
    return float(state["base_rates"].get(d.isoformat(), 300.0))

def occ_ratio(state, start, end):
    res = [r for r in state["reservations"] if r.get("status","Booked") in ("Booked","In-House")]
    if not res: return 0.0
    nightly = [
        sum(ISO(r["arrive"]) <= d < ISO(r["depart"]) for r in res)
        for d in daterange(start, end)
    ]
    return (sum(nightly)/len(nightly))/ROOM_COUNT if nightly else 0.0

def quote_total(state, arrive, depart, rtype):
    start, end = ISO(arrive), ISO(depart)
    if end <= start: raise ValueError("Departure must be after arrival.")
    occ = occ_ratio(state, start, end)
    eligible = (start - TODAY()).days <= 30 and occ <= 0.60
    mult = RATE_MULT.get(rtype, 1.0)
    if rtype == "Incentive" and not eligible:
        mult = 1.0
    nightly = {d.isoformat(): round(base_rate(state, d) * mult, 2) for d in daterange(start, end)}
    return round(sum(nightly.values()), 2), nightly, eligible, occ

def next_locator(state):
    state["last_locator"] += 1
    return f"OO{state['last_locator']}"

class ReservationApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Hotel Reservation System — Reservation")
        self.state_data = load_state()

        if not self.state_data["base_rates"]:
            t = TODAY()
            self.state_data["base_rates"] = {
                (t+dt.timedelta(days=i)).isoformat(): 280.0 + 10*(i % 5) for i in range(14)
            }
            save_state(self.state_data)

        # ------------- Form variables -------------
        self.guest = tk.StringVar()
        self.email = tk.StringVar()
        self.phone = tk.StringVar()
        self.arr = tk.StringVar(value=(TODAY() + dt.timedelta(days=10)).isoformat())
        self.dep = tk.StringVar(value=(TODAY() + dt.timedelta(days=13)).isoformat())
        self.rtype = tk.StringVar(value="Conventional")
        self.room_type = tk.StringVar(value=ROOM_TYPES[0])
        self.status = tk.StringVar(value="Booked")
        self.nights_str = tk.StringVar(value="—")
        self.assigned_room = tk.StringVar(value="")  # form value (optional)
        self.last_quote = None

        # ------------- Layout: left form / right browser -------------
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)
        root.columnconfigure(0, weight=1)
        root.columnconfigure(1, weight=1)
        root.rowconfigure(1, weight=1)

        # Title
        title = ttk.Label(root, text="Reservation — Create & Browse", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0,6))

        # LEFT: Create/Quote form
        form = ttk.LabelFrame(root, text="Create / Quote Reservation")
        form.grid(row=1, column=0, sticky="nsew", padx=(0,8))
        for i in range(2):
            form.columnconfigure(i, weight=1)

        r = 0
        def row(label, var, width=28):
            nonlocal r
            ttk.Label(form, text=label).grid(row=r, column=0, sticky="w", pady=2)
            ttk.Entry(form, textvariable=var, width=width).grid(row=r, column=1, sticky="ew", pady=2)
            r += 1

        row("Guest Name", self.guest)
        row("Email", self.email)
        row("Phone", self.phone, 20)
        row("Arrival (YYYY-MM-DD)", self.arr, 16)
        row("Departure (YYYY-MM-DD)", self.dep, 16)

        ttk.Label(form, text="Reservation Type").grid(row=r, column=0, sticky="w", pady=2)
        ttk.Combobox(
            form, textvariable=self.rtype,
            values=["Prepaid", "60-Day", "Conventional", "Incentive"],
            state="readonly", width=16
        ).grid(row=r, column=1, sticky="w", pady=2); r += 1

        ttk.Label(form, text="Room Type").grid(row=r, column=0, sticky="w", pady=2)
        ttk.Combobox(
            form, textvariable=self.room_type,
            values=ROOM_TYPES, state="readonly", width=16
        ).grid(row=r, column=1, sticky="w", pady=2); r += 1

        ttk.Label(form, text="Status").grid(row=r, column=0, sticky="w", pady=2)
        ttk.Combobox(
            form, textvariable=self.status,
            values=STATUSES, state="readonly", width=16
        ).grid(row=r, column=1, sticky="w", pady=2); r += 1

        ttk.Label(form, text="Nights (auto)").grid(row=r, column=0, sticky="w", pady=2)
        nights_ent = ttk.Entry(form, textvariable=self.nights_str, state="readonly")
        nights_ent.grid(row=r, column=1, sticky="ew", pady=2); r += 1

        ttk.Label(form, text="Assigned Room # (opt)").grid(row=r, column=0, sticky="w", pady=2)
        ttk.Entry(form, textvariable=self.assigned_room, width=10).grid(row=r, column=1, sticky="w", pady=2); r += 1

        # Quote controls
        ttk.Button(form, text="Quote", command=self.on_quote).grid(row=r, column=0, pady=(6,4), sticky="w")
        self.lbl_quote = ttk.Label(form, text="Total: —  | Incentive eligible: —  | Avg occupancy: —%")
        self.lbl_quote.grid(row=r, column=1, sticky="w", pady=(6,4)); r += 1

        # Nightly detail
        cols = ("Date", "Nightly Rate (locked)")
        self.tree = ttk.Treeview(form, columns=cols, show="headings", height=7)
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=160 if c=="Date" else 180, anchor="center")
        self.tree.grid(row=r, column=0, columnspan=2, sticky="nsew", pady=(0,6)); r += 1

        # Save
        ttk.Button(form, text="Confirm & Save", command=self.on_save).grid(row=r, column=1, sticky="e", pady=(4,0))

        form.rowconfigure(r-1, weight=1)

        # RIGHT: Reservations Browser
        right = ttk.LabelFrame(root, text="Reservations Browser")
        right.grid(row=1, column=1, sticky="nsew", padx=(8,0))
        for i in range(2):
            right.columnconfigure(i, weight=1)
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
        self.res_cols = ("Locator","Guest","Arrive","Depart","Nights","Room Type","Res Type","Status","Room#")
        self.res_tree = ttk.Treeview(right, columns=self.res_cols, show="headings", height=12)
        widths = [80, 140, 90, 90, 60, 100, 100, 90, 60]
        for c, w in zip(self.res_cols, widths):
            self.res_tree.heading(c, text=c)
            self.res_tree.column(c, width=w, anchor="center")
        self.res_tree.grid(row=1, column=0, columnspan=2, sticky="nsew")

        ysb = ttk.Scrollbar(right, orient="vertical", command=self.res_tree.yview)
        self.res_tree.configure(yscroll=ysb.set)
        ysb.grid(row=1, column=2, sticky="ns")

        self.res_tree.bind("<<TreeviewSelect>>", self.on_select_res)

        # Details + quick update
        details = ttk.Frame(right)
        details.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(6,0))
        details.columnconfigure(1, weight=1)
        self.d_lbl = ttk.Label(details, text="Select a reservation to see details.", anchor="w")
        self.d_lbl.grid(row=0, column=0, columnspan=3, sticky="ew", pady=(0,4))

        ttk.Label(details, text="Status").grid(row=1, column=0, sticky="w")
        self.d_status = tk.StringVar(value="Booked")
        ttk.Combobox(details, textvariable=self.d_status, values=STATUSES, state="readonly", width=14)\
            .grid(row=1, column=1, sticky="w", padx=(4,12))

        ttk.Label(details, text="Room #").grid(row=1, column=2, sticky="w")
        self.d_room = tk.StringVar()
        ttk.Entry(details, textvariable=self.d_room, width=8).grid(row=1, column=3, sticky="w", padx=(4,0))

        ttk.Button(details, text="Update Selected", command=self.update_selected).grid(row=1, column=4, padx=8)

        # Init populate
        self.refresh_res_list()

        # Auto-calc nights when dates change (basic)
        self.arr.trace_add("write", lambda *_: self._update_nights_only())
        self.dep.trace_add("write", lambda *_: self._update_nights_only())
        self._update_nights_only()

    # ---------- Helpers ----------
    def _calc_nights(self):
        try:
            return (ISO(self.dep.get()) - ISO(self.arr.get())).days
        except Exception:
            return None

    def _update_nights_only(self):
        n = self._calc_nights()
        self.nights_str.set(str(n) if n is not None and n >= 0 else "—")

    # ---------- Form actions ----------
    def on_quote(self):
        try:
            total, nightly, eligible, occ = quote_total(self.state_data, self.arr.get(), self.dep.get(), self.rtype.get())
        except Exception as e:
            messagebox.showerror("Quote error", str(e)); return

        self.lbl_quote.config(text=f"Total: ${total:,.2f} | Incentive eligible: {'Yes' if eligible else 'No'} | Avg occupancy: {occ*100:.1f}%")
        for x in self.tree.get_children(): self.tree.delete(x)
        for d, amt in nightly.items(): self.tree.insert("", "end", values=(d, f"${amt:,.2f}"))
        self.last_quote = (total, nightly, eligible, occ)

        # Also update nights label if possible
        n = self._calc_nights()
        if n is not None and n >= 0:
            self.nights_str.set(str(n))

    def on_save(self):
        if not self.last_quote:
            return messagebox.showwarning("Save", "Please quote first.")
        if not self.guest.get().strip():
            return messagebox.showwarning("Save", "Guest name is required.")

        total, nightly, *_ = self.last_quote
        loc = next_locator(self.state_data)
        adv = total if self.rtype.get() in ("Prepaid", "60-Day") else 0.0

        self.state_data["reservations"].append({
            "locator": loc,
            "guest_name": self.guest.get().strip(),
            "email": self.email.get().strip(),
            "phone": self.phone.get().strip(),
            "arrive": self.arr.get(),
            "depart": self.dep.get(),
            "rtype": self.rtype.get(),
            "room_type": self.room_type.get(),
            "cc_on_file": True,
            "paid_advance": round(adv, 2),
            "paid_advance_date": TODAY().isoformat() if adv else "",
            "total_locked": round(total, 2),
            "snapshot": {"nightly": nightly},
            "assigned_room": self.assigned_room.get().strip(),
            "status": self.status.get(),
        })
        save_state(self.state_data)
        messagebox.showinfo("Saved", f"Reservation saved.\nLocator: {loc}")
        self.refresh_res_list()

    # ---------- Browser actions ----------
    def refresh_res_list(self):
        # Wipe and repopulate from file
        self.res_tree.delete(*self.res_tree.get_children())
        # (Re)load file to reflect other users/processes
        self.state_data = load_state()

        q = (self.search_var.get() or "").strip().lower()
        for r in self.state_data["reservations"]:
            if q and q not in r.get("guest_name","").lower():
                continue
            try:
                n = (ISO(r["depart"]) - ISO(r["arrive"])).days
            except Exception:
                n = ""
            self.res_tree.insert(
                "", "end", iid=r["locator"],
                values=(
                    r.get("locator",""),
                    r.get("guest_name",""),
                    r.get("arrive",""),
                    r.get("depart",""),
                    n,
                    r.get("room_type",""),
                    r.get("rtype",""),
                    r.get("status",""),
                    r.get("assigned_room",""),
                )
            )

    def on_select_res(self, _evt=None):
        sel = self.res_tree.selection()
        if not sel: return
        loc = sel[0]
        rec = next((x for x in self.state_data["reservations"] if x.get("locator")==loc), None)
        if not rec: return
        # Fill details area
        self.d_lbl.config(text=(
            f"Locator: {rec.get('locator','')}   |   Guest: {rec.get('guest_name','')}   |   "
            f"Arrive: {rec.get('arrive','')} → Depart: {rec.get('depart','')}   |   "
            f"Room Type: {rec.get('room_type','')}   |   Res Type: {rec.get('rtype','')}   |   "
            f"Status: {rec.get('status','')}   |   Room#: {rec.get('assigned_room','')}"
        ))
        self.d_status.set(rec.get("status","Booked"))
        self.d_room.set(rec.get("assigned_room",""))

    def update_selected(self):
        sel = self.res_tree.selection()
        if not sel:
            return messagebox.showwarning("Update", "Select a reservation in the table.")
        loc = sel[0]
        found = False
        for r in self.state_data["reservations"]:
            if r.get("locator")==loc:
                r["status"] = self.d_status.get()
                r["assigned_room"] = self.d_room.get().strip()
                found = True
                break
        if not found:
            return messagebox.showerror("Update", "Could not find reservation in data.")
        save_state(self.state_data)
        self.refresh_res_list()
        messagebox.showinfo("Update", f"Reservation {loc} updated.")

if __name__ == "__main__":
    app = ReservationApp()
    app.geometry("980x560")
    app.mainloop()
