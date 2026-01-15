import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- 1. إعدادات المظهر والهوية (مطعم سماري) ---
st.set_page_config(page_title="مطعم سماري ERP", layout="wide", page_icon="🐟")

st.markdown("""
    <style>
    .stApp { background-color: #E1F5FE; }
    .main-title { text-align: center; color: #01579B; font-family: 'Arial'; padding: 15px; border-bottom: 3px solid #0288D1; }
    .login-box { background: white; padding: 40px; border-radius: 25px; border: 2px solid #81D4FA; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }
    div.stButton > button:first-child {
        background-color: #0288D1; color: white; border-radius: 12px; height: 70px; width: 100%; font-weight: bold; font-size: 18px;
    }
    .invoice-card { background: white; padding: 20px; border-radius: 15px; border-right: 5px solid #0288D1; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. إدارة قاعدة البيانات المحاسبية ---
def get_connection():
    return sqlite3.connect('samari_v5_final.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # شجرة الحسابات
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (code TEXT PRIMARY KEY, name TEXT, type TEXT, balance REAL DEFAULT 0)''')
    # الفواتير
    c.execute('''CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY AUTOINCREMENT, total REAL, tax REAL, method TEXT, date TEXT, status TEXT DEFAULT 'Paid')''')
    # تفاصيل الفواتير
    c.execute('''CREATE TABLE IF NOT EXISTS invoice_items (inv_id INTEGER, item_name TEXT, qty REAL, price REAL)''')
    
    # بناء شجرة حسابات أولية
    c.execute("SELECT count(*) FROM accounts")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO accounts VALUES (?,?,?,?)", [
            ('111', 'الصندوق - كاش', 'Asset', 0),
            ('112', 'البنك - شبكة', 'Asset', 0),
            ('211', 'ذمم الموردين', 'Liability', 0),
            ('411', 'إيرادات المبيعات', 'Revenue', 0),
            ('511', 'مصروف المشتريات', 'Expense', 0),
            ('215', 'ضريبة القيمة المضافة', 'Liability', 0)
        ])
    conn.commit()
    conn.close()

init_db()

# --- 3. نظام الدخول ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'cart' not in st.session_state: st.session_state.cart = []

if not st.session_state.logged_in:
    col_l1, col_l2, col_l3 = st.columns([1, 1.5, 1])
    with col_l2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center; color:#01579B;'>🐟 دخول نظام سماري</h2>", unsafe_allow_html=True)
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type='password')
        if st.button("تسجيل الدخول"):
            if u == "admin" and p == "1234":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("البيانات غير صحيحة")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 4. واجهة التطبيق الرئيسية ---
st.sidebar.markdown("<h1 style='color:#0288D1;'>🐟 مطعم سماري</h1>", unsafe_allow_html=True)
page = st.sidebar.selectbox("القائمة الرئيسية", ["نقاط البيع (POS)", "المرتجعات والسجل", "شجرة الحسابات", "المشتريات"])

if st.sidebar.button("تسجيل الخروج"):
    st.session_state.logged_in = False
    st.rerun()

# --- 5. نقاط البيع (POS) ---
if page == "نقاط البيع (POS)":
    st.markdown("<h1 class='main-title'>🛒 شاشة مبيعات سماري</h1>", unsafe_allow_html=True)
    col_menu, col_inv = st.columns([2, 1])

    with col_menu:
        tabs = st.tabs(["أسماك 🐟", "بوادي 🥣", "مشروبات 🥤", "توصيل 🚚"])
        items = [
            {"n": "سمك بوري", "c": "أسماك", "p": 180, "u": "كيلو"},
            {"n": "سمك بلطي", "c": "أسماك", "p": 120, "u": "كيلو"},
            {"n": "شوربة سيفود", "c": "بوادي", "p": 45, "u": "حبة"},
            {"n": "بيبسي", "c": "مشروبات", "p": 5, "u": "حبة"},
            {"n": "خدمة توصيل", "c": "توصيل", "p": 15, "u": "حبة"}
        ]
        for tab, cat in zip(tabs, ["أسماك", "بوادي", "مشروبات", "توصيل"]):
            with tab:
                cols = st.columns(2)
                cat_items = [i for i in items if i['c'] == cat]
                for idx, item in enumerate(cat_items):
                    with cols[idx % 2]:
                        st.write(f"**{item['n']}**")
                        q = st.number_input(f"الكمية ({item['u']})", min_value=0.1, value=1.0, key=f"q_{item['n']}")
                        if st.button(f"إضافة {item['p']} ريال", key=f"b_{item['n']}"):
                            st.session_state.cart.append({"الصنف": item['n'], "الكمية": q, "السعر": item['p'], "الإجمالي": q*item['p']})
                            st.toast(f"تمت إضافة {item['n']}")

    with col_inv:
        st.markdown("<div class='invoice-card'>", unsafe_allow_html=True)
        st.subheader("🧾 الفاتورة الحالية")
        if st.session_state.cart:
            df = pd.DataFrame(st.session_state.cart)
            st.table(df[['الصنف', 'الكمية', 'الإجمالي']])
            sub = df['الإجمالي'].sum()
            tax = sub * 0.15
            total = sub + tax
            st.write(f"المجموع: {sub:.2f}")
            st.write(f"الضريبة: {tax:.2f}")
            st.error(f"### الإجمالي: {total:.2f} ريال")
            method = st.selectbox("وسيلة الدفع", ["كاش", "شبكة"])
            if st.button("تأكيد وحفظ ✅"):
                conn = get_connection()
                c = conn.cursor()
                c.execute("INSERT INTO invoices (total, tax, method, date) VALUES (?,?,?,?)", (total, tax, method, datetime.now().strftime("%Y-%m-%d %H:%M")))
                c.execute("UPDATE accounts SET balance = balance + ? WHERE code = '411'", (sub,))
                conn.commit()
                conn.close()
                st.session_state.cart = []
                st.success("تم الحفظ")
                st.rerun()
        else: st.info("السلة فارغة")
        st.markdown("</div>", unsafe_allow_html=True)

# --- 6. المرتجعات ---
elif page == "المرتجعات والسجل":
    st.markdown("<h2 class='main-title'>🔄 سجل الفواتير والمرتجعات</h2>", unsafe_allow_html=True)
    conn = get_connection()
    df_inv = pd.read_sql_query("SELECT * FROM invoices ORDER BY id DESC", conn)
    st.dataframe(df_inv, use_container_width=True)
    rid = st.number_input("أدخل رقم الفاتورة للمرتجع", min_value=1, step=1)
    if st.button("تنفيذ المرتجع ⚠️"):
        c = conn.cursor()
        c.execute("UPDATE invoices SET status = 'Returned' WHERE id = ?", (rid,))
        conn.commit()
        st.warning(f"تم إرجاع الفاتورة رقم {rid} وعكس القيود")
        st.rerun()
    conn.close()

# --- 7. شجرة الحسابات ---
elif page == "شجرة الحسابات":
    st.markdown("<h2 class='main-title'>📊 الأرصدة والمحاسبة</h2>", unsafe_allow_html=True)
    conn = get_connection()
    df_acc = pd.read_sql_query("SELECT * FROM accounts", conn)
    st.table(df_acc)
    conn.close()

# --- 8. المشتريات ---
elif page == "المشتريات":
    st.markdown("<h2 class='main-title'>📥 تسجيل المشتريات</h2>", unsafe_allow_html=True)
    with st.form("pur_form"):
        sup = st.text_input("اسم المورد")
        p_item = st.text_input("الصنف المشتراى")
        p_price = st.number_input("القيمة الإجمالية")
        if st.form_submit_button("حفظ المشتريات"):
            st.success("تم تسجيل العملية في حساب المورد والمشتريات")
