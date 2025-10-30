
import streamlit as st
import pandas as pd
from gen_file import generate_timetable_image
import io
from datetime import time, timedelta, datetime

# --- App Configuration ---
st.set_page_config(page_title="Timetable Generator", layout="wide")

if 'courses_df' not in st.session_state:
    from gen_file import sample_courses
    st.session_state.courses_df = pd.DataFrame(sample_courses, columns=["Course", "Day", "Start", "End", "Location", "Week Offset"])

# Ensure 'Week Offset' column exists for backward compatibility or new sessions
if 'Week Offset' not in st.session_state.courses_df.columns:
    st.session_state.courses_df['Week Offset'] = 0

if 'current_week_offset' not in st.session_state:
    st.session_state.current_week_offset = 0 # 0 for current week, 1 for next week, -1 for previous week

# --- Helper Functions ---
def get_current_week_dates(week_offset):
    today = datetime.today()
    # Find the most recent Monday (or today if today is Monday)
    start_of_week = today - timedelta(days=today.weekday())
    current_monday = start_of_week + timedelta(weeks=week_offset)
    current_sunday = current_monday + timedelta(days=6)
    return current_monday, current_sunday

# --- Sidebar ---
with st.sidebar:
    st.info("Use the form below to add new courses to your timetable.")
    st.header("Add a New Course")
    with st.form("new_course_form", clear_on_submit=True):
        submitted = st.form_submit_button("Add Course")

        course_name = st.text_input("Course Name", value="Maths")

        day = st.selectbox("Day of the Week", options=list(range(1, 8)), format_func=lambda x: f"Day {x}")
        
        # Time Inputs
        start_time_obj = st.slider(
            "Start Time",
            min_value=time(8, 0),
            max_value=time(21, 0),
            value=time(9, 0),
            step=timedelta(minutes=10),
            format="HH:mm"
        )
        
        duration_hours = st.selectbox("Duration", [0.5, 1.0, 1.5, 2.0], format_func=lambda x: f"{x} hours")

        location = st.text_input("Location (Optional)")
        recursion_type = st.selectbox("Recursion", ["None", "Daily", "Weekly"], index=0)
        
        if submitted:
            if course_name and day and start_time_obj and duration_hours:
                start_datetime = datetime.combine(datetime.today(), start_time_obj)
                end_datetime = start_datetime + timedelta(hours=duration_hours)
                end_time_str = end_datetime.strftime("%H:%M")
                start_time_str = start_time_obj.strftime("%H:%M")

                courses_to_add = []

                if recursion_type == "None":
                    courses_to_add.append([course_name, day, start_time_str, end_time_str, location, st.session_state.current_week_offset])
                elif recursion_type == "Daily":
                    for i in range(7): # Add for 7 days
                        # Day 1 is the selected day, then day+1, day+2, etc.
                        # Need to handle wrapping around to the next week (day 7 -> day 1 of next week)
                        # Streamlit's day is 1-7, so (day + i - 1) % 7 + 1
                        daily_day = (day + i - 1) % 7 + 1
                        courses_to_add.append([course_name, daily_day, start_time_str, end_time_str, location, st.session_state.current_week_offset])
                elif recursion_type == "Weekly":
                    for i in range(8): # Add for 8 weeks (0 to 7)
                        courses_to_add.append([course_name, day, start_time_str, end_time_str, location, st.session_state.current_week_offset + i])
                
                if courses_to_add:
                    new_courses_df = pd.DataFrame(courses_to_add, columns=["Course", "Day", "Start", "End", "Location", "Week Offset"])
                    st.session_state.courses_df = pd.concat([st.session_state.courses_df, new_courses_df], ignore_index=True)
                    st.success(f"{len(courses_to_add)} Course(s) added successfully!")
            else:
                st.error("Please fill in all required fields.")
    
    st.header("Timetable Controls")
    selected_style = st.selectbox("Choose a style", ["modern", "cute", "cool", "fresh"])

# --- Main Section ---
st.title("Timetable Preview")

# Initialize buffers for download buttons
png_buffer = io.BytesIO()
pdf_buffer = io.BytesIO()

# Header and download buttons in one row
download_col1, download_col2 = st.columns(2)
with download_col1:
    st.download_button(
        label="Download PNG",
        data=png_buffer,
        file_name=f"timetable_{selected_style}.png",
        mime="image/png",
        use_container_width=True
    )
with download_col2:
    st.download_button(
        label="Download PDF",
        data=pdf_buffer,
        file_name=f"timetable_{selected_style}.pdf",
        mime="application/octet-stream",
        use_container_width=True
    )

# Week Navigation
week_nav_cols = st.columns([1, 3, 1])
with week_nav_cols[0]:
    if st.button("Previous Week", use_container_width=True):
        if st.session_state.current_week_offset > 0:
            st.session_state.current_week_offset -= 1
            st.rerun()
with week_nav_cols[1]:
    current_monday, current_sunday = get_current_week_dates(st.session_state.current_week_offset)
    st.markdown(f"<h3 style='text-align: center;'>Week: {current_monday.strftime('%m-%d')} to {current_sunday.strftime('%m-%d')}</h3>", unsafe_allow_html=True)
with week_nav_cols[2]:
    if st.button("Next Week", use_container_width=True):
        if st.session_state.current_week_offset < 7: # 0 to 7 makes 8 weeks
            st.session_state.current_week_offset += 1
            st.rerun()

# Display and edit current courses
# Filter courses for the current week offset
current_week_courses_df = st.session_state.courses_df[st.session_state.courses_df['Week Offset'] == st.session_state.current_week_offset]


# Generate and display the timetable
if not current_week_courses_df.empty:
    courses_list = [tuple(row) for row in current_week_courses_df.to_numpy()]
    
    current_monday, current_sunday = get_current_week_dates(st.session_state.current_week_offset)
    final_img = generate_timetable_image(courses=courses_list, selected_style=selected_style, week_date_range=f"{current_monday.strftime('%m-%d')} to {current_sunday.strftime('%m-%d')}")

    # In-memory files for download
    png_buffer.seek(0) # Reset buffer position
    png_buffer.truncate(0) # Clear previous content
    final_img.save(png_buffer, format="PNG")
    png_buffer.seek(0)

    pdf_buffer.seek(0) # Reset buffer position
    pdf_buffer.truncate(0) # Clear previous content
    final_img.save(pdf_buffer, format="PDF")
    pdf_buffer.seek(0)

    st.image(final_img)
    with st.expander("Edit Courses Data"):
        st.header("Current Courses Data")
        edited_df = st.data_editor(current_week_courses_df, use_container_width=True, num_rows="dynamic")

        if not edited_df.equals(current_week_courses_df):
            st.session_state.courses_df = pd.concat([
                st.session_state.courses_df[st.session_state.courses_df['Week Offset'] != st.session_state.current_week_offset],
                edited_df
            ], ignore_index=True)
            st.rerun()
else:
    current_monday, current_sunday = get_current_week_dates(st.session_state.current_week_offset)
    empty_img = generate_timetable_image(courses=[], selected_style=selected_style, week_date_range=f"{current_monday.strftime('%m-%d')} to {current_sunday.strftime('%m-%d')}")

    # In-memory files for download (for empty timetable)
    png_buffer.seek(0) # Reset buffer position
    png_buffer.truncate(0) # Clear previous content
    empty_img.save(png_buffer, format="PNG")
    png_buffer.seek(0)

    pdf_buffer.seek(0) # Reset buffer position
    pdf_buffer.truncate(0) # Clear previous content
    empty_img.save(pdf_buffer, format="PDF")
    pdf_buffer.seek(0)

    st.image(empty_img)
    st.warning("No courses to display for this week. Please add a course using the sidebar.")
