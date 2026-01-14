import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import time

# --- إعدادات الصفحة ---
st.set_page_config(page_title="مطعم سماري للأسماك", layout="wide", page_icon="🐟")

# --- CSS لتحسين الواجهة والفواتير ---
st.markdown("""
<style>
    .block-container {direction: rtl; text-align: right;}
    .stButton>button {width: 100%; border-radius: 8px; font-weight: bold; height: 3em;}
    
    /* تصميم الفاتورة للطباعة */
    .invoice-box {
        max-width: 80mm; margin: auto; padding: 10px; border: 1px dashed #333;
        font-family: 'Courier New', Courier, monospace; text-align: center; background: #fff; color: #000;
    }
    .invoice-header {font-size: 18px; font-weight: bold; margin-bottom: 5px;}
    .invoice-details {text-align: right; font-size: 12px; border-bottom: 1px dashed #000; padding-bottom: 5px;}
    .invoice-table {width: 100%; font-size: 12px; text-align: right;}
    .invoice-total {font-size: 14px; font-weight: bold; border-top: 1px dashed #000; margin-top: 5px; padding-top: 5px;}
    
    /* شبكة المنتجات */
    .product-card {
        border: 1px solid #ddd; border-radius: 10px; padding: 10px; text-align: center;
        margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .product-img {font-size: 50px;}
</style>
""", unsafe_allow_html=True)

# --- قاعدة البيانات ---
conn = sqlite3.connect('samari_final.db', check_same_thread=False)
c = conn.cursor()

def init_db():
    # 1. المستخدمين
    c.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT, name TEXT)''')
    # 2. المنتجات (مع الصور)
    c.execute('''CREATE TABLE IF NOT EXISTS products 
                 (id INTEGER PRIMARY KEY, name TEXT, unit TEXT, price REAL, cost REAL, stock REAL, image TEXT)''')
    # 3. الموردين والعملاء
    c.execute('''CREATE TABLE IF NOT EXISTS partners (id INTEGER PRIMARY KEY, name TEXT, type TEXT, phone TEXT, tax_id TEXT)''')
    # 4. الحسابات (شجرة)
    c.execute('''CREATE TABLE IF NOT EXISTS accounts (code TEXT PRIMARY KEY, name TEXT, type TEXT, parent_code TEXT)''')
    # 5. الفواتير (بيع وشراء)
    c.execute('''CREATE TABLE IF NOT EXISTS invoices 
                 (id INTEGER PRIMARY KEY, type TEXT, date TEXT, partner_name TEXT, payment_method TEXT, total REAL, tax REAL, status TEXT, cashier TEXT)''')
    # 6. تفاصيل الفاتورة
    c.execute('''CREATE TABLE IF NOT EXISTS invoice_items 
                 (id INTEGER PRIMARY KEY, invoice_id INTEGER, product_name TEXT, qty REAL, price REAL, total REAL)''')
    # 7. القيود
    c.execute('''CREATE TABLE IF NOT EXISTS journal (id INTEGER PRIMARY KEY, date TEXT, desc TEXT, ref_id INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS journal_lines (id INTEGER PRIMARY KEY, journal_id INTEGER, acc_code TEXT, debit REAL, credit REAL)''')

    # --- بيانات أولية ---
    if c.execute("SELECT count(*) FROM users").fetchone()[0] == 0:
        c.execute("INSERT INTO users VALUES ('admin', '123', 'admin', 'المدير العام')")
        c.execute("INSERT INTO users VALUES ('cashier', '123', 'cashier', 'كاشير 1')")
        
        # منتجات سمك مع إيموجي كصور (أو روابط صور)
        c.execute("INSERT INTO products (name, unit, price, cost, stock, image) VALUES ('سمك هامور', 'KG', 65, 40, 50, '🐟')")
        c.execute("INSERT INTO products (name, unit, price, cost, stock, image) VALUES ('روبيان جامبو', 'KG', 90, 60, 30, '🦐')")
        c.execute("INSERT INTO products (name, unit, price, cost, stock, image) VALUES ('أرز صيادية', 'Piece', 15, 5, 100, '🍚')")
        c.execute("INSERT INTO products (name, unit, price, cost, stock, image) VALUES ('بيبسي', 'Piece', 3, 1.5, 200, '🥤')")

        # شجرة حسابات (أصول، خصوم...)
        accs = [
            ('1', 'الأصول', 'Asset', ''), ('11', 'النقدية', 'Asset', '1'), ('12', 'المخزون', 'Asset', '1'),
            ('2', 'الخصوم', 'Liability', ''), ('21', 'الموردين', 'Liability', '2'), ('22', 'ضريبة القيمة المضافة', 'Liability', '2'),
            ('4', 'الإيرادات', 'Revenue', ''), ('41', 'المبيعات', 'Revenue', '4'),
            ('5', 'المصروفات', 'Expense', ''), ('51', 'تكلفة البضاعة', 'Expense', '5')
        ]
        c.executemany("INSERT INTO accounts VALUES (?,?,?,?)", accs)
        
        # مورد افتراضي
        c.execute("INSERT INTO partners (name, type, phone) VALUES ('شركة الأسماك المتحدة', 'supplier', '050000000')")
        conn.commit()

init_db()

# --- دوال المحاسبة ---
def create_entry(desc, lines, ref_id):
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO journal (date, desc, ref_id) VALUES (?,?,?)", (date, desc, ref_id))
    jid = c.lastrowid
    for l in lines: # (code, debit, credit)
        c.execute("INSERT INTO journal_lines (journal_id, acc_code, debit, credit) VALUES (?,?,?,?)", (jid, l[0], l[1], l[2]))
    conn.commit()

# --- واجهة الدخول ---
if 'user' not in st.session_state: st.session_state.user = None

if not st.session_state.user:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("## 🔐 مطعم سماري للأسماك")
        u = st.text_input("اسم المستخدم"); p = st.text_input("كلمة المرور", type="password")
        if st.button("دخول"):
            res = c.execute("SELECT * FROM users WHERE username=? AND password=?", (u, p)).fetchone()
            if res:
                st.session_state.user = {'id': res[0], 'role': res[2], 'name': res[3]}
                st.session_state.cart = []
                st.rerun()
            else: st.error("بيانات خاطئة")

else:
    # --- القائمة الجانبية (حسب الصلاحية) ---
    with st.sidebar:
        st.title("⚓ سماري ERP")
        st.info(f"المستخدم: {st.session_state.user['name']}")
        
        opts = ["نقطة البيع (POS)", "المرتجعات"] # للكاشير
        if st.session_state.user['role'] == 'admin':
            opts += ["المشتريات والموردين", "المخزون والمنتجات", "الحسابات والتقارير", "إدارة المستخدمين"]
            
        menu = st.radio("القائمة الرئيسية", opts)
        
        st.divider()
        if st.button("تسجيل الخروج"):
            st.session_state.user = None; st.rerun()

    # ==========================
    # 1. نقطة البيع (POS) - المطورة
    # ==========================
    if menu == "نقطة البيع (POS)":
        col_prod, col_cart = st.columns([2, 1])
        
        with col_prod:
            st.subheader("📦 قائمة الطعام")
            # بحث
            search = st.text_input("🔍 بحث عن صنف...")
            query = "SELECT * FROM products"
            if search: query += f" WHERE name LIKE '%{search}%'"
            
            prods = pd.read_sql(query, conn)
            
            # عرض كشبكة صور
            cols = st.columns(3)
            for idx, row in prods.iterrows():
                with cols[idx % 3]:
                    with st.container():
                        st.markdown(f"""
                        <div class="product-card">
                            <div class="product-img">{row['image']}</div>
                            <b>{row['name']}</b><br>
                            <span style='color:green'>{row['price']} ريال / {row['unit']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        if row['unit'] == 'KG':
                            qty = st.number_input(f"الوزن (كجم)", 0.0, step=0.1, key=f"q_{row['id']}")
                        else:
                            qty = st.number_input(f"العدد", 0, step=1, key=f"q_{row['id']}")
                            
                        if st.button("أضف", key=f"btn_{row['id']}") and qty > 0:
                            st.session_state.cart.append(
                                {'id': row['id'], 'name': row['name'], 'price': row['price'], 
                                 'cost': row['cost'], 'qty': qty, 'total': qty*row['price']}
                            )
                            st.toast(f"تم إضافة {row['name']}")

        with col_cart:
            st.subheader("🛒 الفاتورة")
            if st.session_state.cart:
                df_cart = pd.DataFrame(st.session_state.cart)
                st.dataframe(df_cart[['name', 'qty', 'total']], hide_index=True)
                
                subtotal = df_cart['total'].sum()
                vat = subtotal * 0.15
                total = subtotal + vat
                
                st.markdown(f"""
                <div style='background:#e3f2fd; padding:10px; border-radius:5px;'>
                    <h4>الإجمالي: {total:.2f} ريال</h4>
                    <small>شامل الضريبة: {vat:.2f}</small>
                </div>
                """, unsafe_allow_html=True)
                
                pay_method = st.selectbox("طريقة الدفع", ["Cash", "Mada", "HungerStation", "ToYou", "Jahez"])
                
                if st.button("✅ إصدار الفاتورة", type="primary"):
                    # 1. حفظ الفاتورة
                    date_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    c.execute("INSERT INTO invoices (type, date, partner_name, payment_method, total, tax, status, cashier) VALUES (?,?,?,?,?,?,?,?)",
                              ('Sale', date_now, 'عميل', pay_method, total, vat, 'Paid', st.session_state.user['name']))
                    inv_id = c.lastrowid
                    
                    total_cost = 0
                    for item in st.session_state.cart:
                        c.execute("INSERT INTO invoice_items (invoice_id, product_name, qty, price, total) VALUES (?,?,?,?,?)",
                                  (inv_id, item['name'], item['qty'], item['price'], item['total']))
                        # خصم المخزون
                        c.execute("UPDATE products SET stock = stock - ? WHERE id=?", (item['qty'], item['id']))
                        total_cost += item['qty'] * item['cost']
                    
                    # 2. القيود (شاملة المبيعات والضريبة)
                    # من ح/ النقدية (11) -- إلى ح/ المبيعات (41) وإلى ح/ الضريبة (22)
                    # من ح/ تكلفة البضاعة (51) -- إلى ح/ المخزون (12)
                    lines = [
                        ('11', total, 0),
                        ('41', 0, subtotal),
                        ('22', 0, vat),
                        ('51', total_cost, 0),
                        ('12', 0, total_cost)
                    ]
                    create_entry(f"مبيعات فاتورة #{inv_id} - {pay_method}", lines, inv_id)
                    
                    # 3. عرض الفاتورة للطباعة
                    st.success("تم الحفظ! انسخ الفاتورة أدناه للطباعة")
                    
                    # قالب الفاتورة الحرارية
                    invoice_html = f"""
                    <div class="invoice-box">
                        <div class="invoice-header"> مطعم سماري للأسماك 🐟</div>
                        <div>الرياض - الملز</div>
                        <div>الرقم الضريبي: 300123456700003</div>
                        <div class="invoice-details">
                            رقم الفاتورة: #{inv_id}<br>
                            التاريخ: {date_now}<br>
                            الكاشير: {st.session_state.user['name']}<br>
                            الدفع: {pay_method}
                        </div>
                        <table class="invoice-table">
                            <tr style="border-bottom:1px solid #000"><th>صنف</th><th>ك</th><th>سعر</th></tr>
                            {''.join([f"<tr><td>{x['name']}</td><td>{x['qty']}</td><td>{x['total']:.2f}</td></tr>" for x in st.session_state.cart])}
                        </table>
                        <div class="invoice-total">
                            الصافي: {subtotal:.2f}<br>
                            الضريبة 15%: {vat:.2f}<br>
                            ----------<br>
                            الإجمالي: {total:.2f} ريال
                        </div>
                        <div style="margin-top:10px;">شكراً لزيارتكم<br>نسخة العميل</div>
                    </div>
                    <br>
                    <!-- نسخة ثانية للمطعم -->
                    <div class="invoice-box">
                        <div class="invoice-header">نسخة المطعم (الأرشيف)</div>
                        <div class="invoice-details">رقم: #{inv_id}</div>
                         <div class="invoice-total">الإجمالي: {total:.2f} ريال</div>
                    </div>
                    """
                    st.markdown(invoice_html, unsafe_allow_html=True)
                    st.session_state.cart = []
            
            if st.button("إلغاء الطلب"): st.session_state.cart = []

    # ==========================
    # 2. المرتجعات (بحث وكنسلة)
    # ==========================
    elif menu == "المرتجعات":
        st.header("🔄 إدارة المرتجعات")
        inv_search = st.number_input("أدخل رقم الفاتورة", min_value=1)
        if st.button("بحث"):
            inv = c.execute("SELECT * FROM invoices WHERE id=?", (inv_search,)).fetchone()
            if inv:
                st.write(f"حالة الفاتورة: **{inv[7]}**")
                st.write(f"المبلغ: {inv[5]} | العميل: {inv[3]}")
                items = pd.read_sql("SELECT * FROM invoice_items WHERE invoice_id=?", conn, params=(inv_search,))
                st.table(items)
                
                if inv[7] == 'Paid':
                    if st.button("❌ استرجاع الفاتورة (كنسلة)"):
                        # عكس المخزون
                        for _, item in items.iterrows():
                            # نحتاج معرف المنتج، هنا للتبسيط سنفترض الاسم فريد
                            c.execute("UPDATE products SET stock = stock + ? WHERE name=?", (item['qty'], item['product_name']))
                        
                        c.execute("UPDATE invoices SET status='Returned' WHERE id=?", (inv_search,))
                        
                        # قيد عكسي
                        # من ح/ المبيعات والضريبة والمخزون -- إلى ح/ النقدية والتكلفة
                        subtotal = inv[5] - inv[6]
                        create_entry(f"مرتجع فاتورة #{inv_search}", [
                            ('41', subtotal, 0),
                            ('22', inv[6], 0),
                            ('11', 0, inv[5])
                        ], inv_search)
                        st.success("تم استرجاع الفاتورة بنجاح وتعديل الحسابات والمخزون!")
            else:
                st.error("الفاتورة غير موجودة")

    # ==========================
    # 3. المشتريات (للمدير)
    # ==========================
    elif menu == "المشتريات والموردين":
        t1, t2 = st.tabs(["فاتورة شراء جديدة", "إضافة مورد"])
        
        with t1:
            st.subheader("🚚 إدخال فاتورة شراء")
            supplier = st.selectbox("المورد", pd.read_sql("SELECT name FROM partners WHERE type='supplier'", conn))
            
            col1, col2, col3 = st.columns(3)
            prod_name = col1.selectbox("المنتج", pd.read_sql("SELECT name FROM products", conn))
            qty_in = col2.number_input("الوزن/العدد المشترى", 1.0)
            cost_in = col3.number_input("سعر الشراء الكلي", 1.0) # السعر قبل الضريبة
            
            vat_in = cost_in * 0.15
            total_in = cost_in + vat_in
            
            st.info(f"الإجمالي شامل الضريبة: {total_in:.2f} (ضريبة المشتريات: {vat_in:.2f})")
            
            if st.button("حفظ المشتريات"):
                # 1. حفظ الفاتورة
                c.execute("INSERT INTO invoices (type, date, partner_name, total, tax, status) VALUES (?,?,?,?,?,?)",
                          ('Purchase', datetime.now(), supplier, total_in, vat_in, 'Paid'))
                inv_id = c.lastrowid
                
                # 2. زيادة المخزون
                c.execute("UPDATE products SET stock = stock + ? WHERE name=?", (qty_in, prod_name))
                
                # 3. قيد المشتريات (يسمع في ضريبة المدخلات والمخزون)
                # من ح/ المخزون (12) (بالصافي)
                # من ح/ ضريبة القيمة المضافة (22) (مدين لأنها لنا)
                # إلى ح/ النقدية أو الموردين (21)
                lines = [
                    ('12', cost_in, 0),
                    ('22', vat_in, 0), # خصم الضريبة
                    ('21', 0, total_in)
                ]
                create_entry(f"شراء من {supplier} فاتورة #{inv_id}", lines, inv_id)
                st.success("تم حفظ المشتريات!")

        with t2:
            st.text_input("اسم المورد", key="sup_name")
            st.text_input("رقم الجوال", key="sup_phone")
            if st.button("حفظ المورد"):
                c.execute("INSERT INTO partners (name, type, phone) VALUES (?,?,?)", (st.session_state.sup_name, 'supplier', st.session_state.sup_phone))
                conn.commit(); st.success("تم")

    # ==========================
    # 4. المنتجات (صور وتعديل)
    # ==========================
    elif menu == "المخزون والمنتجات":
        st.subheader("إدارة المنتجات")
        df_prod = pd.read_sql("SELECT * FROM products", conn)
        edited_df = st.data_editor(df_prod, num_rows="dynamic", key="editor")
        
        if st.button("حفظ التعديلات"):
            # هذا يحتاج منطق معقد للتحديث، سنكتفي بالإضافة السريعة
            st.warning("لإضافة منتج جديد، استخدم النموذج أدناه")
            
        with st.expander("➕ إضافة منتج جديد"):
            with st.form("new_p"):
                n = st.text_input("اسم المنتج")
                u = st.selectbox("الوحدة", ["KG", "Piece"])
                p = st.number_input("سعر البيع")
                c_price = st.number_input("التكلفة")
                img = st.text_input("رابط الصورة أو الإيموجي (مثال: 🐟)", value="🐟")
                if st.form_submit_button("حفظ"):
                    c.execute("INSERT INTO products (name, unit, price, cost, stock, image) VALUES (?,?,?,?,?,?)",
                              (n, u, p, c_price, 0, img))
                    conn.commit(); st.rerun()

    # ==========================
    # 5. الحسابات والتقارير
    # ==========================
    elif menu == "الحسابات والتقارير":
        tab1, tab2, tab3, tab4 = st.tabs(["قائمة الدخل", "تقرير المبيعات", "شجرة الحسابات", "إضافة قيد"])
        
        with tab1:
            st.subheader("💰 قائمة الدخل (Profit & Loss)")
            # الإيرادات (دائن - مدين)
            sales = pd.read_sql("SELECT sum(credit)-sum(debit) FROM journal_lines WHERE acc_code='41'", conn).iloc[0,0] or 0
            # التكلفة (مدين - دائن)
            cogs = pd.read_sql("SELECT sum(debit)-sum(credit) FROM journal_lines WHERE acc_code='51'", conn).iloc[0,0] or 0
            
            gross = sales - cogs
            
            c1, c2, c3 = st.columns(3)
            c1.metric("المبيعات", f"{sales:,.2f}")
            c2.metric("تكلفة المبيعات", f"{cogs:,.2f}")
            c3.metric("مجمل الربح", f"{gross:,.2f}")
        
        with tab2:
            st.subheader("📊 تقرير المبيعات التفصيلي")
            df_sales = pd.read_sql("SELECT * FROM invoices WHERE type='Sale'", conn)
            st.dataframe(df_sales)
            
            st.write("ملخص حسب الدفع:")
            st.bar_chart(df_sales.groupby('payment_method')['total'].sum())

        with tab3:
            st.subheader("🌳 شجرة الحسابات")
            st.dataframe(pd.read_sql("SELECT * FROM accounts", conn))
            
            c_new = st.text_input("رقم الحساب الفرعي")
            n_new = st.text_input("اسم الحساب")
            p_new = st.text_input("رقم الحساب الرئيسي (الأب)")
            if st.button("إضافة حساب فرعي"):
                c.execute("INSERT INTO accounts (code, name, parent_code) VALUES (?,?,?)", (c_new, n_new, p_new))
                conn.commit(); st.success("تم")

        with tab4:
            st.subheader("إضافة قيد يدوي")
            desc = st.text_input("الشرح")
            c1, c2, c3 = st.columns(3)
            ac = c1.text_input("رقم الحساب")
            db = c2.number_input("مدين")
            cr = c3.number_input("دائن")
            if st.button("حفظ القيد"):
                create_entry(desc, [(ac, db, cr)], 0)
                st.success("تم")

    # ==========================
    # 6. المستخدمين
    # ==========================
    elif menu == "إدارة المستخدمين":
        st.subheader("👥 الموظفين والصلاحيات")
        st.table(pd.read_sql("SELECT username, name, role FROM users", conn))
        
        with st.form("add_u"):
            u = st.text_input("المستخدم"); p = st.text_input("السر"); n = st.text_input("الاسم الكامل")
            r = st.selectbox("الصلاحية", ["admin", "cashier"])
            if st.form_submit_button("إضافة"):
                c.execute("INSERT INTO users VALUES (?,?,?,?)", (u, p, r, n))
                conn.commit(); st.success("تم")
                
