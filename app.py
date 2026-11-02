import streamlit as st
import pickle
import sqlite3
import datetime
import openpyxl
import os

# Excel file setup including Password column
excel_file = "spam_history.xlsx"
if not os.path.exists(excel_file):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Spam History"
    ws.append(["Username", "Password", "Mobile No.", "Message", "Prediction", "Timestamp"])
    wb.save(excel_file)

# Database setup for Users & History
conn = sqlite3.connect('spam_guard.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        mobile_no TEXT
    )
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        mobile_no TEXT,
        message TEXT,
        prediction TEXT,
        timestamp TEXT
    )
''')
conn.commit()

# Session state initialization
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "username" not in st.session_state:
    st.session_state.username = ""
if "password" not in st.session_state:
    st.session_state.password = ""
if "mobile_no" not in st.session_state:
    st.session_state.mobile_no = ""

# --- LOGIN & SIGN UP SCREEN ---
if not st.session_state.logged_in:
    st.title("SpamGuard Portal")
    
    auth_mode = st.radio("Choose Option", ["Login", "Sign Up"])
    
    col1, col2 = st.columns([2, 3])
    
    with col1:
        user = st.text_input("Username")
        passwd = st.text_input("Password", type="password")
        
        if auth_mode == "Sign Up":
            mobile = st.text_input("Mobile No.")
        else:
            mobile = ""
        
        if auth_mode == "Login":
            if st.button("Login"):
                cursor.execute("SELECT mobile_no FROM users WHERE username = ? AND password = ?", (user, passwd))
                valid_user = cursor.fetchone()
                
                if valid_user or (user == "admin" and passwd == "1234"):
                    st.session_state.logged_in = True
                    st.session_state.username = user
                    st.session_state.password = passwd
                    st.session_state.mobile_no = valid_user[0] if valid_user else "N/A"
                    st.rerun()
                else:
                    st.error("Invalid Username or Password")
                    
        else: # Sign Up Mode
            if st.button("Register"):
                if user.strip() == "" or passwd.strip() == "" or mobile.strip() == "":
                    st.warning("Please fill all fields.")
                else:
                    try:
                        cursor.execute("INSERT INTO users (username, password, mobile_no) VALUES (?, ?, ?)", (user, passwd, mobile))
                        conn.commit()
                        st.success("Registration successful! Please switch to Login.")
                    except sqlite3.IntegrityError:
                        st.error("Username already exists. Choose another.")

# --- MAIN APP (After Login) ---
else:
    st.title("Spam and Ham Detector")
    st.write(f"Logged in as: {st.session_state.username} | Mobile: {st.session_state.mobile_no}")
    
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.password = ""
        st.session_state.mobile_no = ""
        st.rerun()

    st.markdown("---")
    
    vectorizer = pickle.load(open('vectorizer.pkl', 'rb'))
    model = pickle.load(open('spam_model.pkl', 'rb'))

    menu = st.radio("Select Option", ["Check Message", "Search History"])

    if menu == "Check Message":
        st.subheader("Enter text")
        
        if "user_text" not in st.session_state:
            st.session_state.user_text = ""

        def clear_text():
            st.session_state.user_text = ""

        user_input = st.text_area("Message:", value=st.session_state.user_text, key="user_text")

        c1, c2 = st.columns(2)
        with c1:
            check_btn = st.button("Check")
        with c2:
            clear_btn = st.button("Clear", on_click=clear_text)

        if check_btn:
            if user_input.strip() == "":
                st.write("Please enter some text.")
            else:
                vect_input = vectorizer.transform([user_input])
                prediction = model.predict(vect_input)[0]
                
                result = "Spam" if prediction == 1 else "Safe"
                st.write(f"Result: {result}")

                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 1. Save to SQLite database with Password
                cursor.execute("INSERT INTO history (username, password, mobile_no, message, prediction, timestamp) VALUES (?, ?, ?, ?, ?, ?)", 
                               (st.session_state.username, st.session_state.password, st.session_state.mobile_no, user_input, result, timestamp))
                conn.commit()

                # 2. Save to Excel file with Password
                wb = openpyxl.load_workbook(excel_file)
                ws = wb.active
                ws.append([st.session_state.username, st.session_state.password, st.session_state.mobile_no, user_input, result, timestamp])
                wb.save(excel_file)

    elif menu == "Search History":
        st.subheader("History")
        cursor.execute("SELECT message, prediction, timestamp FROM history WHERE username = ? ORDER BY id DESC", (st.session_state.username,))
        rows = cursor.fetchall()
        
        if rows:
            for row in rows:
                st.write(f"Time: {row[2]} | Message: {row[0]} | Result: {row[1]}")
                st.write("-" * 40)
        else:
            st.write("No history found.")