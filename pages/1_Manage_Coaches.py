import streamlit as st
import psycopg2
import psycopg2.extras
import re

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Manage Coaches", page_icon="🧑‍🏫", layout="wide")

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Barlow+Condensed:wght@600;700&family=Barlow:wght@400;500&display=swap');

html, body, [class*="css"] { font-family: 'Barlow', sans-serif; }

.stApp { background: #0d1117; color: #e6edf3; }

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

label {
    font-family: 'DM Mono', monospace !important;
    font-size: 0.78rem !important;
    color: #8b949e !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

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

/* Row card */
.coach-row {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 8px;
    padding: 0.7rem 1rem;
    margin-bottom: 0.5rem;
    display: flex;
    align-items: center;
}

.section-card {
    background: #161b22;
    border: 1px solid #21262d;
    border-radius: 10px;
    padding: 1.4rem 1.6rem;
    margin-bottom: 1.4rem;
}

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
.mode-add  { background:#0f2d1f; color:#3fb950; border:1px solid #238636; }
.mode-edit { background:#1c1a0f; color:#e3b341; border:1px solid #9e6a03; }

.confirm-box {
    background: #2d1a1a;
    border: 1px solid #6e2020;
    border-radius: 8px;
    padding: 0.8rem 1.1rem;
    margin-top: 0.4rem;
}
hr { border-color: #21262d !important; }

.meta-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 0.3rem;
}
</style>
""", unsafe_allow_html=True)

# ── DB helpers ────────────────────────────────────────────────────────────────
@st.cache_resource
def get_connection():
    if "db_conn" not in st.session_state or st.session_state.db_conn.closed:
        st.session_state.db_conn = psycopg2.connect(st.secrets["DB_URL"])
    else:
        try:
            # ping the connection to make sure it's still alive
            st.session_state.db_conn.cursor().execute("SELECT 1")
        except Exception:
            st.session_state.db_conn = psycopg2.connect(st.secrets["DB_URL"])
    return st.session_state.db_conn

def fetch_coaches(conn):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT CoachID, CoachName, Phone
            FROM Coaches
            ORDER BY SPLIT_PART(CoachName, ' ', 2), CoachName;
        """)
        return cur.fetchall()

def insert_coach(conn, name, phone):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO Coaches (CoachName, Phone) VALUES (%s, %s);",
            (name, phone)
        )
    conn.commit()

def update_coach(conn, coach_id, name, phone):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE Coaches SET CoachName=%s, Phone=%s WHERE CoachID=%s;",
            (name, phone, coach_id)
        )
    conn.commit()

def delete_coach(conn, coach_id):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM Coaches WHERE CoachID=%s;", (coach_id,))
    conn.commit()

# ── Validation ────────────────────────────────────────────────────────────────
def validate_coach(name, phone):
    errors = []
    if not name.strip():
        errors.append("Coach Name is required.")
    if not phone.strip():
        errors.append("Phone is required.")
    elif not re.fullmatch(r"\d{10}", phone.strip()):
        errors.append("Phone must be exactly 10 digits (no spaces or dashes).")
    return errors

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in {
    "coach_edit_id":      None,
    "coach_edit_name":    "",
    "coach_edit_phone":   "",
    "confirm_delete_id":  None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("🧑‍🏫 Manage Coaches")
conn = get_connection()

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — Add Coach Form
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<h2>Add New Coach <span class="mode-badge mode-add">New</span></h2>', unsafe_allow_html=True)

with st.container():
    with st.form("add_coach_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_name  = st.text_input("Coach Name *", max_chars=30, placeholder="Jane Smith")
        with col2:
            new_phone = st.text_input("Phone * (10 digits)", max_chars=10, placeholder="5095550123")

        submitted = st.form_submit_button("➕ Add Coach", type="primary")

    if submitted:
        errors = validate_coach(new_name, new_phone)
        if errors:
            for e in errors:
                st.error(e)
        else:
            try:
                insert_coach(conn, new_name.strip(), new_phone.strip())
                st.success(f"✅ Coach **{new_name.strip()}** added successfully!")
                st.rerun()
            except Exception as ex:
                conn.rollback()
                st.error(f"Database error: {ex}")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Edit Form (shown only when editing)
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.coach_edit_id is not None:
    st.markdown("---")
    st.markdown('<h2>Edit Coach <span class="mode-badge mode-edit">Editing</span></h2>', unsafe_allow_html=True)

    with st.form("edit_coach_form"):
        col1, col2 = st.columns(2)
        with col1:
            edit_name  = st.text_input("Coach Name *", value=st.session_state.coach_edit_name,  max_chars=30)
        with col2:
            edit_phone = st.text_input("Phone * (10 digits)", value=st.session_state.coach_edit_phone, max_chars=10)

        save_col, cancel_col, _ = st.columns([1, 1, 4])
        with save_col:
            save_btn   = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)
        with cancel_col:
            cancel_btn = st.form_submit_button("✕ Cancel", type="secondary", use_container_width=True)

    if save_btn:
        errors = validate_coach(edit_name, edit_phone)
        if errors:
            for e in errors:
                st.error(e)
        else:
            try:
                update_coach(conn, st.session_state.coach_edit_id, edit_name.strip(), edit_phone.strip())
                st.success(f"✅ Coach **{edit_name.strip()}** updated successfully!")
                st.session_state.coach_edit_id    = None
                st.session_state.coach_edit_name  = ""
                st.session_state.coach_edit_phone = ""
                st.rerun()
            except Exception as ex:
                conn.rollback()
                st.error(f"Database error: {ex}")

    if cancel_btn:
        st.session_state.coach_edit_id    = None
        st.session_state.coach_edit_name  = ""
        st.session_state.coach_edit_phone = ""
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — Current Coaches Table
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<h2>Current Coaches</h2>', unsafe_allow_html=True)

coaches = fetch_coaches(conn)

if not coaches:
    st.info("No coaches found. Add your first coach above.")
else:
    st.markdown(
        f'<p class="meta-label">{len(coaches)} coach{"es" if len(coaches) != 1 else ""} on staff</p>',
        unsafe_allow_html=True,
    )

    # ── Header row ────────────────────────────────────────────────────────────
    hcol1, hcol2, hcol3, hcol4, hcol5 = st.columns([0.5, 3, 2, 1, 1])
    hcol1.markdown('<p class="meta-label">ID</p>',    unsafe_allow_html=True)
    hcol2.markdown('<p class="meta-label">Name</p>',  unsafe_allow_html=True)
    hcol3.markdown('<p class="meta-label">Phone</p>', unsafe_allow_html=True)
    hcol4.markdown('<p class="meta-label">Edit</p>',  unsafe_allow_html=True)
    hcol5.markdown('<p class="meta-label">Delete</p>',unsafe_allow_html=True)

    st.markdown('<hr style="margin:0.3rem 0 0.6rem 0;">', unsafe_allow_html=True)

    # ── Data rows ─────────────────────────────────────────────────────────────
    for coach in coaches:
        cid   = coach["coachid"]
        cname = coach["coachname"]
        cphone= coach["phone"] or "—"

        col1, col2, col3, col4, col5 = st.columns([0.5, 3, 2, 1, 1])
        col1.markdown(f"<span style='color:#8b949e;font-family:DM Mono,monospace;font-size:0.82rem;'>{cid}</span>", unsafe_allow_html=True)
        col2.markdown(f"<span style='font-weight:500;'>{cname}</span>", unsafe_allow_html=True)
        col3.markdown(f"<span style='font-family:DM Mono,monospace;font-size:0.85rem;'>{cphone}</span>", unsafe_allow_html=True)

        with col4:
            if st.button("✏️ Edit", key=f"edit_{cid}", use_container_width=True):
                st.session_state.coach_edit_id    = cid
                st.session_state.coach_edit_name  = cname
                st.session_state.coach_edit_phone = coach["phone"] or ""
                st.session_state.confirm_delete_id = None
                st.rerun()

        with col5:
            if st.button("🗑️ Delete", key=f"del_{cid}", use_container_width=True):
                st.session_state.confirm_delete_id = cid
                st.session_state.coach_edit_id = None
                st.rerun()

        # ── Inline delete confirmation ─────────────────────────────────────
        if st.session_state.confirm_delete_id == cid:
            st.markdown(
                f'<div class="confirm-box">⚠️ Delete <strong>{cname}</strong>? This cannot be undone.</div>',
                unsafe_allow_html=True,
            )
            conf_col1, conf_col2, _ = st.columns([1, 1, 5])
            with conf_col1:
                if st.button("✅ Yes, Delete", key=f"confirm_{cid}", type="primary", use_container_width=True):
                    try:
                        delete_coach(conn, cid)
                        st.session_state.confirm_delete_id = None
                        st.success(f"🗑️ Coach **{cname}** deleted.")
                        st.rerun()
                    except Exception as ex:
                        conn.rollback()
                        st.error(f"Database error: {ex}")
            with conf_col2:
                if st.button("✕ Cancel", key=f"cancel_del_{cid}", type="secondary", use_container_width=True):
                    st.session_state.confirm_delete_id = None
                    st.rerun()

        st.markdown('<hr style="margin:0.3rem 0;">', unsafe_allow_html=True)
