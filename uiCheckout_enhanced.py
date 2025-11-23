# uiCheckout_enhanced.py - Enhanced Guest Check-Out Module for HRS
# Handles check-in, check-out, and bill generation

import json
import os
import datetime as dt
import tkinter as tk
from tkinter import ttk, messagebox

from validation import validate_reservation_id, validate_amount

# ============== CONFIGURATION ==============
DATA_FILE = "hrs_data.json"
TODAY = dt.date.today
ISO = dt.date.fromisoformat

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


def find_reservation(state, locator):
    """Find reservation by locator."""
    for r in state["reservations"]:
        if r.get("locator") == locator:
            return r
    return None


# ============== BILL CLASS ==============

class Bill:
    """Bill class for generating guest receipts."""
    
    def __init__(self, reservation):
        self.reservation = reservation
        self.bill_id = reservation.get("locator", "")
        self.bill_issue_date = TODAY().isoformat()
        self.guest_name = reservation.get("guest_name", "")
        self.room_number = reservation.get("assigned_room", "N/A")
        self.arrival = reservation.get("arrive", "")
        self.departure = reservation.get("depart", "")
        self.res_type = reservation.get("rtype", "")
        self.room_type = reservation.get("room_type", "")
        
        # Calculate nights
        try:
            self.nights = (ISO(self.departure) - ISO(self.arrival)).days
        except:
            self.nights = 0
        
        # Get amounts
        self.total_amount = reservation.get("total_locked", 0)
        self.paid_advance = reservation.get("paid_advance", 0)
        self.balance_due = self.total_amount - self.paid_advance
        
        # Get nightly breakdown
        self.nightly_rates = reservation.get("snapshot", {}).get("nightly", {})
    
    def generate_bill(self):
        """Generate formatted bill text."""
        lines = [
            "=" * 50,
            "         OPHELIA'S OASIS HOTEL",
            "        Guest Accommodation Bill",
            "=" * 50,
            "",
            f"Bill ID:           {self.bill_id}",
            f"Bill Date:         {self.bill_issue_date}",
            "",
            "-" * 50,
            "GUEST INFORMATION",
            "-" * 50,
            f"Guest Name:        {self.guest_name}",
            f"Room Number:       {self.room_number}",
            f"Room Type:         {self.room_type}",
            "",
            "-" * 50,
            "STAY DETAILS",
            "-" * 50,
            f"Arrival Date:      {self.arrival}",
            f"Departure Date:    {self.departure}",
            f"Nights Stayed:     {self.nights}",
            f"Reservation Type:  {self.res_type}",
            "",
            "-" * 50,
            "NIGHTLY RATE BREAKDOWN",
            "-" * 50,
        ]
        
        # Add nightly rates
        for date, rate in sorted(self.nightly_rates.items()):
            lines.append(f"  {date}:    ${rate:,.2f}")
        
        lines.extend([
            "",
            "-" * 50,
            "PAYMENT SUMMARY",
            "-" * 50,
            f"Total Amount:      ${self.total_amount:,.2f}",
            f"Paid in Advance:   ${self.paid_advance:,.2f}",
            f"Balance Due:       ${self.balance_due:,.2f}",
            "",
            "=" * 50,
            "     Thank you for staying with us!",
            "        We hope to see you again.",
            "=" * 50,
        ])
        
        return "\n".join(lines)
    
    def save_to_file(self, filename=None):
        """Save bill to file."""
        if filename is None:
            filename = f"receipt_{self.bill_id}.txt"
        
        with open(filename, "w") as f:
            f.write(self.generate_bill())
        
        return filename


# ============== CHECK-IN/OUT APPLICATION ==============

class CheckInOutApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ophelia's Oasis — Check-In / Check-Out")
        self.geometry("900x650")
        self.minsize(800, 600)
        
        self.state_data = load_state()
        self.current_reservation = None
        
        self._build_ui()
        self._refresh_list()
    
    def _build_ui(self):
        """Build the user interface."""
        main = ttk.Frame(self, padding=15)
        main.pack(fill="both", expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)
        
        # Title
        ttk.Label(
            main, text="Guest Check-In / Check-Out",
            font=("Segoe UI", 16, "bold")
        ).grid(row=0, column=0, sticky="w", pady=(0, 15))
        
        # Main content - two columns
        content = ttk.Frame(main)
        content.grid(row=1, column=0, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.columnconfigure(1, weight=1)
        content.rowconfigure(0, weight=1)
        
        # === Left: Reservation List ===
        left = ttk.LabelFrame(content, text="Active Reservations", padding=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left.columnconfigure(0, weight=1)
        left.rowconfigure(1, weight=1)
        
        # Filter
        filter_frame = ttk.Frame(left)
        filter_frame.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        
        ttk.Label(filter_frame, text="Show:").pack(side="left")
        self.filter_var = tk.StringVar(value="Today's Arrivals")
        ttk.Combobox(
            filter_frame, textvariable=self.filter_var,
            values=["Today's Arrivals", "In-House", "Today's Departures", "All Booked"],
            state="readonly", width=18
        ).pack(side="left", padx=5)
        ttk.Button(filter_frame, text="Refresh", command=self._refresh_list).pack(side="left")
        
        # Search
        ttk.Label(filter_frame, text="  Search:").pack(side="left")
        self.search_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.search_var, width=12).pack(side="left", padx=5)
        ttk.Button(filter_frame, text="Find", command=self._refresh_list).pack(side="left")
        
        # Treeview
        cols = ("Locator", "Guest", "Arrive", "Depart", "Status", "Room")
        self.tree = ttk.Treeview(left, columns=cols, show="headings", height=18)
        
        widths = [70, 120, 85, 85, 80, 50]
        for c, w in zip(cols, widths):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor="center")
        
        self.tree.grid(row=1, column=0, sticky="nsew")
        
        # Scrollbar
        ysb = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=ysb.set)
        ysb.grid(row=1, column=1, sticky="ns")
        
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        
        # === Right: Details and Actions ===
        right = ttk.Frame(content)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        
        # Reservation Details
        details = ttk.LabelFrame(right, text="Reservation Details", padding=10)
        details.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        details.columnconfigure(1, weight=1)
        
        # Detail labels
        detail_fields = [
            ("Locator:", "locator"),
            ("Guest Name:", "guest_name"),
            ("Email:", "email"),
            ("Phone:", "phone"),
            ("Room Type:", "room_type"),
            ("Res Type:", "rtype"),
            ("Arrival:", "arrive"),
            ("Departure:", "depart"),
            ("Nights:", "nights"),
            ("Status:", "status"),
            ("Room #:", "assigned_room"),
            ("Total:", "total"),
            ("Paid:", "paid"),
            ("Balance:", "balance"),
        ]
        
        self.detail_vars = {}
        for i, (label, key) in enumerate(detail_fields):
            ttk.Label(details, text=label).grid(row=i, column=0, sticky="w", pady=2)
            var = tk.StringVar(value="—")
            self.detail_vars[key] = var
            ttk.Label(details, textvariable=var, font=("Segoe UI", 10)).grid(
                row=i, column=1, sticky="w", pady=2, padx=(10, 0)
            )
        
        # Room Assignment
        assign_frame = ttk.LabelFrame(right, text="Room Assignment", padding=10)
        assign_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        
        ttk.Label(assign_frame, text="Assign Room #:").pack(side="left")
        self.room_var = tk.StringVar()
        ttk.Entry(assign_frame, textvariable=self.room_var, width=10).pack(side="left", padx=10)
        ttk.Button(assign_frame, text="Assign", command=self._assign_room).pack(side="left")
        
        # Action Buttons
        actions = ttk.LabelFrame(right, text="Actions", padding=10)
        actions.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        
        btn_frame = ttk.Frame(actions)
        btn_frame.pack(fill="x")
        
        ttk.Button(
            btn_frame, text="CHECK IN", 
            command=self._check_in, width=15
        ).pack(side="left", padx=5, pady=5)
        
        ttk.Button(
            btn_frame, text="CHECK OUT",
            command=self._check_out, width=15
        ).pack(side="left", padx=5, pady=5)
        
        ttk.Button(
            btn_frame, text="Mark No-Show",
            command=self._mark_no_show, width=15
        ).pack(side="left", padx=5, pady=5)
        
        # Bill Preview
        bill_frame = ttk.LabelFrame(right, text="Bill Preview", padding=10)
        bill_frame.grid(row=3, column=0, sticky="nsew")
        right.rowconfigure(3, weight=1)
        bill_frame.columnconfigure(0, weight=1)
        bill_frame.rowconfigure(0, weight=1)
        
        self.bill_text = tk.Text(bill_frame, wrap="word", font=("Courier New", 9), height=12)
        self.bill_text.grid(row=0, column=0, sticky="nsew")
        self.bill_text.config(state="disabled")
        
        bill_btn_frame = ttk.Frame(bill_frame)
        bill_btn_frame.grid(row=1, column=0, sticky="e", pady=(5, 0))
        
        ttk.Button(bill_btn_frame, text="Preview Bill", command=self._preview_bill).pack(side="left", padx=5)
        ttk.Button(bill_btn_frame, text="Save Bill", command=self._save_bill).pack(side="left", padx=5)
    
    def _refresh_list(self):
        """Refresh the reservation list."""
        self.state_data = load_state()
        
        # Clear tree
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        today = TODAY().isoformat()
        filter_val = self.filter_var.get()
        search = self.search_var.get().strip().lower()
        
        for r in self.state_data["reservations"]:
            # Apply search filter
            if search:
                if search not in r.get("guest_name", "").lower() and \
                   search not in r.get("locator", "").lower():
                    continue
            
            # Apply status filter
            status = r.get("status", "Booked")
            arrive = r.get("arrive", "")
            depart = r.get("depart", "")
            
            if filter_val == "Today's Arrivals":
                if arrive != today or status not in ("Booked",):
                    continue
            elif filter_val == "In-House":
                if status != "In-House":
                    continue
            elif filter_val == "Today's Departures":
                if depart != today or status != "In-House":
                    continue
            elif filter_val == "All Booked":
                if status not in ("Booked", "In-House"):
                    continue
            
            self.tree.insert("", "end", iid=r["locator"], values=(
                r.get("locator", ""),
                r.get("guest_name", ""),
                r.get("arrive", ""),
                r.get("depart", ""),
                r.get("status", ""),
                r.get("assigned_room", "")
            ))
    
    def _on_select(self, _evt=None):
        """Handle reservation selection."""
        sel = self.tree.selection()
        if not sel:
            return
        
        locator = sel[0]
        self.current_reservation = find_reservation(self.state_data, locator)
        
        if not self.current_reservation:
            return
        
        r = self.current_reservation
        
        # Update detail vars
        self.detail_vars["locator"].set(r.get("locator", "—"))
        self.detail_vars["guest_name"].set(r.get("guest_name", "—"))
        self.detail_vars["email"].set(r.get("email", "—"))
        self.detail_vars["phone"].set(r.get("phone", "—"))
        self.detail_vars["room_type"].set(r.get("room_type", "—"))
        self.detail_vars["rtype"].set(r.get("rtype", "—"))
        self.detail_vars["arrive"].set(r.get("arrive", "—"))
        self.detail_vars["depart"].set(r.get("depart", "—"))
        self.detail_vars["status"].set(r.get("status", "—"))
        self.detail_vars["assigned_room"].set(r.get("assigned_room", "—") or "Not Assigned")
        
        # Calculate nights
        try:
            nights = (ISO(r["depart"]) - ISO(r["arrive"])).days
        except:
            nights = 0
        self.detail_vars["nights"].set(str(nights))
        
        # Calculate amounts
        total = r.get("total_locked", 0)
        paid = r.get("paid_advance", 0)
        balance = total - paid
        
        self.detail_vars["total"].set(f"${total:,.2f}")
        self.detail_vars["paid"].set(f"${paid:,.2f}")
        self.detail_vars["balance"].set(f"${balance:,.2f}")
        
        # Set room var
        self.room_var.set(r.get("assigned_room", ""))
        
        # Clear bill preview
        self.bill_text.config(state="normal")
        self.bill_text.delete("1.0", "end")
        self.bill_text.config(state="disabled")
    
    def _assign_room(self):
        """Assign a room to the reservation."""
        if not self.current_reservation:
            messagebox.showwarning("Warning", "Select a reservation first.")
            return
        
        room = self.room_var.get().strip()
        if not room:
            messagebox.showwarning("Warning", "Enter a room number.")
            return
        
        locator = self.current_reservation["locator"]
        
        for r in self.state_data["reservations"]:
            if r.get("locator") == locator:
                r["assigned_room"] = room
                save_state(self.state_data)
                self._refresh_list()
                self.detail_vars["assigned_room"].set(room)
                messagebox.showinfo("Success", f"Room {room} assigned to {locator}.")
                return
    
    def _check_in(self):
        """Check in the guest."""
        if not self.current_reservation:
            messagebox.showwarning("Warning", "Select a reservation first.")
            return
        
        r = self.current_reservation
        
        if r.get("status") != "Booked":
            messagebox.showwarning("Warning", f"Cannot check in. Current status: {r.get('status')}")
            return
        
        if not r.get("assigned_room"):
            messagebox.showwarning("Warning", "Please assign a room first.")
            return
        
        locator = r["locator"]
        
        for res in self.state_data["reservations"]:
            if res.get("locator") == locator:
                res["status"] = "In-House"
                res["check_in_date"] = TODAY().isoformat()
                res["check_in_time"] = dt.datetime.now().strftime("%H:%M:%S")
                save_state(self.state_data)
                self._refresh_list()
                self.detail_vars["status"].set("In-House")
                messagebox.showinfo("Success", f"Guest {r.get('guest_name')} checked in to room {r.get('assigned_room')}.")
                return
    
    def _check_out(self):
        """Check out the guest."""
        if not self.current_reservation:
            messagebox.showwarning("Warning", "Select a reservation first.")
            return
        
        r = self.current_reservation
        
        if r.get("status") != "In-House":
            messagebox.showwarning("Warning", f"Cannot check out. Current status: {r.get('status')}")
            return
        
        locator = r["locator"]
        
        # Calculate balance
        total = r.get("total_locked", 0)
        paid = r.get("paid_advance", 0)
        balance = total - paid
        
        if balance > 0:
            if not messagebox.askyesno(
                "Balance Due",
                f"Balance due: ${balance:,.2f}\n\nConfirm payment received and check out?"
            ):
                return
        
        for res in self.state_data["reservations"]:
            if res.get("locator") == locator:
                res["status"] = "Checked-out"
                res["check_out_date"] = TODAY().isoformat()
                res["check_out_time"] = dt.datetime.now().strftime("%H:%M:%S")
                res["paid_at_checkout"] = balance
                res["final_paid"] = total
                save_state(self.state_data)
                
                # Generate and save bill
                bill = Bill(res)
                filename = bill.save_to_file()
                
                self._refresh_list()
                self.detail_vars["status"].set("Checked-out")
                
                messagebox.showinfo(
                    "Success",
                    f"Guest {r.get('guest_name')} checked out.\nBill saved to: {filename}"
                )
                
                # Show bill
                self._preview_bill()
                return
    
    def _mark_no_show(self):
        """Mark reservation as no-show."""
        if not self.current_reservation:
            messagebox.showwarning("Warning", "Select a reservation first.")
            return
        
        r = self.current_reservation
        
        if r.get("status") != "Booked":
            messagebox.showwarning("Warning", f"Cannot mark no-show. Current status: {r.get('status')}")
            return
        
        if not messagebox.askyesno("Confirm", f"Mark reservation {r.get('locator')} as No-Show?"):
            return
        
        locator = r["locator"]
        
        for res in self.state_data["reservations"]:
            if res.get("locator") == locator:
                res["status"] = "No-Show"
                res["no_show_date"] = TODAY().isoformat()
                
                # Calculate no-show fee based on type
                rtype = res.get("rtype", "")
                nightly = res.get("snapshot", {}).get("nightly", {})
                
                if rtype in ("Conventional", "Incentive"):
                    # First night charge
                    if nightly:
                        first_night = list(nightly.values())[0]
                        res["no_show_fee"] = first_night
                    else:
                        res["no_show_fee"] = 0
                elif rtype in ("Prepaid", "60-Day"):
                    # Full amount (already paid)
                    res["no_show_fee"] = res.get("total_locked", 0)
                
                save_state(self.state_data)
                self._refresh_list()
                self.detail_vars["status"].set("No-Show")
                
                fee = res.get("no_show_fee", 0)
                messagebox.showinfo("No-Show", f"Reservation marked as No-Show.\nNo-show fee: ${fee:,.2f}")
                return
    
    def _preview_bill(self):
        """Preview the bill."""
        if not self.current_reservation:
            messagebox.showwarning("Warning", "Select a reservation first.")
            return
        
        bill = Bill(self.current_reservation)
        bill_text = bill.generate_bill()
        
        self.bill_text.config(state="normal")
        self.bill_text.delete("1.0", "end")
        self.bill_text.insert("1.0", bill_text)
        self.bill_text.config(state="disabled")
    
    def _save_bill(self):
        """Save the bill to file."""
        if not self.current_reservation:
            messagebox.showwarning("Warning", "Select a reservation first.")
            return
        
        bill = Bill(self.current_reservation)
        filename = bill.save_to_file()
        
        messagebox.showinfo("Saved", f"Bill saved to: {filename}")


# ============== MAIN ==============

if __name__ == "__main__":
    app = CheckInOutApp()
    app.mainloop()
