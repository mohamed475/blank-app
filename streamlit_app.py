import streamlit as st
import pandas as pd
import hashlib
import plotly.express as px

# Function to hash a password using SHA-256
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Load users from CSV file
def load_users(file_path):
    try:
        users = pd.read_csv(file_path)
        return users
    except FileNotFoundError:
        # Create a default file if none exists
        default_users = pd.DataFrame({
            "username": ["admin"],
            "password": [hash_password("admin")]
        })
        default_users.to_csv(file_path, index=False)
        return default_users

# Authenticate user credentials
def authenticate(username, password, users):
    hashed_password = hash_password(password)
    user_row = users[(users['username'] == username) & (users['password'] == hashed_password)]
    return not user_row.empty

# Check if the user is an admin
def is_admin(username):
    return username == "admin"

# Load dashboard data
@st.cache_data
def load_data(file_path):
    data = pd.read_csv(file_path)
    data['Date'] = pd.to_datetime(data['Date'], errors='coerce')
    return data

# File paths
users_file_path = "users.csv"
data_file_path = "revtee_data.csv"

# Load users and dashboard data
users_data = load_users(users_file_path)

# Authentication interface
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("Authentication Page")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    login_button = st.button("Login")

    if login_button:
        if authenticate(username, password, users_data):
            st.session_state.authenticated = True
            st.session_state.username = username  # Store username in session
            st.success("Login successful! Redirecting to the dashboard...")
            st.rerun()
        else:
            st.error("Invalid username or password. Please try again.")
else:
    # Load data after authentication
    data = load_data(data_file_path)
    st.title("Rev-Tee Dashboard - Performance Tracking")

    # Add a logout button
    if st.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.success("You have been logged out.")
        st.rerun()  # Rerun the app to show the login page

    # Sidebar filters
    st.sidebar.header("Filters")

    if data['Date'].isna().all():
        st.error("The 'Date' column contains no valid data. Check your CSV file.")
    else:
        date_range = st.sidebar.date_input(
            "Select a Date Range", 
            value=(data['Date'].min(), data['Date'].max())
        )
        product_options = ["All"] + list(data['Produits_vendus'].unique())
        selected_products = st.sidebar.multiselect(
            "Select Products",
            options=product_options,
            default=["All"]
        )

        st.sidebar.header("Advanced Options")
        show_trends = st.sidebar.checkbox("Show Sales Trends", value=True)
        show_comparison = st.sidebar.checkbox("Show Product Comparisons", value=True)
        download_full_data = st.sidebar.checkbox("Download Full Data", value=False)

        # Apply filters
        if "All" in selected_products:
            filtered_data = data[ 
                (data['Date'] >= pd.to_datetime(date_range[0])) & 
                (data['Date'] <= pd.to_datetime(date_range[1]))
            ]
            selected_products = ["All"]
        else:
            filtered_data = data[
                (data['Date'] >= pd.to_datetime(date_range[0])) & 
                (data['Date'] <= pd.to_datetime(date_range[1])) & 
                (data['Produits_vendus'].isin(selected_products))
            ]

        # KPIs
        st.header("Performance Indicators")

        if len(selected_products) == 0:
            st.warning("Please select at least one product to display indicators.")
        elif "All" in selected_products:
            st.subheader("Indicators for All Products")
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                total_sales = filtered_data['Ventes'].sum()
                st.metric(label="Total Sales", value=f"{total_sales} T-shirts")

            with col2:
                total_visitors = filtered_data['Visiteurs'].sum()
                st.metric(label ="Total Visitors", value=f"{total_visitors} ")

            with col3:
                conversion_rate = (filtered_data['Conversions'].sum() / total_visitors) * 100 if total_visitors > 0 else 0
                st.metric(label="Conversion Rate", value=f"{conversion_rate:.2f}%")

            with col4:
                total_revenue = filtered_data['Revenus'].sum()
                st.metric(label="Total Revenue", value=f"{total_revenue} MAD")
        else:
            for product in selected_products:
                st.subheader(f"Indicators for {product}")
                product_data = filtered_data[filtered_data['Produits_vendus'] == product]

                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    total_sales = product_data['Ventes'].sum()
                    st.metric(label="Total Sales", value=f"{total_sales} T-shirts")

                with col2:
                    total_visitors = product_data['Visiteurs'].sum()
                    st.metric(label="Total Visitors", value=f"{total_visitors} ")

                with col3:
                    conversion_rate = (product_data['Conversions'].sum() / total_visitors) * 100 if total_visitors > 0 else 0
                    st.metric(label="Conversion Rate", value=f"{conversion_rate:.2f}%")

                with col4:
                    total_revenue = product_data['Revenus'].sum()
                    st.metric(label="Total Revenue", value=f"{total_revenue} MAD")

        # Visualizations
        st.header("Visualizations")

        # Sales trends
        if show_trends:
            fig_sales = px.line(
                filtered_data, x='Date', y='Ventes', color='Produits_vendus', 
                title='Daily Sales by Product', markers=True, line_shape='spline', color_discrete_sequence=px.colors.qualitative.Set1
            )
            fig_sales.update_traces(marker=dict(size=8, line=dict(width=2, color='DarkSlateGrey')))
            fig_sales.update_layout(title_font_size=18, plot_bgcolor="#f9f9f9")
            st.plotly_chart(fig_sales, use_container_width=True)

        # Visitors comparison
        if show_comparison:
            fig_visitors = px.bar(
                filtered_data, x='Date', y='Visiteurs', color='Produits_vendus', 
                title='Daily Visitors by Product', color_discrete_sequence=px.colors.qualitative.Plotly
            )
            fig_visitors.update_layout(title_font_size=18, plot_bgcolor="#f9f9f9")
            st.plotly_chart(fig_visitors, use_container_width=True)

        # Revenue distribution
        fig_revenue = px.pie(
            filtered_data, values='Revenus', names='Produits_vendus', title='Revenue Distribution by Product', color_discrete_sequence=px.colors.sequential.RdBu
        )
        st.plotly_chart(fig_revenue)

        # Export CSV
        st.download_button(
            label="Download Filtered Data (CSV)",
            data=filtered_data.to_csv(index=False),
            file_name="revtee_data_filtered.csv",
            mime="text/csv"
        )

        if download_full_data:
            st.download_button(
                label="Download Full Data (CSV)",
                data=data.to_csv(index=False),
                file_name="revtee_data_complete.csv",
                mime="text/csv"
            )

    # Admin functionalities - only available to admins
    if is_admin(st.session_state.username):
        # Add new data
        st.sidebar.header("Add Data")

        with st.sidebar.form("add_data_form"):
            new_date = st.date_input("Date")

            product_options = list(data['Produits_vendus'].unique()) + ["Add a New Product"]
            product_selection = st.selectbox("Product Sold", product_options)

            if product_selection == "Add a New Product":
                new_product = st.text_input("New Product Name", key="new_product_input")
            else:
                new_product = product_selection

            new_sales = st.number_input("Sales", min_value=0, step=1)
            new_visitors = st.number_input("Visitors", min_value=0, step=1)
            new_conversions = st.number_input("Conversions", min_value=0, step=1)
            new_revenue = st.number_input("Revenue (MAD)", min_value=0.0, step=0.01)
            submitted = st.form_submit_button("Add")

        if submitted:
            if not new_product:
                st.error("Please enter the name of the new product.")
            else:
                try:
                    new_data = {
                        'Date': [new_date],
                        'Produits_vendus': [new_product],
                        'Ventes': [new_sales],
                        'Visiteurs': [new_visitors],
                        'Conversions': [new_conversions],
                        'Revenus': [new_revenue]
                    }
                    new_df = pd.DataFrame(new_data)

                    updated_data = pd.concat([data, new_df], ignore_index=True)
                    updated_data.to_csv(data_file_path, index=False)

                    st.success("Data successfully added and CSV file updated.")
                except FileNotFoundError:
                    st.error("Data file not found. Please check the path.")

        # User management
        st.sidebar.header("User Management")

        with st.sidebar.form("add_user_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            add_user_button = st.form_submit_button("Add User")

        if add_user_button:
            if not new_username or not new_password:
                st.error("Please enter a username and password.")
            else:
                new_user_data = pd.DataFrame({
                    "username": [new_username],
                    "password": [hash_password(new_password)]
                })
                updated_users_data = pd.concat([users_data, new_user_data], ignore_index=True)
                updated_users_data.to_csv(users_file_path, index=False)
                st.success("New user added successfully.")

        # Edit user information
        st.sidebar.header("Edit User Information")

        with st.sidebar.form("edit_user_form"):
            edit_username = st.selectbox("Select User", users_data['username'])
            new_username_edit = st.text_input("New Username", value=edit_username)
            new_password_edit = st.text_input("New Password", type="password")
            edit_user_button = st.form_submit_button("Edit User")

        if edit_user_button:
            if not new_username_edit or not new_password_edit:
                st.error("Please enter a new username and password.")
            else:
                users_data.loc[users_data['username'] == edit_username, 'username'] = new_username_edit
                users_data.loc[users_data['username'] == new_username_edit, 'password'] = hash_password(new_password_edit)
                users_data.to_csv(users_file_path, index=False)
                st.success("User information successfully updated.")
