import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import json, os

DATA_FILE = "hrs_data.json"

# ---------------- Bill Model ----------------
class Bill:
    def __init__(self, billId, guestName, roomNum, arrival, departure, nights, resType, totalAmt, paidAmt, balance):
        self.billId = billId
        self.billIssueDate = datetime.now().strftime("%Y-%m-%d")
        self.billTotalAmt = float(totalAmt or 0.0)
        self.billPaidAmt = float(paidAmt or 0.0)
        self.billBalanceAmt = float(balance or 0.0)
        self.billGuestName = guestName or ""
        self.billRoomNum = roomNum or ""
        self.billDateArrival = arrival or ""
        self.billDateDeparture = departure or ""
        self.billNightsStayedNum = str(nights or "")
        self.billResType = resType or ""

    def generateBill(self):
        lines = [
            "Ophelia's Oasis Hotel",
            "-------------------------",
            f"Bill ID: {self.billId}",
            f"Bill Issue Date: {self.billIssueDate}",
            f"Guest Name: {self.billGuestName}",
            f"Room Number: {self.billRoomNum}",
            f"Arrival Date: {self.billDateArrival}",
            f"Departure Date: {self.billDateDeparture}",
            f"Nights Stayed: {self.billNightsStayedNum}",
            f"Reservation Type: {self.billResType}",
            f"Total Amount: ${self.billTotalAmt:.2f}",
            f"Paid: ${self.billPaidAmt:.2f}",
            f"Balance: ${self.billBalanceAmt:.2f}",
            "-------------------------",
        ]
        return "\n".join(lines)

# ---------------- Data Helpers ----------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r") as f:
        try:
            data = json.load(f)
            return data.get("reservations", [])
        except Exception:
            return []

def find_reservation_by_locator(locator):
    locator = (locator or "").strip()
    if not locator:
        return None
    for r in load_data():
        if r.get("locator") == locator:
            return r
    return None

def compute_nights(arrive, depart):
    try:
        a = datetime.strptime(arrive, "%Y-%m-%d")
        d = datetime.strptime(depart, "%Y-%m-%d")
        return (d - a).days
    except Exception:
        return ""

def compute_totals(rec):
    total = float(rec.get("total_locked", 0.0))
    paid = float(rec.get("paid_advance", 0.0))
    penalty = float(rec.get("no_show_penalty", 0.0) or 0.0)
    balance = max(0.0, total - paid) + penalty
    return total, paid, balance

# ---------------- UI Helpers ----------------
def set_entry(entry_widget, value):
    entry_widget.config(state="normal")
    entry_widget.delete(0, tk.END)
    entry_widget.insert(0, value if value is not None else "")
    entry_widget.config(state="readonly")

def clear_form():
    for e in [
        ent_res_id, ent_guest, ent_room, ent_mobile,
        ent_issue_date, ent_arrival, ent_departure, ent_nights, ent_res_type
    ]:
        e.config(state="normal")
        e.delete(0, tk.END)
        e.config(state="readonly")
    total_lbl["text"] = "-"
    paid_lbl["text"] = "-"
    bal_lbl["text"] = "-"
    status_lbl["text"] = "-"

def populate_locator_dropdown():
    reservations = load_data()
    locs = [r.get("locator", "") for r in reservations if r.get("locator")]
    locator_combo["values"] = sorted(locs)

# ---------------- Actions ----------------
def load_reservation_action():
    locator = ent_res_id.get().strip()
    if not locator:
        locator = locator_combo.get().strip()
    rec = find_reservation_by_locator(locator)
    if not rec:
        return messagebox.showerror("Error", "Reservation not found.")

    # basic fields
    set_entry(ent_res_id, locator)
    set_entry(ent_guest, rec.get("guest_name", ""))
    set_entry(ent_room, rec.get("assigned_room", ""))
    set_entry(ent_mobile, rec.get("phone", ""))

    set_entry(ent_issue_date, datetime.now().strftime("%Y-%m-%d"))
    set_entry(ent_arrival, rec.get("arrive", ""))
    set_entry(ent_departure, rec.get("depart", ""))

    nights = compute_nights(rec.get("arrive", ""), rec.get("depart", ""))
    set_entry(ent_nights, str(nights))
    set_entry(ent_res_type, rec.get("rtype", ""))

    total, paid, balance = compute_totals(rec)
    total_lbl["text"] = f"${total:.2f}"
    paid_lbl["text"] = f"${paid:.2f}"
    bal_lbl["text"] = f"${balance:.2f}"

    status_lbl["text"] = rec.get("status", "Booked") or "Booked"

def preview_bill_action():
    locator = ent_res_id.get().strip() or locator_combo.get().strip()
    rec = find_reservation_by_locator(locator)
    if not rec:
        return messagebox.showerror("Error", "No reservation loaded.")

    total, paid, balance = compute_totals(rec)
    nights = compute_nights(rec.get("arrive", ""), rec.get("depart", ""))

    bill = Bill(
        billId=locator,
        guestName=rec.get("guest_name", ""),
        roomNum=rec.get("assigned_room", ""),
        arrival=rec.get("arrive", ""),
        departure=rec.get("depart", ""),
        nights=nights,
        resType=rec.get("rtype", ""),
        totalAmt=total,
        paidAmt=paid,
        balance=balance
    )

    top = tk.Toplevel(root)
    top.title(f"Bill Preview — {locator}")
    top.geometry("460x460")
    top.transient(root)
    top.grab_set()

    tk.Label(top, text="Bill Preview", font=("Arial", 14, "bold")).pack(pady=(10, 4))
    txt = tk.Text(top, wrap="word", font=("Courier New", 10))
    txt.pack(expand=True, fill="both", padx=10, pady=6)
    txt.insert("1.0", bill.generateBill())
    txt.config(state="disabled")

    btn_frame = tk.Frame(top); btn_frame.pack(pady=8)
    def save_from_preview():
        fname = f"receipt_{locator}.txt"
        with open(fname, "w") as f:
            f.write(bill.generateBill())
        messagebox.showinfo("Saved", f"Saved {fname}")
    tk.Button(btn_frame, text="Save to File", command=save_from_preview).grid(row=0, column=0, padx=6)
    tk.Button(btn_frame, text="Close", command=top.destroy).grid(row=0, column=1, padx=6)

def process_checkout_action():
    locator = ent_res_id.get().strip() or locator_combo.get().strip()
    rec = find_reservation_by_locator(locator)
    if not rec:
        return messagebox.showerror("Error", "No reservation loaded.")

    # Business rules: if Conventional/Incentive with unpaid balance, allow checkout and compute final balance
    total, paid, balance = compute_totals(rec)
    nights = compute_nights(rec.get("arrive", ""), rec.get("depart", ""))

    # Generate and save bill regardless of status; staff can use this as final receipt
    bill = Bill(
        billId=locator,
        guestName=rec.get("guest_name", ""),
        roomNum=rec.get("assigned_room", ""),
        arrival=rec.get("arrive", ""),
        departure=rec.get("depart", ""),
        nights=nights,
        resType=rec.get("rtype", ""),
        totalAmt=total,
        paidAmt=paid,
        balance=balance
    )
    fname = f"receipt_{locator}.txt"
    with open(fname, "w") as f:
        f.write(bill.generateBill())

    messagebox.showinfo("Checkout Complete", f"Bill generated and saved: {fname}")
    clear_form()

# ---------------- UI ----------------
root = tk.Tk()
root.title("Guest Check-Out")
root.geometry("520x720")

tk.Label(root, text="Guest Check-Out", font=("Arial", 16, "bold")).pack(pady=10)

# Load row (typed locator + dropdown)
load_frame = tk.Frame(root); load_frame.pack(pady=5, fill="x")
tk.Label(load_frame, text="Reservation ID:", width=16, anchor="e").grid(row=0, column=0, sticky="e")
ent_res_id = tk.Entry(load_frame, width=14)
ent_res_id.grid(row=0, column=1, padx=6)

tk.Label(load_frame, text="or Select:", width=10, anchor="e").grid(row=0, column=2, sticky="e")
locator_combo = ttk.Combobox(load_frame, state="readonly", width=16)
locator_combo.grid(row=0, column=3, padx=6)
tk.Button(load_frame, text="Load", command=load_reservation_action).grid(row=0, column=4, padx=6)

# Readonly entry builder
def make_entry(label):
    wrap = tk.Frame(root); wrap.pack(anchor="w", padx=10, pady=3, fill="x")
    tk.Label(wrap, text=label, width=18, anchor="w").pack(side="left")
    e = tk.Entry(wrap, state="readonly")
    e.pack(side="left", fill="x", expand=True)
    return e

# Guest info
ent_guest  = make_entry("Guest Name:")
ent_room   = make_entry("Room Number:")
ent_mobile = make_entry("Mobile Number:")

# Bill details
ent_issue_date = make_entry("Bill Issue Date:")
ent_arrival    = make_entry("Arrival Date:")
ent_departure  = make_entry("Departure Date:")
ent_nights     = make_entry("Nights Stayed:")
ent_res_type   = make_entry("Reservation Type:")

# Status row
status_row = tk.Frame(root); status_row.pack(anchor="w", padx=10, pady=(8,2), fill="x")
tk.Label(status_row, text="Reservation Status:", width=18, anchor="w").pack(side="left")
status_lbl = tk.Label(status_row, text="-", font=("Arial", 10, "bold"))
status_lbl.pack(side="left")

# Amounts
def make_amount_row(text, bold=False):
    row = tk.Frame(root); row.pack(anchor="w", padx=10, pady=3, fill="x")
    tk.Label(row, text=text, width=18, anchor="w").pack(side="left")
    lbl = tk.Label(row, text="-", font=("Arial", 11, "bold") if bold else ("Arial", 10))
    lbl.pack(side="left")
    return lbl

total_lbl = make_amount_row("Total:", bold=True)
paid_lbl  = make_amount_row("Paid:")
bal_lbl   = make_amount_row("Balance:", bold=True)

# Buttons
btns = tk.Frame(root); btns.pack(pady=14)
tk.Button(btns, text="Preview Bill", command=preview_bill_action).grid(row=0, column=0, padx=8)
tk.Button(btns, text="Process Checkout", bg="#4CAF50", fg="white", command=process_checkout_action).grid(row=0, column=1, padx=8)

# Populate locator dropdown initially
populate_locator_dropdown()

root.mainloop()