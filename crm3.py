import streamlit as st
import pandas as pd
import datetime

# Persistent storage (CSV files)
users_file = "users.csv"
tasks_file = "tasks.csv"
login_logout_file = "login_logout.csv"

# Initialize files if they don't exist or have incorrect columns
try:
    users = pd.read_csv(users_file)
    if "Username" not in users.columns:
        raise ValueError("Missing required columns in users.csv")
    users = users.set_index("Username").to_dict("index")
except (FileNotFoundError, ValueError):
    # Recreate users file with default admin entry
    users = {"admin": {"password": "admin123", "role": "admin"}}
    pd.DataFrame.from_dict(users, orient="index").reset_index().rename(columns={"index": "Username"}).to_csv(users_file, index=False)

try:
    tasks_data = pd.read_csv(tasks_file)
except FileNotFoundError:
    tasks_data = pd.DataFrame(columns=["Task", "Priority", "Employee Name", "Employee Role", "Status", "Start Date", "End Date"])
    tasks_data.to_csv(tasks_file, index=False)

try:
    login_logout_data = pd.read_csv(login_logout_file)
except FileNotFoundError:
    login_logout_data = pd.DataFrame(columns=["Username", "Action", "Timestamp"])
    login_logout_data.to_csv(login_logout_file, index=False)

# Login Function
def login(username, password):
    if username in users:
        if users[username]["password"] == password:
            return users[username]["role"]
        else:
            return None  # Password mismatch
    return None  # Username not found

# Record login/logout
def record_time(username, action):
    global login_logout_data
    now = datetime.datetime.now()
    new_entry = pd.DataFrame({"Username": [username], "Action": [action], "Timestamp": [now]})
    login_logout_data = pd.concat([login_logout_data, new_entry])
    login_logout_data.to_csv(login_logout_file, index=False)

# Login Page
def login_page():
    st.title("JobGenix CRM - Login or Register")
    st.subheader("#BeUnbeatable")

    # Two columns: Login for existing users and Registration for new employees/admins
    col1, col2 = st.columns(2)

    # Existing User Login
    with col1:
        st.subheader("Login")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login"):
            role = login(username, password)
            if role:
                st.session_state.current_user = username
                st.session_state.role = role
                record_time(username, "Login")
                st.success(f"Welcome, {username}! Redirecting to the task page...")
                st.session_state.page = "tasks"
            else:
                st.error("Invalid username or password!")

    # New Employee/Admin Registration
    with col2:
        st.subheader("Register")
        new_username = st.text_input("New Username", key="register_username")
        new_password = st.text_input("New Password", type="password", key="register_password")
        role = st.selectbox("Role", ["admin", "employee"], key="register_role")
        if st.button("Register"):
            if new_username in users:
                st.error("Username already exists!")
            elif new_username.strip() == "" or new_password.strip() == "":
                st.error("Username and Password cannot be empty!")
            else:
                # Add the new user to the users dictionary
                users[new_username] = {"password": new_password, "role": role}
                pd.DataFrame.from_dict(users, orient="index").reset_index().rename(columns={"index": "Username"}).to_csv(users_file, index=False)
                st.success(f"Account created for {new_username} as {role}")

# Task Assigning Tree Page
def task_page():
    global tasks_data, login_logout_data
    st.sidebar.title("Menu")
    menu = ["View Task Tree", "Update Tasks", "Add New Task", "Delete Employee", "Password Records", "Login Details", "Logout"]
    choice = st.sidebar.selectbox("Navigation", menu)

    st.title("Task Assigning Tree")
    st.subheader(f"Welcome, {st.session_state.current_user} ({st.session_state.role.capitalize()})")

    if choice == "View Task Tree":
        st.dataframe(tasks_data)

    elif choice == "Update Tasks" and st.session_state.role == "employee":
        st.subheader("Update Task Status (For Employees)")
        task_index = st.number_input("Task Index (Row Number)", min_value=0, max_value=len(tasks_data) - 1, step=1)
        new_status = st.selectbox("Update Status", ["Done", "Delayed", "At risk", "On Track", "Not Done", "Just Notified"])
        start_date = st.date_input("Update Start Date")
        end_date = st.date_input("Update End Date")
        if st.button("Update Task"):
            tasks_data.loc[task_index, "Status"] = new_status
            tasks_data.loc[task_index, "Start Date"] = start_date
            tasks_data.loc[task_index, "End Date"] = end_date
            tasks_data.to_csv(tasks_file, index=False)
            st.success("Task updated successfully!")

    elif choice == "Add New Task" and st.session_state.role == "admin":
        st.subheader("Add New Task (Admin Only)")
        task = st.text_input("Task")
        priority = st.selectbox("Priority", ["High", "Medium", "Low"])
        employee_name = st.text_input("Employee Name")
        employee_role = st.selectbox("Employee Role", ["Manager", "Staff", "Intern"])
        status = st.selectbox("Status", ["Done", "Delayed", "At risk", "On Track", "Not Done", "Just Notified"])
        start_date = st.date_input("Start Date")
        end_date = st.date_input("End Date")
        if st.button("Add Task"):
            new_task = pd.DataFrame([[task, priority, employee_name, employee_role, status, start_date, end_date]],
                                    columns=["Task", "Priority", "Employee Name", "Employee Role", "Status", "Start Date", "End Date"])
            tasks_data = pd.concat([tasks_data, new_task])
            tasks_data.to_csv(tasks_file, index=False)
            st.success("Task added successfully!")

    elif choice == "Delete Employee" and st.session_state.role == "admin":
        st.subheader("Delete Employee (Admin Only)")
        delete_username = st.text_input("Enter Username to Delete")
        if st.button("Delete Employee"):
            if delete_username in users:
                del users[delete_username]
                pd.DataFrame.from_dict(users, orient="index").reset_index().rename(columns={"index": "Username"}).to_csv(users_file, index=False)
                st.success(f"Employee {delete_username} has been deleted.")
            else:
                st.error("Employee not found!")

    elif choice == "Password Records" and st.session_state.role == "admin":
        st.subheader("Password Records (Admin Only)")
        password_df = pd.DataFrame(users).transpose().reset_index().rename(columns={"index": "Username", "password": "Password", "role": "Role"})
        st.dataframe(password_df)

    elif choice == "Login Details" and st.session_state.role == "admin":
        st.subheader("Login Details (Admin Only)")
        if not login_logout_data.empty:
            st.dataframe(login_logout_data)
        else:
            st.write("No login/logout records available.")

    elif choice == "Logout":
        record_time(st.session_state.current_user, "Logout")
        st.session_state.current_user = None
        st.session_state.role = None
        st.session_state.page = "login"
        st.success("Logged out successfully!")

# Main Control Logic
if "page" not in st.session_state:
    st.session_state.page = "login"

if st.session_state.page == "login":
    login_page()
elif st.session_state.page == "tasks":
    task_page()
