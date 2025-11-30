import json
import os
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime

# Bill class based on your UML diagram
class Bill:
    def __init__(self, billId, guestName, roomNum, arrival, departure, nights, resType, totalAmt):
        self.billId = billId
        self.billIssueDate = datetime.now().strftime("%Y-%m-%d")
        self.billTotalAmt = totalAmt
        self.billGuestName = guestName
        self.billRoomNum = roomNum
        self.billDateArrival = arrival
        self.billDateDeparture = departure
        self.billNightsStayedNum = str(nights)
        self.billResType = resType

    def determineAdvance(self, resType):
        rates = {"Prepaid": 0.75, "60-Day": 0.85, "Conventional": 1.0, "Incentive": 0.8}
        return rates.get(resType, 1.0)

    def generateBill(self):
        return (
            f"Ophelia's Oasis Hotel\n"
            f"-------------------------\n"
            f"Bill ID: {self.billId}\n"
            f"Bill Issue Date: {self.billIssueDate}\n"
            f"Guest Name: {self.billGuestName}\n"
            f"Room Number: {self.billRoomNum}\n"
            f"Arrival Date: {self.billDateArrival}\n"
            f"Departure Date: {self.billDateDeparture}\n"
            f"Nights Stayed: {self.billNightsStayedNum}\n"
            f"Reservation Type: {self.billResType}\n"
            f"Total Amount: ${self.billTotalAmt:.2f}\n"
            f"-------------------------\n"
        )


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
    )
    
    # Create preview window
    top = tk.Toplevel(root)
    top.title(f"Bill Preview – {locator}")
    top.geometry("420x420")
    top.transient(root)
    top.grab_set()
    
    tk.Label(top, text="Bill Preview", font=("Arial", 14, "bold")).pack(pady=(10, 4))
    txt = tk.Text(top, wrap="word", font=("Courier New", 10))
    txt.pack(expand=True, fill="both", padx=10, pady=6)
    txt.insert("1.0", bill.generateBill())
    txt.config(state="disabled")
    
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

# --- UI setup ---
root = tk.Tk()
root.title("Guest Check-Out System")
root.geometry("450x700")

# Global variable to store current reservation
current_reservation = None

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
    lbl.pack(side="left")
    return lbl

total_lbl = make_amount_row("Total Amount:", bold=True)
paid_lbl = make_amount_row("Amount Paid:")
bal_lbl = make_amount_row("Balance Due:", bold=True)

# Separator
tk.Frame(root, height=2, bd=1, relief="sunken").pack(fill="x", padx=20, pady=10)

# Action buttons
btns = tk.Frame(root)
btns.pack(pady=15)
tk.Button(btns, text="Preview Bill", command=preview_bill, width=15).grid(row=0, column=0, padx=6)
tk.Button(btns, text="Process Checkout", bg="#4CAF50", fg="white", 
          command=checkout, width=15).grid(row=0, column=1, padx=6)
tk.Button(btns, text="Clear Form", command=clear_form, width=15).grid(row=1, column=0, columnspan=2, pady=5)

root.mainloop()