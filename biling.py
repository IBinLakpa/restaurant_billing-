import sqlite3
from tkinter import *
from tkinter import messagebox, ttk
from datetime import datetime

# Database setup
def setup_database():
    conn = sqlite3.connect("sales.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS bill (
                      id INTEGER PRIMARY KEY,
                      customer_name TEXT,
                      timestamp TEXT,
                      payment_status TEXT,
                      payment_method TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS solditems (
                      bill_id INTEGER,
                      item_name TEXT,
                      qty INTEGER,
                      price REAL,
                      FOREIGN KEY(bill_id) REFERENCES bill(id))''')
    conn.commit()
    conn.close()

# Save a new or edited bill to the database
def save_bill(customer_name, payment_status, payment_method, items, quantities, prices, load_sales, bill_id=None):
    conn = sqlite3.connect("sales.db")
    cursor = conn.cursor()
    
    if bill_id is None:  # New bill
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("INSERT INTO bill (customer_name, timestamp, payment_status, payment_method) VALUES (?, ?, ?, ?)",
                       (customer_name, timestamp, payment_status, payment_method))
        bill_id = cursor.lastrowid
    else:  # Editing existing bill
        cursor.execute("UPDATE bill SET customer_name=?, payment_status=?, payment_method=? WHERE id=?",
                       (customer_name, payment_status, payment_method, bill_id))
        cursor.execute("DELETE FROM solditems WHERE bill_id=?", (bill_id,))  # Clear old items
    
    for item, qty, price in zip(items, quantities, prices):
        cursor.execute("INSERT INTO solditems (bill_id, item_name, qty, price) VALUES (?, ?, ?, ?)",
                       (bill_id, item, qty, price))
    
    conn.commit()
    conn.close()
    load_sales()  # Refresh sales history

# Billing window for creating or editing bills
def create_billing_window(load_sales, existing_sale=None):
    # Set the title based on whether it's a new or existing bill
    if existing_sale:
        title = f"Edit Bill: {existing_sale['customer_name']}, {existing_sale['timestamp']}"
    else:
        title = "New Bill"

    billing_window = Toplevel()
    billing_window.title(title)
    billing_window.geometry("600x600")

    # Customer details section
    Label(billing_window, text="Customer Name:").grid(row=0, column=0, padx=5, pady=5, sticky=W)
    customer_name_var = StringVar(value=existing_sale["customer_name"] if existing_sale else "")
    Entry(billing_window, textvariable=customer_name_var, width=30).grid(row=0, column=1, columnspan=2, padx=5, pady=5)

    Label(billing_window, text="Payment Method:").grid(row=1, column=0, padx=5, pady=5, sticky=W)
    payment_method_var = StringVar(value=existing_sale["payment_method"] if existing_sale else "QR")
    OptionMenu(billing_window, payment_method_var, "QR", "Cash").grid(row=1, column=1, padx=5, pady=5)

    Label(billing_window, text="Payment Status:").grid(row=1, column=2, padx=5, pady=5, sticky=W)
    payment_status_var = StringVar(value=existing_sale["payment_status"] if existing_sale else "Unpaid")
    OptionMenu(billing_window, payment_status_var, "Paid", "Unpaid").grid(row=1, column=3, padx=5, pady=5)

    # Lists to hold references to item fields
    item_entries, price_entries, quantity_entries, subtotal_labels, delete_buttons = [], [], [], [], []

    # Calculate total for all items
    def calculate_total():
        total = 0
        for subtotal in subtotal_labels:
            total += float(subtotal.get())
        total_label.config(text=f"Total: Rs. {total:.2f}")
        return total

    # Add a row for each item
    def add_item_row(item_name="", item_price=0.0, item_qty=1):
        row = len(item_entries) + 3  # Start from row 3 to avoid overlap with customer info

        # Initialize item variables with default values to prevent errors
        item_var, price_var, quantity_var = StringVar(value=item_name), DoubleVar(value=item_price), IntVar(value=item_qty)
        subtotal_var = StringVar(value=f"{item_price * item_qty:.2f}")
        
        # Widgets for item details
        Entry(billing_window, textvariable=item_var, width=15).grid(row=row, column=0, padx=5, pady=5)
        Entry(billing_window, textvariable=price_var, width=10).grid(row=row, column=1, padx=5, pady=5)
        Entry(billing_window, textvariable=quantity_var, width=5).grid(row=row, column=2, padx=5, pady=5)
        Label(billing_window, textvariable=subtotal_var, width=10).grid(row=row, column=3, padx=5, pady=5)

        # Update subtotal and total on change, default to 0 if empty
        def update_subtotal(*args):
            price = float(price_var.get() if price_var.get() else 0)
            qty = int(quantity_var.get() if quantity_var.get() else 0)
            subtotal = price * qty
            subtotal_var.set(f"{subtotal:.2f}")
            calculate_total()

        price_var.trace_add("write", update_subtotal)
        quantity_var.trace_add("write", update_subtotal)

        # Append data to lists
        item_entries.append(item_var)
        price_entries.append(price_var)
        quantity_entries.append(quantity_var)
        subtotal_labels.append(subtotal_var)

    # Populate items if editing, otherwise add one default item row
    if existing_sale:
        conn = sqlite3.connect("sales.db")
        cursor = conn.cursor()
        cursor.execute("SELECT item_name, qty, price FROM solditems WHERE bill_id=?", (existing_sale["bill_id"],))
        for item_name, qty, price in cursor.fetchall():
            add_item_row(item_name, price, qty)
        conn.close()
    else:
        add_item_row()  # Add one default item row for new bills

    # Add item button and total label
    Button(billing_window, text="Add Item", command=add_item_row).grid(row=len(item_entries) + 4, column=0, padx=5, pady=10)
    total_label = Label(billing_window, text="Total: Rs. 0.00", font=("Arial", 14))
    total_label.grid(row=len(item_entries) + 5, column=0, columnspan=4, pady=10)

    # Save function for creating or updating bill
    def save_current_bill():
        customer_name = customer_name_var.get().strip()
        payment_status = payment_status_var.get()
        payment_method = payment_method_var.get()
        items = [item.get() for item in item_entries if item.get()]
        quantities = [quantity.get() for quantity in quantity_entries]
        prices = [price.get() for price in price_entries]

        if not customer_name:
            messagebox.showwarning("Incomplete Data", "Please enter the customer name.")
            return

        save_bill(customer_name, payment_status, payment_method, items, quantities, prices, load_sales, bill_id=existing_sale["bill_id"] if existing_sale else None)
        billing_window.destroy()  # Close the billing window after saving

    # Save button
    Button(billing_window, text="Save Bill", command=save_current_bill).grid(row=len(item_entries) + 6, column=0, columnspan=4, pady=10)

# Sales history window with default display
def create_sales_history_window():
    history_window = Tk()
    history_window.title("Sales History")
    history_window.geometry("800x500")

    # Treeview for sales records
    columns = ("ID", "Customer Name", "Timestamp", "Payment Status", "Payment Method", "Total")
    tree = ttk.Treeview(history_window, columns=columns, show="headings")
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=100 if col == "ID" else 150)
    tree.pack(fill=BOTH, expand=True)

    # Load all sales records
    def load_sales():
        for row in tree.get_children():
            tree.delete(row)
        conn = sqlite3.connect("sales.db")
        cursor = conn.cursor()
        cursor.execute("SELECT bill.id, customer_name, timestamp, payment_status, payment_method, "
                       "(SELECT SUM(qty * price) FROM solditems WHERE solditems.bill_id = bill.id) AS total "
                       "FROM bill")
        for sale in cursor.fetchall():
            tree.insert("", "end", values=sale)
        conn.close()

    # Delete selected sale
    def delete_sale():
        selected_item = tree.selection()
        if selected_item:
            bill_id = tree.item(selected_item)["values"][0]
            conn = sqlite3.connect("sales.db")
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bill WHERE id=?", (bill_id,))
            cursor.execute("DELETE FROM solditems WHERE bill_id=?", (bill_id,))
            conn.commit()
            conn.close()
            load_sales()
            messagebox.showinfo("Deleted", "Sale record has been deleted.")

    # Edit selected bill
    def edit_sale():
        selected_item = tree.selection()
        if selected_item:
            bill_id = tree.item(selected_item)["values"][0]
            conn = sqlite3.connect("sales.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM bill WHERE id=?", (bill_id,))
            result = cursor.fetchone()
            conn.close()
            if result:
                existing_sale = {
                    "bill_id": result[0],
                    "customer_name": result[1],
                    "timestamp": result[2],
                    "payment_status": result[3],
                    "payment_method": result[4]
                }
                create_billing_window(load_sales, existing_sale)

    # Buttons for creating, editing, and deleting bills
    Button(history_window, text="Create Bill", command=lambda: create_billing_window(load_sales)).pack(side=LEFT, padx=10, pady=10)
    Button(history_window, text="Edit Selected", command=edit_sale).pack(side=LEFT, padx=10, pady=10)
    Button(history_window, text="Delete Selected", command=delete_sale).pack(side=LEFT, padx=10, pady=10)

    load_sales()

# Database setup on launch and show sales history
setup_database()
create_sales_history_window()
mainloop()
