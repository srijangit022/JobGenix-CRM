import streamlit as st
import pandas as pd
import os
import pytz
from datetime import datetime
from PyPDF2 import PdfReader
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# File paths
users_file = "users.csv"
tasks_file = "tasks.csv"
log_file = "login_logout.csv"
leave_file = "leave_applications.csv"
attendance_file = "attendance.csv"
employee_directory = "employee_details/"
resume_directory = "resumes/"

# Create directories if they don't exist
if not os.path.exists(employee_directory):
    os.makedirs(employee_directory)
if not os.path.exists(resume_directory):
    os.makedirs(resume_directory)

# Initialize files and data
try:
    users = pd.read_csv(users_file).set_index("Username").to_dict("index")
except FileNotFoundError:
    users = {"admin": {"password": "admin123", "role": "admin"}}
    pd.DataFrame.from_dict(users, orient="index").reset_index().rename(columns={"index": "Username"}).to_csv(users_file,
                                                                                                             index=False)

try:
    tasks_data = pd.read_csv(tasks_file)
except FileNotFoundError:
    tasks_data = pd.DataFrame(
        columns=["Task", "Priority", "Employee Name", "Employee Role", "Status", "Start Date", "End Date"])
    tasks_data.to_csv(tasks_file, index=False)

try:
    log_data = pd.read_csv(log_file)
except FileNotFoundError:
    log_data = pd.DataFrame(columns=["Username", "Action", "Timestamp"])
    log_data.to_csv(log_file, index=False)

try:
    leave_data = pd.read_csv(leave_file)
except FileNotFoundError:
    leave_data = pd.DataFrame(columns=["Employee Name", "Leave Type", "Start Date", "End Date", "Status"])
    leave_data.to_csv(leave_file, index=False)

try:
    attendance_data = pd.read_csv(attendance_file)
except FileNotFoundError:
    attendance_data = pd.DataFrame(columns=["Username", "Date", "Check-In Time", "Check-Out Time", "Status"])
    attendance_data.to_csv(attendance_file, index=False)

# Session state variables
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "role" not in st.session_state:
    st.session_state.role = None
if "page" not in st.session_state:
    st.session_state.page = "login"
if "refresh" not in st.session_state:
    st.session_state.refresh = False


# Helper functions
def login(username, password):
    return users[username]["role"] if username in users and users[username]["password"] == password else None


def record_action(username, action):
    global log_data
    india_timezone = pytz.timezone('Asia/Kolkata')
    timestamp = datetime.now(india_timezone).strftime("%Y-%m-%d %H:%M:%S")
    new_entry = pd.DataFrame({"Username": [username], "Action": [action], "Timestamp": [timestamp]})
    log_data = pd.concat([log_data, new_entry], ignore_index=True)
    log_data.to_csv(log_file, index=False)


def delete_task_data(delete_all=False, index=None):
    global tasks_data
    if delete_all:
        tasks_data = pd.DataFrame(
            columns=["Task", "Priority", "Employee Name", "Employee Role", "Status", "Start Date", "End Date"])
    elif index is not None:
        tasks_data = tasks_data.drop(index=index).reset_index(drop=True)
    tasks_data.to_csv(tasks_file, index=False)


def delete_user(username):
    if username in users:
        del users[username]
        pd.DataFrame.from_dict(users, orient="index").reset_index().rename(columns={"index": "Username"}).to_csv(
            users_file, index=False)
        return True
    return False


def delete_all_login_logout_details():
    global log_data
    log_data = pd.DataFrame(columns=["Username", "Action", "Timestamp"])
    log_data.to_csv(log_file, index=False)


def filter_login_details(username=None, start_date=None, end_date=None):
    filtered_data = log_data
    if username:
        filtered_data = filtered_data[filtered_data["Username"] == username]
    if start_date:
        filtered_data = filtered_data[filtered_data["Timestamp"] >= str(start_date)]
    if end_date:
        filtered_data = filtered_data[filtered_data["Timestamp"] <= str(end_date)]
    return filtered_data


def daily_logs():
    today = datetime.now(pytz.timezone('Asia/Kolkata')).date()
    today_logs = log_data[log_data["Timestamp"].str.startswith(str(today))]
    return today_logs


def apply_for_leave(employee_name, leave_type, start_date, end_date):
    global leave_data
    new_application = pd.DataFrame([[employee_name, leave_type, start_date, end_date, "Pending"]],
                                   columns=["Employee Name", "Leave Type", "Start Date", "End Date", "Status"])
    leave_data = pd.concat([leave_data, new_application], ignore_index=True)
    leave_data.to_csv(leave_file, index=False)


def manage_leave_applications():
    global leave_data
    st.title("Leave Applications")
    st.subheader("Pending Leave Applications")
    pending_leaves = leave_data[leave_data["Status"] == "Pending"]
    if not pending_leaves.empty:
        st.dataframe(pending_leaves)
        selected_application = st.selectbox("Select Application to Manage", pending_leaves.index)
        action = st.selectbox("Select Action", ["Accept", "Reject"])
        if st.button("Submit Action"):
            if action == "Accept":
                leave_data.at[selected_application, "Status"] = "Accepted"
                st.success("Leave application accepted!")
                send_email_notification(leave_data.at[selected_application, "Employee Name"], "Accepted")
            else:
                leave_data.at[selected_application, "Status"] = "Rejected"
                st.success("Leave application rejected!")
                send_email_notification(leave_data.at[selected_application, "Employee Name"], "Rejected")
            leave_data.to_csv(leave_file, index=False)
    else:
        st.info("No pending leave applications.")


def send_email_notification(employee_name, status):
    employee_email = f"{employee_name}@gmail.com"
    subject = "Leave Application Status"
    body = f"Your leave application has been {status}."
    msg = MIMEMultipart()
    msg['From'] = "your_email@gmail.com"  # Replace with your email
    msg['To'] = employee_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login("your_email@gmail.com", "your_email_password")  # Replace with your email and password
            server.send_message(msg)
            st.success(f"Email notification sent to {employee_name}.")
    except Exception as e:
        st.error(f"Failed to send email: {e}")


def employee_leave_status():
    st.title("Leave Status Overview")
    employee_name = st.session_state.current_user
    employee_leaves = leave_data[leave_data["Employee Name"] == employee_name]
    if not employee_leaves.empty:
        for index, row in employee_leaves.iterrows():
            with st.expander(f"Leave Application: {row['Leave Type']}"):
                st.write(f"**Start Date:** {row['Start Date']}")
                st.write(f"**End Date:** {row['End Date']}")
                st.write(f"**Status:** {row['Status']}")
    else:
        st.info("No leave applications found.")


def record_attendance(username, action):
    global attendance_data
    india_timezone = pytz.timezone('Asia/Kolkata')
    today = datetime.now(india_timezone).date()
    current_time = datetime.now(india_timezone).strftime("%H:%M:%S")

    # Check if there's an existing record for the user today
    today_record = attendance_data[(attendance_data["Username"] == username) & (attendance_data["Date"] == str(today))]

    if action == "Check-In":
        if not today_record.empty:
            st.error("You have already checked in today!")
        else:
            new_entry = pd.DataFrame({
                "Username": [username],
                "Date": [str(today)],
                "Check-In Time": [current_time],
                "Check-Out Time": [""],
                "Status": ["Checked In"]
            })
            attendance_data = pd.concat([attendance_data, new_entry], ignore_index=True)
            attendance_data.to_csv(attendance_file, index=False)
            st.success("Successfully checked in!")

    elif action == "Check-Out":
        if today_record.empty:
            st.error("You haven't checked in today!")
        elif not today_record["Check-Out Time"].iloc[0] == "":
            st.error("You have already checked out today!")
        else:
            attendance_data.loc[(attendance_data["Username"] == username) & (
                        attendance_data["Date"] == str(today)), "Check-Out Time"] = current_time
            attendance_data.loc[(attendance_data["Username"] == username) & (
                        attendance_data["Date"] == str(today)), "Status"] = "Checked Out"
            attendance_data.to_csv(attendance_file, index=False)
            st.success("Successfully checked out!")


def view_attendance():
    st.title("Attendance Records")

    # Filters
    username = st.text_input("Filter by Username (optional)")
    start_date = st.date_input("Start Date (optional)", value=None)
    end_date = st.date_input("End Date (optional)", value=None)

    filtered_attendance = attendance_data
    if username:
        filtered_attendance = filtered_attendance[filtered_attendance["Username"] == username]
    if start_date:
        filtered_attendance = filtered_attendance[filtered_attendance["Date"] >= str(start_date)]
    if end_date:
        filtered_attendance = filtered_attendance[filtered_attendance["Date"] <= str(end_date)]

    if not filtered_attendance.empty:
        st.dataframe(filtered_attendance)
        # Download button
        csv = filtered_attendance.to_csv(index=False)
        st.download_button(
            label="Download Attendance Data as CSV",
            data=csv,
            file_name="attendance_export.csv",
            mime="text/csv",
        )
    else:
        st.info("No attendance records found for the selected filters.")


def employee_details_page():
    st.title("Employee Details")
    if st.session_state.role != "admin":
        st.error("You do not have permission to access this section.")
        return
    uploaded_file = st.file_uploader("Upload Employee Details Excel File", type=["xlsx"])
    if uploaded_file:
        existing_files = os.listdir(employee_directory)
        if len(existing_files) >= 30:
            st.error(
                "You can only upload up to 30 employee detail files. Please delete some files before uploading new ones.")
        else:
            file_path = os.path.join(employee_directory, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            st.success("Employee details file uploaded successfully!")
    st.subheader("Existing Employee Details Files")
    existing_files = os.listdir(employee_directory)
    if existing_files:
        selected_file = st.selectbox("Select a file to view", existing_files)
        if selected_file:
            file_path = os.path.join(employee_directory, selected_file)
            sheets = pd.ExcelFile(file_path).sheet_names
            selected_sheet = st.selectbox("Select a sheet to view", sheets)
            df = pd.read_excel(file_path, sheet_name=selected_sheet)
            st.dataframe(df)
            edited_df = df.copy()
            for index, row in df.iterrows():
                with st.expander(f"Edit Row {index + 1}"):
                    for col in df.columns:
                        edited_df.at[index, col] = st.text_input(f"{col}", value=row[col], key=f"{col}_{index}")
            if st.button("Save Changes"):
                with pd.ExcelWriter(file_path, engine='openpyxl', mode='a') as writer:
                    edited_df.to_excel(writer, sheet_name=selected_sheet, index=False)
                st.success("Changes saved successfully!")
            search_term = st.text_input("Search Employee:")
            if st.button("Search"):
                if search_term:
                    filtered_data = edited_df[
                        edited_df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(),
                                        axis=1)]
                    if not filtered_data.empty:
                        st.dataframe(filtered_data)
                    else:
                        st.warning("No matching records found.")
                else:
                    st.warning("Please enter a search term.")
            if st.button(f"Delete {selected_file}"):
                os.remove(file_path)
                st.success(f"{selected_file} deleted successfully!")
    else:
        st.info("No employee details files uploaded yet.")


def employee_background_page():
    st.title("Employee Background")
    uploaded_file = st.file_uploader("Upload Employee Resume (PDF)", type=["pdf"])
    if uploaded_file is not None:
        file_path = os.path.join(resume_directory, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success("Resume uploaded successfully!")
    st.subheader("Uploaded Resumes")
    resumes = [resume for resume in os.listdir(resume_directory) if resume.endswith(".pdf")]
    if resumes:
        selected_resume = st.selectbox("Select a resume to view", resumes)
        if st.button(f"View {selected_resume}"):
            with open(os.path.join(resume_directory, selected_resume), "rb") as f:
                pdf_reader = PdfReader(f)
                pdf_text = ""
                for page in pdf_reader.pages:
                    pdf_text += page.extract_text() + "\n"
                st.text_area("Resume Content", pdf_text, height=300)
        if st.button(f"Delete {selected_resume}"):
            os.remove(os.path.join(resume_directory, selected_resume))
            st.success(f"{selected_resume} deleted successfully!")
    else:
        st.write("No resumes uploaded yet.")


def login_page():
    st.title("HRMS Login or Register")  # Updated title
    col1, col2 = st.columns(2)
    with col1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            role = login(username, password)
            if role:
                st.session_state.current_user = username
                st.session_state.role = role
                st.session_state.page = "tasks"
                record_action(username, "Login")
                st.success(f"Welcome, {username}!")
            else:
                st.error("Invalid credentials!")
    with col2:
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        role = st.selectbox("Role", ["admin", "employee"])
        if st.button("Register"):
            if new_user in users:
                st.error("Username already exists!")
            elif not new_user.strip() or not new_pass.strip():
                st.error("Username and password cannot be empty!")
            else:
                users[new_user] = {"password": new_pass, "role": role}
                pd.DataFrame.from_dict(users, orient="index").reset_index().rename(
                    columns={"index": "Username"}).to_csv(users_file, index=False)
                st.success(f"Account created for {new_user} as {role}.")


def task_page():
    global tasks_data
    st.sidebar.title("Menu")
    menu = ["View Tasks", "Add Task", "Update Task", "Delete Task Data", "Login Details", "Daily Logs", "Delete User",
            "View Passwords", "Employee Details", "Employee Background", "Apply for Leave", "Manage Leave Applications",
            "Leave Status", "Mark Attendance", "View Attendance", "Logout"]
    choice = st.sidebar.selectbox("Options", menu)
    st.header(f"Welcome, {st.session_state.current_user} ({st.session_state.role.capitalize()})")
    if choice == "View Tasks":
        if st.button("Refresh Tasks"):
            st.session_state.refresh = not st.session_state.refresh
        if st.session_state.refresh:
            st.success("Task view refreshed!")
        st.dataframe(tasks_data)
        search_name = st.text_input("Search Tasks by Employee Name")
        if st.button("Search"):
            filtered_tasks = tasks_data[tasks_data["Employee Name"].str.contains(search_name, case=False, na=False)]
            if filtered_tasks.empty:
                st.info("No tasks found for the entered name.")
            else:
                st.dataframe(filtered_tasks)
    if choice == "Add Task" and st.session_state.role == "admin":
        task = st.text_input("Task")
        priority = st.selectbox("Priority", ["High", "Medium", "Low"])
        employee_names = [u for u, d in users.items() if d["role"] == "employee"]
        employee_name = st.selectbox("Employee Name", employee_names)
        role = st.selectbox("Role", ["Manager", "Staff", "Intern"])
        status = st.selectbox("Status", ["Done", "Delayed", "To be Done", "On Track", "Not Done"])
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        if st.button("Add Task"):
            if not task.strip():
                st.error("Task name cannot be empty!")
            else:
                tasks_data = pd.concat(
                    [tasks_data, pd.DataFrame([[task, priority, employee_name, role, status, start_date, end_date]],
                                              columns=["Task", "Priority", "Employee Name", "Employee Role", "Status",
                                                       "Start Date", "End Date"])])
                tasks_data.to_csv(tasks_file, index=False)
                st.success("Task added!")
    if choice == "Update Task" and st.session_state.role == "employee":
        employee_name = st.session_state.current_user
        employee_tasks = tasks_data[tasks_data["Employee Name"] == employee_name]
        if not employee_tasks.empty:
            task_index = st.selectbox("Select Task to Update", employee_tasks.index)
            status = st.selectbox("Update Status", ["Done", "Delayed", "To Be Done", "On Track", "Not Done"])
            if st.button("Update Task"):
                tasks_data.at[task_index, "Status"] = status
                tasks_data.to_csv(tasks_file, index=False)
                st.success("Task updated!")
        else:
            st.info("You have no tasks assigned.")
    if choice == "Delete Task Data" and st.session_state.role == "admin":
        if st.button("Delete All Tasks"):
            delete_task_data(delete_all=True)
            st.success("All tasks deleted!")
        if not tasks_data.empty:
            task_index = st.number_input("Task Index to Delete", min_value=0, max_value=len(tasks_data) - 1, step=1)
            if st.button("Delete Task"):
                delete_task_data(index=task_index)
                st.success(f"Task {task_index} deleted!")
    if choice == "Login Details" and st.session_state.role == "admin":
        username = st.text_input("Username")
        start_date = st.date_input("Start Date", value=None)
        end_date = st.date_input("End Date", value=None)
        if st.button("Search Logs"):
            filtered_logs = filter_login_details(username=username, start_date=start_date, end_date=end_date)
            st.dataframe(filtered_logs)
    if choice == "Daily Logs" and st.session_state.role == "admin":
        st.subheader("Daily Login/Logout Details")
        today_logs = daily_logs()
        if today_logs.empty:
            st.info("No login/logout details for today.")
        else:
            st.dataframe(today_logs)
        if st.button("Delete All Login/Logout Details"):
            delete_all_login_logout_details()
            st.success("All login/logout details have been deleted!")
    if choice == "Delete User" and st.session_state.role == "admin":
        del_user = st.text_input("Enter Username to Delete")
        if st.button("Delete User"):
            if delete_user(del_user):
                st.success(f"User '{del_user}' has been deleted!")
            else:
                st.error(f"User '{del_user}' not found!")
    if choice == "View Passwords" and st.session_state.role == "admin":
        passwords = pd.DataFrame(users).transpose().reset_index().rename(columns={"index": "Username"})
        st.dataframe(passwords)
    if choice == "Employee Details":
        employee_details_page()
    if choice == "Employee Background":
        employee_background_page()
    if choice == "Apply for Leave" and st.session_state.role == "employee":
        st.subheader("Leave Application Form")
        leave_type = st.selectbox("Leave Type", ["Sick Leave", "Casual Leave", "Annual Leave"])
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        if st.button("Apply for Leave"):
            apply_for_leave(st.session_state.current_user, leave_type, start_date, end_date)
            st.success("Leave application submitted!")
    if choice == "Manage Leave Applications" and st.session_state.role == "admin":
        manage_leave_applications()
    if choice == "Leave Status":
        employee_leave_status()
    if choice == "Mark Attendance":
        st.title("Mark Attendance")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Check-In"):
                record_attendance(st.session_state.current_user, "Check-In")
        with col2:
            if st.button("Check-Out"):
                record_attendance(st.session_state.current_user, "Check-Out")
        # Show today's attendance status
        today = datetime.now(pytz.timezone('Asia/Kolkata')).date()
        today_record = attendance_data[
            (attendance_data["Username"] == st.session_state.current_user) & (attendance_data["Date"] == str(today))]
        if not today_record.empty:
            st.write(f"**Today's Status:** {today_record['Status'].iloc[0]}")
            st.write(f"**Check-In Time:** {today_record['Check-In Time'].iloc[0]}")
            if today_record['Check outta Time'].iloc[0]:
                st.write(f"**Check-Out Time:** {today_record['Check-Out Time'].iloc[0]}")
    if choice == "View Attendance":
        view_attendance()
    if choice == "Logout":
        record_action(st.session_state.current_user, "Logout")
        st.session_state.current_user = None
        st.session_state.role = None
        st.session_state.page = "login"
        st.success("Logged out!")


# Main Logic
if st.session_state.page == "login":
    login_page()
elif st.session_state.page == "tasks":
    task_page()

