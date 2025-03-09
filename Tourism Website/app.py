from flask import Flask, render_template, request, redirect, url_for, flash 
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import psycopg2

app = Flask(__name__)   
app.secret_key = "your_secret_key"  # Required for session handling

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"  # Redirects to login page if not authenticated

# PostgreSQL Connection String
DATABASE_URL = "postgresql://admin:admin@localhost:5432/tourism_db"

def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL)
        print("Database connection successful!")
        return conn
    except psycopg2.Error as e:
        print("Database connection error:", e)
        return None

# User Model
class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    if conn:
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id, username, email FROM users WHERE id = %s", (user_id,))
                user = cur.fetchone()
            if user:
                return User(user[0], user[1], user[2])
        finally:
            conn.close()
    return None

@app.route("/")
def login_redirect():
    """Redirect to login page."""
    return redirect(url_for("login"))

@app.route("/home")
@login_required
def home():
    """Show homepage (index.html)."""
    username = current_user.username if current_user.is_authenticated else None
    return render_template("index.html", username=username)

@app.route("/about")
def about():
    """Show about page (about.html)."""
    return render_template("about.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        print("Received data:", username, email, password, confirm_password)

        if not username or not email or not password or not confirm_password:
            flash("All fields are required!", "danger")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("register"))

        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    # Ensure email isn't already registered
                    cur.execute("SELECT id FROM users WHERE email = %s", (email,))
                    existing_user = cur.fetchone()
                    if existing_user:
                        flash("Email already exists. Please log in.", "danger")
                        return redirect(url_for("login"))

                    # Insert new user and return their ID
                    cur.execute(
                        "INSERT INTO users (username, email, password) VALUES (%s, %s, %s) RETURNING id",
                        (username, email, password)
                    )
                    new_user_id = cur.fetchone()[0]
                    conn.commit()
                    print("Inserted new user with ID:", new_user_id)

                    flash("Account created successfully! Please log in.", "success")
                    return redirect(url_for("login"))

            except psycopg2.Error as e:
                flash(f"Database error: {e.pgerror}", "danger")
                print("Database error:", e)

            finally:
                conn.close()

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        flash(email + " " + password)

        conn = get_db_connection()
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, username, email, password FROM users WHERE email = %s", (email,))
                    user = cur.fetchone()

                    if user and user[3] == password:
                        user_obj = User(user[0], user[1], user[2])
                        login_user(user_obj)
                        flash("Login successful!", "success")
                        return redirect(url_for("home"))
                    else:
                        flash("Invalid email or password.", "danger")

            except psycopg2.Error as e:
                flash("A database error occurred.", "danger")
                print("Database error:", e)
            finally:
                conn.close()

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
