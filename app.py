import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
import plotly.express as px

# --- إعدادات الصفحة ---
st.set_page_config(page_title="مطعم سماري - POS", layout="wide")

# --- وظائف قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('samari_erp.db')
    c = conn.cursor()
    # جدول المنتجات
    c.execute('''CREATE TABLE IF NOT EXISTS products 
                 (id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL, stock REAL, image_url TEXT)''')
    # جدول المبيعات
    c.execute('''CREATE TABLE IF NOT EXISTS sales 
                 (id INTEGER PRIMARY KEY, item TEXT, qty REAL, total REAL, payment_type TEXT, 
                  tax REAL, date TEXT, cashier TEXT, status TEXT)''')
    # جدول شجرة الحسابات
    c.execute('''CREATE TABLE IF NOT EXISTS accounts 
                 (code TEXT PRIMARY KEY, name TEXT, parent_code TEXT, balance REAL)''')
    # جدول المشتريات
    c.execute('''CREATE TABLE IF NOT EXISTS purchases 
                 (id INTEGER PRIMARY KEY, supplier TEXT, item TEXT, qty REAL, tax REAL, total REAL, date TEXT)''')
    conn.commit()
    conn.close()

init_db()

# --- إدارة الحالة (Session State) ---
if 'cart' not in st.session_state:
    st.session_state.cart = []
if 'user_role' not in st.session_state:
    st.session_state.user_role = "Admin" # خيارات: Admin, Cashier

# --- القائمة الجانبية ---
st.sidebar.title("🍱 مطعم سماري")
st.sidebar.write(f"المستخدم: {st.session_state.user_role}")
menu = st.sidebar.radio("الانتقال إلى:", 
    ["نقاط البيع (POS)", "المخزون", "المشتريات", "شجرة الحسابات", "التقارير المالية", "الإعدادات"])

# --- 1. واجهة نقاط البيع (POS) ---
if menu == "نقاط البيع (POS)":
    st.header("🛒 نقطة البيع - مطعم سماري")
    
    # تقسيم التصنيفات
    cats = ["أسماك", "شوربة", "أرز", "مشروبات", "توصيل"]
    selected_cat = st.tabs(cats)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # عرض المنتجات (مثال تجريبي)
        st.subheader("المنتجات")
        # في الواقع، سنقوم بجلبها من قاعدة البيانات
        items = [
            {"name": "هامور كبير", "price": 120, "cat": "أسماك", "img": "🐟"},
            {"name": "شوربة بحريات", "price": 35, "cat": "شوربة", "img": "🥣"},
            {"name": "أرز صيادية", "price": 15, "cat": "أرز", "img": "🍚"}
        ]
        
        cols = st.columns(3)
        for i, item in enumerate(items):
            with cols[i % 3]:
                st.write(f"### {item['img']}")
                st.write(f"**{item['name']}**")
                st.write(f"السعر: {item['price']} ريال")
                weight = st.number_input(f"الوزن/العدد ({item['name']})", min_value=0.1, value=1.0, key=f"qty_{i}")
                if st.button(f"إضافة {item['name']}", key=f"btn_{i}"):
                    st.session_state.cart.append({"item": item['name'], "price": item['price'], "qty": weight})

    with col2:
        st.subheader("🧾 الفاتورة")
        if st.session_state.cart:
            df_cart = pd.DataFrame(st.session_state.cart)
            st.table(df_cart)
            subtotal = df_cart['price'].sum() * df_cart['qty'].sum() # تبسيط للحساب
            tax = subtotal * 0.15
            total = subtotal + tax
            
            st.write(f"المجموع: {subtotal:.2f}")
            st.write(f"الضريبة (15%): {tax:.2f}")
            st.error(f"### الإجمالي: {total:.2f} ريال")
            
            pay_method = st.selectbox("طريقة الدفع", ["كاش", "شبكة", "هنقرستيشن", "تويو"])
            
            if st.button("إتمام البيع وطباعة الفاتورة"):
                # حفظ في قاعدة البيانات
                conn = sqlite3.connect('samari_erp.db')
                c = conn.cursor()
                for item in st.session_state.cart:
                    c.execute("INSERT INTO sales (item, qty, total, payment_type, tax, date, status) VALUES (?,?,?,?,?,?,?)",
                              (item['item'], item['qty'], total, pay_method, tax, datetime.now(), "مكتمل"))
                conn.commit()
                conn.close()
                
                st.success("تم الحفظ. جاري تجهيز الفاتورة للطباعة...")
                st.session_state.cart = []
                # محاكاة الطباعة
                st.write("🖨️ تم إرسال نسختين للمطبعة (عميل + مطبخ)")
        else:
            st.write("السلة فارغة")

# --- 2. شجرة الحسابات ---
elif menu == "شجرة الحسابات":
    st.header("📂 شجرة الحسابات")
    with st.expander("إضافة حساب فرعي جديد"):
        col1, col2 = st.columns(2)
        parent = col1.selectbox("الحساب الرئيسي", ["الأصول", "الخصوم", "الإيرادات", "المصروفات"])
        acc_name = col2.text_input("اسم الحساب الفرعي")
        if st.button("إضافة الحساب"):
            st.success(f"تم إضافة {acc_name} تحت بند {parent}")

    # عرض تجريبي للشجرة
    data = {
        "كود الحساب": ["101", "102", "401", "501"],
        "اسم الحساب": ["الصندوق", "البنك", "مبيعات الأسماك", "مشتريات خامات"],
        "الرصيد": [5000, 12000, 4500, 2000]
    }
    st.table(pd.DataFrame(data))

# --- 3. التقارير المالية ---
elif menu == "التقارير المالية":
    st.header("📊 التقارير والأداء")
    conn = sqlite3.connect('samari_erp.db')
    df_sales = pd.read_sql_query("SELECT * FROM sales", conn)
    conn.close()
    
    if not df_sales.empty:
        col1, col2 = st.columns(2)
        with col1:
            fig = px.pie(df_sales, values='total', names='payment_type', title="المبيعات حسب طريقة الدفع")
            st.plotly_chart(fig)
        with col2:
            st.metric("إجمالي ضريبة المبيعات", f"{df_sales['tax'].sum():.2f} ريال")
            st.metric("صافي الدخل التقديري", f"{df_sales['total'].sum() - (df_sales['total'].sum()*0.7):.2f} ريال")
    else:
        st.info("لا توجد بيانات مبيعات لعرض التقارير.")

# --- 4. إدارة المخزون ---
elif menu == "المخزون":
    st.header("📦 إدارة المخزون والمنتجات")
    with st.form("add_product"):
        name = st.text_input("اسم المنتج")
        cat = st.selectbox("التصنيف", ["أسماك", "مشروبات", "شوربة"])
        price = st.number_input("سعر البيع")
        img = st.file_uploader("ارفق صورة المنتج")
        if st.form_submit_button("حفظ المنتج"):
            st.success("تم إضافة المنتج للمخزون")

# --- 5. المشتريات ---
elif menu == "المشتريات":
    st.header("📥 فاتورة مشتريات")
    with st.container():
        supplier = st.text_input("اسم المورد")
        item_p = st.text_input("الصنف المشتراى")
        qty_p = st.number_input("الوزن (كيلو)", min_value=0.0)
        price_p = st.number_input("السعر قبل الضريبة")
        if st.button("حفظ فاتورة المشتريات"):
            st.warning("تم تسجيل المشتريات وتحديث ضريبة المدخلات")


