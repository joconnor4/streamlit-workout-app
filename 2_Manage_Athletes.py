import streamlit as st
import psycopg2
import psycopg2.extras
import re
from datetime import datetime

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Manage Athletes",
    page_icon="🏅",
    layout="wide",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Barlow+Condensed:wght@600;700&family=Barlow:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'Barlow', sans-serif;
    }

    /* ── Background ── */
    .stApp {
        background: #0d1117;
        color: #e6edf3;
    }

    /* ── Page title ── */
    h1 {
        font-family: 'Barlow Condensed', sans-serif;
        font-size: 2.6rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.04em;
        color: #58a6ff !important;
        border-bottom: 2px solid #21262d;
        padding-bottom: 0.4rem;
        margin-bottom: 1.4rem !important;
    }

    h2, h3 {
        font-family: 'Barlow Condensed', sans-serif;
        font-weight: 600 !important;
        letter-spacing: 0.03em;
        color: #c9d1d9 !important;
    }

    /* ── Cards / containers ── */
    .card {
        background: #161b22;
        border: 1px solid #21262d;
        border-radius: 10px;
        padding: 1.6rem 1.8rem;
        margin-bottom: 1.6rem;
    }

    /* ── Form labels ── */
    label {
        font-family: 'DM Mono', monospace !important;
        font-size: 0.78rem !important;
        color: #8b949e !important;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }

    /* ── Inputs ── */
    input[type="text"], input[type="date"], textarea, select {
        background: #0d1117 !important;
        color: #e6edf3 !important;
        border: 1px solid #30363d !important;
        border-radius: 6px !important;
        font-family: 'Barlow', sans-serif !important;
    }
    input[type="text"]:focus, input[type="date"]:focus {
        border-color: #58a6ff !important;
        box-shadow: 0 0 0 3px rgba(88,166,255,0.15) !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        font-family: 'Barlow Condensed', sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: 0.06em;
        border-radius: 6px !important;
        transition: all 0.18s ease !important;
    }
    .stButton > button[kind="primary"] {
        background: #238636 !important;
        border-color: #2ea043 !important;
        color: #fff !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #2ea043 !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(46,160,67,0.35) !important;
    }
    .stButton > button[kind="secondary"] {
        background: #21262d !important;
        border-color: #30363d !important;
        color: #c9d1d9 !important;
    }

    /* ── Selectbox ── */
    .stSelectbox > div > div {
        background: #0d1117 !important;
        border-color: #30363d !important;
        color: #e6edf3 !important;
    }

    /* ── DataTable ── */
    .stDataFrame {
        border: 1px solid #21262d !important;
        border-radius: 8px;
        overflow: hidden;
    }
    .stDataFrame thead tr th {
        background: #161b22 !important;
        color: #58a6ff !important;
        font-family: 'DM Mono', monospace !important;
        font-size: 0.76rem !important;
        letter-spacing: 0.07em;
        text-transform: uppercase;
        border-bottom: 2px solid #21262d !important;
    }
    .stDataFrame tbody tr:nth-child(even) td {
        background: #0d1117 !important;
    }
    .stDataFrame tbody tr:hover td {
        background: #1c2128 !important;
    }

    /* ── Alert banners ── */
    .stAlert {
        border-radius: 8px !important;
    }

    /* ── Mode badge ── */
    .mode-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 20px;
        font-family: 'DM Mono', monospace;
        font-size: 0.72rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        margin-left: 0.5rem;
        vertical-align: middle;
    }
    .mode-add  { background: #0f2d1f; color: #3fb950; border: 1px solid #238636; }
    .mode-edit { background: #1c1a0f; color: #e3b341; border: 1px solid #9e6a03; }

    /* ── Divider ── */
    hr { border-color: #21262d !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── DB helpers ────────────────────────────────────────────────────────────────

@st.cache_resource
def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"])


def get_cursor(conn):
    return conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def fetch_athletes(conn):
    with get_cursor(conn) as cur:
        cur.execute(
            "SELECT AthleteID, AthleteName, Phone, BirthDate, GradYear "
            "FROM Athletes ORDER BY AthleteName;"
        )
        return cur.fetchall()


def insert_athlete(conn, name, phone, birth, grad):
    with get_cursor(conn) as cur:
        cur.execute(
            "INSERT INTO Athletes (AthleteName, Phone, BirthDate, GradYear) "
            "VALUES (%s, %s, %s, %s);",
            (name, phone, birth, grad),
        )
    conn.commit()


def update_athlete(conn, aid, name, phone, birth, grad):
    with get_cursor(conn) as cur:
        cur.execute(
            "UPDATE Athletes SET AthleteName=%s, Phone=%s, BirthDate=%s, GradYear=%s "
            "WHERE AthleteID=%s;",
            (name, phone, birth, grad, aid),
        )
    conn.commit()


# ── Validation ────────────────────────────────────────────────────────────────

def validate(name, phone, birth, grad):
    errors = []
    if not name.strip():
        errors.append("Athlete Name is required.")
    if not phone.strip():
        errors.append("Phone is required.")
    elif not re.fullmatch(r"\d{10}", phone.strip()):
        errors.append("Phone must be exactly 10 digits (no spaces or dashes).")
    if not birth.strip():
        errors.append("Birth Date is required.")
    else:
        try:
            datetime.strptime(birth.strip(), "%Y-%m-%d")
        except ValueError:
            errors.append("Birth Date must be in YYYY-MM-DD format.")
    if not grad.strip():
        errors.append("Graduation Year is required.")
    elif not re.fullmatch(r"\d{4}", grad.strip()):
        errors.append("Graduation Year must be exactly 4 digits.")
    return errors


# ── Session state ─────────────────────────────────────────────────────────────

if "mode" not in st.session_state:
    st.session_state.mode = "add"          # "add" | "edit"
if "edit_athlete" not in st.session_state:
    st.session_state.edit_athlete = None
if "refresh" not in st.session_state:
    st.session_state.refresh = 0


# ── Layout ────────────────────────────────────────────────────────────────────

st.title("🏅 Manage Athletes")

conn = get_connection()

# ── Helper: load roster (re-runs on refresh counter change) ──────────────────
athletes = fetch_athletes(conn)

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 – Form
# ─────────────────────────────────────────────────────────────────────────────

mode = st.session_state.mode
badge_cls = "mode-add" if mode == "add" else "mode-edit"
badge_lbl = "Add New" if mode == "add" else "Edit"

st.markdown(
    f'<h2>Athlete Form '
    f'<span class="mode-badge {badge_cls}">{badge_lbl}</span></h2>',
    unsafe_allow_html=True,
)

# Pre-fill values when editing
ea = st.session_state.edit_athlete or {}
default_name  = ea.get("athletename", "")
default_phone = ea.get("phone", "")
default_birth = str(ea.get("birthdate", "")) if ea.get("birthdate") else ""
default_grad  = ea.get("gradyear", "")

with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)

    with st.form("athlete_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            name  = st.text_input("Athlete Name *", value=default_name, max_chars=30)
            phone = st.text_input("Phone * (10 digits)", value=default_phone, max_chars=10,
                                  placeholder="5095550123")
        with col2:
            birth = st.text_input("Birth Date * (YYYY-MM-DD)", value=default_birth,
                                  placeholder="2005-08-15")
            grad  = st.text_input("Graduation Year * (4 digits)", value=default_grad,
                                  max_chars=4, placeholder="2027")

        st.markdown("<br>", unsafe_allow_html=True)
        btn_col1, btn_col2, _ = st.columns([1, 1, 4])
        with btn_col1:
            submitted = st.form_submit_button(
                "💾 Save Athlete" if mode == "add" else "✏️ Update Athlete",
                type="primary",
                use_container_width=True,
            )
        with btn_col2:
            cancelled = st.form_submit_button(
                "✕ Cancel", type="secondary", use_container_width=True
            )

    st.markdown("</div>", unsafe_allow_html=True)

# ── Form logic (outside the form block so state can change) ──────────────────
if submitted:
    errors = validate(name, phone, birth, grad)
    if errors:
        for e in errors:
            st.error(e)
    else:
        try:
            if mode == "add":
                insert_athlete(conn, name.strip(), phone.strip(), birth.strip(), grad.strip())
                st.success(f"✅ Athlete **{name.strip()}** added successfully!")
            else:
                update_athlete(
                    conn,
                    ea["athleteid"],
                    name.strip(), phone.strip(), birth.strip(), grad.strip(),
                )
                st.success(f"✅ Athlete **{name.strip()}** updated successfully!")
            # Reset to add mode and refresh roster
            st.session_state.mode = "add"
            st.session_state.edit_athlete = None
            st.session_state.refresh += 1
            st.rerun()
        except Exception as ex:
            conn.rollback()
            st.error(f"Database error: {ex}")

if cancelled:
    st.session_state.mode = "add"
    st.session_state.edit_athlete = None
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 – Roster Table
# ─────────────────────────────────────────────────────────────────────────────

st.markdown("---")
st.markdown('<h2>Athlete Roster</h2>', unsafe_allow_html=True)

if not athletes:
    st.info("No athletes found. Add your first athlete above.")
else:
    # Build display rows
    rows = [
        {
            "ID":           a["athleteid"],
            "Name":         a["athletename"],
            "Phone":        a["phone"],
            "Birth Date":   str(a["birthdate"]),
            "Grad Year":    a["gradyear"],
        }
        for a in athletes
    ]

    # Sub-header with count
    st.markdown(
        f'<p style="font-family:\'DM Mono\',monospace;font-size:0.78rem;'
        f'color:#8b949e;margin-bottom:0.6rem;">'
        f'{len(rows)} ATHLETE{"S" if len(rows)!=1 else ""} REGISTERED</p>',
        unsafe_allow_html=True,
    )

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        column_order=["ID", "Name", "Phone", "Birth Date", "Grad Year"],
    )

    # ── Edit picker ──────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<p style="font-family:\'Barlow Condensed\',sans-serif;font-weight:600;'
        'font-size:1rem;color:#c9d1d9;letter-spacing:0.04em;">EDIT AN ATHLETE</p>',
        unsafe_allow_html=True,
    )

    athlete_options = {f"{a['athletename']} (ID {a['athleteid']})": a for a in athletes}
    selected_label = st.selectbox(
        "Select athlete to edit",
        options=["— select —"] + list(athlete_options.keys()),
        label_visibility="collapsed",
    )

    if selected_label != "— select —":
        if st.button("✏️ Load into Form", type="secondary"):
            selected = athlete_options[selected_label]
            st.session_state.edit_athlete = dict(selected)
            st.session_state.mode = "edit"
            st.rerun()