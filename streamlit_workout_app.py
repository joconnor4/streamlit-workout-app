import streamlit as st
import psycopg2

st.set_page_config(page_title="Workout Tracker App", page_icon="🏋️", layout="wide")

def get_connection():
    return psycopg2.connect(st.secrets["DB_URL"])

st.title("🏋️ Workout Tracker App")
st.write("Welcome! Use the sidebar to navigate between pages.")
st.markdown("---")

try:
    conn = get_connection()
    cur = conn.cursor()

    # ── Metrics ──────────────────────────────────────────────────────────────
    st.subheader("📊 Current Data")

    cur.execute("SELECT COUNT(*) FROM Athletes;")
    athlete_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(DISTINCT WorkoutType) FROM Workouts;")
    workout_type_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM WorkoutRecords;")
    record_count = cur.fetchone()[0]

    cur.execute("SELECT CoachName FROM Coaches ORDER BY CoachName;")
    coach_names = [row[0] for row in cur.fetchall()]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👟 Athletes",       athlete_count)
    col2.metric("🗂️ Workout Types",  workout_type_count)
    col3.metric("📝 Total Records",  record_count)
    col4.metric("🧑‍🏫 Coaches",        len(coach_names))

    # ── Coaches list ─────────────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🧑‍🏫 Coaching Staff")
    if coach_names:
        cols = st.columns(min(len(coach_names), 4))
        for i, name in enumerate(coach_names):
            cols[i % 4].info(f"👤 {name}")
    else:
        st.info("No coaches added yet.")

    # ── Workout Types breakdown ───────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🗂️ Workout Types")

    cur.execute("""
        SELECT WorkoutType, COUNT(*) AS workout_count
        FROM Workouts
        GROUP BY WorkoutType
        ORDER BY workout_count DESC;
    """)
    type_rows = cur.fetchall()

    if type_rows:
        type_cols = st.columns(min(len(type_rows), 4))
        for i, (wtype, count) in enumerate(type_rows):
            type_cols[i % 4].metric(label=wtype or "Uncategorized", value=f"{count} workout{'s' if count != 1 else ''}")
    else:
        st.info("No workout types found.")

    # ── Recent Workout Submissions ────────────────────────────────────────────
    st.markdown("---")
    st.subheader("📋 Recent Workout Submissions")

    cur.execute("""
        SELECT
            a.AthleteName,
            w.WorkoutName,
            w.WorkoutType,
            wr.StartTime,
            wr.Duration,
            wr.Pace,
            wr.AverageHR
        FROM WorkoutRecords wr
        JOIN Athletes a  ON wr.AthleteID  = a.AthleteID
        JOIN Workouts w  ON wr.WorkoutID  = w.WorkoutID
        ORDER BY wr.StartTime DESC
        LIMIT 20;
    """)
    rows = cur.fetchall()

    if rows:
        st.table([
            {
                "Athlete":     r[0],
                "Workout":     r[1],
                "Type":        r[2],
                "Start Time":  r[3].strftime("%Y-%m-%d %H:%M") if r[3] else "—",
                "Duration":    r[4] or "—",
                "Pace":        r[5] or "—",
                "Avg HR (bpm)": r[6] if r[6] else "—",
            }
            for r in rows
        ])
    else:
        st.info("No workout records yet. Log some workouts to see them here!")

    cur.close()
    conn.close()

except Exception as e:
    st.error(f"Database connection error: {e}")