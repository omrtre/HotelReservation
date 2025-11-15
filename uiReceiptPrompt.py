import tkinter as tk
from tkinter import messagebox
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


# Sample reservation data
reservations = {
    "1001": {
        "guest": "Ava Thompson",
        "room": "205",
        "in": "2025-10-15",
        "out": "2025-10-20",
        "rate": 150,
        "paid": 300,
        "type": "Conventional",
    }
}

def load_reservation():
    rid = res_id.get().strip()
    if rid not in reservations:
        return messagebox.showerror("Error", "Reservation not found.")
    r = reservations[rid]

    # Basic fields
    set_entry(name, r["guest"])
    set_entry(room, r["room"])
    set_entry(rtype, r["type"])

    # Bill details
    set_entry(bill_issue_date, datetime.now().strftime("%Y-%m-%d"))
    set_entry(bill_arrival, r["in"])
    set_entry(bill_departure, r["out"])
    nights = (datetime.strptime(r["out"], "%Y-%m-%d") - datetime.strptime(r["in"], "%Y-%m-%d")).days
    set_entry(bill_nights, str(nights))
    set_entry(bill_res_type, r["type"])

    # Money
    total = nights * r["rate"]
    total_lbl["text"] = f"${total:.2f}"
    paid_lbl["text"] = f"${r['paid']:.2f}"
    bal_lbl["text"] = f"${total - r['paid']:.2f}"

def checkout():
    rid = res_id.get().strip()
    if rid not in reservations:
        return messagebox.showerror("Error", "No reservation loaded.")
    r = reservations[rid]
    nights = (datetime.strptime(r["out"], "%Y-%m-%d") - datetime.strptime(r["in"], "%Y-%m-%d")).days
    total = nights * r["rate"]

    bill = Bill(
        billId=rid,
        guestName=r["guest"],
        roomNum=r["room"],
        arrival=r["in"],
        departure=r["out"],
        nights=nights,
        resType=r["type"],
        totalAmt=total
    )

    with open(f"receipt_{rid}.txt", "w") as f:
        f.write(bill.generateBill())

    messagebox.showinfo("Checkout Complete", f"Bill generated for {r['guest']} (ID: {rid}).")
    clear_form()

def preview_bill():
    """Open a Toplevel window with the generated bill preview."""
    rid = res_id.get().strip()
    if rid not in reservations:
        return messagebox.showerror("Error", "No reservation loaded.")
    r = reservations[rid]
    nights = (datetime.strptime(r["out"], "%Y-%m-%d") - datetime.strptime(r["in"], "%Y-%m-%d")).days
    total = nights * r["rate"]

    bill = Bill(
        billId=rid,
        guestName=r["guest"],
        roomNum=r["room"],
        arrival=r["in"],
        departure=r["out"],
        nights=nights,
        resType=r["type"],
        totalAmt=total
    )

    top = tk.Toplevel(root)
    top.title(f"Bill Preview — {rid}")
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
        with open(f"receipt_{rid}.txt", "w") as f:
            f.write(bill.generateBill())
        messagebox.showinfo("Saved", f"Saved receipt_{rid}.txt")

    tk.Button(btn_frame, text="Save to File", command=save_from_preview).grid(row=0, column=0, padx=6)
    tk.Button(btn_frame, text="Close", command=top.destroy).grid(row=0, column=1, padx=6)

def set_entry(entry_widget, value):
    entry_widget.config(state="normal")
    entry_widget.delete(0, tk.END)
    entry_widget.insert(0, value)
    entry_widget.config(state="readonly")

def clear_form():
    for e in [res_id, name, room, rtype, bill_issue_date, bill_arrival, bill_departure, bill_nights, bill_res_type]:
        e.config(state="normal"); e.delete(0, tk.END); e.config(state="readonly")
    for lbl in [total_lbl, paid_lbl, bal_lbl]:
        lbl["text"] = "-"

# --- UI setup ---
root = tk.Tk()
root.title("Guest Check-Out")
root.geometry("420x640")

tk.Label(root, text="Guest Check-Out", font=("Arial", 16, "bold")).pack(pady=10)

# Load row
f = tk.Frame(root); f.pack(pady=5)
tk.Label(f, text="Reservation ID:").grid(row=0, column=0, sticky="e")
res_id = tk.Entry(f, width=12); res_id.grid(row=0, column=1, padx=5)
tk.Button(f, text="Load", command=load_reservation).grid(row=0, column=2, padx=5)

# Helper to build stacked readonly entries
def make_entry(label_text):
    wrap = tk.Frame(root); wrap.pack(anchor="w", padx=10, pady=2, fill="x")
    tk.Label(wrap, text=label_text, width=18, anchor="w").pack(side="left")
    e = tk.Entry(wrap, state="readonly")
    e.pack(side="left", fill="x", expand=True)
    return e

# Basic guest info
name  = make_entry("Guest Name:")
room  = make_entry("Room Number:")
rtype = make_entry("Type:")

# Bill details (new)
bill_issue_date = make_entry("Bill Issue Date:")
bill_arrival     = make_entry("Arrival Date:")
bill_departure   = make_entry("Departure Date:")
bill_nights      = make_entry("Nights Stayed:")
bill_res_type    = make_entry("Reservation Type:")

# Amounts
amt_frame = tk.Frame(root); amt_frame.pack(anchor="w", padx=10, pady=(8,2), fill="x")
def make_amount_row(text, bold=False):
    row = tk.Frame(root); row.pack(anchor="w", padx=10, pady=2, fill="x")
    tk.Label(row, text=text, width=18, anchor="w").pack(side="left")
    lbl = tk.Label(row, text="-", font=("Arial", 10, "bold") if bold else ("Arial", 10))
    lbl.pack(side="left")
    return lbl

total_lbl = make_amount_row("Total:", bold=True)
paid_lbl  = make_amount_row("Paid:")
bal_lbl   = make_amount_row("Balance:", bold=True)

# Buttons
btns = tk.Frame(root); btns.pack(pady=12)
tk.Button(btns, text="Preview Bill", command=preview_bill).grid(row=0, column=0, padx=6)
tk.Button(btns, text="Process Checkout", bg="#4CAF50", fg="white", command=checkout).grid(row=0, column=1, padx=6)

root.mainloop()
