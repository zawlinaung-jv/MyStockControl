import os
import json
from datetime import datetime, timedelta
import re

# CRITICAL FOR RAILWAY: Railway Persistent Volume ရဲ့ Mount Path သို့ လမ်းကြောင်း ပြောင်းထားပါတယ်
DB_PATH = "/app/data/sales_data.json"

def init_db():
    """Initializes the structural database schema if the file doesn't exist."""
    # တကယ်လို့ /app/data folder မရှိသေးရင် ဆောက်ပေးဖို့ လိုပါတယ်
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
    """Calculates current timestamp in Yangon Time (UTC +6:30)."""
    return (datetime.utcnow() + timedelta(hours=6, minutes=30)).strftime('%Y-%m-%d %H:%M:%S')

def add_new_customer(customer_name):
    data = read_db()
    c_name = customer_name.strip().upper()
    if c_name in data["customers"]:
        return f"⚠️ Warning: Customer '{c_name}' already exists."
    data["customers"][c_name] = {"total_balance": 0}
    write_db(data)
    return f"👤 [Customer Registered]\nName: {c_name}\nTotal Balance: 0 ks"

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
            price = tx["price"]
            customer_items[p_name] = customer_items.get(p_name, 0) + qty
            total_qty += qty

    for p, q in customer_items.items():
        r_price = data["products"].get(p, {}).get("sale_price", 0)
        invoice_details += f"{p} : {r_price:,} * {q} = {q * r_price:,} ks\n"

    prod_summary_list = [f"{p} (x{q})" for p, q in customer_items.items()]
    products_inline = ", ".join(prod_summary_list) if prod_summary_list else "None"
    
    profile_block = (
        f"👤 [Customer Profile]\n"
        f"----------------------------------\n"
        f"Customer Name : {c_name}\n"
        f"Product : {products_inline}\n"
        f"{invoice_details.strip()}\n"
        f"Total Qty : {total_qty}\n"
        f"Total Balance : {balance:,} ks\n\n"
        f"📝 Details Sales History Logs\n"
        f"+---------------------+------------+----+------------+------------+\n"
        f"| Date & Time (MMT)   | Product    | Qty| Total (ks) | Remark     |\n"
        f"+---------------------+------------+----+------------+------------+\n"
    )
    
    sales_found = False
    for tx in reversed(matched_txs):
        sales_found = True
        tx_time = tx["timestamp"]
        p_name = tx["product"]
        qty = str(tx["qty"])
        line_total = f"{tx['qty'] * tx['price']:,}"
        remark = tx.get("remark", "UNPAID")
        
        profile_block += (
            f"| {tx_time.ljust(19)} "
            f"| {p_name.ljust(10)[:10]} "
            f"| {qty.rjust(2)} "
            f"| {line_total.rjust(10)} "
            f"| {remark.ljust(10)[:10]} |\n"
        )
        
    if not sales_found:
        profile_block += f"| { 'No purchase logs found for this customer.'.ljust(63) } |\n"
        
    profile_block += f"+---------------------+------------+----+------------+------------+"
    return profile_block

def check_customer_balance(customer_name):
    data = read_db()
    c_name = customer_name.strip().upper()
    if c_name not in data["customers"]:
        return f"❌ Error: Customer '{c_name}' not found."
    return build_single_customer_profile(data, c_name)

def get_all_customers_report():
    data = read_db()
    if not data["customers"]:
        return {"type": "MULTI_MSG", "data": ["👥 [All Customer Database Entries]\n⚠️ System contains zero registered customer profiles."]}
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
    return f"📥 [Stock Ingested Successfully]\nProduct: {p_name}\nQuantity Added: {qty} pcs\nTotal Stock: {data['products'][p_name]['stock']} pcs"

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
            return f"❌ Transaction Aborted: Insufficient Stock for '{p_name}'. (Available: {current_stk} pcs)"
            
    for p_raw, qty_val in items_list:
        p_name = p_raw.strip().upper()
        sale_price = data["products"][p_name]["sale_price"]
        item_total = qty_val * sale_price
        
        data["products"][p_name]["stock"] -= qty_val
        voucher_total_balance += item_total
        total_qty += qty_val
        
        detailed_product_summary.append(f"{p_name} (x{qty_val})")
        invoice_items_text += f"{p_name} : {sale_price:,} * {qty_val} = {item_total:,} ks\n"
        
        data["transactions"].append({
            "type": "SALE", "customer": c_name, "product": p_name, "qty": qty_val, "price": sale_price, "timestamp": timestamp, "remark": remark_upper
        })
        
    data["customers"][c_name]["total_balance"] += voucher_total_balance
    write_db(data)
    
    products_inline = ", ".join(detailed_product_summary)
    return (
        f"📝 [Sales Voucher]\n----------------------------------\n"
        f"Customer Name : {customer_name.strip()}\nProduct : {products_inline}\n"
        f"{invoice_items_text.strip()}\nTotal Qty : {total_qty}\n"
        f"Total Balance : {voucher_total_balance:,} ks\nRemark : {remark_upper}\n----------------------------------"
    )

def get_stock_report():
    data = read_db()
    timestamp = get_yangon_time()
    total_asset_cost_value = 0
    unique_active_customers = set()
    total_sales_qty_items = 0
    total_revenue = 0
    total_cost_of_goods_sold = 0
    
    stock_report = (
        f"📊 --- EXECUTIVE OVERALL SUMMARY --- 📊\n📅 Generated At: {timestamp} (Yangon Time)\n"
        f"----------------------------------------------------\n\n📦 [Inventory Stock Levels]\n"
        f"+--------------------+----------+------------------+\n| Product Name       | Stock    | Retail Price     |\n"
        f"+--------------------+----------+------------------+\n"
    )
    
    if not data["products"]:
        stock_report += f"| { 'No inventory records available.'.ljust(48) } |\n"
    else:
        for p_name, info in data["products"].items():
            stk_qty = info['stock']
            stk_str = f"{stk_qty} pcs"
            price_str = f"{info['sale_price']:,} ks"
            stock_report += f"| {p_name.ljust(18)} | {stk_str.ljust(8)} | {price_str.ljust(16)} |\n"
            cost_baseline = info.get('pur_price', 0)
            if cost_baseline == 0: cost_baseline = int(info['sale_price'] * 0.7)
            total_asset_cost_value += (stk_qty * cost_baseline)
            
    stock_report += f"+--------------------+----------+------------------+\n\n"

    for tx in data["transactions"]:
        if tx["type"] == "SALE":
            qty = tx["qty"]
            sale_price = tx["price"]
            total_sales_qty_items += qty
            total_revenue += (qty * sale_price)
            if tx.get("customer"): unique_active_customers.add(tx["customer"].upper())
            p_name = tx["product"]
            p_cost = data["products"].get(p_name, {}).get("pur_price", 0)
            if p_cost == 0: p_cost = int(sale_price * 0.7)
            total_cost_of_goods_sold += (qty * p_cost)

    total_gp = total_revenue - total_cost_of_goods_sold
    total_pnl = total_gp
    total_customers_count = len(unique_active_customers) if unique_active_customers else len(data["customers"])

    metrics_board = (
        f"💰 [Financial Performance Indicators Board]\n"
        f"+-----------------------------+--------------------+\n| Operational Metric Key      | Valuation/Value    |\n"
        f"+-----------------------------+--------------------+\n"
        f"| Stock လက်ကျန် (Asset Cost)   | {f'{total_asset_cost_value:,} ks'.ljust(18)} |\n"
        f"| Total Amount (Gross Value)  | {f'{total_revenue:,} ks'.ljust(18)} |\n"
        f"| Total Customer Accounts     | {f'{total_customers_count} members'.ljust(18)} |\n"
        f"| Total Sales Volume          | {f'{total_sales_qty_items} pcs'.ljust(18)} |\n"
        f"| Total Revenue Inflow        | {f'{total_revenue:,} ks'.ljust(18)} |\n"
        f"| Total Gross Profit (GP)     | {f'{total_gp:,} ks'.ljust(18)} |\n"
        f"| Total Net P&L Statement     | {f'{total_pnl:,} ks'.ljust(18)} |\n"
        f"+-----------------------------+--------------------+\n----------------------------------------------------"
    )
    return stock_report + metrics_board

def process_message(message_text):
    cleaned_text = re.sub(r'(?<=\d)(pcs|pc|ks|ks\.)', '', message_text, flags=re.IGNORECASE)
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    if cleaned_text.lower() in ["clear", "/clear", "all clear", "reset"]:
        return (
            "⚠️ [SAFETY CHECK: DATABASE CLEAR REQUEST]\nAre you sure you want to clear data? Please reply with one of the specific commands below:\n\n"
            "🔄 Options Available:\n• `/clear_customers` -> Wipe all customer profiles.\n• `/clear_stock` -> Wipe all product inventory.\n• `/clear_sales` -> Wipe transaction logs.\n• `/clear_all` -> Factory reset everything."
        )

    if cleaned_text.lower() == "/clear_customers":
        data = read_db(); data["customers"] = {}; write_db(data); return "✅ Success: All Customer profiles cleared."
    if cleaned_text.lower() == "/clear_stock":
        data = read_db(); data["products"] = {}; write_db(data); return "✅ Success: All Inventory Stock entries cleared."
    if cleaned_text.lower() == "/clear_sales":
        data = read_db(); data["transactions"] = []; write_db(data); return "✅ Success: All Detailed Sales logs cleared."
    if cleaned_text.lower() == "/clear_all":
        write_db({"products": {}, "customers": {}, "transactions": []}); return "🚨 Factory Reset Complete: All data wiped."

    add_cust_match = re.match(r"^/addcustomer\s+(.+)$", cleaned_text, re.IGNORECASE)
    if add_cust_match: return add_new_customer(add_cust_match.group(1))
        
    check_cust_match = re.match(r"^/customer\s+(.+)$", cleaned_text, re.IGNORECASE)
    if check_cust_match: return check_customer_balance(check_cust_match.group(1))

    if cleaned_text.lower() in ["/allcustomers", "all customer", "all customers", "customers"]:
        return get_all_customers_report()

    buy_match = re.match(r"^/buy\s+([a-zA-Z0-9_-]+)\s+(\d+)\s+(\d+)\s+(\d+)", cleaned_text, re.IGNORECASE)
    if buy_match: return purchase_product(buy_match.group(1), int(buy_match.group(2)), int(buy_match.group(3)), int(buy_match.group(4)))
        
    if cleaned_text.lower() in ["/report", "report", "stock", "summary", "/summary"]: return get_stock_report()
        
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