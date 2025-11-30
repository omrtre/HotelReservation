import json
import os
import tkinter as tk
<<<<<<< HEAD
from tkinter import messagebox, ttk
=======
from tkinter import ttk, messagebox
>>>>>>> 6253323191cdc802b0e26ebcaa5008ac5dc1220f
from datetime import datetime
import json, os
# the data file is "hrs_data"
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

<<<<<<< HEAD
# Load data from hrs_data.json
DATA_FILE = "hrs_data.json"

def load_state():
    """Load the hotel reservation data from JSON file."""
    if not os.path.exists(DATA_FILE):
        return {"base_rates": {}, "reservations": [], "last_locator": 4000}
    with open(DATA_FILE) as f: 
        return json.load(f)

def save_state(state):
    """Save the updated state back to JSON file."""
    with open(DATA_FILE, "w") as f:
        json.dump(state, f, indent=2)

def load_reservation():
    """Load a reservation from hrs_data.json by locator ID."""
    locator = res_id.get().strip()
    if not locator:
        return messagebox.showerror("Error", "Please enter a reservation locator.")
    
    # Load current data
    state = load_state()
    
    # Find reservation by locator
    reservation = None
    for r in state["reservations"]:
        if r.get("locator", "") == locator:
            reservation = r
            break
    
    if not reservation:
        return messagebox.showerror("Error", f"Reservation '{locator}' not found.")
    
    # Populate form with reservation data
    set_entry(name, reservation.get("guest_name", ""))
    set_entry(room, reservation.get("assigned_room", "Not assigned"))
    set_entry(rtype, reservation.get("rtype", ""))
    set_entry(status_field, reservation.get("status", "Booked"))
    
    # Bill details
    set_entry(bill_issue_date, datetime.now().strftime("%Y-%m-%d"))
    set_entry(bill_arrival, reservation.get("arrive", ""))
    set_entry(bill_departure, reservation.get("depart", ""))
    
    # Calculate nights
    try:
        arrive_date = datetime.strptime(reservation["arrive"], "%Y-%m-%d")
        depart_date = datetime.strptime(reservation["depart"], "%Y-%m-%d")
        nights = (depart_date - arrive_date).days
    except:
        nights = 0
    
    set_entry(bill_nights, str(nights))
    set_entry(bill_res_type, reservation.get("rtype", ""))
    
    # Money calculations
    total = reservation.get("total_locked", 0.0)
    paid = reservation.get("paid_advance", 0.0)
    balance = total - paid
    
    total_lbl["text"] = f"${total:.2f}"
    paid_lbl["text"] = f"${paid:.2f}"
    bal_lbl["text"] = f"${balance:.2f}"
    
    # Store the loaded reservation for later use
    global current_reservation
    current_reservation = reservation

def checkout():
    """Process checkout and update the reservation status."""
    locator = res_id.get().strip()
    if not locator or not current_reservation:
        return messagebox.showerror("Error", "No reservation loaded.")
    
    # Calculate nights and total
    try:
        arrive_date = datetime.strptime(current_reservation["arrive"], "%Y-%m-%d")
        depart_date = datetime.strptime(current_reservation["depart"], "%Y-%m-%d")
        nights = (depart_date - arrive_date).days
    except:
        nights = 0
    
    total = current_reservation.get("total_locked", 0.0)
    
    # Create bill
    bill = Bill(
        billId=locator,
        guestName=current_reservation.get("guest_name", ""),
        roomNum=current_reservation.get("assigned_room", "Not assigned"),
        arrival=current_reservation.get("arrive", ""),
        departure=current_reservation.get("depart", ""),
        nights=nights,
        resType=current_reservation.get("rtype", ""),
        totalAmt=total
    )
    
    # Save receipt to file
    receipt_filename = f"receipt_{locator}.txt"
    with open(receipt_filename, "w") as f:
        f.write(bill.generateBill())
    
    # Update reservation status to Checked-out
    state = load_state()
    for r in state["reservations"]:
        if r.get("locator", "") == locator:
            r["status"] = "Checked-out"
            break
    save_state(state)
    
    messagebox.showinfo("Checkout Complete", 
        f"Bill generated for {current_reservation.get('guest_name', '')} (Locator: {locator}).\n"
        f"Receipt saved as {receipt_filename}\n"
        f"Status updated to Checked-out.")
    
    clear_form()

def preview_bill():
    """Open a Toplevel window with the generated bill preview."""
    locator = res_id.get().strip()
    if not locator or not current_reservation:
        return messagebox.showerror("Error", "No reservation loaded.")
    
    # Calculate nights and total
    try:
        arrive_date = datetime.strptime(current_reservation["arrive"], "%Y-%m-%d")
        depart_date = datetime.strptime(current_reservation["depart"], "%Y-%m-%d")
        nights = (depart_date - arrive_date).days
    except:
        nights = 0
    
    total = current_reservation.get("total_locked", 0.0)
    
    # Create bill
    bill = Bill(
        billId=locator,
        guestName=current_reservation.get("guest_name", ""),
        roomNum=current_reservation.get("assigned_room", "Not assigned"),
        arrival=current_reservation.get("arrive", ""),
        departure=current_reservation.get("depart", ""),
        nights=nights,
        resType=current_reservation.get("rtype", ""),
        totalAmt=total
=======
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
>>>>>>> 6253323191cdc802b0e26ebcaa5008ac5dc1220f
    )
    
    # Create preview window
    top = tk.Toplevel(root)
<<<<<<< HEAD
    top.title(f"Bill Preview – {locator}")
    top.geometry("420x420")
=======
    top.title(f"Bill Preview — {locator}")
    top.geometry("460x460")
>>>>>>> 6253323191cdc802b0e26ebcaa5008ac5dc1220f
    top.transient(root)
    top.grab_set()
    
    tk.Label(top, text="Bill Preview", font=("Arial", 14, "bold")).pack(pady=(10, 4))
    txt = tk.Text(top, wrap="word", font=("Courier New", 10))
    txt.pack(expand=True, fill="both", padx=10, pady=6)
    txt.insert("1.0", bill.generateBill())
    txt.config(state="disabled")
<<<<<<< HEAD
    
    btn_frame = tk.Frame(top)
    btn_frame.pack(pady=8)
    
    def save_from_preview():
        receipt_filename = f"receipt_{locator}.txt"
        with open(receipt_filename, "w") as f:
            f.write(bill.generateBill())
        messagebox.showinfo("Saved", f"Saved {receipt_filename}")
    
    tk.Button(btn_frame, text="Save to File", command=save_from_preview).grid(row=0, column=0, padx=6)
    tk.Button(btn_frame, text="Close", command=top.destroy).grid(row=0, column=1, padx=6)

def show_all_reservations():
    """Show a window with all available reservations for easy selection."""
    state = load_state()
    if not state["reservations"]:
        return messagebox.showinfo("No Reservations", "No reservations found in the system.")
    
    # Create a new window
    list_window = tk.Toplevel(root)
    list_window.title("Select Reservation")
    list_window.geometry("800x400")
    list_window.transient(root)
    list_window.grab_set()
    
    # Create Treeview
    columns = ("Locator", "Guest", "Arrive", "Depart", "Status", "Room")
    tree = ttk.Treeview(list_window, columns=columns, show="headings", height=15)
    
    # Define headings
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=130 if col != "Guest" else 200)
    
    # Add data
    for r in state["reservations"]:
        tree.insert("", "end", values=(
            r.get("locator", ""),
            r.get("guest_name", ""),
            r.get("arrive", ""),
            r.get("depart", ""),
            r.get("status", ""),
            r.get("assigned_room", "Not assigned")
        ))
    
    tree.pack(padx=10, pady=10, fill="both", expand=True)
    
    # Selection handler
    def on_select():
        selected = tree.selection()
        if selected:
            item = tree.item(selected[0])
            locator = item['values'][0]
            res_id.delete(0, tk.END)
            res_id.insert(0, locator)
            list_window.destroy()
            load_reservation()
    
    # Buttons
    btn_frame = tk.Frame(list_window)
    btn_frame.pack(pady=5)
    tk.Button(btn_frame, text="Select", command=on_select).pack(side="left", padx=5)
    tk.Button(btn_frame, text="Cancel", command=list_window.destroy).pack(side="left", padx=5)

def set_entry(entry_widget, value):
    """Helper to set readonly entry value."""
    entry_widget.config(state="normal")
    entry_widget.delete(0, tk.END)
    entry_widget.insert(0, value)
    entry_widget.config(state="readonly")

def clear_form():
    """Clear all form fields."""
    for e in [res_id, name, room, rtype, status_field, bill_issue_date, 
              bill_arrival, bill_departure, bill_nights, bill_res_type]:
        e.config(state="normal")
        e.delete(0, tk.END)
        if e != res_id:  # Keep res_id editable
            e.config(state="readonly")
    for lbl in [total_lbl, paid_lbl, bal_lbl]:
        lbl["text"] = "-"
    global current_reservation
    current_reservation = None
=======

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
>>>>>>> 6253323191cdc802b0e26ebcaa5008ac5dc1220f

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
<<<<<<< HEAD
root.title("Guest Check-Out System")
root.geometry("450x700")
=======
root.title("Guest Check-Out")
root.geometry("520x720")
>>>>>>> 6253323191cdc802b0e26ebcaa5008ac5dc1220f

# Global variable to store current reservation
current_reservation = None

<<<<<<< HEAD
# Title
tk.Label(root, text="Guest Check-Out System", font=("Arial", 16, "bold")).pack(pady=10)

# Load section with browse button
f = tk.Frame(root)
f.pack(pady=5)
tk.Label(f, text="Reservation Locator:").grid(row=0, column=0, sticky="e")
res_id = tk.Entry(f, width=15)
res_id.grid(row=0, column=1, padx=5)
tk.Button(f, text="Load", command=load_reservation).grid(row=0, column=2, padx=2)
tk.Button(f, text="Browse", command=show_all_reservations).grid(row=0, column=3, padx=2)

# Helper to build stacked readonly entries
def make_entry(label_text):
    wrap = tk.Frame(root)
    wrap.pack(anchor="w", padx=20, pady=2, fill="x")
    tk.Label(wrap, text=label_text, width=18, anchor="w").pack(side="left")
    e = tk.Entry(wrap, state="readonly", width=30)
    e.pack(side="left", fill="x", expand=True)
    return e

# Separator
tk.Frame(root, height=2, bd=1, relief="sunken").pack(fill="x", padx=20, pady=10)

# Basic guest info section
tk.Label(root, text="Guest Information", font=("Arial", 12, "bold")).pack(anchor="w", padx=20)
name = make_entry("Guest Name:")
room = make_entry("Room Number:")
rtype = make_entry("Reservation Type:")
status_field = make_entry("Current Status:")

# Separator
tk.Frame(root, height=2, bd=1, relief="sunken").pack(fill="x", padx=20, pady=10)

# Bill details section
tk.Label(root, text="Bill Details", font=("Arial", 12, "bold")).pack(anchor="w", padx=20)
bill_issue_date = make_entry("Bill Issue Date:")
bill_arrival = make_entry("Arrival Date:")
bill_departure = make_entry("Departure Date:")
bill_nights = make_entry("Nights Stayed:")
bill_res_type = make_entry("Reservation Type:")

# Separator
tk.Frame(root, height=2, bd=1, relief="sunken").pack(fill="x", padx=20, pady=10)

# Financial summary section
tk.Label(root, text="Financial Summary", font=("Arial", 12, "bold")).pack(anchor="w", padx=20)

def make_amount_row(text, bold=False):
    row = tk.Frame(root)
    row.pack(anchor="w", padx=20, pady=2, fill="x")
    tk.Label(row, text=text, width=18, anchor="w").pack(side="left")
    lbl = tk.Label(row, text="-", font=("Arial", 11, "bold") if bold else ("Arial", 11))
=======
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
>>>>>>> 6253323191cdc802b0e26ebcaa5008ac5dc1220f
    lbl.pack(side="left")
    return lbl

total_lbl = make_amount_row("Total Amount:", bold=True)
paid_lbl = make_amount_row("Amount Paid:")
bal_lbl = make_amount_row("Balance Due:", bold=True)

<<<<<<< HEAD
# Separator
tk.Frame(root, height=2, bd=1, relief="sunken").pack(fill="x", padx=20, pady=10)

# Action buttons
btns = tk.Frame(root)
btns.pack(pady=15)
tk.Button(btns, text="Preview Bill", command=preview_bill, width=15).grid(row=0, column=0, padx=6)
tk.Button(btns, text="Process Checkout", bg="#4CAF50", fg="white", 
          command=checkout, width=15).grid(row=0, column=1, padx=6)
tk.Button(btns, text="Clear Form", command=clear_form, width=15).grid(row=1, column=0, columnspan=2, pady=5)
=======
# Buttons
btns = tk.Frame(root); btns.pack(pady=14)
tk.Button(btns, text="Preview Bill", command=preview_bill_action).grid(row=0, column=0, padx=8)
tk.Button(btns, text="Process Checkout", bg="#4CAF50", fg="white", command=process_checkout_action).grid(row=0, column=1, padx=8)

# Populate locator dropdown initially
populate_locator_dropdown()
>>>>>>> 6253323191cdc802b0e26ebcaa5008ac5dc1220f

root.mainloop()