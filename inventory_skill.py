import os
import json
from datetime import datetime, timedelta
import re

# CRITICAL FOR RAILWAY: Persistent Volume Storage Path
DB_PATH = "/app/data/sales_data.json"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if not os.path.exists(DB_PATH):
        initial_data = {"products": {}, "customers": {}, "transactions": []}
        with open(DB_PATH, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, indent=4, ensure_ascii=False)

def read_db():
    init_db()
    with open(DB_PATH, 'r', encoding='utf-8') as f: 
        return json.load(f)

def write_db(data):
    with open(DB_PATH, 'w', encoding='utf-8') as f: 
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_yangon_time():
    return (datetime.utcnow() + timedelta(hours=6, minutes=30)).strftime('%Y-%m-%d %H:%M:%S')

def add_new_customer(customer_name):
    data = read_db()
    c_name = customer_name.strip().upper()
    if c_name in data["customers"]:
        return f"⚠️ Warning: Customer '{c_name}' already exists!"
    data["customers"][c_name] = {"total_balance": 0}
    write_db(data)
    return f"👤 [NEW CUSTOMER REGISTERED]\n----------------------------------\nName: {c_name}\nCurrent Balance: 0 ks"

def build_single_customer_profile(data, c_name):
    balance = data["customers"][c_name]["total_balance"]
    customer_items = {}
    invoice_details = ""
    total_qty = 0
    matched_txs = []
    
    for tx in data["transactions"]:
        if tx["type"] == "SALE" and tx.get("customer", "").upper() == c_name:
            matched_txs.append(tx)
            p_name = tx["product"]
            qty = tx["qty"]
            customer_items[p_name] = customer_items.get(p_name, 0) + qty
            total_qty += qty

    for p, q in customer_items.items():
        r_price = data["products"].get(p, {}).get("sale_price", 0)
        invoice_details += f"🔹 {p} : {r_price:,} * {q} = {q * r_price:,} ks\n"

    prod_summary_list = [f"{p} (x{q})" for p, q in customer_items.items()]
    products_inline = ", ".join(prod_summary_list) if prod_summary_list else "None"
    
    profile_block = (
        f"👤 [CUSTOMER PROFILE LEDGER]\n"
        f"----------------------------------\n"
        f"🏢 Name: {c_name}\n"
        f"📦 Purchased Items: {products_inline}\n\n"
        f"📋 [PURCHASE DETAILS]\n"
        f"----------------------------------\n"
        f"{invoice_details.strip()}\n"
        f"🧮 Total Quantity: {total_qty} pcs\n"
        f"🔺 Total Debt Balance: {balance:,} ks\n\n"
        f"🕒 [TRANSACTION HISTORY]\n"
        f"----------------------------------\n"
    )
    
    sales_found = False
    for tx in reversed(matched_txs):
        sales_found = True
        tx_time = tx["timestamp"]
        p_name = tx["product"]
        qty = tx["qty"]
        line_total = tx['qty'] * tx['price']
        remark = tx.get("remark", "UNPAID")
        
        profile_block += f"📆 {tx_time} | {p_name} ({qty}pcs) = {line_total:,} ks [{remark}]\n"
        
    if not sales_found:
        profile_block += f"ℹ️ No transaction history found for this customer.\n"
        
    return profile_block

def check_customer_balance(customer_name):
    data = read_db()
    c_name = customer_name.strip().upper()
    if c_name not in data["customers"]:
        return f"❌ Error: Customer '{c_name}' not found!"
    return build_single_customer_profile(data, c_name)

def get_all_customers_report():
    data = read_db()
    if not data["customers"]:
        return {"type": "MULTI_MSG", "data": ["👥 [CUSTOMERS DATABASE MASTER]\n----------------------------------\n⚠️ No registered customers found."]}
    output_messages = []
    for c_name in sorted(data["customers"].keys()):
        output_messages.append(build_single_customer_profile(data, c_name))
    return {"type": "MULTI_MSG", "data": output_messages}

def purchase_product(product_name, qty, pur_price, sale_price):
    data = read_db()
    p_name = product_name.strip().upper()
    if p_name not in data["products"]:
        data["products"][p_name] = {"stock": 0, "pur_price": 0, "sale_price": 0}
        
    data["products"][p_name]["stock"] += qty
    data["products"][p_name]["pur_price"] = pur_price
    data["products"][p_name]["sale_price"] = sale_price
    
    timestamp = get_yangon_time()
    data["transactions"].append({
        "type": "PURCHASE", "product": p_name, "qty": qty, "price": pur_price, "timestamp": timestamp
    })
    write_db(data)
    return (
        f"📥 [STOCK INGESTED SUCCESSFULLY]\n"
        f"----------------------------------\n"
        f"📦 Product Name: {p_name}\n"
        f"➕ Added Qty: {qty} pcs\n"
        f"💰 Buy Price: {pur_price:,} ks | Sell Price: {sale_price:,} ks\n"
        f"📊 Total Stock Available: {data['products'][p_name]['stock']} pcs"
    )

def sell_multi_products(customer_name, items_list, remark_val="UNPAID"):
    data = read_db()
    c_name = customer_name.strip().upper()
    timestamp = get_yangon_time()
    remark_upper = remark_val.strip().upper()
    
    if c_name not in data["customers"]:
        data["customers"][c_name] = {"total_balance": 0}
        
    invoice_items_text = ""
    detailed_product_summary = []
    total_qty = 0
    voucher_total_balance = 0
    
    for p_raw, qty_val in items_list:
        p_name = p_raw.strip().upper()
        if p_name not in data["products"] or data["products"][p_name]["stock"] < qty_val:
            current_stk = data["products"][p_name]["stock"] if p_name in data["products"] else 0
            return f"❌ Sale Cancelled: '{p_name}' is Out of Stock! (Available: {current_stk} pcs)"
            
    for p_raw, qty_val in items_list:
        p_name = p_raw.strip().upper()
        sale_price = data["products"][p_name]["sale_price"]
        item_total = qty_val * sale_price
        
        data["products"][p_name]["stock"] -= qty_val
        voucher_total_balance += item_total
        total_qty += qty_val
        
        detailed_product_summary.append(f"{p_name} (x{qty_val})")
        invoice_items_text += f"🔹 {p_name} : {sale_price:,} * {qty_val} = {item_total:,} ks\n"
        
        data["transactions"].append({
            "type": "SALE", "customer": c_name, "product": p_name, "qty": qty_val, "price": sale_price, "timestamp": timestamp, "remark": remark_upper
        })
        
    data["customers"][c_name]["total_balance"] += voucher_total_balance
    write_db(data)
    
    products_inline = ", ".join(detailed_product_summary)
    return (
        f"📝 [SALES VOUCHER]\n"
        f"----------------------------------\n"
        f"👤 Customer: {customer_name.strip()}\n"
        f"📦 Items: {products_inline}\n\n"
        f"[BREAKDOWN]\n"
        f"----------------------------------\n"
        f"{invoice_items_text.strip()}\n"
        f"🧮 Total Quantity: {total_qty} pcs\n"
        f"💰 Total Amount: {voucher_total_balance:,} ks\n"
        f"📌 Status: {remark_upper}\n"
        f"----------------------------------"
    )

def get_stock_report():
    data = read_db()
    timestamp = get_yangon_time()
    
    total_stock_balance = 0
    total_sales = 0
    total_volumes = 0
    total_cost_of_goods_sold = 0
    
    stock_report_text = (
        f"📊 [EXECUTIVE INVENTORY REPORT]\n"
        f"📅 Generated At: {timestamp}\n"
        f"----------------------------------\n\n"
        f"📦 [CURRENT INVENTORY STOCK]\n"
        f"----------------------------------\n"
    )
    
    if not data["products"]:
        stock_report_text += f"ℹ️ Inventory is empty. No products found.\n"
    else:
        for p_name, info in data["products"].items():
            stk_qty = info['stock']
            pur_price = info.get('pur_price', 0)
            sale_price = info['sale_price']
            
            stock_report_text += f"▪️ {p_name} -> Stock: {stk_qty} pcs | Price: {sale_price:,} ks\n"
            total_stock_balance += (stk_qty * pur_price)

    for tx in data["transactions"]:
        if tx["type"] == "SALE":
            qty = tx["qty"]
            sale_price = tx["price"]
            p_name = tx["product"]
            
            total_sales += (qty * sale_price)
            total_volumes += qty
            
            pur_price = data["products"].get(p_name, {}).get("pur_price", 0)
            total_cost_of_goods_sold += (qty * pur_price)

    total_gp = total_sales - total_cost_of_goods_sold
    total_pnl = total_gp

    metrics_board = (
        f"\n💰 [FINANCIAL INDICATORS BOARD]\n"
        f"----------------------------------\n"
        f"🏦 Total Stock Balance : {total_stock_balance:,} ks\n"
        f"📈 Total Sales         : {total_sales:,} ks\n"
        f"📦 Total Volumes       : {total_volumes} pcs\n"
        f"💵 Total GP            : {total_gp:,} ks\n"
        f"⚖️ Total PNL           : {total_pnl:,} ks\n"
        f"----------------------------------"
    )
    return stock_report_text + metrics_board

def process_message(message_text):
    cleaned_text = re.sub(r'(?<=\d)(pcs|pc|ks|ks\.)', '', message_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    # CRITICAL: Implemented immediate clear executions without nesting blockers
    if cleaned_text.lower() in ["clear all", "/clear_all", "clear_all"]:
        write_db({"products": {}, "customers": {}, "transactions": []})
        return "🚨 [DATABASE FACTORY RESET] Entire system database has been wiped clean successfully!"

    if cleaned_text.lower() in ["clear stock", "/clear_stock", "clear_stock"]:
        data = read_db(); data["products"] = {}; write_db(data)
        return "✅ [STOCK RESET] All inventory stock products have been wiped clean."

    if cleaned_text.lower() in ["clear customer", "/clear_customer", "clear_customer"]:
        data = read_db(); data["customers"] = {}; write_db(data)
        return "✅ [CUSTOMER RESET] All customer profiles have been wiped clean."

    # Stock quantity level explicit modifications
    update_stk_match = re.match(r"^/update_stock\s+([a-zA-Z0-9_-]+)\s+(\d+)", cleaned_text, re.IGNORECASE)
    if update_stk_match:
        data = read_db()
        p_name = update_stk_match.group(1).strip().upper()
        new_qty = int(update_stk_match.group(2))
        if p_name in data["products"]:
            data["products"][p_name]["stock"] = new_qty
            write_db(data)
            return f"🔧 [Stock Updated] '{p_name}' stock quantity has been explicitly set to {new_qty} pcs."
        return f"❌ Error: Product '{p_name}' not found."

    # Complete product structural purging
    del_prod_match = re.match(r"^/delete_product\s+([a-zA-Z0-9_-]+)", cleaned_text, re.IGNORECASE)
    if del_prod_match:
        data = read_db()
        p_name = del_prod_match.group(1).strip().upper()
        if p_name in data["products"]:
            del data["products"][p_name]
            write_db(data)
            return f"🗑️ [Product Deleted] '{p_name}' has been completely removed from the database."
        return f"❌ Error: Product '{p_name}' not found."

    # Inbound /purchase router
    buy_match = re.match(r"^/(purchase|buy)\s+([a-zA-Z0-9_-]+)\s+(\d+)\s+(\d+)\s+(\d+)", cleaned_text, re.IGNORECASE)
    if buy_match: return purchase_product(buy_match.group(2), int(buy_match.group(3)), int(buy_match.group(4)), int(buy_match.group(5)))

    # Customer registration & tracking
    add_cust_match = re.match(r"^/addcustomer\s+(.+)$", cleaned_text, re.IGNORECASE)
    if add_cust_match: return add_new_customer(add_cust_match.group(1))
        
    check_cust_match = re.match(r"^/customer\s+(.+)$", cleaned_text, re.IGNORECASE)
    if check_cust_match: return check_customer_balance(check_cust_match.group(1))

    if cleaned_text.lower() in ["/allcustomers", "all customer", "all customers", "customers"]:
        return get_all_customers_report()
        
    if cleaned_text.lower() in ["/report", "report", "stock", "summary", "/summary"]: return get_stock_report()
        
    # Multi-item Sales parser engine
    tokens = cleaned_text.split(" ")
    if len(tokens) >= 3:
        possible_remark = tokens[-1].upper()
        remark_val = "UNPAID"
        if possible_remark in ["PAID", "UNPAID", "TRADE", "NOT-PAID", "NOT_PAID"]:
            remark_val = possible_remark
            tokens.pop()
            
        items = []
        idx = len(tokens) - 1
        while idx > 0:
            if tokens[idx].isdigit() and not tokens[idx-1].isdigit():
                qty = int(tokens[idx])
                prod = tokens[idx-1]
                items.insert(0, (prod, qty))
                idx -= 2
            else: break
        if items:
            customer_name = " ".join(tokens[:idx + 1]).strip()
            if customer_name: return sell_multi_products(customer_name, items, remark_val)
                
    return None