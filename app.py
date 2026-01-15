import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px

# --- 1. إعدادات الهوية والتنسيق (CSS) ---
st.set_page_config(page_title="مطعم سماري المتكامل", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #F8F9FA; }
    .main-title { text-align: center; color: #1E3A5F; font-family: 'Arial'; border-bottom: 2px solid #1E3A5F; padding-bottom: 10px; }
    div.stButton > button:first-child {
        background-color: #1E3A5F; color: white; border-radius: 12px; height: 80px; width: 100%; font-size: 18px; font-weight: bold;
    }
    .invoice-box { background: white; padding: 20px; border-radius: 15px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 1px solid #1E3A5F; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. إدارة قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('samari_erp_v2.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY, item TEXT, weight REAL, total REAL, tax REAL, method TEXT, date TEXT, cashier TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS inventory (id INTEGER PRIMARY KEY, name TEXT, stock REAL, price REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (code TEXT PRIMARY KEY, name TEXT, balance REAL, type TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- 3. نظام الجلسة (للحفاظ على الفاتورة) ---
if 'cart' not in st.session_state: st.session_state.cart = []
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_role' not in st.session_state: st.session_state.user_role = ""

# --- 4. شاشة تسجيل الدخول ---
if not st.session_state.logged_in:
    st.markdown("<h1 class='main-title'>🔒 تسجيل الدخول - مطعم سماري</h1>", unsafe_allow_html=True)
    user = st.text_input("اسم المستخدم")
    pw = st.text_input("كلمة المرور", type='password')
    if st.button("دخول"):
        if user == "admin" and pw == "123":
            st.session_state.logged_in = True
            st.session_state.user_role = "Admin"
            st.rerun()
        elif user == "cashier" and pw == "123":
            st.session_state.logged_in = True
            st.session_state.user_role = "Cashier"
            st.rerun()
        else:
            st.error("خطأ في البيانات")
    st.stop()

# --- 5. القائمة الجانبية ---
st.sidebar.markdown(f"### 👤 {st.session_state.user_role}")
if st.session_state.user_role == "Admin":
    menu = st.sidebar.radio("القائمة الرئيسية", ["نقاط البيع (POS)", "المخزون", "شجرة الحسابات", "التقارير المالية"])
else:
    menu = st.sidebar.radio("القائمة الرئيسية", ["نقاط البيع (POS)"])

if st.sidebar.button("تسجيل الخروج"):
    st.session_state.logged_in = False
    st.rerun()

# --- 6. واجهة نقاط البيع (POS) ---
if menu == "نقاط البيع (POS)":
    st.markdown("<h2 class='main-title'>🐟 واجهة المبيعات السريعة</h2>", unsafe_allow_html=True)
    col_products, col_invoice = st.columns([2, 1])

    with col_products:
        items = [
            {"name": "سمك بوري", "price": 180, "icon": "🐟"},
            {"name": "سمك بلطي", "price": 120, "icon": "🐠"},
            {"name": "جمبري", "price": 450, "icon": "🦐"},
            {"name": "أرز صيادية", "price": 15, "icon": "🍚"}
        ]
        
        cols = st.columns(2)
        for i, item in enumerate(items):
            with cols[i % 2]:
                st.write(f"### {item['icon']} {item['name']}")
                w = st.number_input(f"الوزن (كيلو) - {item['name']}", min_value=0.1, step=0.5, key=f"w_{i}")
                if st.button(f"إضافة {item['name']}", key=f"btn_{i}"):
                    st.session_state.cart.append({"item": item['name'], "qty": w, "total": item['price']*w})
                    st.toast("تمت الإضافة للسلة")

    with col_invoice:
        st.markdown("<div class='invoice-box'>", unsafe_allow_html=True)
        st.subheader("🧾 الفاتورة")
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            st.table(df_cart)
            subtotal = df_cart['total'].sum()
            tax = subtotal * 0.15
            grand_total = subtotal + tax
            
            st.write(f"المجموع: {subtotal:.2f}")
            st.write(f"الضريبة (15%): {tax:.2f}")
            st.error(f"### الإجمالي: {grand_total:.2f} ريال")
            
            method = st.selectbox("وسيلة الدفع", ["كاش", "شبكة", "هنقرستيشن", "تويو"])
            
            if st.button("إتمام البيع وطباعة الفاتورة 🖨️"):
                conn = sqlite3.connect('samari_erp_v2.db')
                c = conn.cursor()
                for _, row in df_cart.iterrows():
                    c.execute("INSERT INTO sales (item, weight, total, tax, method, date, cashier) VALUES (?,?,?,?,?,?,?)",
                              (row['item'], row['qty'], grand_total, tax, method, datetime.now().strftime("%Y-%m-%d %H:%M"), st.session_state.user_role))
                conn.commit()
                conn.close()
                st.session_state.cart = []
                st.success("تم الحفظ والطباعة")
                st.rerun()
        else:
            st.info("السلة فارغة")
        st.markdown("</div>", unsafe_allow_html=True)

# --- 7. التقارير المالية (للمدير فقط) ---
elif menu == "التقارير المالية":
    st.subheader("📊 تقارير المبيعات والضريبة")
    conn = sqlite3.connect('samari_erp_v2.db')
    df = pd.read_sql_query("SELECT * FROM sales", conn)
    conn.close()
    
    if not df.empty:
        c1, c2 = st.columns(2)
        with c1:
            fig1 = px.pie(df, values='total', names='item', title="المبيعات حسب نوع السمك")
            st.plotly_chart(fig1)
        with c2:
            fig2 = px.bar(df, x='method', y='total', color='method', title="المبيعات حسب وسيلة الدفع")
            st.plotly_chart(fig2)
        
        st.write("### سجل العمليات التفصيلي")
        st.dataframe(df)
    else:
        st.warning("لا توجد بيانات بعد")

# --- 8. شجرة الحسابات ---
elif menu == "شجرة الحسابات":
    st.subheader("📂 الإدارة المالية")
    with st.form("acc_form"):
        st.write("إضافة حساب فرعي جديد")
        acc_name = st.text_input("اسم الحساب")
        acc_type = st.selectbox("النوع", ["أصول", "خصوم", "إيرادات", "مصاريف"])
        if st.form_submit_button("إضافة"):
            st.success(f"تمت إضافة الحساب: {acc_name}")
