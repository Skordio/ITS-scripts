"""Simple Tkinter GUI to compute absolute difference between two military times.

Usage: run this file with Python 3. No external dependencies required.

Times may be entered as HHMM or HH:MM (24-hour / military time). Output
is always a positive duration shown as H hours M minutes and total minutes.
"""

import re
import sys
import tkinter as tk
from tkinter import messagebox


def parse_time(s: str):
	"""Parse a military time string and return minutes since midnight.

	Accepts formats like 'HHMM' or 'HH:MM'. Raises ValueError on invalid.
	"""
	if not s:
		raise ValueError("Empty time")
	if s == "0":
		return 0

	s = s.strip()
	m = re.fullmatch(r"(\d{1,2}):(\d{2})", s)
	if m:
		hh = int(m.group(1))
		mm = int(m.group(2))
	else:
		# Accept 'HHMM' or 'HMM' as well
		if not re.fullmatch(r"\d{3,4}", s) or s == "0":
			raise ValueError(f"Invalid time format: {s}")
		if len(s) == 3:
			hh = int(s[0])
			mm = int(s[1:])
		else:
			hh = int(s[:2])
			mm = int(s[2:])

	if not (0 <= hh <= 23 and 0 <= mm <= 59):
		raise ValueError(f"Hour/minute out of range: {s}")

	return hh * 60 + mm


def format_duration(total_minutes: int):
	h = total_minutes // 60
	m = total_minutes % 60
	parts = []
	if h:
		parts.append(f"{h} hour" + ("s" if h != 1 else ""))
	if m or not parts:
		parts.append(f"{m} minute" + ("s" if m != 1 else ""))
	return ", ".join(parts)


class TimeDiffApp(tk.Tk):
	def __init__(self):
		super().__init__()
		self.title("Time Difference Calculator")
		self.resizable(False, False)

		frm = tk.Frame(self, padx=10, pady=10)
		frm.pack()

		# self.helpmsg = tk.Label(frm, text="Time A is the earlier time, and Time B is the later time. \nThe calculator will not work properly otherwise.", fg="#8ecaff", bg="#1e1e1e", font=("Arial", 9, "bold")).grid(row=0, column=0, sticky="w")

		tk.Label(frm, text="Start Time (HHMM or HH:MM):").grid(row=1, column=0, sticky="w")
		self.a_entry = tk.Entry(frm, width=12)
		self.a_entry.grid(row=1, column=1, padx=6, pady=4)

		tk.Label(frm, text="End Time (HHMM or HH:MM):").grid(row=2, column=0, sticky="w")
		self.b_entry = tk.Entry(frm, width=12)
		self.b_entry.grid(row=2, column=1, padx=6, pady=4)

		calc_btn = tk.Button(frm, text="Calculate", width=12, command=self.calculate)
		calc_btn.grid(row=3, column=0, pady=8)

		clear_btn = tk.Button(frm, text="Clear", width=12, command=self.clear)
		clear_btn.grid(row=3, column=1, pady=8)

		self.result_var = tk.StringVar(value="Duration = ")
		result_label = tk.Label(frm, textvariable=self.result_var, fg="#8ecaff", bg="#1e1e1e", font=("Arial", 10, "bold"))
		result_label.grid(row=4, column=0, columnspan=2, pady=(4, 0))

		# Bind Enter to calculate
		self.bind('<Return>', lambda e: self.calculate())

	def calculate(self):
		a = self.a_entry.get()
		b = self.b_entry.get()
		try:
			ma = parse_time(a)
			mb = parse_time(b)
		except ValueError as e:
			messagebox.showerror("Invalid time", str(e))
			return
		
		if mb < ma:
			mb += 24 * 60  # Treat as next day

		diff = abs(mb-ma)
		human = format_duration(diff)
		self.result_var.set(f"Duration = {human} ({diff} minutes)")

	def clear(self):
		self.b_entry.delete(0, tk.END)
		self.a_entry.delete(0, tk.END)
		self.result_var.set("Duration = ")


def main():
	app = TimeDiffApp()
	app.mainloop()


if __name__ == '__main__':
	main()

