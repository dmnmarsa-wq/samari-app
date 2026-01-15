import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- 1. إعدادات المظهر (ألوان قوية وواضحة جداً) ---
st.set_page_config(page_title="ERP مطعم سماري", layout="wide")

st.markdown("""
    <style>
    /* خلفية التطبيق رمادي فاتح جداً لراحة العين */
    .stApp { background-color: #F0F2F5; }
    
    /* إجبار كافة النصوص على اللون الأسود الغامق */
    * { color: #1A1A1A !important; font-family: 'Arial', sans-serif; }

    /* العناوين باللون الأزرق الغامق */
    .main-title { 
        text-align: center; color: #ffffff !important; 
        background-color: #004D40; padding: 15px; border-radius: 10px;
    }

    /* صناديق البيانات بيضاء مع حدود سوداء واضحة */
    .data-card { 
        background: #FFFFFF; padding: 20px; border-radius: 10px; 
        border: 2px solid #333333; margin-bottom: 10px;
    }

    /* أزرار البيع ملونة وواضحة */
    .stButton>button {
        background-color: #00796B !important; color: white !important;
        border-radius: 8px; height: 50px; font-weight: bold; width: 100%;
    }
    
    /* جداول البيانات المحاسبية */
    .styled-table { width: 100%; border-collapse: collapse; background: white; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. قاعدة البيانات المحاسبية ---
def get_db():
    conn = sqlite3.connect('samari_v7.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS accounts (code TEXT PRIMARY KEY, name TEXT, type TEXT, balance REAL)')
    c.execute('CREATE TABLE IF NOT EXISTS sales (id INTEGER PRIMARY KEY, item TEXT, total REAL, tax REAL, date TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY, date TEXT, desc TEXT, debit_acc TEXT, credit_acc TEXT, amount REAL)')
    
    # التأكد من وجود الحسابات الأساسية
    c.execute("SELECT count(*) FROM accounts")
    if c.fetchone()[0] == 0:
        acc_data = [
            ('101', 'الصندوق (كاش)', 'أصول', 0.0),
            ('102', 'البنك (شبكة)', 'أصول', 0.0),
            ('201', 'الموردين', 'خصوم', 0.0),
            ('401', 'إيرادات المبيعات', 'إيرادات', 0.0),
            ('501', 'تكلفة المشتريات', 'مصروفات', 0.0),
            ('502', 'رواتب وكهرباء', 'مصروفات', 0.0)
        ]
        c.executemany("INSERT INTO accounts VALUES (?,?,?,?)", acc_data)
    conn.commit()
    conn.close()

init_db()

# --- 3. نظام الدخول ---
if 'auth' not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("<h1 class='main-title'>🔒 دخول نظام سماري المحاسبي</h1>", unsafe_allow_html=True)
    with st.container():
        st.write("---")
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type='password')
        if st.button("دخول"):
            if u == "admin" and p == "1234":
                st.session_state.auth = True
                st.rerun()
            else: st.error("خطأ في البيانات")
    st.stop()

# --- 4. القائمة الجانبية ---
st.sidebar.markdown("## 🐟 مطعم سماري")
menu = st.sidebar.radio("انتقل إلى:", ["لوحة التقارير", "نقاط البيع (POS)", "شجرة الحسابات", "القيود والعمليات"])

# --- 5. لوحة التقارير (Dashboard) ---
if menu == "لوحة التقارير":
    st.markdown("<h1 class='main-title'>📈 لوحة تقارير الأداء</h1>", unsafe_allow_html=True)
    conn = get_db()
    df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
    
    c1, c2, c3 = st.columns(3)
    with c1: st.metric("إجمالي المبيعات", f"{df_sales['total'].sum():.2f} ر.س")
    with c2: st.metric("إجمالي الضريبة", f"{df_sales['tax'].sum():.2f} ر.س")
    with c3: st.metric("عدد العمليات", len(df_sales))
    
    st.write("### سجل المبيعات الأخير")
    st.dataframe(df_sales.tail(10), use_container_width=True)
    conn.close()

# --- 6. نقاط البيع (POS) ---
elif menu == "نقاط البيع (POS)":
    st.markdown("<h1 class='main-title'>🛒 كاونتر المبيعات</h1>", unsafe_allow_html=True)
    col_products, col_bill = st.columns([2, 1])
    
    if 'cart' not in st.session_state: st.session_state.cart = []

    with col_products:
        st.write("### قائمة الأصناف (حبة / وزن)")
        items = [
            {"n": "سمك بوري", "p": 180, "u": "كيلو"},
            {"n": "سمك بلطي", "p": 120, "u": "كيلو"},
            {"n": "شوربة", "p": 15, "u": "حبة"},
            {"n": "بيبسي", "p": 5, "u": "حبة"}
        ]
        for it in items:
            with st.container():
                st.markdown(f"<div class='data-card'><b>{it['n']}</b> - {it['p']} ر.س / {it['u']}</div>", unsafe_allow_html=True)
                qty = st.number_input(f"الكمية ({it['n']})", 0.1, 100.0, 1.0, key=it['n'])
                if st.button(f"إضافة {it['n']} للسلة"):
                    st.session_state.cart.append({"الصنف": it['n'], "السعر": it['p'], "الكمية": qty, "الإجمالي": it['p']*qty})
                    st.rerun()

    with col_bill:
        st.write("### 🧾 السلة")
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            st.table(df_cart)
            sub = df_cart['الإجمالي'].sum()
            tax = sub * 0.15
            st.write(f"المجموع: {sub:.2f}")
            st.error(f"### الإجمالي النهائي: {sub+tax:.2f} ر.س")
            if st.button("إتمام العملية ✅"):
                conn = get_db()
                c = conn.cursor()
                c.execute("INSERT INTO sales (item, total, tax, date) VALUES (?,?,?,?)", ("فاتورة مجمعة", sub+tax, tax, datetime.now().strftime("%Y-%m-%d")))
                c.execute("UPDATE accounts SET balance = balance + ? WHERE code = '101'", (sub+tax,))
                c.execute("UPDATE accounts SET balance = balance + ? WHERE code = '401'", (sub,))
                conn.commit()
                conn.close()
                st.session_state.cart = []
                st.success("تم ترحيل الفاتورة للحسابات")
                st.rerun()
        else: st.info("السلة فارغة")

# --- 7. شجرة الحسابات ---
elif menu == "شجرة الحسابات":
    st.markdown("<h1 class='main-title'>📂 شجرة الحسابات المحاسبية</h1>", unsafe_allow_html=True)
    conn = get_db()
    df_acc = pd.read_sql_query("SELECT code AS الكود, name AS الحساب, type AS النوع, balance AS الرصيد FROM accounts", conn)
    st.write("---")
    st.dataframe(df_acc, use_container_width=True, hide_index=True)
    conn.close()

# --- 8. القيود اليومية ---
elif menu == "الالقيود والعمليات":
    st.markdown("<h1 class='main-title'>📝 تسجيل القيود والمرتجعات</h1>", unsafe_allow_html=True)
    with st.form("entry"):
        st.write("إضافة قيد يدوي / مرتجع:")
        desc = st.text_input("شرح العملية")
        amt = st.number_input("المبلغ", 1.0)
        if st.form_submit_button("حفظ القيد"):
            st.success("تم تسجيل العملية في دفتر الأستاذ")
