# uiLogin.py - Staff Authentication Module for HRS
# Handles user login with file-based credential verification

import tkinter as tk
from tkinter import ttk, messagebox
import os
import hashlib
from validation import validate_user_number, validate_password

# ============== CONFIGURATION ==============
USERS_FILE = "users.txt"
DEFAULT_USERS = [
    ("1234567", "password1", "Admin", "Administrator"),
    ("2345678", "password2", "Staff", "Front Desk"),
    ("3456789", "password3", "Manager", "Hotel Manager"),
]

# ============== USER MANAGEMENT ==============

def initialize_users_file():
    """Create default users file if it doesn't exist."""
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            f.write("# HRS Users File\n")
            f.write("# Format: user_number|password|name|role\n")
            for user_num, pwd, name, role in DEFAULT_USERS:
                f.write(f"{user_num}|{pwd}|{name}|{role}\n")
        return True
    return False


def load_users():
    """
    Load users from file.
    Returns: dict of {user_number: {'password': str, 'name': str, 'role': str}}
    """
    users = {}
    
    if not os.path.exists(USERS_FILE):
        return None  # File doesn't exist
    
    try:
        with open(USERS_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                parts = line.split('|')
                if len(parts) >= 2:
                    user_num = parts[0].strip()
                    password = parts[1].strip()
                    name = parts[2].strip() if len(parts) > 2 else "User"
                    role = parts[3].strip() if len(parts) > 3 else "Staff"
                    users[user_num] = {
                        'password': password,
                        'name': name,
                        'role': role
                    }
        return users
    except Exception as e:
        print(f"Error loading users: {e}")
        return None


def verify_user(user_number, password):
    """
    Verify user credentials.
    Returns: (success: bool, message: str, user_info: dict or None)
    """
    # Validate user number format
    is_valid, error = validate_user_number(user_number)
    if not is_valid:
        return False, error, None
    
    # Validate password not empty
    is_valid, error = validate_password(password)
    if not is_valid:
        return False, error, None
    
    # Load users from file
    users = load_users()
    
    if users is None:
        return False, "User file does not exist. Please contact administrator.", None
    
    # Check if user exists
    if user_number not in users:
        return False, "User number not found in system.", None
    
    # Verify password
    user = users[user_number]
    if user['password'] != password:
        return False, "Invalid password.", None
    
    return True, "Login successful.", user


# ============== LOGIN APPLICATION ==============

class LoginApp(tk.Tk):
    def __init__(self, on_success_callback=None):
        super().__init__()
        self.title("Ophelia's Oasis — Staff Login")
        self.geometry("400x350")
        self.resizable(False, False)
        
        self.on_success_callback = on_success_callback
        self.logged_in_user = None
        
        # Initialize users file if needed
        if initialize_users_file():
            print("Created default users file.")
        
        self._create_ui()
        
        # Center window
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def _create_ui(self):
        # Main frame
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_lbl = ttk.Label(
            main_frame, 
            text="🏨 Ophelia's Oasis", 
            font=("Segoe UI", 18, "bold")
        )
        title_lbl.pack(pady=(0, 5))
        
        subtitle_lbl = ttk.Label(
            main_frame,
            text="Hotel Reservation System",
            font=("Segoe UI", 11)
        )
        subtitle_lbl.pack(pady=(0, 20))
        
        # Login frame
        login_frame = ttk.LabelFrame(main_frame, text="Staff Login", padding=15)
        login_frame.pack(fill="x", padx=20)
        
        # User Number
        ttk.Label(login_frame, text="User Number (7 digits):").grid(
            row=0, column=0, sticky="w", pady=5
        )
        self.user_num_var = tk.StringVar()
        self.user_num_entry = ttk.Entry(
            login_frame, 
            textvariable=self.user_num_var,
            width=25
        )
        self.user_num_entry.grid(row=0, column=1, pady=5, padx=(10, 0))
        self.user_num_entry.focus()
        
        # Password
        ttk.Label(login_frame, text="Password:").grid(
            row=1, column=0, sticky="w", pady=5
        )
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(
            login_frame,
            textvariable=self.password_var,
            show="*",
            width=25
        )
        self.password_entry.grid(row=1, column=1, pady=5, padx=(10, 0))
        
        # Bind Enter key
        self.user_num_entry.bind('<Return>', lambda e: self.password_entry.focus())
        self.password_entry.bind('<Return>', lambda e: self._on_login())
        
        # Error label
        self.error_var = tk.StringVar()
        self.error_lbl = ttk.Label(
            main_frame,
            textvariable=self.error_var,
            foreground="red",
            wraplength=300
        )
        self.error_lbl.pack(pady=(10, 0))
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=20)
        
        login_btn = ttk.Button(
            btn_frame,
            text="Login",
            command=self._on_login,
            width=15
        )
        login_btn.grid(row=0, column=0, padx=5)
        
        exit_btn = ttk.Button(
            btn_frame,
            text="Exit",
            command=self.destroy,
            width=15
        )
        exit_btn.grid(row=0, column=1, padx=5)
        
        # Info label
        info_lbl = ttk.Label(
            main_frame,
            text="Default: 1234567 / password1",
            font=("Segoe UI", 9),
            foreground="gray"
        )
        info_lbl.pack(side="bottom")
    
    def _on_login(self):
        """Handle login button click."""
        self.error_var.set("")
        
        user_num = self.user_num_var.get().strip()
        password = self.password_var.get()
        
        # Verify credentials
        success, message, user_info = verify_user(user_num, password)
        
        if success:
            self.logged_in_user = {
                'user_number': user_num,
                **user_info
            }
            
            messagebox.showinfo(
                "Welcome",
                f"Welcome, {user_info['name']}!\nRole: {user_info['role']}"
            )
            
            if self.on_success_callback:
                self.withdraw()  # Hide login window
                self.on_success_callback(self.logged_in_user)
            else:
                self.destroy()
        else:
            self.error_var.set(message)
            # Clear password on failure
            self.password_var.set("")
            self.password_entry.focus()
    
    def get_logged_in_user(self):
        """Return the logged in user info."""
        return self.logged_in_user


# ============== STANDALONE LAUNCHER ==============

def launch_main_app(user_info):
    """Launch the main reservation app after successful login."""
    print(f"Launching main app for user: {user_info['name']}")
    
    # Import and launch main reservation app
    try:
        from uiMakeReservation_enhanced import ReservationApp
        app = ReservationApp(user_info=user_info)
        app.mainloop()
    except ImportError:
        # Fallback to original
        try:
            from uiMakeReservation import ReservationApp
            app = ReservationApp()
            app.mainloop()
        except ImportError:
            messagebox.showinfo("Info", f"Logged in as {user_info['name']}")


if __name__ == "__main__":
    app = LoginApp(on_success_callback=launch_main_app)
    app.mainloop()
