import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import mysql.connector
from datetime import datetime
import hashlib
from fpdf import FPDF

class Database:
    def __init__(self):
        # First try to connect without database to create it
        try:
            temp_conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="root"  # Apna MySQL password yahan daalein
            )
            temp_cursor = temp_conn.cursor()
            temp_cursor.execute("CREATE DATABASE IF NOT EXISTS expense_tracker")
            temp_conn.close()
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", 
                f"MySQL connection failed!\n\nError: {err}\n\nPlease check:\n1. MySQL is running\n2. Username is correct (default: root)\n3. Password is correct")
            raise
        
        # Now connect to the database
        try:
            self.conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="root",  # Apna MySQL password yahan daalein
                database="expense_tracker"
            )
            self.cursor = self.conn.cursor()
            self.create_tables()
        except mysql.connector.Error as err:
            messagebox.showerror("Database Error", f"Failed to connect: {err}")
            raise
    
    def create_tables(self):
        # Users table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(100) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        
        # Expenses table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                expense_name VARCHAR(255),
                amount DECIMAL(10,2),
                exp_date DATE,
                exp_time TIME,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Admin user (username: admin, password: admin123)
        admin_pass = hashlib.sha256("admin123".encode()).hexdigest()
        try:
            self.cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                ("admin", "admin@expense.com", admin_pass)
            )
            self.conn.commit()
        except:
            pass
    
    def register_user(self, username, email, password):
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        try:
            self.cursor.execute(
                "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
                (username, email, hashed_pw)
            )
            self.conn.commit()
            return True
        except mysql.connector.IntegrityError:
            return False
    
    def login_user(self, username, password):
        hashed_pw = hashlib.sha256(password.encode()).hexdigest()
        self.cursor.execute(
            "SELECT id, username FROM users WHERE username=%s AND password=%s",
            (username, hashed_pw)
        )
        return self.cursor.fetchone()
    
    def add_expense(self, user_id, name, amount, date, time):
        self.cursor.execute(
            "INSERT INTO expenses (user_id, expense_name, amount, exp_date, exp_time) VALUES (%s, %s, %s, %s, %s)",
            (user_id, name, amount, date, time)
        )
        self.conn.commit()
    
    def get_expenses(self, user_id):
        self.cursor.execute(
            "SELECT expense_name, amount, exp_date, exp_time FROM expenses WHERE user_id=%s ORDER BY exp_date DESC",
            (user_id,)
        )
        return self.cursor.fetchall()
    
    def get_total_expense(self, user_id):
        self.cursor.execute(
            "SELECT SUM(amount) FROM expenses WHERE user_id=%s",
            (user_id,)
        )
        result = self.cursor.fetchone()[0]
        return result if result else 0
    
    def get_all_users(self):
        self.cursor.execute(
            "SELECT username, email, created_at, is_active FROM users WHERE username != 'admin'"
        )
        return self.cursor.fetchall()

class ExpenseTrackerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Expense Tracker")
        self.root.geometry("900x600")
        
        try:
            self.db = Database()
            self.current_user = None
            self.show_login()
        except Exception as e:
            messagebox.showerror("Startup Error", 
                "Failed to initialize application!\n\nPlease check MySQL settings in code:\n" +
                "- Line 13: host='localhost'\n" +
                "- Line 14: user='root'\n" +
                "- Line 15: password='YOUR_PASSWORD'")
            self.root.destroy()
    
    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def show_login(self):
        self.clear_window()
        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(frame, text="🔐 Login", font=("Arial", 24, "bold"), bg="#f0f0f0").grid(row=0, column=0, columnspan=2, pady=20)
        
        tk.Label(frame, text="Username:", font=("Arial", 12), bg="#f0f0f0").grid(row=1, column=0, sticky="e", padx=10, pady=10)
        username_entry = tk.Entry(frame, font=("Arial", 12), width=25)
        username_entry.grid(row=1, column=1, padx=10, pady=10)
        
        tk.Label(frame, text="Password:", font=("Arial", 12), bg="#f0f0f0").grid(row=2, column=0, sticky="e", padx=10, pady=10)
        password_entry = tk.Entry(frame, font=("Arial", 12), width=25, show="*")
        password_entry.grid(row=2, column=1, padx=10, pady=10)
        
        def login():
            user = self.db.login_user(username_entry.get(), password_entry.get())
            if user:
                self.current_user = {"id": user[0], "username": user[1]}
                if user[1] == "admin":
                    self.show_admin_dashboard()
                else:
                    self.show_home()
            else:
                messagebox.showerror("Error", "Invalid credentials!")
        
        tk.Button(frame, text="Login", font=("Arial", 12), bg="#4CAF50", fg="white", 
                 width=15, command=login).grid(row=3, column=0, columnspan=2, pady=15)
        
        tk.Button(frame, text="Register New User", font=("Arial", 10), bg="#2196F3", fg="white",
                 command=self.show_register).grid(row=4, column=0, columnspan=2)
    
    def show_register(self):
        self.clear_window()
        frame = tk.Frame(self.root, bg="#f0f0f0")
        frame.place(relx=0.5, rely=0.5, anchor="center")
        
        tk.Label(frame, text="📝 Registration", font=("Arial", 24, "bold"), bg="#f0f0f0").grid(row=0, column=0, columnspan=2, pady=20)
        
        tk.Label(frame, text="Username:", font=("Arial", 12), bg="#f0f0f0").grid(row=1, column=0, sticky="e", padx=10, pady=10)
        username_entry = tk.Entry(frame, font=("Arial", 12), width=25)
        username_entry.grid(row=1, column=1, padx=10, pady=10)
        
        tk.Label(frame, text="Email:", font=("Arial", 12), bg="#f0f0f0").grid(row=2, column=0, sticky="e", padx=10, pady=10)
        email_entry = tk.Entry(frame, font=("Arial", 12), width=25)
        email_entry.grid(row=2, column=1, padx=10, pady=10)
        
        tk.Label(frame, text="Password:", font=("Arial", 12), bg="#f0f0f0").grid(row=3, column=0, sticky="e", padx=10, pady=10)
        password_entry = tk.Entry(frame, font=("Arial", 12), width=25, show="*")
        password_entry.grid(row=3, column=1, padx=10, pady=10)
        
        def register():
            if self.db.register_user(username_entry.get(), email_entry.get(), password_entry.get()):
                messagebox.showinfo("Success", "Registration successful!")
                self.show_login()
            else:
                messagebox.showerror("Error", "Username or email already exists!")
        
        tk.Button(frame, text="Register", font=("Arial", 12), bg="#4CAF50", fg="white",
                 width=15, command=register).grid(row=4, column=0, columnspan=2, pady=15)
        
        tk.Button(frame, text="Back to Login", font=("Arial", 10), bg="#607D8B", fg="white",
                 command=self.show_login).grid(row=5, column=0, columnspan=2)
    
    def show_home(self):
        self.clear_window()
        
        # Header
        header = tk.Frame(self.root, bg="#2196F3", height=80)
        header.pack(fill="x")
        tk.Label(header, text=f"Welcome, {self.current_user['username']}!", 
                font=("Arial", 20, "bold"), bg="#2196F3", fg="white").pack(pady=20)
        
        tk.Button(header, text="Logout", bg="#f44336", fg="white", 
                 command=self.show_login).place(relx=0.95, rely=0.3, anchor="e")
        
        # Summary section
        summary_frame = tk.Frame(self.root, bg="#e3f2fd", height=100)
        summary_frame.pack(fill="x", pady=10)
        
        total = self.db.get_total_expense(self.current_user['id'])
        tk.Label(summary_frame, text=f"💰 Total Expenses: ₹{total:.2f}", 
                font=("Arial", 18, "bold"), bg="#e3f2fd", fg="#1976D2").pack(pady=30)
        
        # Add expense section
        add_frame = tk.LabelFrame(self.root, text="➕ Add New Expense", font=("Arial", 14, "bold"), 
                                  bg="#f5f5f5", padx=20, pady=20)
        add_frame.pack(pady=10, padx=20, fill="x")
        
        tk.Label(add_frame, text="Expense Name:", bg="#f5f5f5").grid(row=0, column=0, padx=5, pady=5)
        name_entry = tk.Entry(add_frame, width=20)
        name_entry.grid(row=0, column=1, padx=5, pady=5)
        
        tk.Label(add_frame, text="Amount (₹):", bg="#f5f5f5").grid(row=0, column=2, padx=5, pady=5)
        amount_entry = tk.Entry(add_frame, width=15)
        amount_entry.grid(row=0, column=3, padx=5, pady=5)
        
        tk.Label(add_frame, text="Date (YYYY-MM-DD):", bg="#f5f5f5").grid(row=0, column=4, padx=5, pady=5)
        date_entry = tk.Entry(add_frame, width=15)
        date_entry.insert(0, datetime.now().strftime("%Y-%m-%d"))
        date_entry.grid(row=0, column=5, padx=5, pady=5)
        
        tk.Label(add_frame, text="Time (HH:MM):", bg="#f5f5f5").grid(row=1, column=0, padx=5, pady=5)
        time_entry = tk.Entry(add_frame, width=15)
        time_entry.insert(0, datetime.now().strftime("%H:%M"))
        time_entry.grid(row=1, column=1, padx=5, pady=5)
        
        def add_expense():
            try:
                self.db.add_expense(
                    self.current_user['id'],
                    name_entry.get(),
                    float(amount_entry.get()),
                    date_entry.get(),
                    time_entry.get()
                )
                messagebox.showinfo("Success", "Expense added!")
                self.show_home()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add expense: {str(e)}")
        
        tk.Button(add_frame, text="Add Expense", bg="#4CAF50", fg="white", 
                 command=add_expense).grid(row=1, column=2, columnspan=2, pady=10)
        
        # Expenses list
        list_frame = tk.LabelFrame(self.root, text="📊 Your Expenses", font=("Arial", 14, "bold"), 
                                   bg="#f5f5f5", padx=20, pady=10)
        list_frame.pack(pady=10, padx=20, fill="both", expand=True)
        
        tree = ttk.Treeview(list_frame, columns=("Name", "Amount", "Date", "Time"), show="headings", height=10)
        tree.heading("Name", text="Expense Name")
        tree.heading("Amount", text="Amount (₹)")
        tree.heading("Date", text="Date")
        tree.heading("Time", text="Time")
        
        expenses = self.db.get_expenses(self.current_user['id'])
        for exp in expenses:
            tree.insert("", "end", values=(exp[0], f"₹{exp[1]:.2f}", exp[2], exp[3]))
        
        tree.pack(fill="both", expand=True)
        
        # PDF button
        def generate_pdf():
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, f"Expense Report - {self.current_user['username']}", ln=True, align="C")
            pdf.ln(10)
            
            pdf.set_font("Arial", "B", 12)
            pdf.cell(60, 10, "Expense Name", border=1)
            pdf.cell(40, 10, "Amount", border=1)
            pdf.cell(40, 10, "Date", border=1)
            pdf.cell(40, 10, "Time", border=1, ln=True)
            
            pdf.set_font("Arial", "", 10)
            for exp in expenses:
                pdf.cell(60, 10, str(exp[0])[:25], border=1)
                pdf.cell(40, 10, f"Rs {exp[1]:.2f}", border=1)
                pdf.cell(40, 10, str(exp[2]), border=1)
                pdf.cell(40, 10, str(exp[3]), border=1, ln=True)
            
            pdf.ln(10)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, f"Total: Rs {total:.2f}", ln=True)
            
            filename = f"expense_report_{self.current_user['username']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            pdf.output(filename)
            messagebox.showinfo("Success", f"PDF saved as {filename}")
        
        tk.Button(list_frame, text="📄 Generate PDF Report", bg="#FF9800", fg="white", 
                 font=("Arial", 12), command=generate_pdf).pack(pady=10)
    
    def show_admin_dashboard(self):
        self.clear_window()
        
        # Header
        header = tk.Frame(self.root, bg="#673AB7", height=80)
        header.pack(fill="x")
        tk.Label(header, text="🔧 Admin Dashboard", font=("Arial", 20, "bold"), 
                bg="#673AB7", fg="white").pack(pady=20)
        
        tk.Button(header, text="Logout", bg="#f44336", fg="white", 
                 command=self.show_login).place(relx=0.95, rely=0.3, anchor="e")
        
        # Users list
        list_frame = tk.LabelFrame(self.root, text="👥 Registered Users", font=("Arial", 14, "bold"), 
                                   bg="#f5f5f5", padx=20, pady=10)
        list_frame.pack(pady=20, padx=20, fill="both", expand=True)
        
        tree = ttk.Treeview(list_frame, columns=("Username", "Email", "Created", "Status"), 
                           show="headings", height=15)
        tree.heading("Username", text="Username")
        tree.heading("Email", text="Email")
        tree.heading("Created", text="Registration Date")
        tree.heading("Status", text="Status")
        
        users = self.db.get_all_users()
        for user in users:
            status = "🟢 Active" if user[3] else "🔴 Inactive"
            tree.insert("", "end", values=(user[0], user[1], user[2], status))
        
        tree.pack(fill="both", expand=True)
        
        tk.Label(list_frame, text=f"Total Users: {len(users)}", font=("Arial", 12, "bold"), 
                bg="#f5f5f5").pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = ExpenseTrackerApp(root)
    root.mainloop()