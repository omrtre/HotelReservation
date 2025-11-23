# main.py - Main Launcher for Ophelia's Oasis Hotel Reservation System
# Integrates all modules with login authentication

import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys

# ============== CONFIGURATION ==============
USERS_FILE = "users.txt"

# ============== MAIN LAUNCHER ==============

class MainLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Ophelia's Oasis — Hotel Reservation System")
        self.geometry("500x450")
        self.resizable(False, False)
        
        self.logged_in_user = None
        
        self._create_login_ui()
        
        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def _create_login_ui(self):
        """Create the login interface."""
        # Main frame
        main = ttk.Frame(self, padding=30)
        main.pack(fill="both", expand=True)
        
        # Title
        ttk.Label(
            main, text="🏨 Ophelia's Oasis",
            font=("Segoe UI", 22, "bold")
        ).pack(pady=(0, 5))
        
        ttk.Label(
            main, text="Hotel Reservation System",
            font=("Segoe UI", 12)
        ).pack(pady=(0, 20))
        
        # Login Frame
        login = ttk.LabelFrame(main, text="Staff Login", padding=20)
        login.pack(fill="x", pady=10)
        
        # User Number
        ttk.Label(login, text="User Number (7 digits):").grid(row=0, column=0, sticky="w", pady=8)
        self.user_var = tk.StringVar()
        self.user_entry = ttk.Entry(login, textvariable=self.user_var, width=20)
        self.user_entry.grid(row=0, column=1, pady=8, padx=(10, 0))
        self.user_entry.focus()
        
        # Password
        ttk.Label(login, text="Password:").grid(row=1, column=0, sticky="w", pady=8)
        self.pass_var = tk.StringVar()
        self.pass_entry = ttk.Entry(login, textvariable=self.pass_var, show="*", width=20)
        self.pass_entry.grid(row=1, column=1, pady=8, padx=(10, 0))
        
        # Bind Enter
        self.user_entry.bind('<Return>', lambda e: self.pass_entry.focus())
        self.pass_entry.bind('<Return>', lambda e: self._login())
        
        # Error label
        self.error_var = tk.StringVar()
        ttk.Label(main, textvariable=self.error_var, foreground="red").pack(pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(pady=15)
        
        ttk.Button(btn_frame, text="Login", command=self._login, width=12).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Exit", command=self.destroy, width=12).pack(side="left", padx=5)
        
        # Default credentials info
        ttk.Label(
            main, text="Default: 1234567 / password1",
            font=("Segoe UI", 9), foreground="gray"
        ).pack(side="bottom", pady=5)
        
        # Initialize users file
        self._init_users()
    
    def _init_users(self):
        """Initialize users file if it doesn't exist."""
        if not os.path.exists(USERS_FILE):
            with open(USERS_FILE, 'w') as f:
                f.write("# HRS Users File - Format: user_number|password|name|role\n")
                f.write("1234567|password1|Admin User|Administrator\n")
                f.write("2345678|password2|Front Desk|Staff\n")
                f.write("3456789|password3|Hotel Manager|Manager\n")
    
    def _login(self):
        """Handle login."""
        self.error_var.set("")
        
        user_num = self.user_var.get().strip()
        password = self.pass_var.get()
        
        # Validate
        if not user_num:
            self.error_var.set("User number is required.")
            return
        
        if not user_num.isdigit() or len(user_num) != 7:
            self.error_var.set("User number must be exactly 7 digits.")
            return
        
        if not password:
            self.error_var.set("Password is required.")
            return
        
        # Check credentials
        if not os.path.exists(USERS_FILE):
            self.error_var.set("User file does not exist.")
            return
        
        user_info = None
        with open(USERS_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('|')
                if len(parts) >= 2 and parts[0] == user_num:
                    if parts[1] == password:
                        user_info = {
                            'user_number': parts[0],
                            'name': parts[2] if len(parts) > 2 else "User",
                            'role': parts[3] if len(parts) > 3 else "Staff"
                        }
                    break
        
        if not user_info:
            self.error_var.set("Invalid user number or password.")
            self.pass_var.set("")
            return
        
        self.logged_in_user = user_info
        self._show_main_menu()
    
    def _show_main_menu(self):
        """Show the main menu after login."""
        # Clear login UI
        for widget in self.winfo_children():
            widget.destroy()
        
        # Resize window
        self.geometry("450x500")
        
        # Main frame
        main = ttk.Frame(self, padding=20)
        main.pack(fill="both", expand=True)
        
        # Header
        header = ttk.Frame(main)
        header.pack(fill="x", pady=(0, 20))
        
        ttk.Label(
            header, text="🏨 Ophelia's Oasis",
            font=("Segoe UI", 18, "bold")
        ).pack(side="left")
        
        user_frame = ttk.Frame(header)
        user_frame.pack(side="right")
        ttk.Label(
            user_frame, text=f"Welcome, {self.logged_in_user['name']}",
            font=("Segoe UI", 10)
        ).pack()
        ttk.Label(
            user_frame, text=f"Role: {self.logged_in_user['role']}",
            font=("Segoe UI", 9), foreground="gray"
        ).pack()
        
        ttk.Separator(main, orient="horizontal").pack(fill="x", pady=10)
        
        # Menu Label
        ttk.Label(
            main, text="Main Menu",
            font=("Segoe UI", 14, "bold")
        ).pack(pady=(10, 20))
        
        # Menu Buttons
        btn_style = {"width": 30}
        
        ttk.Button(
            main, text=" Make Reservation",
            command=self._open_reservation, **btn_style
        ).pack(pady=8)
        
        ttk.Button(
            main, text=" Check-In / Check-Out",
            command=self._open_checkinout, **btn_style
        ).pack(pady=8)
        
        ttk.Button(
            main, text=" Base Rate Management",
            command=self._open_baserates, **btn_style
        ).pack(pady=8)
        
        ttk.Button(
            main, text=" Reports",
            command=self._open_reports, **btn_style
        ).pack(pady=8)
        
        ttk.Separator(main, orient="horizontal").pack(fill="x", pady=20)
        
        # Bottom buttons
        bottom = ttk.Frame(main)
        bottom.pack(fill="x")
        
        ttk.Button(
            bottom, text="Logout",
            command=self._logout, width=12
        ).pack(side="left")
        
        ttk.Button(
            bottom, text="Exit",
            command=self.destroy, width=12
        ).pack(side="right")
    
    def _open_reservation(self):
        """Open reservation module."""
        try:
            from uiMakeReservation_enhanced import ReservationApp
            self.withdraw()
            app = tk.Toplevel(self)
            app.title("Ophelia's Oasis — Reservations")
            
            # Import and embed
            res_app = ReservationApp.__new__(ReservationApp)
            res_app.user_info = self.logged_in_user
            
            # Recreate as toplevel
            self.withdraw()
            new_app = ReservationApp(user_info=self.logged_in_user)
            new_app.protocol("WM_DELETE_WINDOW", lambda: self._on_child_close(new_app))
            
        except ImportError as e:
            messagebox.showerror("Error", f"Could not load Reservation module: {e}")
            self.deiconify()
    
    def _open_checkinout(self):
        """Open check-in/out module."""
        try:
            from uiCheckout_enhanced import CheckInOutApp
            self.withdraw()
            app = CheckInOutApp()
            app.protocol("WM_DELETE_WINDOW", lambda: self._on_child_close(app))
        except ImportError as e:
            messagebox.showerror("Error", f"Could not load Check-In/Out module: {e}")
            self.deiconify()
    
    def _open_baserates(self):
        """Open base rates module."""
        try:
            from uiBaseRates import BaseRateApp
            self.withdraw()
            app = BaseRateApp()
            app.protocol("WM_DELETE_WINDOW", lambda: self._on_child_close(app))
        except ImportError as e:
            messagebox.showerror("Error", f"Could not load Base Rates module: {e}")
            self.deiconify()
    
    def _open_reports(self):
        """Open reports module."""
        try:
            from uiReportSystem_enhanced import ReportApp
            self.withdraw()
            app = ReportApp()
            app.protocol("WM_DELETE_WINDOW", lambda: self._on_child_close(app))
        except ImportError as e:
            messagebox.showerror("Error", f"Could not load Reports module: {e}")
            self.deiconify()
    
    def _on_child_close(self, child):
        """Handle child window closing."""
        child.destroy()
        self.deiconify()
    
    def _logout(self):
        """Logout and return to login screen."""
        self.logged_in_user = None
        for widget in self.winfo_children():
            widget.destroy()
        self.geometry("500x450")
        self._create_login_ui()


# ============== MAIN ==============

if __name__ == "__main__":
    app = MainLauncher()
    app.mainloop()
