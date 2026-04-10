import streamlit as st
import psycopg2
import psycopg2.extras
from datetime import datetime

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Workout Records", page_icon="📋", layout="wide")

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

.step-pill {
    display: inline-block;
    background: #1c2128;
    border: 1px solid #30363d;
    border-radius: 20px;
    padding: 3px 12px;
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    color: #58a6ff;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    margin-bottom: 0.6rem;
}
.type-badge {
    background: #1c2128;
    padding: 2px 8px;
    border-radius: 12px;
    color: #79c0ff;
    border: 1px solid #30363d;
    font-family: 'DM Mono', monospace;
    font-size: 0.82rem;
}
.meta-label {
    font-family: 'DM Mono', monospace;
    font-size: 0.72rem;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-bottom: 0.3rem;
}
.divider-line { border-color: #21262d !important; }
hr { border-color: #21262d !important; }
</style>
""", unsafe_allow_html=True)

# ── DB helpers ────────────────────────────────────────────────────────────────
def get_connection():
    if "db_conn" not in st.session_state or st.session_state.db_conn.closed:
        st.session_state.db_conn = psycopg2.connect(st.secrets["DB_URL"])
    else:
        try:
            st.session_state.db_conn.cursor().execute("SELECT 1")
        except Exception:
            st.session_state.db_conn = psycopg2.connect(st.secrets["DB_URL"])
    return st.session_state.db_conn

def fetch_athletes(conn):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT AthleteID, AthleteName FROM Athletes ORDER BY AthleteName;")
    results = cur.fetchall()
    cur.close()
    return results

def fetch_workout_types(conn):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT DISTINCT WorkoutType FROM Workouts WHERE WorkoutType IS NOT NULL ORDER BY WorkoutType;")
    results = [r["workouttype"] for r in cur.fetchall()]
    cur.close()
    return results

def fetch_workouts_by_type(conn, wtype):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT WorkoutID, WorkoutName FROM Workouts WHERE WorkoutType=%s ORDER BY WorkoutName;",
        (wtype,)
    )
    results = cur.fetchall()
    cur.close()
    return results

def fetch_records(conn):
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT
            wr.AthleteID,
            wr.WorkoutID,
            a.AthleteName,
            w.WorkoutName,
            w.WorkoutType,
            wr.Duration,
            wr.Pace,
            wr.AverageHR
        FROM WorkoutRecords wr
        JOIN Athletes a ON wr.AthleteID  = a.AthleteID
        JOIN Workouts w ON wr.WorkoutID  = w.WorkoutID
        ORDER BY w.WorkoutType, a.AthleteName;
    """)
    results = cur.fetchall()
    cur.close()
    return results

def insert_record(conn, athlete_id, workout_id, duration, pace, avg_hr):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO WorkoutRecords (AthleteID, WorkoutID, Duration, Pace, AverageHR)
        VALUES (%s, %s, %s, %s, %s);
    """, (athlete_id, workout_id, duration, pace, avg_hr))
    cur.close()
    conn.commit()

def update_record(conn, athlete_id, workout_id, duration, pace, avg_hr):
    cur = conn.cursor()
    cur.execute("""
        UPDATE WorkoutRecords
        SET Duration=%s, Pace=%s, AverageHR=%s
        WHERE AthleteID=%s AND WorkoutID=%s;
    """, (duration, pace, avg_hr, athlete_id, workout_id))
    cur.close()
    conn.commit()

def delete_record(conn, athlete_id, workout_id):
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM WorkoutRecords WHERE AthleteID=%s AND WorkoutID=%s;",
        (athlete_id, workout_id)
    )
    cur.close()
    conn.commit()

# ── Validation ────────────────────────────────────────────────────────────────
def validate_record(duration, pace, avg_hr_str):
    errors = []
    if not duration.strip():
        errors.append("Duration is required.")
    if not pace.strip():
        errors.append("Pace is required.")
    if not avg_hr_str.strip():
        errors.append("Average Heart Rate is required.")
    else:
        try:
            hr = int(avg_hr_str.strip())
            if hr <= 0 or hr > 300:
                errors.append("Average Heart Rate must be a positive number between 1 and 300.")
        except ValueError:
            errors.append("Average Heart Rate must be a whole number.")
    return errors

# ── Session state ─────────────────────────────────────────────────────────────
for key, default in {
    # Step 1 selections
    "selected_athlete_id":   None,
    "selected_athlete_name": "",
    "selected_type":         None,
    "selected_workout_id":   None,
    "selected_workout_name": "",
    "step":                  1,
    # Edit state
    "edit_athlete_id":       None,
    "edit_workout_id":       None,
    "edit_duration":         "",
    "edit_pace":             "",
    "edit_avg_hr":           "",
    # Delete confirmation
    "confirm_delete_key":    None,
    # Filter
    "filter_type":           "All",
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("📋 Workout Records")
conn = get_connection()

athletes     = fetch_athletes(conn)
workout_types = fetch_workout_types(conn)

athlete_map  = {a["athletename"]: a["athleteid"] for a in athletes}
athlete_names = list(athlete_map.keys())

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 1 — Record a Workout Session (2-step)
# ─────────────────────────────────────────────────────────────────────────────
st.markdown('<h2>Record a Workout Session <span class="mode-badge mode-add">New</span></h2>', unsafe_allow_html=True)

# ── STEP 1: Select Athlete & Workout ─────────────────────────────────────────
st.markdown('<div class="step-pill">Step 1 — Select Athlete & Workout</div>', unsafe_allow_html=True)

with st.form("step1_form"):
    col1, col2 = st.columns(2)
    with col1:
        chosen_athlete = st.selectbox(
            "Athlete *",
            options=["— select athlete —"] + athlete_names,
            index=0,
        )
    with col2:
        chosen_type = st.selectbox(
            "Workout Type *",
            options=["— select type —"] + workout_types,
            index=0,
        )
    next_btn = st.form_submit_button("Next: Choose Workout →", type="primary")

if next_btn:
    if chosen_athlete == "— select athlete —":
        st.error("Please select an athlete.")
    elif chosen_type == "— select type —":
        st.error("Please select a workout type.")
    else:
        st.session_state.selected_athlete_id   = athlete_map[chosen_athlete]
        st.session_state.selected_athlete_name = chosen_athlete
        st.session_state.selected_type         = chosen_type
        st.session_state.step                  = 2
        st.session_state.selected_workout_id   = None
        st.rerun()

# ── STEP 2: Pick specific workout + log metrics ───────────────────────────────
if st.session_state.step == 2 and st.session_state.selected_type:
    workouts_for_type = fetch_workouts_by_type(conn, st.session_state.selected_type)
    workout_map  = {w["workoutname"]: w["workoutid"] for w in workouts_for_type}
    workout_names = list(workout_map.keys())

    st.markdown("---")
    st.markdown(
        f'<div class="step-pill">Step 2 — Log Metrics</div>'
        f'<p style="font-family:\'DM Mono\',monospace;font-size:0.8rem;color:#8b949e;margin-top:0.2rem;">'
        f'Athlete: <strong style="color:#e6edf3;">{st.session_state.selected_athlete_name}</strong>'
        f' &nbsp;|&nbsp; Type: <strong style="color:#79c0ff;">{st.session_state.selected_type}</strong></p>',
        unsafe_allow_html=True,
    )

    with st.form("step2_form"):
        workout_choice = st.selectbox(
            "Workout *",
            options=["— select workout —"] + workout_names,
        )

        col1, col2 = st.columns(2)
        with col1:
            duration_str = st.text_input("Duration *", placeholder="45:00")
        with col2:
            pace_str     = st.text_input("Pace *", placeholder="8:30 /mi")

        avg_hr_str = st.text_input("Average Heart Rate * (bpm)", placeholder="155")

        save_col, back_col, _ = st.columns([1, 1, 4])
        with save_col:
            log_btn  = st.form_submit_button("💾 Log Workout", type="primary", use_container_width=True)
        with back_col:
            back_btn = st.form_submit_button("← Back",         type="secondary", use_container_width=True)

    if back_btn:
        st.session_state.step = 1
        st.rerun()

    if log_btn:
        if workout_choice == "— select workout —":
            st.error("Please select a workout.")
        else:
            errors = validate_record(duration_str, pace_str, avg_hr_str)
            if errors:
                for e in errors:
                    st.error(e)
            else:
                try:
                    insert_record(
                        conn,
                        st.session_state.selected_athlete_id,
                        workout_map[workout_choice],
                        duration_str.strip(),
                        pace_str.strip(),
                        int(avg_hr_str.strip()),
                    )
                    st.success(
                        f"✅ Workout logged for **{st.session_state.selected_athlete_name}** — "
                        f"**{workout_choice}**!"
                    )
                    st.session_state.step = 1
                    st.session_state.selected_type = None
                    st.rerun()
                except psycopg2.errors.UniqueViolation:
                    conn.rollback()
                    st.error("A record for this athlete and workout already exists. Use Edit to update it.")
                except Exception as ex:
                    conn.rollback()
                    st.error(f"Database error: {ex}")

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 2 — Edit Form
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.edit_athlete_id is not None:
    st.markdown("---")
    st.markdown('<h2>Edit Workout Record <span class="mode-badge mode-edit">Editing</span></h2>', unsafe_allow_html=True)

    with st.form("edit_record_form"):
        col1, col2 = st.columns(2)
        with col1:
            e_duration = st.text_input("Duration *", value=st.session_state.edit_duration)
        with col2:
            e_pace     = st.text_input("Pace *",     value=st.session_state.edit_pace)

        e_avg_hr = st.text_input("Average Heart Rate * (bpm)", value=st.session_state.edit_avg_hr)

        save_col, cancel_col, _ = st.columns([1, 1, 4])
        with save_col:
            edit_save   = st.form_submit_button("💾 Save Changes", type="primary",   use_container_width=True)
        with cancel_col:
            edit_cancel = st.form_submit_button("✕ Cancel",        type="secondary", use_container_width=True)

    if edit_save:
        errors = validate_record(e_duration, e_pace, e_avg_hr)
        if errors:
            for e in errors:
                st.error(e)
        else:
            try:
                update_record(
                    conn,
                    st.session_state.edit_athlete_id,
                    st.session_state.edit_workout_id,
                    e_duration.strip(),
                    e_pace.strip(),
                    int(e_avg_hr.strip()),
                )
                st.success("✅ Workout record updated successfully!")
                st.session_state.edit_athlete_id = None
                st.rerun()
            except Exception as ex:
                conn.rollback()
                st.error(f"Database error: {ex}")

    if edit_cancel:
        st.session_state.edit_athlete_id = None
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# SECTION 3 — All Workout Records Table
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<h2>All Workout Records</h2>', unsafe_allow_html=True)

records = fetch_records(conn)

if not records:
    st.info("No workout records yet. Log your first session above.")
else:
    st.markdown(
        f'<p class="meta-label">{len(records)} record{"s" if len(records) != 1 else ""} logged</p>',
        unsafe_allow_html=True,
    )

    # ── Header ────────────────────────────────────────────────────────────────
    hc = st.columns([2.5, 2, 1.5, 2, 1.5, 1.5, 1, 1])
    for label, col in zip(
        ["Athlete", "Workout", "Type", "Start Time", "Duration", "Pace", "Avg HR", "Actions"],
        hc,
    ):
        col.markdown(f'<p class="meta-label">{label}</p>', unsafe_allow_html=True)

    st.markdown('<hr style="margin:0.3rem 0 0.5rem 0;">', unsafe_allow_html=True)

    # ── Rows ──────────────────────────────────────────────────────────────────
    for r in records:
        aid      = r["athleteid"]
        wid      = r["workoutid"]
        row_key  = f"{aid}_{wid}"

        col = st.columns([2.5, 2, 1.5, 2, 1.5, 1.5, 1, 1])
        col[0].markdown(f"<span style='font-weight:500;'>{r['athletename']}</span>",  unsafe_allow_html=True)
        col[1].markdown(f"{r['workoutname']}",                                         unsafe_allow_html=True)
        col[2].markdown(
            f"<span class='type-badge'>{r['workouttype'] or '—'}</span>",
            unsafe_allow_html=True,
        )
        col[3].markdown(
            f"<span style='font-family:DM Mono,monospace;font-size:0.8rem;'>"
            f"{r['starttime'].strftime('%Y-%m-%d %H:%M') if r['starttime'] else '—'}</span>",
            unsafe_allow_html=True,
        )
        col[4].markdown(f"{r['duration'] or '—'}", unsafe_allow_html=True)
        col[5].markdown(f"{r['pace'] or '—'}",     unsafe_allow_html=True)
        col[6].markdown(
            f"<span style='font-family:DM Mono,monospace;'>{r['averagehr'] or '—'}</span>",
            unsafe_allow_html=True,
        )

        with col[7]:
            edit_del = st.columns(2)
            with edit_del[0]:
                if st.button("✏️", key=f"edit_{row_key}", use_container_width=True, help="Edit record"):
                    st.session_state.edit_athlete_id  = aid
                    st.session_state.edit_workout_id  = wid
                    st.session_state.edit_start_time  = r["starttime"].strftime("%Y-%m-%d %H:%M:%S") if r["starttime"] else ""
                    st.session_state.edit_duration    = r["duration"]  or ""
                    st.session_state.edit_pace        = r["pace"]      or ""
                    st.session_state.edit_avg_hr      = str(r["averagehr"]) if r["averagehr"] else ""
                    st.session_state.confirm_delete_key = None
                    st.rerun()
            with edit_del[1]:
                if st.button("🗑️", key=f"del_{row_key}", use_container_width=True, help="Delete record"):
                    st.session_state.confirm_delete_key = row_key
                    st.session_state.edit_athlete_id    = None
                    st.rerun()

        # ── Inline delete confirmation ─────────────────────────────────────
        if st.session_state.confirm_delete_key == row_key:
            st.markdown(
                f'<div class="confirm-box">⚠️ Delete the record for '
                f'<strong>{r["athletename"]}</strong> — <strong>{r["workoutname"]}</strong>? '
                f'This cannot be undone.</div>',
                unsafe_allow_html=True,
            )
            c1, c2, _ = st.columns([1, 1, 5])
            with c1:
                if st.button("✅ Confirm", key=f"confirm_{row_key}", type="primary", use_container_width=True):
                    try:
                        delete_record(conn, aid, wid)
                        st.session_state.confirm_delete_key = None
                        st.success("🗑️ Record deleted.")
                        st.rerun()
                    except Exception as ex:
                        conn.rollback()
                        st.error(f"Database error: {ex}")
            with c2:
                if st.button("✕ Cancel", key=f"cancel_{row_key}", type="secondary", use_container_width=True):
                    st.session_state.confirm_delete_key = None
                    st.rerun()

        st.markdown('<hr style="margin:0.3rem 0;">', unsafe_allow_html=True)
