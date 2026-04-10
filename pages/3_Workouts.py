import streamlit as st
import psycopg2
import psycopg2.extras

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Manage Workouts", page_icon="🏃", layout="wide")

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

.confirm-box {
    background: #2d1a1a;
    border: 1px solid #6e2020;
    border-radius: 8px;
    padding: 0.8rem 1.1rem;
    margin-top: 0.4rem;
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

.meta-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 0.3rem;
}

hr { border-color: #21262d !important; }
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

def fetch_workouts(conn):
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            SELECT WorkoutID, WorkoutName, WorkoutType
            FROM Workouts
            ORDER BY WorkoutType, WorkoutName;
        """)
        return cur.fetchall()

def insert_workout(conn, name, wtype):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO Workouts (WorkoutName, WorkoutType) VALUES (%s, %s);",
            (name, wtype)
        )
    conn.commit()

def update_workout(conn, workout_id, name, wtype):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE Workouts SET WorkoutName=%s, WorkoutType=%s WHERE WorkoutID=%s;",
            (name, wtype, workout_id)
        )
    conn.commit()

def delete_workout(conn, workout_id):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM Workouts WHERE WorkoutID=%s;", (workout_id,))
    conn.commit()

# ── Validation ────────────────────────────────────────────────────────────────
def validate_workout(name, wtype):
    errors = []
    if not name.strip():
        errors.append("Workout Name is required.")
    if not wtype.strip():
        errors.append("Workout Type is required.")
    return errors

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in {
    "workout_edit_id":    None,
    "workout_edit_name":  "",
    "workout_edit_type":  "",
    "confirm_delete_id":  None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("🏃 Manage Workouts")
conn = get_connection()

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — Add Workout Form
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<h2>Add New Workout <span class="mode-badge mode-add">New</span></h2>', unsafe_allow_html=True)

with st.form("add_workout_form", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        new_name  = st.text_input("Workout Name *", max_chars=20, placeholder="5K Tempo Run")
    with col2:
        new_type  = st.text_input("Workout Type *", max_chars=20, placeholder="Cardio")

    submitted = st.form_submit_button("➕ Add Workout", type="primary")

if submitted:
    errors = validate_workout(new_name, new_type)
    if errors:
        for e in errors:
            st.error(e)
    else:
        try:
            insert_workout(conn, new_name.strip(), new_type.strip())
            st.success(f"✅ Workout **{new_name.strip()}** added successfully!")
            st.rerun()
        except Exception as ex:
            conn.rollback()
            st.error(f"Database error: {ex}")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Edit Form (shown only when editing)
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.workout_edit_id is not None:
    st.markdown("---")
    st.markdown('<h2>Edit Workout <span class="mode-badge mode-edit">Editing</span></h2>', unsafe_allow_html=True)

    with st.form("edit_workout_form"):
        col1, col2 = st.columns(2)
        with col1:
            edit_name = st.text_input("Workout Name *", value=st.session_state.workout_edit_name, max_chars=20)
        with col2:
            edit_type = st.text_input("Workout Type *", value=st.session_state.workout_edit_type, max_chars=20)

        save_col, cancel_col, _ = st.columns([1, 1, 4])
        with save_col:
            save_btn   = st.form_submit_button("💾 Save Changes", type="primary",   use_container_width=True)
        with cancel_col:
            cancel_btn = st.form_submit_button("✕ Cancel",        type="secondary", use_container_width=True)

    if save_btn:
        errors = validate_workout(edit_name, edit_type)
        if errors:
            for e in errors:
                st.error(e)
        else:
            try:
                update_workout(conn, st.session_state.workout_edit_id, edit_name.strip(), edit_type.strip())
                st.success(f"✅ Workout **{edit_name.strip()}** updated successfully!")
                st.session_state.workout_edit_id   = None
                st.session_state.workout_edit_name = ""
                st.session_state.workout_edit_type = ""
                st.rerun()
            except Exception as ex:
                conn.rollback()
                st.error(f"Database error: {ex}")

    if cancel_btn:
        st.session_state.workout_edit_id   = None
        st.session_state.workout_edit_name = ""
        st.session_state.workout_edit_type = ""
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — Current Workouts Table
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<h2>Current Workouts</h2>', unsafe_allow_html=True)

workouts = fetch_workouts(conn)

if not workouts:
    st.info("No workouts found. Add your first workout above.")
else:
    st.markdown(
        f'<p class="meta-label">{len(workouts)} workout{"s" if len(workouts) != 1 else ""} on record</p>',
        unsafe_allow_html=True,
    )

    # ── Header row ────────────────────────────────────────────────────────────
    hc1, hc2, hc3, hc4, hc5 = st.columns([0.5, 3, 3, 1, 1])
    hc1.markdown('<p class="meta-label">ID</p>',           unsafe_allow_html=True)
    hc2.markdown('<p class="meta-label">Workout Name</p>', unsafe_allow_html=True)
    hc3.markdown('<p class="meta-label">Type</p>',         unsafe_allow_html=True)
    hc4.markdown('<p class="meta-label">Edit</p>',         unsafe_allow_html=True)
    hc5.markdown('<p class="meta-label">Delete</p>',       unsafe_allow_html=True)

    st.markdown('<hr style="margin:0.3rem 0 0.6rem 0;">', unsafe_allow_html=True)

    # ── Data rows ─────────────────────────────────────────────────────────────
    for workout in workouts:
        wid   = workout["workoutid"]
        wname = workout["workoutname"]
        wtype = workout["workouttype"] or "—"

        col1, col2, col3, col4, col5 = st.columns([0.5, 3, 3, 1, 1])
        col1.markdown(
            f"<span style='color:#8b949e;font-family:DM Mono,monospace;font-size:0.82rem;'>{wid}</span>",
            unsafe_allow_html=True,
        )
        col2.markdown(f"<span style='font-weight:500;'>{wname}</span>", unsafe_allow_html=True)
        col3.markdown(
            f"<span style='font-family:DM Mono,monospace;font-size:0.85rem;"
            f"background:#1c2128;padding:2px 8px;border-radius:12px;"
            f"color:#79c0ff;border:1px solid #30363d;'>{wtype}</span>",
            unsafe_allow_html=True,
        )

        with col4:
            if st.button("✏️ Edit", key=f"edit_{wid}", use_container_width=True):
                st.session_state.workout_edit_id   = wid
                st.session_state.workout_edit_name = wname
                st.session_state.workout_edit_type = workout["workouttype"] or ""
                st.session_state.confirm_delete_id = None
                st.rerun()

        with col5:
            if st.button("🗑️ Delete", key=f"del_{wid}", use_container_width=True):
                st.session_state.confirm_delete_id = wid
                st.session_state.workout_edit_id   = None
                st.rerun()

        # ── Inline delete confirmation ─────────────────────────────────────
        if st.session_state.confirm_delete_id == wid:
            st.markdown(
                f'<div class="confirm-box">⚠️ Delete <strong>{wname}</strong>? '
                f'This will also remove all associated workout records.</div>',
                unsafe_allow_html=True,
            )
            conf1, conf2, _ = st.columns([1, 1, 5])
            with conf1:
                if st.button("✅ Yes, Delete", key=f"confirm_{wid}", type="primary", use_container_width=True):
                    try:
                        delete_workout(conn, wid)
                        st.session_state.confirm_delete_id = None
                        st.success(f"🗑️ Workout **{wname}** deleted.")
                        st.rerun()
                    except Exception as ex:
                        conn.rollback()
                        st.error(f"Database error: {ex}")
            with conf2:
                if st.button("✕ Cancel", key=f"cancel_del_{wid}", type="secondary", use_container_width=True):
                    st.session_state.confirm_delete_id = None
                    st.rerun()

        st.markdown('<hr style="margin:0.3rem 0;">', unsafe_allow_html=True)
