import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- إعداد الصفحة ---
st.set_page_config(page_title="نظام سماري للأسماك", layout="wide", page_icon="🐟")

# --- CSS لتحسين المظهر ---
st.markdown("""
<style>
    .block-container {direction: rtl; text-align: right;}
    .stButton>button {width: 100%; border-radius: 10px; height: 3em; font-weight: bold;}
    h1, h2, h3 {text-align: right; color: #0277bd;}
</style>
""", unsafe_allow_html=True)

# --- قاعدة البيانات ---
conn = sqlite3.connect('samari.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, type TEXT, price REAL, cost REAL, stock REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY, date TEXT, total REAL, payment_method TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS sale_items (id INTEGER PRIMARY KEY, sale_id INTEGER, product_name TEXT, quantity REAL, price REAL, total REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY, date TEXT, account TEXT, debit REAL, credit REAL, description TEXT)''')
    
    # منتجات افتراضية
    c.execute("SELECT count(*) FROM products")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO products (name, type, price, cost, stock) VALUES (?, ?, ?, ?, ?)", ('سمك هامور', 'KG', 65.0, 40.0, 50.0))
        c.execute("INSERT INTO products (name, type, price, cost, stock) VALUES (?, ?, ?, ?, ?)", ('روبيان', 'KG', 85.0, 60.0, 30.0))
        c.execute("INSERT INTO products (name, type, price, cost, stock) VALUES (?, ?, ?, ?, ?)", ('أرز صيادية', 'Unit', 15.0, 5.0, 100.0))
        c.execute("INSERT INTO products (name, type, price, cost, stock) VALUES (?, ?, ?, ?, ?)", ('بيبسي', 'Unit', 3.0, 1.5, 200.0))
        conn.commit()

init_db()

# --- دالة القيود ---
def add_journal_entry(date, desc, lines):
    for line in lines:
        c.execute("INSERT INTO journal (date, account, debit, credit, description) VALUES (?, ?, ?, ?, ?)", (date, line[0], line[1], line[2], desc))
    conn.commit()

# --- القائمة الجانبية ---
st.sidebar.title("⚓ مطعم سماري")
menu = st.sidebar.radio("القائمة", ["نقطة البيع", "المخزون", "التقارير"])

# 1. نقطة البيع
if menu == "نقطة البيع":
    if 'cart' not in st.session_state: st.session_state.cart = []
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("📦 المنتجات")
        df = pd.read_sql("SELECT * FROM products", conn)
        for _, row in df.iterrows():
            with st.container():
                c1, c2, c3 = st.columns([2,1,1])
                c1.write(f"**{row['name']}** ({row['price']} ريال)")
                if row['type'] == 'KG':
                    qty = c2.number_input(f"وزن {row['name']}", 0.0, step=0.1, key=f"q{row['id']}")
                else:
                    qty = c2.number_input(f"عدد {row['name']}", 0, step=1, key=f"q{row['id']}")
                if c3.button("أضف", key=f"b{row['id']}") and qty > 0:
                    st.session_state.cart.append({"name": row['name'], "qty": qty, "price": row['price'], "cost": row['cost'], "total": qty*row['price']})
                    st.success("تم!")
                    st.rerun()

    with col2:
        st.subheader("🛒 السلة")
        if st.session_state.cart:
            cart_df = pd.DataFrame(st.session_state.cart)
            st.dataframe(cart_df[['name', 'qty', 'total']], hide_index=True)
            total = cart_df['total'].sum()
            st.markdown(f"### المجموع: {total:.2f}")
            pay_method = st.selectbox("الدفع", ["Cash", "Mada"])
            if st.button("✅ بيع"):
                date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                c.execute("INSERT INTO sales (date, total, payment_method) VALUES (?, ?, ?)", (date, total, pay_method))
                sale_id = c.lastrowid
                total_cost = 0
                for item in st.session_state.cart:
                    c.execute("INSERT INTO sale_items (sale_id, product_name, quantity, price, total) VALUES (?, ?, ?, ?, ?)", (sale_id, item['name'], item['qty'], item['price'], item['total']))
                    c.execute("UPDATE products SET stock = stock - ? WHERE name = ?", (item['qty'], item['name']))
                    total_cost += item['qty'] * item['cost']
                
                # قيود محاسبية
                entries = [("الصندوق", total, 0), ("المبيعات", 0, total), ("تكلفة المبيعات", total_cost, 0), ("المخزون", 0, total_cost)]
                add_journal_entry(date, f"فاتورة {sale_id}", entries)
                
                st.session_state.cart = []
                st.balloons()
                st.success(f"تم البيع! فاتورة #{sale_id}")
                st.rerun()

# 2. المخزون
elif menu == "المخزون":
    st.header("📦 إدارة المخزون")
    with st.form("new_prod"):
        n = st.text_input("الاسم"); p = st.number_input("السعر"); co = st.number_input("التكلفة"); s = st.number_input("الرصيد"); t = st.selectbox("النوع", ["KG", "Unit"])
        if st.form_submit_button("حفظ"):
            c.execute("INSERT INTO products (name, type, price, cost, stock) VALUES (?, ?, ?, ?, ?)", (n, t, p, co, s))
            conn.commit(); st.success("تم")
    st.dataframe(pd.read_sql("SELECT * FROM products", conn))

# 3. التقارير
elif menu == "التقارير":
    st.header("📊 التقارير")
    tab1, tab2 = st.tabs(["المبيعات", "الأرباح"])
    with tab1: st.dataframe(pd.read_sql("SELECT * FROM sales", conn))
    with tab2:
        rev = pd.read_sql("SELECT sum(credit) FROM journal WHERE account='المبيعات'", conn).iloc[0,0] or 0
        cogs = pd.read_sql("SELECT sum(debit) FROM journal WHERE account='تكلفة المبيعات'", conn).iloc[0,0] or 0
        st.metric("صافي الربح", f"{rev - cogs} ريال")
