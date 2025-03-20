import streamlit as st
import pandas as pd
import datetime

# File paths
users_file, tasks_file, log_file = "users.csv", "tasks.csv", "login_logout.csv"

# Initialize files and data
try:
    users = pd.read_csv(users_file).set_index("Username").to_dict("index")
except:
    users = {"admin": {"password": "admin123", "role": "admin"}}
    pd.DataFrame.from_dict(users, orient="index").reset_index().rename(columns={"index": "Username"}).to_csv(users_file,
                                                                                                             index=False)

try:
    tasks_data = pd.read_csv(tasks_file)
except:
    tasks_data = pd.DataFrame(
        columns=["Task", "Priority", "Employee Name", "Employee Role", "Status", "Start Date", "End Date"])
    tasks_data.to_csv(tasks_file, index=False)

try:
    log_data = pd.read_csv(log_file)
except:
    log_data = pd.DataFrame(columns=["Username", "Action", "Timestamp"])
    log_data.to_csv(log_file, index=False)

# Session state variables
if "current_user" not in st.session_state: st.session_state.current_user = None
if "role" not in st.session_state: st.session_state.role = None
if "page" not in st.session_state: st.session_state.page = "login"
if "refresh" not in st.session_state: st.session_state.refresh = False
if "date_format" not in st.session_state: st.session_state.date_format = "%Y-%m-%d %H:%M:%S"  # Default format


# Helper functions
def login(username, password):
    return users[username]["role"] if username in users and users[username]["password"] == password else None


def record_action(username, action):
    global log_data
    timestamp = datetime.datetime.now().strftime(st.session_state.date_format)  # Use configured date format
    new_entry = pd.DataFrame({"Username": [username], "Action": [action], "Timestamp": [timestamp]})
    log_data = pd.concat([log_data, new_entry])
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
    log_data = pd.DataFrame(columns=["Username", "Action", "Timestamp"])  # Clear log data
    log_data.to_csv(log_file, index=False)  # Update the CSV file


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
    today = datetime.datetime.now().date()
    today_logs = log_data[log_data["Timestamp"].str.startswith(str(today))]
    return today_logs


# Pages
def login_page():
    st.title("JobGenix CRM - Login or Register")
    col1, col2 = st.columns(2)

    with col1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            role = login(username, password)
            if role:
                st.session_state.current_user, st.session_state.role, st.session_state.page = username, role, "tasks"
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
            "View Passwords", "Configure Date Format", "Logout"]
    choice = st.sidebar.selectbox("Options", menu)

    st.header(f"Welcome, {st.session_state.current_user} ({st.session_state.role.capitalize()})")

    # Configure Date Format - Admin Only
    if choice == "Configure Date Format":
        if st.session_state.role == "admin":
            st.subheader("Configure Date and Time Format")
            date_format = st.text_input("Enter Date Format (e.g., %Y-%m-%d %H:%M:%S)",
                                        value=st.session_state.date_format)
            if st.button("Save Format"):
                st.session_state.date_format = date_format
                st.success("Date format updated!")
        else:
            st.error("You do not have permission to access this feature.")

    if choice == "View Tasks":
        if st.button("Refresh Tasks"):
            st.session_state.refresh = not st.session_state.refresh
        if st.session_state.refresh:
            st.success("Task view refreshed!")

        # Show all tasks
        st.dataframe(tasks_data)

        # Search tasks by employee name
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
        start_date, end_date = st.date_input("Start Date"), st.date_input("End Date")
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
        task_index = st.number_input("Task Index", min_value=0, max_value=len(tasks_data) - 1, step=1)
        status = st.selectbox("Update Status", ["Done", "Delayed", "To Be Done", "On Track", "Not Done"])
        if st.button("Update Task"):
            tasks_data.at[task_index, "Status"] = status
            tasks_data.to_csv(tasks_file, index=False)
            st.success("Task updated!")

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

        # Option to delete all login/logout details
        if st.button("Delete All Login/Logout Details"):
            delete_all_login_logout_details()
            st.success("All login/logout details have been deleted!")

    if choice == "Delete User" and st.session_state.role == "admin":
        del_user = st.text_input("Enter Username to Delete")
        if st.button("Delete User"):
            if delete_user(del_user):
                st.success(f"User   '{del_user}' has been deleted!")
            else:
                st.error(f"User   '{del_user}' not found!")

    if choice == "View Passwords" and st.session_state.role == "admin":
        passwords = pd.DataFrame(users).transpose().reset_index().rename(columns={"index": "Username"})
        st.dataframe(passwords)

    if choice == "Logout":
        record_action(st.session_state.current_user, "Logout")
        st.session_state.current_user, st.session_state.role, st.session_state.page = None, None, "login"
        st.success("Logged out!")


# Main Logic

if st.session_state.page == "login":
    login_page()
elif st.session_state.page == "tasks":
    task_page()
