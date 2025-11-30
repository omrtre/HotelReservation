import sys
import subprocess
import tkinter as tk
from tkinter import PhotoImage, ttk, messagebox
from pathlib import Path

BASE = Path(__file__).resolve().parent


def moduleRun(filename):
	"""Run a UI module in a separate Python process.

	Running in a subprocess avoids creating multiple `tk.Tk()` instances
	in the same interpreter (each module creates its own Tk root).
	"""
	path = BASE / filename
	if not path.exists():
		messagebox.showerror("Error", f"Module not found: {path}")
		return
	try:
		subprocess.Popen([sys.executable, str(path)])
	except Exception as e:
		messagebox.showerror("Error", f"Failed to launch {filename}: {e}")


def moduleLanucher():
	root = tk.Tk()
	root.title("Hotel Reservation Booking System")
	root.geometry("900x600")
	root.resizable(False, False)

	frm = ttk.Frame(root, padding=16)
	frm.pack(expand=True, fill="both")

	ttk.Label(frm, text="Welcome to Ophelia's Oasis!", font=("Segoe UI", 14, "bold")).pack(pady=(0,12))

	btn_frame = ttk.Frame(frm)
	btn_frame.pack(fill="x", pady=6)

	# Load and display an image 
	root.imgBanner = PhotoImage(file=BASE / "bannerHotel.png")

	# Create a label to display the image
	image_label = tk.Label(frm, image=root.imgBanner)
	image_label.pack()

	ttk.Label(btn_frame, text="📅 Check In").pack()
	ttk.Button(btn_frame, text="Make a Reservation", width=28, command=lambda: moduleRun("uiMakeReservation.py")).pack(pady=6)
	
	ttk.Label(btn_frame, text="📄 View Reports").pack()
	ttk.Button(btn_frame, text="View Report System", width=28, command=lambda: moduleRun("uiReportSystem.py")).pack(pady=6)

	ttk.Label(btn_frame, text="🧾 Check Out").pack()
	ttk.Button(btn_frame, text="Generate a Reciept", width=28, command=lambda: moduleRun("uiReceiptPrompt.py")).pack(pady=6)

	ttk.Separator(frm, orient="horizontal").pack(fill="x", pady=(10,8))
	ttk.Button(frm, text="Quit", command=root.destroy).pack(side="bottom")

	return root


if __name__ == "__main__":
	app = moduleLanucher()
	app.mainloop()

