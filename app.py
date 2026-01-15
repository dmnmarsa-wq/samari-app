import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- 1. إعدادات المظهر واللون السماوي (CSS) ---
st.set_page_config(page_title="مطعم سماري ERP", layout="wide", page_icon="🐟")

st.markdown("""
    <style>
    /* تنسيق الخلفية والألوان السماوية */
    .stApp { background-color: #E0F2F7; }
    .main-title { text-align: center; color: #0277BD; font-family: 'Arial'; padding: 20px; }
    .login-box { background: white; padding: 30px; border-radius: 20px; border: 2px solid #81D4FA; box-shadow: 0 10px 25px rgba(0,0,0,0.1); }
    
    /* أزرار المنتجات */
    div.stButton > button:first-child {
        background-color: #0288D1; color: white; border-radius: 15px; height: 80px; width: 100%; font-weight: bold; font-size: 18px; border: none;
    }
    div.stButton > button:hover { background-color: #01579B; color: #E1F5FE; }
    
    /* صندوق الفاتورة */
    .invoice-card { background: white; padding: 20px; border-radius: 15px; border-top: 5px solid #0288D1; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. إدارة قاعدة البيانات ---
def get_connection():
    return sqlite3.connect('samari_ultimate_v4.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (code TEXT PRIMARY KEY, name TEXT, balance REAL DEFAULT 0)''')
    c.execute('''CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY AUTOINCREMENT, total REAL, tax REAL, method TEXT, date TEXT, status TEXT DEFAULT 'Paid')''')
    c.execute('''CREATE TABLE IF NOT EXISTS invoice_items (inv_id INTEGER, item_name TEXT, qty REAL, price REAL)''')
    
    # حسابات المحاسبة الأساسية
    c.execute("SELECT count(*) FROM accounts")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO accounts VALUES (?,?,?)", [
            ('111', 'الصندوق (كاش)', 0), ('411', 'المبيعات', 0), ('211', 'ضريبة القيمة المضافة', 0)
        ])
    conn.commit()
    conn.close()

init_db()

# --- 3. إدارة الجلسة والدخول ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'cart' not in st.session_state: st.session_state.cart = []

# --- 4. شاشة تسجيل الدخول ---
if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center; color:#0277BD;'>🐟 تسجيل دخول <br> مطعم سماري</h2>", unsafe_allow_html=True)
        user = st.text_input("اسم المستخدم")
        pw = st.text_input("كلمة المرور", type='password')
        if st.button("دخول للنظام"):
            if user == "admin" and pw == "1234": # يمكنك تغيير كلمة السر هنا
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("خطأ في اسم المستخدم أو كلمة المرور")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 5. واجهة التطبيق الداخلية ---
st.sidebar.markdown("<h2 style='color:#0288D1;'>🐟 مطعم سماري</h2>", unsafe_allow_html=True)
st.sidebar.write(f"المستخدم الحالي: **Admin**")
page = st.sidebar.selectbox("القائمة", ["نقاط البيع (POS)", "المرتجعات والسجل", "شجرة الحسابات"])

if st.sidebar.button("تسجيل الخروج"):
    st.session_state.logged_in = False
    st.rerun()

# --- 6. صفحة البيع (POS) ---
if page == "نقاط البيع (POS)":
    st.markdown("<h1 class='main-title'>🐟 مطعم سماري - نظام نقاط البيع</h1>", unsafe_allow_html=True)
    
    col_menu, col_inv = st.columns([2, 1])
    
    with col_menu:
        tabs = st.tabs(["الأسماك 🐟", "بوادي 🥣", "مشروبات 🥤", "خدمات أخرى 🚚"])
        
        # قائمة المنتجات (أضف أصنافك هنا)
        items_list = [
            {"name": "سمك بوري", "cat": "الأسماك", "price": 180, "unit": "كيلو"},
            {"name": "سمك بلطي", "cat": "الأسماك", "price": 120, "unit": "كيلو"},
            {"name": "شوربة سيفود", "cat": "بوادي", "price": 45, "unit": "حبة"},
            {"name": "بيبسي عائلي", "cat": "مشروبات", "price": 12, "unit": "حبة"},
            {"name": "خدمة توصيل", "cat": "خدمات أخرى", "price": 15, "unit": "حبة"}
        ]
        
        for tab, cat in zip(tabs, ["الأسماك", "بوادي", "مشروبات", "خدمات أخرى"]):
            with tab:
                cols = st.columns(2)
                cat_items = [i for i in items_list if i['cat'] == cat]
                for idx, item in enumerate(cat_items):
                    with cols[idx % 2]:
                        st.write(f"### {item['name']}")
                        qty = st.number_input(f"الكمية ({item['unit']})", min_value=0.1, value=1.0, key=f"q_{item['name']}")
                        if st.button(f"إضافة - {item['price']} ريال", key=f"b_{item['name']}"):
                            st.session_state.cart.append({"item": item['name'], "qty": qty, "price": item['price']})
                            st.toast(f"تم إضافة {item['name']}")

    with col_inv:
        st.markdown("<div class='invoice-card'>", unsafe_allow_html=True)
        st.subheader("🧾 فاتورة سماري")
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            st.dataframe(df_cart[['item', 'qty', 'price']], use_container_width=True)
            subtotal = (df_cart['qty'] * df_cart['price']).sum()
            tax = subtotal * 0.15
            total = subtotal + tax
            st.write(f"المجموع: {subtotal:.2f}")
            st.write(f"الضريبة 15%: {tax:.2f}")
            st.markdown(f"<h2 style='color:red;'>الإجمالي: {total:.2f} ريال</h2>", unsafe_allow_html=True)
            
            method = st.selectbox("الدفع", ["كاش", "شبكة", "تطبيق توصيل"])
            if st.button("حفظ وطباعة الفاتورة"):
                conn = get_connection()
                c = conn.cursor()
                c.execute("INSERT INTO invoices (total, tax, method, date) VALUES (?,?,?,?)", 
                          (total, tax, method, datetime.now().strftime("%Y-%m-%d %H:%M")))
                # تحديث الحسابات
                c.execute("UPDATE accounts SET balance = balance + ? WHERE code = '111'", (total,))
                conn.commit()
                conn.close()
                st.session_state.cart = []
                st.success("تمت العملية بنجاح")
                st.rerun()
        else:
            st.info("السلة فارغة")
        st.markdown("</div>", unsafe_allow_html=True)

# --- 7. صفحة المرتجعات ---
elif page == "المرتجعات والسجل":
    st.markdown("<h2 class='main-title'>🔄 سجل الفواتير والمرتجعات</h2>", unsafe_allow_html=True)
    conn = get_connection()
    df_invoices = pd.read_sql_query("SELECT * FROM invoices ORDER BY id DESC", conn)
    st.dataframe(df_invoices, use_container_width=True)
    
    inv_id = st.number_input("أدخل رقم الفاتورة لعمل مرتجع:", min_value=1, step=1)
    if st.button("تأكيد المرتجع ⚠️"):
        c = conn.cursor()
        c.execute("UPDATE invoices SET status = 'Returned' WHERE id = ?", (inv_id,))
        conn.commit()
        st.warning(f"تم تسجيل الفاتورة {inv_id} كمرتجع")
        st.rerun()
    conn.close()

# --- 8. شجرة الحسابات ---
elif page == "شجرة الحسابات":
    st.markdown("<h2 class='main-title'>📊 الأرصدة والمحاسبة</h2>", unsafe_allow
