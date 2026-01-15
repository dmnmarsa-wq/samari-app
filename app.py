import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime

# 1. إعدادات الصفحة والتنسيق الجمالي (CSS) لجعلها تشبه التطبيقات الاحترافية
st.set_page_config(page_title="سماري POS", layout="wide")

st.markdown("""
    <style>
    /* تغيير الخلفية العامة */
    .stApp { background-color: #F0F2F6; }
    
    /* تنسيق أزرار المنتجات لتكون كبيرة وسهلة اللمس */
    div.stButton > button:first-child {
        background-color: #1E3A5F;
        color: white;
        border-radius: 15px;
        height: 100px;
        width: 100%;
        font-size: 20px;
        font-weight: bold;
        border: none;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    /* تأثير عند تمرير الماوس على الزر */
    div.stButton > button:hover {
        background-color: #2D5A8E;
        color: #FFD700;
        border: 1px solid #FFD700;
    }

    /* تنسيق صندوق الفاتورة */
    .invoice-container {
        background-color: white;
        padding: 20px;
        border-radius: 20px;
        border: 1px solid #E0E0E0;
    }
    </style>
    """, unsafe_allow_html=True)

# 2. تهيئة قاعدة البيانات لحفظ المبيعات
def init_db():
    conn = sqlite3.connect('samari_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS sales 
                 (id INTEGER PRIMARY KEY, item TEXT, qty REAL, total REAL, date TEXT)''')
    conn.commit()
    conn.close()

init_db()

# 3. واجهة المستخدم
st.markdown("<h1 style='text-align: center; color: #1E3A5F;'>🐟 مطعم سماري - نظام نقاط البيع</h1>", unsafe_allow_html=True)
st.write("---")

# تقسيم الشاشة: جهة للمنتجات وجهة للفاتورة
col_products, col_invoice = st.columns([2, 1])

with col_products:
    st.subheader("🍽️ قائمة الطعام")
    
    # تعريف الأصناف (يمكنك تعديلها لاحقاً)
    items = [
        {"name": "سمك بوري", "icon": "🐟", "price": 180},
        {"name": "سمك بلطي", "icon": "🐠", "price": 120},
        {"name": "جمبري", "icon": "🦐", "price": 450},
        {"name": "أرز صيادية", "icon": "🍚", "price": 15},
        {"name": "شوربة", "icon": "🥣", "price": 40},
        {"name": "مشروب", "icon": "🥤", "price": 10}
    ]
    
    # عرض الأصناف في شبكة (Grid) من 3 أعمدة
    cols = st.columns(3)
    for i, item in enumerate(items):
        with cols[i % 3]:
            st.markdown(f"<div style='text-align:center;'><h3>{item['icon']}</h3></div>", unsafe_allow_html=True)
            if st.button(f"{item['name']}\n{item['price']} ريال", key=f"item_{i}"):
                # سيتم إضافة منطق السلة هنا في الخطوة القادمة
                st.toast(f"تم اختيار {item['name']}")

with col_invoice:
    st.markdown("<div class='invoice-container'>", unsafe_allow_html=True)
    st.subheader("🧾 الفاتورة")
    
    # محاكاة لعرض الفاتورة
    st.write("**الأصناف المختارة:**")
    st.info("لم يتم إضافة أصناف بعد") 
    
    st.write("---")
    st.write("الضريبة (15%): 0.00")
    st.error("### الإجمالي: 0.00 ريال")
    
    if st.button("إتمام العملية 💳"):
        st.success("تم الحفظ والطباعة")
    st.markdown("</div>", unsafe_allow_html=True)

# 4. سجل سريع للمبيعات في الأسفل
with st.expander("📊 مبيعات اليوم"):
    st.write("سيظهر هنا جدول بآخر العمليات التي تمت.")
