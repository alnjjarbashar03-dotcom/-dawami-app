import csv
import json
import os
from datetime import datetime, timedelta, date

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components

script_dir = os.path.dirname(os.path.abspath(__file__))
EMP_PATH = os.path.join(script_dir, "employees.csv")
ATT_PATH = os.path.join(script_dir, "attendance.csv")
REQ_PATH = os.path.join(script_dir, "requests.csv")
PAY_PATH = os.path.join(script_dir, "payments.csv")
COMPANY_PATH = os.path.join(script_dir, "company.json")

# ============================================================
# ألوان الثيم
# ============================================================
PRIMARY = "#4F46E5"
PALETTE = ["#4F46E5", "#22C55E", "#F59E0B", "#EF4444", "#06B6D4", "#A855F7"]

# ============================================================
# أسماء أعمدة كل ملف CSV (مرجع موحّد يُستخدم بالقراءة والكتابة)
# ============================================================
EMP_FIELDS = ["id", "name", "role", "base_salary", "work_start", "work_end",
              "required_hours", "branch", "overtime_rate", "current_debt"]
ATT_FIELDS = ["emp_id", "date_time", "type", "status", "overtime_hours", "paid"]
REQ_FIELDS = ["req_id", "emp_id", "req_type", "details", "status"]
PAY_FIELDS = ["payment_id", "emp_id", "amount", "pay_date", "admin_confirmed", "employee_confirmed", "confirm_date",
              "base_salary", "overtime_hours", "overtime_pay", "advances_deducted", "debt_before", "debt_after"]

# ============================================================
# تهيئة الملفات
# ============================================================
def init_files():
    try:
        with open(EMP_PATH, "x", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(EMP_FIELDS)
            writer.writerow(["101", "Main Admin", "admin", "5000", "08:00", "16:00", "8",
                              "الفرع الرئيسي", "0", "0"])
    except FileExistsError:
        pass

    try:
        with open(ATT_PATH, "x", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(ATT_FIELDS)
    except FileExistsError:
        pass

    try:
        with open(REQ_PATH, "x", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(REQ_FIELDS)
    except FileExistsError:
        pass

    try:
        with open(PAY_PATH, "x", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(PAY_FIELDS)
    except FileExistsError:
        pass


def load_employees():
    employees = []
    if os.path.exists(EMP_PATH):
        with open(EMP_PATH, "r", encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                employees.append(row)
    return employees


def load_requests():
    reqs = []
    if os.path.exists(REQ_PATH):
        with open(REQ_PATH, "r", encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                reqs.append(row)
    return reqs


def load_attendance():
    rows = []
    if os.path.exists(ATT_PATH):
        with open(ATT_PATH, "r", encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    return rows


def load_payments():
    rows = []
    if os.path.exists(PAY_PATH):
        with open(PAY_PATH, "r", encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    return rows


# ============================================================
# إعدادات الشركة (اسم الشركة + الفروع)
# ============================================================
def load_company():
    if os.path.exists(COMPANY_PATH):
        with open(COMPANY_PATH, "r", encoding='utf-8') as f:
            try:
                data = json.load(f)
                data.setdefault("company_name", "")
                data.setdefault("branches", [])
                return data
            except json.JSONDecodeError:
                pass
    return {"company_name": "", "branches": []}


def save_company(company_name, branches):
    with open(COMPANY_PATH, "w", encoding='utf-8') as f:
        json.dump({"company_name": company_name, "branches": branches}, f, ensure_ascii=False, indent=2)


def add_branch(branch_name):
    company = load_company()
    if branch_name not in company["branches"]:
        company["branches"].append(branch_name)
        save_company(company["company_name"], company["branches"])


def remove_branch(branch_name):
    company = load_company()
    if branch_name in company["branches"]:
        company["branches"].remove(branch_name)
        save_company(company["company_name"], company["branches"])


# ============================================================
# منطق الأعمال
# ============================================================
def add_employee(emp_id, name, role, salary, work_start, work_end, required_hours, branch, overtime_rate):
    existing = load_employees()
    for e in existing:
        if e['id'] == emp_id:
            return False, "❌ رقم الموظف موجود مسبقاً!"

    try:
        overtime_rate_val = float(overtime_rate)
    except (ValueError, TypeError):
        overtime_rate_val = 0.0

    with open(EMP_PATH, "a", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([emp_id, name, role, salary, work_start, work_end, required_hours,
                          branch, f"{overtime_rate_val:.2f}", "0"])
    return True, f"✅ تمت إضافة الموظف '{name}' بنجاح!"


def update_employee_debt(emp_id, new_debt):
    employees = load_employees()
    updated = False
    for e in employees:
        if e.get('id') == emp_id:
            e['current_debt'] = f"{new_debt:.2f}"
            updated = True
    if updated:
        with open(EMP_PATH, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=EMP_FIELDS)
            writer.writeheader()
            for e in employees:
                writer.writerow({k: e.get(k, '') for k in EMP_FIELDS})
    return updated


def record_attendance(user, action_type):
    now = datetime.now()
    current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")
    status = "On Time"
    overtime_hours = "0"

    if action_type == "Check-In":
        work_start_str = user.get('work_start', '08:00')
        work_start = datetime.strptime(f"{now.strftime('%Y-%m-%d')} {work_start_str}", "%Y-%m-%d %H:%M")
        late_threshold = work_start + timedelta(minutes=30)
        if now > late_threshold:
            status = "Late Check-In"

    elif action_type == "Check-Out":
        last_checkin = None
        for row in load_attendance():
            row_emp_id = row.get('emp_id', '')
            row_type = row.get('type', '')
            row_datetime = row.get('date_time', '')
            if row_emp_id == user['id'] and row_type == 'Check-In' and row_datetime.startswith(now.strftime("%Y-%m-%d")):
                try:
                    last_checkin = datetime.strptime(row_datetime, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass

        if last_checkin:
            worked_hours = (now - last_checkin).total_seconds() / 3600.0
            req_hours = float(user.get('required_hours', 8) or 8)
            if worked_hours > req_hours:
                extra = worked_hours - req_hours
                overtime_hours = f"{extra:.2f}"
                status = f"Completed ({overtime_hours} hrs Overtime)"
            else:
                status = "Completed"

    with open(ATT_PATH, "a", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([user['id'], current_time_str, action_type, status, overtime_hours, "No"])

    return f"✅ تم تسجيل {action_type} ({status}) الساعة {current_time_str}"


def mark_attendance_paid(emp_id):
    rows = load_attendance()
    updated = False
    for r in rows:
        if r.get('emp_id') == emp_id and r.get('type') == 'Check-Out' and r.get('paid', 'No') != 'Yes':
            try:
                if float(r.get('overtime_hours', 0) or 0) > 0:
                    r['paid'] = 'Yes'
                    updated = True
            except ValueError:
                pass
    if updated:
        with open(ATT_PATH, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=ATT_FIELDS)
            writer.writeheader()
            for r in rows:
                writer.writerow({k: r.get(k, '') for k in ATT_FIELDS})
    return updated


def submit_request(user_id, req_type, details):
    req_id = datetime.now().strftime("%Y%m%d%H%M%S")
    with open(REQ_PATH, "a", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([req_id, user_id, req_type, details, "Pending"])
    return "✅ تم إرسال الطلب بنجاح!"


def update_request_status(req_id, new_status):
    reqs = load_requests()
    updated = False
    for req in reqs:
        if req.get('req_id') == req_id:
            req['status'] = new_status
            updated = True

    if updated:
        with open(REQ_PATH, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=REQ_FIELDS)
            writer.writeheader()
            writer.writerows(reqs)
    return updated


def mark_advances_deducted(emp_id):
    reqs = load_requests()
    updated = False
    for r in reqs:
        if r.get('emp_id') == emp_id and r.get('req_type') == 'Advance' and r.get('status') == 'Approved':
            r['status'] = 'Deducted'
            updated = True
    if updated:
        with open(REQ_PATH, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=REQ_FIELDS)
            writer.writeheader()
            writer.writerows(reqs)
    return updated


def compute_payroll(emp):
    """
    يحسب راتب موظف بالاعتماد على:
    - الراتب الأساسي
    - ساعات العمل الإضافي غير المدفوعة × سعر الساعة الإضافية
    - السلف المقبولة غير المخصومة بعد
    - أي دين سابق من شهر ماضٍ (سلفة أكبر من الراتب)
    إذا كان المستحق (سلف + دين) أكبر من الراتب + الإضافي، ياخذ صفر هالشهر
    والفرق يتحول لدين يُخصم من الشهر القادم.
    """
    base_salary = float(emp.get('base_salary', 0) or 0)
    overtime_rate = float(emp.get('overtime_rate', 0) or 0)
    previous_debt = float(emp.get('current_debt', 0) or 0)

    unpaid_overtime_hours = 0.0
    for row in load_attendance():
        if row.get('emp_id') == emp['id'] and row.get('type') == 'Check-Out' and row.get('paid', 'No') != 'Yes':
            try:
                unpaid_overtime_hours += float(row.get('overtime_hours', 0) or 0)
            except ValueError:
                pass
    overtime_pay = unpaid_overtime_hours * overtime_rate

    unpaid_advances_list = []
    unpaid_advances_total = 0.0
    for row in load_requests():
        if row.get('emp_id') == emp['id'] and row.get('req_type') == 'Advance' and row.get('status') == 'Approved':
            try:
                amt = float(row.get('details', 0))
            except ValueError:
                amt = 0.0
            unpaid_advances_total += amt
            unpaid_advances_list.append(row)

    gross = base_salary + overtime_pay
    total_owed = unpaid_advances_total + previous_debt

    if gross >= total_owed:
        net = gross - total_owed
        new_debt = 0.0
    else:
        net = 0.0
        new_debt = total_owed - gross

    return {
        'base_salary': base_salary,
        'overtime_rate': overtime_rate,
        'unpaid_overtime_hours': unpaid_overtime_hours,
        'overtime_pay': overtime_pay,
        'unpaid_advances_total': unpaid_advances_total,
        'unpaid_advances_list': unpaid_advances_list,
        'previous_debt': previous_debt,
        'gross': gross,
        'total_owed': total_owed,
        'net': net,
        'new_debt': new_debt,
    }


def get_company_payroll():
    employees = load_employees()
    rows = []
    grand_total = 0.0
    for emp in employees:
        if emp['role'] == 'employee':
            calc = compute_payroll(emp)
            grand_total += calc['net']
            rows.append({
                "رقم الموظف": emp['id'], "الاسم": emp['name'], "الفرع": emp.get('branch', '-'),
                "الراتب الأساسي": f"${calc['base_salary']:.2f}",
                "الإضافي": f"${calc['overtime_pay']:.2f}",
                "السلف والدين": f"-${calc['total_owed']:.2f}",
                "الصافي المستحق": f"${calc['net']:.2f}",
                "الدين القادم": f"${calc['new_debt']:.2f}",
            })
    return rows, grand_total


def pay_salary(emp, pay_date_str):
    """يعالج دفع راتب فعلي: يسجّل الدفعة، يصفّر الساعات الإضافية والسلف المدفوعة، ويحدّث الدين."""
    calc = compute_payroll(emp)
    payment_id = datetime.now().strftime("%Y%m%d%H%M%S%f")
    with open(PAY_PATH, "a", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            payment_id, emp['id'], f"{calc['net']:.2f}", pay_date_str, "Yes", "No", "",
            f"{calc['base_salary']:.2f}", f"{calc['unpaid_overtime_hours']:.2f}", f"{calc['overtime_pay']:.2f}",
            f"{calc['unpaid_advances_total']:.2f}", f"{calc['previous_debt']:.2f}", f"{calc['new_debt']:.2f}",
        ])
    mark_attendance_paid(emp['id'])
    mark_advances_deducted(emp['id'])
    update_employee_debt(emp['id'], calc['new_debt'])
    return payment_id, calc


def confirm_payment_received(payment_id):
    payments = load_payments()
    updated = False
    for p in payments:
        if p.get('payment_id') == payment_id:
            p['employee_confirmed'] = "Yes"
            p['confirm_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            updated = True

    if updated:
        with open(PAY_PATH, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=PAY_FIELDS)
            writer.writeheader()
            for p in payments:
                writer.writerow({k: p.get(k, '') for k in PAY_FIELDS})
    return updated


def simplify_attendance_status(status):
    if "Late" in status:
        return "متأخر"
    if "Overtime" in status:
        return "مكتمل + إضافي"
    if status == "Completed":
        return "مكتمل"
    if status == "On Time":
        return "بالوقت المحدد"
    return status or "غير محدد"


def req_type_ar(req_type):
    return "إجازة" if req_type == "Leave" else "سلفة على الراتب"


def req_status_ar(status):
    return {
        "Approved": "مقبول (بانتظار الخصم)",
        "Rejected": "مرفوض",
        "Pending": "قيد المراجعة",
        "Deducted": "تم خصمها من الراتب",
    }.get(status, status)


def req_date_from_id(req_id):
    try:
        return datetime.strptime(req_id[:14], "%Y%m%d%H%M%S").strftime("%Y-%m-%d")
    except Exception:
        return "-"


def count_attendance_days(emp_id):
    dates = set()
    for row in load_attendance():
        if row.get('emp_id') == emp_id and row.get('type') == 'Check-In':
            dt = row.get('date_time', '')
            if dt:
                dates.add(dt.split(' ')[0])
    return len(dates)


def generate_payslip_html(emp, company):
    calc = compute_payroll(emp)
    company_name = company.get('company_name') or "اسم الشركة"
    branch = emp.get('branch') or "-"
    today_str = date.today().strftime("%Y-%m-%d")

    all_reqs = [r for r in load_requests() if r.get('emp_id') == emp['id']]
    advances = [r for r in all_reqs if r.get('req_type') == 'Advance']
    leaves = [r for r in all_reqs if r.get('req_type') == 'Leave']

    def rows_html(reqs, is_advance):
        if not reqs:
            return "<tr><td colspan='3' style='text-align:center;color:#888;'>لا يوجد</td></tr>"
        out = ""
        for r in reqs:
            d = req_date_from_id(r.get('req_id', ''))
            detail = r.get('details', '')
            status = req_status_ar(r.get('status', ''))
            label = f"${detail}" if is_advance else detail
            out += f"<tr><td>{d}</td><td>{label}</td><td>{status}</td></tr>"
        return out

    days_count = count_attendance_days(emp['id'])

    html = f"""
    <html dir="rtl" lang="ar">
    <head>
    <meta charset="utf-8">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Arial, sans-serif; padding: 24px; color:#1e293b; }}
        .header {{ text-align:center; border-bottom: 3px solid {PRIMARY}; padding-bottom: 14px; margin-bottom: 20px; }}
        .header h1 {{ margin:0; color:{PRIMARY}; }}
        .header p {{ margin:4px 0 0; color:#64748b; }}
        table {{ width:100%; border-collapse: collapse; margin: 10px 0 20px; }}
        th, td {{ border:1px solid #E2E8F0; padding:8px 10px; text-align:center; font-size:14px; }}
        th {{ background:#F8FAFC; }}
        .info-grid {{ display:flex; flex-wrap:wrap; gap:10px; margin-bottom:20px; }}
        .info-box {{ flex:1; min-width:180px; background:#F8FAFC; border:1px solid #E2E8F0; border-radius:10px; padding:10px 14px; }}
        .info-box .label {{ font-size:12px; color:#64748b; }}
        .info-box .value {{ font-size:18px; font-weight:700; color:#1e293b; }}
        .debt {{ color:#EF4444; }}
        .ok {{ color:#22C55E; }}
        .sign {{ display:flex; justify-content:space-between; margin-top:50px; }}
        .sign div {{ width:45%; text-align:center; border-top:1px solid #333; padding-top:6px; }}
        h3 {{ border-right:4px solid {PRIMARY}; padding-right:8px; }}
    </style>
    </head>
    <body>
        <div class="header">
            <h1>{company_name}</h1>
            <p>قسيمة راتب — بتاريخ {today_str}</p>
        </div>

        <div class="info-grid">
            <div class="info-box"><div class="label">اسم الموظف</div><div class="value">{emp['name']}</div></div>
            <div class="info-box"><div class="label">رقم الموظف</div><div class="value">{emp['id']}</div></div>
            <div class="info-box"><div class="label">الفرع</div><div class="value">{branch}</div></div>
        </div>

        <h3>تفاصيل الراتب</h3>
        <div class="info-grid">
            <div class="info-box"><div class="label">الراتب الأساسي</div><div class="value">${calc['base_salary']:.2f}</div></div>
            <div class="info-box"><div class="label">ساعات العمل الإضافي غير المدفوعة</div><div class="value">{calc['unpaid_overtime_hours']:.2f} ساعة</div></div>
            <div class="info-box"><div class="label">قيمة الساعات الإضافية</div><div class="value">${calc['overtime_pay']:.2f}</div></div>
            <div class="info-box"><div class="label">عدد أيام الحضور المسجلة</div><div class="value">{days_count} يوم</div></div>
        </div>

        <div class="info-grid">
            <div class="info-box"><div class="label">إجمالي السلف غير المخصومة</div><div class="value debt">-${calc['unpaid_advances_total']:.2f}</div></div>
            <div class="info-box"><div class="label">دين سابق من شهر ماضٍ</div><div class="value debt">-${calc['previous_debt']:.2f}</div></div>
            <div class="info-box"><div class="label">صافي الراتب المستحق حالياً</div><div class="value ok">${calc['net']:.2f}</div></div>
            <div class="info-box"><div class="label">دين متبقٍ للشهر القادم</div><div class="value debt">${calc['new_debt']:.2f}</div></div>
        </div>

        <h3>سجل السلف</h3>
        <table>
            <tr><th>التاريخ</th><th>المبلغ</th><th>الحالة</th></tr>
            {rows_html(advances, True)}
        </table>

        <h3>سجل الإجازات</h3>
        <table>
            <tr><th>التاريخ</th><th>التفاصيل</th><th>الحالة</th></tr>
            {rows_html(leaves, False)}
        </table>

        <div class="sign">
            <div>توقيع الموظف</div>
            <div>توقيع الإدارة</div>
        </div>
    </body>
    </html>
    """
    return html


# ============================================================
# واجهة Streamlit
# ============================================================
st.set_page_config(page_title="نظام دوامي", page_icon="🕒", layout="wide")
init_files()
company = load_company()

# ---------------- تنسيق عام (RTL + شكل أنظف) ----------------
st.markdown("""
<style>
    html, body, [class*="css"]  { direction: rtl; }
    .stApp { font-family: 'Segoe UI', Tahoma, sans-serif; }
    h1, h2, h3 { text-align: right; }
    div[data-testid="stMetric"] {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 14px 16px;
    }
    div[data-testid="stMetricLabel"] { justify-content: center; }
    div[data-testid="stMetricValue"] { justify-content: center; }
    .stTabs [data-baseweb="tab-list"] { gap: 6px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0 0;
        padding: 8px 16px;
    }
    div.stButton > button {
        border-radius: 8px;
        font-weight: 600;
    }
    div.stAlert { border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

if "user" not in st.session_state:
    st.session_state.user = None

title_suffix = f" — {company['company_name']}" if company.get('company_name') else ""
st.title(f"🕒 نظام دوامي{title_suffix}")

# ---------------- شاشة الدخول ----------------
if st.session_state.user is None:
    st.subheader("تسجيل الدخول")
    with st.form("login_form"):
        emp_id_input = st.text_input("رقم الموظف")
        submitted = st.form_submit_button("دخول", use_container_width=True)

    if submitted:
        found = None
        for emp in load_employees():
            if emp['id'] == emp_id_input.strip():
                found = emp
                break
        if found:
            st.session_state.user = found
            st.success(f"مرحباً بعودتك، {found['name']}! (الصلاحية: {found['role']})")
            st.rerun()
        else:
            st.error("❌ رقم الموظف غير صحيح!")

# ---------------- بعد الدخول ----------------
else:
    user = st.session_state.user
    st.sidebar.markdown(f"### 👤 {user['name']}")
    st.sidebar.markdown(f"الصلاحية: **{user['role']}**")
    if user.get('branch'):
        st.sidebar.markdown(f"الفرع: **{user['branch']}**")
    st.sidebar.divider()
    if st.sidebar.button("🚪 تسجيل الخروج", use_container_width=True):
        st.session_state.user = None
        st.rerun()

    # ============================================================
    # لوحة الأدمن
    # ============================================================
    if user['role'] == 'admin':
        tab_company, tab_overview, tab_add, tab_payroll, tab_payslip, tab_att, tab_reqs = st.tabs([
            "🏢 إعدادات الشركة", "📊 نظرة عامة", "➕ إضافة موظف", "💰 الرواتب والدفع",
            "🧾 قسيمة الراتب", "📋 سجل الحضور", "📨 إدارة الطلبات"
        ])

        # ---------- إعدادات الشركة ----------
        with tab_company:
            st.subheader("🏢 بيانات الشركة")
            company = load_company()
            with st.form("company_form"):
                company_name_input = st.text_input("اسم الشركة", value=company.get('company_name', ''))
                save_company_btn = st.form_submit_button("💾 حفظ اسم الشركة", use_container_width=True)
            if save_company_btn:
                if not company_name_input.strip():
                    st.error("الرجاء إدخال اسم الشركة.")
                else:
                    save_company(company_name_input.strip(), company.get('branches', []))
                    st.success("✅ تم حفظ اسم الشركة.")
                    st.rerun()

            st.divider()
            st.markdown("#### 🏬 الفروع")
            company = load_company()
            branches = company.get('branches', [])
            if branches:
                for b in branches:
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"📍 {b}")
                    if c2.button("🗑️ حذف", key=f"del_branch_{b}"):
                        remove_branch(b)
                        st.rerun()
            else:
                st.info("لم تتم إضافة أي فرع بعد. أضف فرعاً واحداً على الأقل قبل إضافة الموظفين.")

            with st.form("add_branch_form", clear_on_submit=True):
                new_branch_name = st.text_input("اسم فرع جديد")
                add_branch_btn = st.form_submit_button("➕ إضافة فرع", use_container_width=True)
            if add_branch_btn:
                if not new_branch_name.strip():
                    st.error("الرجاء إدخال اسم الفرع.")
                else:
                    add_branch(new_branch_name.strip())
                    st.success(f"✅ تمت إضافة فرع '{new_branch_name.strip()}'.")
                    st.rerun()

        # ---------- نظرة عامة + تشارتات ----------
        with tab_overview:
            employees = load_employees()
            att_rows = load_attendance()
            reqs = load_requests()
            payroll_rows, grand_total = get_company_payroll()

            n_employees = len([e for e in employees if e['role'] == 'employee'])
            n_pending = len([r for r in reqs if r.get('status') == 'Pending'])
            total_debt = sum(compute_payroll(e)['new_debt'] for e in employees if e['role'] == 'employee')

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("👥 عدد الموظفين", n_employees)
            c2.metric("📨 طلبات قيد المراجعة", n_pending)
            c3.metric("💵 إجمالي الرواتب المستحقة", f"${grand_total:,.2f}")
            c4.metric("⚠️ إجمالي الديون على الموظفين", f"${total_debt:,.2f}")

            st.divider()
            g1, g2 = st.columns(2)

            with g1:
                st.markdown("##### توزيع حالات الحضور")
                if att_rows:
                    df_att = pd.DataFrame(att_rows)
                    df_att["الحالة"] = df_att["status"].apply(simplify_attendance_status)
                    counts = df_att["الحالة"].value_counts().reset_index()
                    counts.columns = ["الحالة", "العدد"]
                    fig = px.pie(counts, names="الحالة", values="العدد", hole=0.4,
                                 color_discrete_sequence=PALETTE)
                    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), legend_title="")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("لا توجد سجلات حضور بعد.")

            with g2:
                st.markdown("##### توزيع الطلبات حسب الحالة")
                if reqs:
                    df_req = pd.DataFrame(reqs)
                    df_req["الحالة"] = df_req["status"].apply(req_status_ar)
                    counts = df_req["الحالة"].value_counts().reset_index()
                    counts.columns = ["الحالة", "العدد"]
                    fig = px.pie(counts, names="الحالة", values="العدد", hole=0.4,
                                 color_discrete_sequence=PALETTE)
                    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), legend_title="")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("لا توجد طلبات بعد.")

            st.markdown("##### صافي الراتب المستحق لكل موظف")
            if payroll_rows:
                df_pay = pd.DataFrame(payroll_rows)
                df_pay["_صافي"] = df_pay["الصافي المستحق"].str.replace("$", "", regex=False).astype(float)
                fig = px.bar(df_pay, x="الاسم", y="_صافي", text="الصافي المستحق",
                             color="الاسم", color_discrete_sequence=PALETTE)
                fig.update_layout(showlegend=False, yaxis_title="الصافي ($)", xaxis_title="",
                                   margin=dict(t=10, b=10, l=10, r=10))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("لا يوجد موظفون مسجّلون بعد.")

        # ---------- إضافة موظف ----------
        with tab_add:
            st.subheader("إضافة موظف جديد")
            company = load_company()
            branches = company.get('branches', [])
            if not branches:
                st.warning("⚠️ الرجاء إضافة فرع واحد على الأقل من تبويب 'إعدادات الشركة' قبل إضافة موظف.")
            else:
                with st.form("add_emp_form", clear_on_submit=True):
                    c1, c2 = st.columns(2)
                    new_id = c1.text_input("رقم الموظف")
                    new_name = c2.text_input("الاسم")
                    new_role = c1.selectbox("الصلاحية", ["employee", "admin"])
                    new_salary = c2.text_input("الراتب الأساسي ($)")
                    new_branch = c1.selectbox("الفرع", branches)
                    new_overtime_rate = c2.text_input("سعر الساعة الإضافية ($)", value="0")
                    new_start = c1.text_input("بداية الدوام (HH:MM)", value="08:00")
                    new_end = c2.text_input("نهاية الدوام (HH:MM)", value="16:00")
                    new_required = st.text_input("عدد ساعات العمل المطلوبة يومياً", value="8")
                    add_submitted = st.form_submit_button("➕ إضافة الموظف", use_container_width=True)

                if add_submitted:
                    if not new_id or not new_name or not new_salary:
                        st.error("الرجاء تعبئة رقم الموظف والاسم والراتب على الأقل.")
                    else:
                        ok, msg = add_employee(new_id, new_name, new_role, new_salary, new_start, new_end,
                                                new_required, new_branch, new_overtime_rate)
                        st.success(msg) if ok else st.error(msg)

        # ---------- الرواتب والدفع ----------
        with tab_payroll:
            st.subheader("تقرير الرواتب الكلي")
            rows, grand_total = get_company_payroll()
            if rows:
                st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                st.metric("إجمالي الرواتب المستحقة", f"${grand_total:.2f}")
            else:
                st.info("لا يوجد موظفون مسجّلون بعد.")

            st.divider()
            st.subheader("💳 دفع راتب لموظف")
            employees_only = [e for e in load_employees() if e['role'] == 'employee']
            if not employees_only:
                st.info("لا يوجد موظفون لدفع رواتبهم بعد.")
            else:
                emp_labels = {f"{e['id']} — {e['name']}": e for e in employees_only}
                chosen_label = st.selectbox("اختر الموظف لدفع راتبه", list(emp_labels.keys()), key="pay_emp_select")
                chosen_emp = emp_labels[chosen_label]
                calc = compute_payroll(chosen_emp)

                st.markdown("##### معاينة الراتب قبل الدفع")
                c1, c2, c3 = st.columns(3)
                c1.metric("الراتب الأساسي", f"${calc['base_salary']:.2f}")
                c2.metric(f"الإضافي ({calc['unpaid_overtime_hours']:.2f} ساعة)", f"${calc['overtime_pay']:.2f}")
                c3.metric("دين سابق", f"-${calc['previous_debt']:.2f}")

                c4, c5 = st.columns(2)
                c4.metric("سلف مستحقة الخصم", f"-${calc['unpaid_advances_total']:.2f}")
                c5.metric("💵 الصافي المستحق الآن", f"${calc['net']:.2f}")

                if calc['new_debt'] > 0:
                    st.warning(f"⚠️ سيبقى الموظف مديوناً بمبلغ ${calc['new_debt']:.2f} يُخصم من راتب الشهر القادم.")

                pay_date = st.date_input("تاريخ الدفع", value=date.today(), key="pay_date_input")
                if st.button("✅ تأكيد ومعالجة دفع الراتب", use_container_width=True):
                    pay_salary(chosen_emp, pay_date.strftime("%Y-%m-%d"))
                    st.success(f"✅ تم دفع ${calc['net']:.2f} للموظف {chosen_emp['name']} بتاريخ {pay_date}.")
                    st.rerun()

            st.divider()
            st.subheader("📜 سجل عمليات الدفع")
            payments = load_payments()
            if payments:
                emp_name_map = {e['id']: e['name'] for e in load_employees()}
                df_p = pd.DataFrame(payments)
                df_p["اسم الموظف"] = df_p["emp_id"].map(emp_name_map).fillna(df_p["emp_id"])
                df_p["تأكيد الموظف"] = df_p["employee_confirmed"].apply(
                    lambda v: "✅ تم التأكيد" if v == "Yes" else "⏳ بانتظار التأكيد")
                df_show = df_p.rename(columns={
                    "base_salary": "الأساسي", "overtime_pay": "الإضافي",
                    "advances_deducted": "السلف المخصومة", "debt_before": "دين سابق",
                    "debt_after": "دين لاحق", "amount": "الصافي المدفوع",
                    "pay_date": "تاريخ الدفع", "confirm_date": "تاريخ التأكيد",
                })[["اسم الموظف", "الأساسي", "الإضافي", "السلف المخصومة", "دين سابق",
                    "الصافي المدفوع", "دين لاحق", "تاريخ الدفع", "تأكيد الموظف", "تاريخ التأكيد"]]
                st.dataframe(df_show, use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد عمليات دفع مسجّلة بعد.")

        # ---------- قسيمة الراتب ----------
        with tab_payslip:
            st.subheader("🧾 إصدار قسيمة راتب")
            all_emps = load_employees()
            company = load_company()
            if not all_emps:
                st.info("لا يوجد موظفون بعد.")
            else:
                emp_labels2 = {f"{e['id']} — {e['name']}": e for e in all_emps}
                chosen_label2 = st.selectbox("اختر الموظف", list(emp_labels2.keys()), key="payslip_emp")
                chosen_emp2 = emp_labels2[chosen_label2]
                payslip_html = generate_payslip_html(chosen_emp2, company)
                components.html(payslip_html, height=750, scrolling=True)
                st.download_button(
                    "⬇️ تحميل القسيمة (HTML)",
                    data=payslip_html,
                    file_name=f"قسيمة_راتب_{chosen_emp2['name']}.html",
                    mime="text/html",
                    use_container_width=True,
                )
                st.caption("افتح الملف المحمّل بالمتصفح، ثم استخدم خيار الطباعة (Ctrl+P) واحفظه كـ PDF إذا رغبت.")

        # ---------- سجل الحضور ----------
        with tab_att:
            st.subheader("سجل الحضور والانصراف")
            att_rows = load_attendance()
            if att_rows:
                df = pd.DataFrame(att_rows)
                df = df.rename(columns={
                    "emp_id": "رقم الموظف", "date_time": "التاريخ والوقت",
                    "type": "الإجراء", "status": "الحالة", "overtime_hours": "ساعات إضافية",
                    "paid": "تم احتسابها بالراتب"
                })
                if "تم احتسابها بالراتب" in df.columns:
                    df["تم احتسابها بالراتب"] = df["تم احتسابها بالراتب"].apply(
                        lambda v: "✅" if v == "Yes" else "—")
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد سجلات حضور بعد.")

        # ---------- إدارة الطلبات ----------
        with tab_reqs:
            st.subheader("إدارة الطلبات (سلف وإجازات)")
            reqs = load_requests()
            if not reqs:
                st.info("لا توجد طلبات بعد.")
            else:
                df = pd.DataFrame(reqs).rename(columns={
                    "req_id": "رقم الطلب", "emp_id": "رقم الموظف",
                    "req_type": "النوع", "details": "التفاصيل", "status": "الحالة"
                })
                df["الحالة"] = pd.DataFrame(reqs)["status"].apply(req_status_ar)
                st.dataframe(df, use_container_width=True, hide_index=True)

                pending = [r for r in reqs if r.get('status') == 'Pending']
                if pending:
                    st.markdown("#### الرد على طلب معلّق")
                    options = {f"{r['req_id']} — موظف {r['emp_id']} — {r['req_type']} ({r['details']})": r['req_id'] for r in pending}
                    choice = st.selectbox("اختر الطلب", list(options.keys()))
                    c1, c2 = st.columns(2)
                    if c1.button("✅ قبول الطلب", use_container_width=True):
                        update_request_status(options[choice], "Approved")
                        st.success("تم قبول الطلب.")
                        st.rerun()
                    if c2.button("❌ رفض الطلب", use_container_width=True):
                        update_request_status(options[choice], "Rejected")
                        st.warning("تم رفض الطلب.")
                        st.rerun()
                else:
                    st.success("لا توجد طلبات معلّقة حالياً.")

    # ============================================================
    # لوحة الموظف
    # ============================================================
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "🕒 حضور وانصراف", "📨 تقديم طلب", "💵 راتبي", "📋 حالة طلباتي"
        ])

        with tab1:
            st.subheader("تسجيل الحضور والانصراف")
            c1, c2 = st.columns(2)
            if c1.button("✅ تسجيل حضور", use_container_width=True):
                st.success(record_attendance(user, "Check-In"))
            if c2.button("🚪 تسجيل انصراف", use_container_width=True):
                st.success(record_attendance(user, "Check-Out"))

        with tab2:
            st.subheader("تقديم طلب جديد")
            req_kind = st.radio("نوع الطلب", ["إجازة", "سلفة على الراتب"])
            if req_kind == "إجازة":
                details = st.text_area("سبب/عدد أيام الإجازة")
                req_type = "Leave"
            else:
                details = st.text_input("مبلغ السلفة ($)")
                req_type = "Advance"

            if st.button("📤 إرسال الطلب", use_container_width=True):
                if not details:
                    st.error("الرجاء تعبئة تفاصيل الطلب.")
                else:
                    st.success(submit_request(user['id'], req_type, details))

        with tab3:
            st.subheader("راتبي")
            calc = compute_payroll(user)
            c1, c2, c3 = st.columns(3)
            c1.metric("الراتب الأساسي", f"${calc['base_salary']:.2f}")
            c2.metric(f"الإضافي ({calc['unpaid_overtime_hours']:.2f} ساعة)", f"${calc['overtime_pay']:.2f}")
            c3.metric("الصافي المتوقع الآن", f"${calc['net']:.2f}")

            if calc['unpaid_advances_total'] > 0:
                st.info(f"لديك سلفة مقبولة بقيمة ${calc['unpaid_advances_total']:.2f} سيتم خصمها من راتبك القادم.")
            if calc['previous_debt'] > 0:
                st.info(f"لديك دين سابق قدره ${calc['previous_debt']:.2f} يتم خصمه من راتبك.")
            if calc['new_debt'] > 0:
                st.warning(f"⚠️ بعد خصم السلف، سيتبقى عليك دين قدره ${calc['new_debt']:.2f} يُخصم من راتب الشهر القادم.")

            # طلبات دفع بانتظار تأكيد الموظف
            my_payments = [p for p in load_payments() if p.get('emp_id') == user['id']]
            pending_payments = [p for p in my_payments if p.get('employee_confirmed') != 'Yes']

            if pending_payments:
                st.divider()
                st.markdown("#### 💰 لديك دفعة راتب بانتظار تأكيدك")
                for p in pending_payments:
                    with st.container(border=True):
                        st.write(f"تم دفع مبلغ **${float(p['amount']):.2f}** بتاريخ **{p['pay_date']}**.")
                        if float(p.get('debt_after', 0) or 0) > 0:
                            st.caption(f"⚠️ تبقى عليك دين ${float(p['debt_after']):.2f} من هذه الدفعة.")
                        if st.button("✅ أؤكد استلام الراتب", key=f"confirm_{p['payment_id']}", use_container_width=True):
                            confirm_payment_received(p['payment_id'])
                            st.success("✅ تم تأكيد استلام الراتب، شكراً لك!")
                            st.rerun()

            if my_payments:
                st.divider()
                st.markdown("#### 📜 سجل رواتبي المدفوعة")
                df_mp = pd.DataFrame(my_payments)
                df_mp["الحالة"] = df_mp["employee_confirmed"].apply(lambda v: "✅ مؤكد" if v == "Yes" else "⏳ بانتظار تأكيدك")
                df_show = df_mp.rename(columns={"amount": "المبلغ", "pay_date": "تاريخ الدفع"})[
                    ["المبلغ", "تاريخ الدفع", "الحالة"]
                ]
                st.dataframe(df_show, use_container_width=True, hide_index=True)

        with tab4:
            st.subheader("حالة طلباتي")
            my_reqs = [r for r in load_requests() if r.get('emp_id') == user['id']]
            if not my_reqs:
                st.info("لم تقدّم أي طلبات بعد.")
            else:
                for r in my_reqs:
                    status = r.get('status', 'Pending')
                    label = req_type_ar(r.get('req_type'))
                    if status in ("Approved", "Deducted"):
                        st.success(f"**{label}** — {r.get('details')} — {req_status_ar(status)}")
                    elif status == "Rejected":
                        st.error(f"**{label}** — {r.get('details')} — ❌ تم الرفض")
                    else:
                        st.warning(f"**{label}** — {r.get('details')} — ⏳ قيد المراجعة")
