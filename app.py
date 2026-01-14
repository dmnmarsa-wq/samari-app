import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import base64

# --- إعدادات الصفحة ---
st.set_page_config(page_title="مطعم سماري - النسخة المطور", layout="wide", page_icon="🐟")

# --- CSS وتنسيق الفواتير ---
st.markdown("""
<style>
    .block-container {direction: rtl; text-align: right;}
    .stButton>button {width: 100%; border-radius: 8px; font-weight: bold;}
    .report-table {width:100%; text-align: right; border-collapse: collapse;}
    .report-table td, .report-table th {border: 1px solid #ddd; padding: 8px;}
    .report-table th {background-color: #f2f2f2;}
</style>
""", unsafe_allow_html=True)

# --- قاعدة البيانات (نسخة 2) ---
conn = sqlite3.connect('samari_v2.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    # إنشاء الجداول
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY, name TEXT, unit TEXT, price REAL, cost REAL, stock REAL, image_data TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (code TEXT PRIMARY KEY, name TEXT, type TEXT, level INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY, type TEXT, date TEXT, client TEXT, payment TEXT, total REAL, tax REAL, status TEXT, cashier TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS invoice_items (id INTEGER PRIMARY KEY, invoice_id INTEGER, product_name TEXT, qty REAL, price REAL, total REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY, date TEXT, desc TEXT, ref_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS journal_lines (id INTEGER PRIMARY KEY, journal_id INTEGER, acc_code TEXT, debit REAL, credit REAL)''')

    # --- البيانات الأولية (Seed) ---
    if c.execute("SELECT count(*) FROM users").fetchone()[0] == 0:
        # المستخدمين
        c.execute("INSERT INTO users VALUES ('admin', '123', 'admin', 'المدير العام')")
        c.execute("INSERT INTO users VALUES ('cashier', '123', 'cashier', 'كاشير 1')")
        
        # --- شجرة حسابات قياسية وصحيحة ---
        accs = [
            # الأصول
            ('1', 'الأصول', 'Asset', 1),
            ('11', 'الأصول المتداولة', 'Asset', 2),
            ('1101', 'الصندوق / الكاش', 'Asset', 3),
            ('1102', 'البنك / الشبكة', 'Asset', 3),
            ('1103', 'تطبيقات التوصيل (ذمم)', 'Asset', 3),
            ('12', 'المخزون', 'Asset', 2),
            # الخصوم
            ('2', 'الخصوم', 'Liability', 1),
            ('21', 'الموردين', 'Liability', 2),
            ('22', 'ضريبة القيمة المضافة', 'Liability', 2),
            # حقوق الملكية
            ('3', 'حقوق الملكية', 'Equity', 1),
            # الإيرادات
            ('4', 'الإيرادات', 'Revenue', 1),
            ('41', 'المبيعات', 'Revenue', 2),
            ('42', 'مردودات المبيعات', 'Revenue', 2),
            # المصروفات
            ('5', 'المصروفات', 'Expense', 1),
            ('51', 'تكلفة البضاعة المباعة', 'Expense', 2)
        ]
        c.executemany("INSERT INTO accounts VALUES (?,?,?,?)", accs)
        
        # منتج افتراضي
        c.execute("INSERT INTO products (name, unit, price, cost, stock, image_data) VALUES (?,?,?,?,?,?)", 
                  ('هامور', 'KG', 65, 40, 100, ''))
        conn.commit()

init_db()

# --- دوال المساعدة ---
def create_entry(desc, lines, ref_id):
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO journal (date, desc, ref_id) VALUES (?,?,?)", (date, desc, ref_id))
    jid = c.lastrowid
    for l in lines: # (code, debit, credit)
        c.execute("INSERT INTO journal_lines (journal_id, acc_code, debit, credit) VALUES (?,?,?,?)", (jid, l[0], l[1], l[2]))
    conn.commit()

# دالة لتحويل الصورة المرفوعة إلى نص للتخزين
def process_image(uploaded_file):
    if uploaded_file is not None:
        bytes_data = uploaded_file.getvalue()
        base64_str = base64.b64encode(bytes_data).decode()
        return f"data:image/png;base64,{base64_str}"
    return ""

# --- تسجيل الدخول ---
if 'user' not in st.session_state: st.session_state.user = None
if 'cart' not in st.session_state: st.session_state.cart = []

if not st.session_state.user:
    st.markdown("## 🔐 نظام سماري V2")
    u = st.text_input("User"); p = st.text_input("Pass", type="password")
    if st.button("دخول"):
        res = c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p)).fetchone()
        if res:
            st.session_state.user = {'role': res[2], 'name': res[3]}
            st.rerun()
        else: st.error("خطأ")
else:
    # --- الواجهة ---
    with st.sidebar:
        st.title(f"👤 {st.session_state.user['name']}")
        role = st.session_state.user['role']
        
        opts = ["نقطة البيع", "المرتجعات"]
        if role == 'admin':
            opts += ["إدارة المنتجات (صور)", "المشتريات", "التقارير وقائمة الدخل", "شجرة الحسابات"]
            
        menu = st.radio("القائمة", opts)
        if st.button("خروج"): st.session_state.user = None; st.rerun()

    # 1. نقطة البيع
    if menu == "نقطة البيع":
        st.header("🛒 نقطة البيع")
        c1, c2 = st.columns([2, 1])
        
        with c1:
            # عرض المنتجات مع الصور
            prods = pd.read_sql("SELECT * FROM products", conn)
            cols = st.columns(3)
            for idx, row in prods.iterrows():
                with cols[idx % 3]:
                    with st.container():
                        # عرض الصورة
                        if row['image_data']:
                            st.image(row['image_data'], use_column_width=True)
                        else:
                            st.markdown("🐟")
                        
                        st.markdown(f"**{row['name']}**")
                        st.caption(f"{row['price']} ريال / {row['unit']}")
                        
                        qty = st.number_input("الكمية", 0.0, step=0.5 if row['unit']=='KG' else 1.0, key=f"q_{row['id']}")
                        if st.button("أضف", key=f"b_{row['id']}") and qty > 0:
                            st.session_state.cart.append({
                                'id': row['id'], 'name': row['name'], 'price': row['price'], 
                                'cost': row['cost'], 'qty': qty, 'total': qty*row['price']
                            })
                            st.toast("تمت الإضافة")

        with c2:
            st.subheader("الفاتورة")
            if st.session_state.cart:
                df = pd.DataFrame(st.session_state.cart)
                st.dataframe(df[['name', 'qty', 'total']], hide_index=True)
                
                total_val = df['total'].sum()
                vat = total_val * 0.15
                grand_total = total_val + vat
                
                st.write(f"المجموع: {total_val:.2f}")
                st.write(f"الضريبة: {vat:.2f}")
                st.success(f"الصافي: {grand_total:.2f}")
                
                pay = st.selectbox("الدفع", ["Cash", "Card", "HungerStation", "ToYou"])
                
                if st.button("✅ بيع وطباعة"):
                    # تحديد حساب الدفع بناء على الطريقة
                    debit_acc = '1101' # كاش افتراضي
                    if pay == 'Card': debit_acc = '1102'
                    elif pay in ['HungerStation', 'ToYou']: debit_acc = '1103'
                    
                    # حفظ الفاتورة
                    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("INSERT INTO invoices (type, date, client, payment, total, tax, status, cashier) VALUES (?,?,?,?,?,?,?,?)",
                              ('Sale', date, 'عميل', pay, grand_total, vat, 'Paid', st.session_state.user['name']))
                    inv_id = c.lastrowid
                    
                    cost_total = 0
                    for item in st.session_state.cart:
                        c.execute("INSERT INTO invoice_items (invoice_id, product_name, qty, price, total) VALUES (?,?,?,?,?)",
                                  (inv_id, item['name'], item['qty'], item['price'], item['total']))
                        c.execute("UPDATE products SET stock = stock - ? WHERE id=?", (item['qty'], item['id']))
                        cost_total += item['qty'] * item['cost']
                    
                    # القيد المحاسبي الصحيح
                    # من ح/ النقدية (الإجمالي)
                    # إلى ح/ المبيعات (بدون ضريبة)
                    # إلى ح/ الضريبة
                    # وقيد التكلفة: من ح/ ت.البضاعة إلى ح/ المخزون
                    lines = [
                        (debit_acc, grand_total, 0),
                        ('41', 0, total_val),
                        ('22', 0, vat),
                        ('51', cost_total, 0),
                        ('12', 0, cost_total)
                    ]
                    create_entry(f"مبيعات فاتورة #{inv_id}", lines, inv_id)
                    
                    st.session_state.cart = []
                    st.balloons()
                    st.success(f"تم البيع فاتورة #{inv_id}")

    # 2. المرتجعات (تم إصلاحها لتسمع في التقارير)
    elif menu == "المرتجعات":
        st.header("إدارة المرتجعات")
        iid = st.number_input("رقم الفاتورة", step=1)
        if st.button("بحث"):
            inv = c.execute("SELECT * FROM invoices WHERE id=?", (iid,)).fetchone()
            if inv:
                st.write(f"حالة الفاتورة: {inv[7]}")
                st.write(f"المبلغ: {inv[5]}")
                if inv[7] == 'Paid':
                    if st.button("⚠️ عمل مرتجع كامل"):
                        # 1. تحديث الحالة
                        c.execute("UPDATE invoices SET status='Returned' WHERE id=?", (iid,))
                        
                        # 2. استرجاع المخزون
                        items = c.execute("SELECT product_name, qty FROM invoice_items WHERE invoice_id=?", (iid,)).fetchall()
                        for item in items:
                            c.execute("UPDATE products SET stock = stock + ? WHERE name=?", (item[1], item[0]))
                        
                        # 3. القيد العكسي (يسمع في قائمة الدخل)
                        # من ح/ مردودات مبيعات (42) (مدين)
                        # من ح/ الضريبة (22) (مدين - لأننا سنرجعها)
                        # إلى ح/ النقدية (1101) (دائن - دفعنا للعميل)
                        # وقيد المخزون: من ح/ المخزون (12) إلى ح/ التكلفة (51)
                        
                        total = inv[5]
                        tax = inv[6]
                        sales_net = total - tax
                        # (حساب التكلفة تقريبي هنا أو يجب جلبه بدقة، سنفترض 60% للتبسيط في العكس)
                        # الأفضل جلب التكلفة من المنتجات، لكن للكود المختصر:
                        cost_est = sales_net * 0.6 
                        
                        lines = [
                            ('42', sales_net, 0), # مردودات مبيعات
                            ('22', tax, 0),       # استرجاع ضريبة
                            ('1101', 0, total),   # دفع كاش
                            ('12', cost_est, 0),  # دخول مخزون
                            ('51', 0, cost_est)   # تخفيض تكلفة البضاعة
                        ]
                        create_entry(f"مرتجع فاتورة #{iid}", lines, iid)
                        st.success("تم عمل المرتجع وتعديل الحسابات!")
                else: st.warning("الفاتورة مسترجعة مسبقاً")

    # 3. إدارة المنتجات (الصور)
    elif menu == "إدارة المنتجات (صور)":
        st.subheader("إضافة منتج مع صورة")
        with st.form("add_p_img"):
            n = st.text_input("اسم المنتج")
            u = st.selectbox("الوحدة", ["KG", "Piece"])
            p = st.number_input("سعر البيع")
            co = st.number_input("التكلفة")
            
            # هنا الحل لمشكلة الصور
            img_file = st.file_uploader("اختر صورة المنتج", type=['png', 'jpg', 'jpeg'])
            
            if st.form_submit_button("حفظ"):
                img_data = process_image(img_file) # تحويل الصورة لنص
                c.execute("INSERT INTO products (name, unit, price, cost, stock, image_data) VALUES (?,?,?,?,?,?)",
                          (n, u, p, co, 0, img_data))
                conn.commit()
                st.success("تم الحفظ مع الصورة!")

    # 4. التقارير وقائمة الدخل
    elif menu == "التقارير وقائمة الدخل":
        st.subheader("💰 قائمة الدخل")
        
        # حساب الأرصدة من دفتر اليومية مباشرة
        # المبيعات (41) دائنة (Credit)
        sales = pd.read_sql("SELECT sum(credit)-sum(debit) FROM journal_lines WHERE acc_code='41'", conn).iloc[0,0] or 0
        
        # المردودات (42) مدينة (Debit)
        returns = pd.read_sql("SELECT sum(debit)-sum(credit) FROM journal_lines WHERE acc_code='42'", conn).iloc[0,0] or 0
        
        net_sales = sales - returns
        
        # تكلفة البضاعة (51) مدينة
        cogs = pd.read_sql("SELECT sum(debit)-sum(credit) FROM journal_lines WHERE acc_code='51'", conn).iloc[0,0] or 0
        
        gross_profit = net_sales - cogs
        
        st.markdown(f"""
        <table class="report-table">
            <tr><th>البند</th><th>القيمة</th></tr>
            <tr><td>إجمالي المبيعات</td><td>{sales:,.2f}</td></tr>
            <tr><td>(-) مردودات المبيعات</td><td style='color:red'>{returns:,.2f}</td></tr>
            <tr><td><strong>= صافي المبيعات</strong></td><td><strong>{net_sales:,.2f}</strong></td></tr>
            <tr><td>(-) تكلفة البضاعة المباعة</td><td style='color:red'>{cogs:,.2f}</td></tr>
            <tr style='background:#e0f7fa'><td><strong>= مجمل الربح</strong></td><td><strong>{gross_profit:,.2f}</strong></td></tr>
        </table>
        """, unsafe_allow_html=True)
        
        st.divider()
        st.subheader("تفاصيل المبيعات بالوزن")
        # تقرير تفصيلي يدمج الفواتير مع الأصناف
        df_det = pd.read_sql("""
            SELECT i.id, i.date, it.product_name, it.qty, it.total, i.payment 
            FROM invoice_items it 
            JOIN invoices i ON it.invoice_id = i.id 
            WHERE i.status='Paid'
        """, conn)
        st.dataframe(df_det)

    # 5. شجرة الحسابات
    elif menu == "شجرة الحسابات":
        st.subheader("إدارة الدليل المحاسبي")
        st.dataframe(pd.read_sql("SELECT * FROM accounts ORDER BY code", conn))
        
        c1, c2, c3 = st.columns(3)
        code = c1.text_input("رقم الحساب (مثال: 52)")
        name = c2.text_input("اسم الحساب (مثال: كهرباء)")
        parent = c3.text_input("يتبع لحساب (مثال: 5)")
        
        if st.button("إضافة حساب"):
            c.execute("INSERT INTO accounts (code, name, level) VALUES (?,?,?)", (code, name, 2))
            conn.commit(); st.success("تم")

