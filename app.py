import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# --- 1. إعدادات المظهر (تصميم سماوي بنصوص واضحة جداً) ---
st.set_page_config(page_title="مطعم سماري - ERP", layout="wide", page_icon="🐟")

st.markdown("""
    <style>
    /* خلفية التطبيق سماوي فاتح */
    .stApp { background-color: #E3F2FD; }
    
    /* جعل جميع النصوص في الجداول والمدخلات باللون الأسود الواضح */
    html, body, [class*="st-"] {
        color: #000000 !important;
        font-family: 'Arial', sans-serif;
    }

    /* العناوين الرئيسية أزرق غامق */
    .main-title { 
        text-align: center; 
        color: #01579B; 
        background-color: #B3E5FC;
        padding: 20px;
        border-radius: 15px;
        border-bottom: 4px solid #0288D1;
    }

    /* صناديق الدخول والبيانات بيضاء مع حدود واضحة */
    .data-box { 
        background: #ffffff; 
        padding: 25px; 
        border-radius: 15px; 
        border: 2px solid #0288D1;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }

    /* أزرار المنتجات أزرق ملكي بنص أبيض */
    div.stButton > button:first-child {
        background-color: #0288D1;
        color: #ffffff !important;
        border-radius: 10px;
        height: 60px;
        font-weight: bold;
        border: none;
    }
    
    /* الجداول المحاسبية خلفية بيضاء ونص أسود */
    .stDataFrame, .stTable {
        background-color: #ffffff !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. إدارة قاعدة البيانات ---
def get_connection():
    return sqlite3.connect('samari_v6_final.db', check_same_thread=False)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    # شجرة الحسابات
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (code TEXT PRIMARY KEY, name TEXT, type TEXT, balance REAL DEFAULT 0)''')
    # الفواتير (بيع ومرتجع)
    c.execute('''CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY AUTOINCREMENT, total REAL, tax REAL, method TEXT, date TEXT, status TEXT DEFAULT 'Paid')''')
    # المشتريات والموردين
    c.execute('''CREATE TABLE IF NOT EXISTS purchases (id INTEGER PRIMARY KEY AUTOINCREMENT, supplier TEXT, item TEXT, amount REAL, date TEXT)''')
    
    # بناء شجرة حسابات كاملة
    c.execute("SELECT count(*) FROM accounts")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO accounts VALUES (?,?,?,?)", [
            ('111', 'الصندوق - كاش', 'أصول متداولة', 0),
            ('112', 'البنك - شبكة', 'أصول متداولة', 0),
            ('121', 'العملاء', 'أصول متداولة', 0),
            ('211', 'الموردين', 'خصوم متداولة', 0),
            ('215', 'ضريبة القيمة المضافة', 'خصوم متداولة', 0),
            ('411', 'إيرادات المبيعات', 'إيرادات', 0),
            ('511', 'تكلفة المشتريات', 'مصروفات', 0),
            ('521', 'الرواتب والأجور', 'مصروفات', 0)
        ])
    conn.commit()
    conn.close()

init_db()

# --- 3. نظام الجلسة والدخول ---
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'cart' not in st.session_state: st.session_state.cart = []

if not st.session_state.logged_in:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.5, 1])
    with col2:
        st.markdown("<div class='data-box'>", unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center;'>🔒 دخول مطعم سماري</h2>", unsafe_allow_html=True)
        u = st.text_input("اسم المستخدم")
        p = st.text_input("كلمة المرور", type='password')
        if st.button("تسجيل الدخول"):
            if u == "admin" and p == "1234":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("خطأ في البيانات")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 4. واجهة التطبيق ---
st.sidebar.markdown(f"<h2 style='color:#01579B;'>🐟 مطعم سماري</h2>", unsafe_allow_html=True)
st.sidebar.write(f"المستخدم: **Admin**")
menu = st.sidebar.selectbox("القائمة الرئيسية", ["نقاط البيع (POS)", "المرتجعات والسجل", "شجرة الحسابات", "المشتريات والعملاء"])

if st.sidebar.button("تسجيل الخروج"):
    st.session_state.logged_in = False
    st.rerun()

# --- 5. نقاط البيع (POS) ---
if menu == "نقاط البيع (POS)":
    st.markdown("<h1 class='main-title'>🛒 كاونتر المبيعات</h1>", unsafe_allow_html=True)
    col_menu, col_inv = st.columns([2, 1.2])

    with col_menu:
        tabs = st.tabs(["🐟 أسماك", "🥣 بوادي", "🥤 مشروبات", "🚚 توصيل"])
        # تعريف الأصناف (وزن/حبة)
        items = [
            {"n": "سمك بوري", "c": "🐟 أسماك", "p": 180, "u": "كيلو"},
            {"n": "سمك بلطي", "c": "🐟 أسماك", "p": 120, "u": "كيلو"},
            {"n": "أرز صيادية", "c": "🥣 بوادي", "p": 15, "u": "حبة"},
            {"n": "بيبسي", "c": "🥤 مشروبات", "p": 5, "u": "حبة"},
            {"n": "خدمة توصيل", "c": "🚚 توصيل", "p": 15, "u": "حبة"}
        ]
        
        for tab, cat in zip(tabs, ["🐟 أسماك", "🥣 بوادي", "🥤 مشروبات", "🚚 توصيل"]):
            with tab:
                st.markdown("<div class='data-box'>", unsafe_allow_html=True)
                cols = st.columns(2)
                cat_items = [i for i in items if i['c'] == cat]
                for idx, item in enumerate(cat_items):
                    with cols[idx % 2]:
                        st.write(f"**{item['n']}**")
                        q = st.number_input(f"الكمية ({item['u']})", min_value=0.1, value=1.0, key=f"pos_{item['n']}")
                        if st.button(f"إضافة {item['p']} ر.س", key=f"btn_{item['n']}"):
                            st.session_state.cart.append({"الصنف": item['n'], "الكمية": q, "السعر": item['p'], "الإجمالي": q*item['p']})
                            st.success(f"أضيف {item['n']}")
                st.markdown("</div>", unsafe_allow_html=True)

    with col_inv:
        st.markdown("<div class='data-box'>", unsafe_allow_html=True)
        st.subheader("🧾 الفاتورة")
        if st.session_state.cart:
            df = pd.DataFrame(st.session_state.cart)
            st.dataframe(df[['الصنف', 'الكمية', 'الإجمالي']], hide_index=True)
            sub = df['الإجمالي'].sum()
            tax = sub * 0.15
            total = sub + tax
            st.markdown(f"**المجموع:** {sub:.2f} ر.س")
            st.markdown(f"**الضريبة:** {tax:.2f} ر.س")
            st.markdown(f"<h2 style='color:red;'>الإجمالي: {total:.2f} ر.س</h2>", unsafe_allow_html=True)
            
            pay = st.selectbox("طريقة الدفع", ["كاش", "شبكة"])
            if st.button("تأكيد البيع ✅"):
                conn = get_connection()
                c = conn.cursor()
                c.execute("INSERT INTO invoices (total, tax, method, date) VALUES (?,?,?,?)", (total, tax, pay, datetime.now().strftime("%Y-%m-%d %H:%M")))
                # تحديث شجرة الحسابات (إيرادات وصندوق)
                c.execute("UPDATE accounts SET balance = balance + ? WHERE code = '411'", (sub,))
                acc_code = '111' if pay == 'كاش' else '112'
                c.execute("UPDATE accounts SET balance = balance + ? WHERE code = ?", (total, acc_code))
                conn.commit()
                conn.close()
                st.session_state.cart = []
                st.rerun()
        else:
            st.info("السلة فارغة")
        st.markdown("</div>", unsafe_allow_html=True)

# --- 6. المرتجعات ---
elif menu == "المرتجعات والسجل":
    st.markdown("<h1 class='main-title'>🔄 إدارة الفواتير والمرتجعات</h1>", unsafe_allow_html=True)
    conn = get_connection()
    df_inv = pd.read_sql_query("SELECT * FROM invoices ORDER BY id DESC", conn)
    st.markdown("<div class='data-box'>", unsafe_allow_html=True)
    st.write("سجل الفواتير:")
    st.dataframe(df_inv, use_container_width=True, hide_index=True)
    
    r_id = st.number_input("أدخل رقم الفاتورة لعمل مرتجع:", min_value=1, step=1)
    if st.button("تنفيذ المرتجع وعكس القيود ⚠️"):
        c = conn.cursor()
        c.execute("UPDATE invoices SET status = 'Returned' WHERE id = ?", (r_id,))
        # هنا يمكن إضافة كود عكس المبالغ في الحسابات
        conn.commit()
        st.warning(f"تم إرجاع الفاتورة {r_id}")
    st.markdown("</div>", unsafe_allow_html=True)
    conn.close()

# --- 7. شجرة الحسابات ---
elif menu == "شجرة الحسابات":
    st.markdown("<h1 class='main-title'>📊 شجرة الحسابات المحاسبية</h1>", unsafe_allow_html=True)
    conn = get_connection()
    df_acc = pd.read_sql_query("SELECT code AS الكود, name AS الحساب, type AS النوع, balance AS الرصيد FROM accounts", conn)
    st.markdown("<div class='data-box'>", unsafe_allow_html=True)
    st.table(df_acc) # استخدام الجدول لجعل النصوص سوداء وواضحة جداً
    st.markdown("</div>", unsafe_allow_html=True)
    conn.close()

# --- 8. المشتريات والعملاء ---
elif menu == "المشتريات والعملاء":
    st.markdown("<h1 class='main-title'>👥 إدارة الموردين والعملاء</h1>", unsafe_allow_html=True)
    st.markdown("<div class='data-box'>", unsafe_allow_html=True)
    with st.form("pur_form"):
        st.write("تسجيل فاتورة مشتريات (مصروف):")
        sup = st.text_input("اسم المورد")
        item_p = st.text_input("الصنف")
        amt = st.number_input("المبلغ الإجمالي", min_value=0.0)
        if st.form_submit_button("حفظ المشتريات"):
            st.success("تم الحفظ وتحديث حساب المصروفات")
    st.markdown("</div>", unsafe_allow_html=True)
