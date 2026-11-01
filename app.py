import os
from flask import Flask, render_template, request, redirect, url_for, session
if os.environ.get("DATABASE_URL"):
    from database_postgres import get_db_connection
else:
    from database import get_db_connection
from werkzeug.security import generate_password_hash, check_password_hash
from flask_wtf.csrf import CSRFProtect

app = Flask(__name__)
app.secret_key = os.environ.get("SYNQ_SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("SYNQ_SECRET_KEY environment variable is missing.")

app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
csrf = CSRFProtect(app)

# -----------------------------------
# HOME PAGE
# -----------------------------------
@app.route("/")
def home():
    if session.get("user_id"):
        if str(session.get("role", "")).lower() == "admin":
            return redirect(url_for("admin_dashboard"))

        return redirect(url_for("dashboard"))

    return render_template("home.html")


# -----------------------------------
# REGISTER USER
# -----------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():

    if session.get("user_id"):
        if str(session.get("role", "")).lower() == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            return render_template("register.html",
                                   error="All fields are required."), 400

        if len(name) > 100:
            return render_template("register.html",
                                   error="Name must be 100 characters or fewer."), 400

        if ("@" not in email or email.startswith("@")
                or email.endswith("@") or "." not in email.split("@")[-1]):
            return render_template("register.html",
                                   error="Please enter a valid email address."), 400

        if len(password) < 8:
            return render_template("register.html",
                                   error="Password must contain at least 8 characters."), 400

        conn = get_db_connection()

        try:
            existing_user = conn.execute(
                'SELECT user_id, name, password_hash, role FROM "user" WHERE email = ?',
                (email,)
            ).fetchone()

            # If the first form submission already created the account,
            # allow the same user to continue instead of showing a false error.
            if existing_user:
                if (
                    existing_user["role"] == "Student"
                    and check_password_hash(
                        existing_user["password_hash"], password
                    )
                ):
                    session["user_id"] = existing_user["user_id"]
                    session["user_name"] = existing_user["name"]
                    session["role"] = "Student"
                    return redirect(url_for("dashboard"))

                return render_template(
                    "register.html",
                    error="This email is already registered. Please log in."
                ), 400

            password_hash = generate_password_hash(password)

            conn.execute(
                """
                INSERT INTO "user" (name, email, password_hash, role)
                VALUES (?, ?, ?, ?)
                """,
                (name, email, password_hash, "Student")
            )

            new_user = conn.execute(
                'SELECT user_id FROM "user" WHERE email = ?',
                (email,)
            ).fetchone()

            conn.commit()

            if not new_user:
                raise RuntimeError("Could not retrieve the new account ID.")

            session["user_id"] = new_user["user_id"]
            session["user_name"] = name
            session["role"] = "Student"

        except Exception:
            conn.rollback()
            app.logger.exception("Registration failed")
            return render_template(
                "error.html",
                message="Registration failed. Please try again."
            ), 500

        finally:
            conn.close()

        return redirect(url_for("dashboard"))

    return render_template("register.html")


# -----------------------------------
# LOGIN USER
# -----------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():

    if session.get("user_id"):
        if str(session.get("role", "")).lower() == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            return render_template(
                "login.html",
                error="Please enter both email and password."
            ), 400

        conn = get_db_connection()

        try:
            user = conn.execute(
                "SELECT * FROM user WHERE email = ?",
                (email,)
            ).fetchone()
        finally:
            conn.close()

        if user and check_password_hash(
            user["password_hash"], password
        ):

            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]

            if str(user["role"]).lower() == "admin":
                return redirect(url_for("admin_dashboard"))

            return redirect(url_for("dashboard"))

        return render_template(
            "login.html",
            error="Invalid email or password. Please try again."
        ), 401

    return render_template("login.html")


# -----------------------------------
# ADMIN DASHBOARD
# -----------------------------------
@app.route("/admin")
def admin_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "Admin":
        return render_template("access_denied.html"), 403

    conn = get_db_connection()

    try:
        events = conn.execute(
            "SELECT * FROM event ORDER BY date ASC"
        ).fetchall()

        total_events = conn.execute(
            "SELECT COUNT(*) FROM event"
        ).fetchone()[0]

        total_students = conn.execute(
            "SELECT COUNT(*) FROM user WHERE role = 'Student'"
        ).fetchone()[0]

        total_registrations = conn.execute(
            "SELECT COUNT(*) FROM registration"
        ).fetchone()[0]

        return render_template(
            "admin_dashboard.html",
            events=events,
            total_events=total_events,
            total_students=total_students,
            total_registrations=total_registrations
        )

    finally:
        conn.close()

# -----------------------------------
# ADMIN: VIEW EVENT PARTICIPANTS
# -----------------------------------
@app.route("/admin/participants")
def admin_participants():

    # Only logged-in admins can access this page
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "Admin":
        return render_template("access_denied.html"), 403

    conn = get_db_connection()

    try:
        participants = conn.execute("""
            SELECT
                registration.registration_id,
                registration.phone,
                registration.department,
                registration.year_of_study,
                registration.class_division,
                registration.status,
                registration.registered_at,
                user.name,
                user.email,
                event.title AS event_title,
                event.date AS event_date
            FROM registration
            JOIN user
                ON registration.user_id = user.user_id
            JOIN event
                ON registration.event_id = event.event_id
            ORDER BY event.date ASC, user.name ASC
        """).fetchall()

        return render_template(
            "admin_participants.html",
            participants=participants
        )

    finally:
        conn.close()

# -----------------------------------
# STUDENT DASHBOARD
# SEARCH, FILTER AND STATISTICS
# -----------------------------------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") == "Admin":
        return redirect(url_for("admin_dashboard"))

    search_query = request.args.get("search", "").strip()
    selected_category = request.args.get("category", "").strip()

    conn = get_db_connection()

    sql = "SELECT * FROM event WHERE 1=1"
    params = []

    if search_query:
        sql += """
            AND (
                title LIKE ?
                OR description LIKE ?
                OR venue LIKE ?
                OR category LIKE ?
            )
        """
        keyword = f"%{search_query}%"
        params.extend([keyword, keyword, keyword, keyword])

    if selected_category:
        sql += " AND category = ?"
        params.append(selected_category)

    sql += " ORDER BY date ASC"

    events = conn.execute(sql, params).fetchall()

    total_events = conn.execute(
        "SELECT COUNT(*) AS count FROM event"
    ).fetchone()["count"]

    my_registration_count = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM registration
        WHERE user_id = ?
        """,
        (session["user_id"],)
    ).fetchone()["count"]

    unread_notification_count = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM notification
        WHERE user_id = ? AND is_read = 0
        """,
        (session["user_id"],)
    ).fetchone()["count"]

    conn.close()

    return render_template(
        "dashboard.html",
        user_name=session["user_name"],
        events=events,
        search_query=search_query,
        selected_category=selected_category,
        total_events=total_events,
        my_registration_count=my_registration_count,
        unread_notification_count=unread_notification_count
    )


# -----------------------------------
# LOGOUT
# -----------------------------------
@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# -----------------------------------
# CREATE EVENT - ADMIN ONLY
# -----------------------------------
@app.route("/create-event", methods=["GET", "POST"])
def create_event():
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "Admin":
        return "Access denied! Admins only.", 403

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        venue = request.form["venue"]
        date = request.form["date"]
        capacity = request.form["capacity"]
        category = request.form["category"]

        conn = get_db_connection()

        try:
            # Create the event
            cursor = conn.execute(
                """
                INSERT INTO event
                (title, description, venue, date, capacity, category, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    title,
                    description,
                    venue,
                    date,
                    capacity,
                    category,
                    session["user_id"]
                )
            )

            event_id = cursor.lastrowid

            # Notify all student accounts about the new event
            conn.execute(
                """
                INSERT INTO notification (user_id, event_id, message)
                SELECT user_id, ?, ?
                FROM user
                WHERE role = 'Student'
                """,
                (
                    event_id,
                    f"New event announced: {title}!"
                )
            )

            conn.commit()

        except Exception as e:
            conn.rollback()
            print("EVENT CREATION ERROR:", repr(e), flush=True)
            app.logger.exception("Event creation failed")
            return f"Event creation failed: {e}", 500

        finally:
            conn.close()

        return redirect(url_for("admin_dashboard"))

    return render_template("create_event.html")

# -----------------------------------
# EDIT EVENT - ADMIN ONLY
# -----------------------------------
@app.route("/edit-event/<int:event_id>", methods=["GET", "POST"])
def edit_event(event_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "Admin":
        return "Access denied! Admins only.", 403

    conn = get_db_connection()

    try:
        event = conn.execute(
            "SELECT * FROM event WHERE event_id = ?",
            (event_id,)
        ).fetchone()

        if event is None:
            return "Event not found.", 404

        if request.method == "POST":
            title = request.form.get("title", "").strip()
            description = request.form.get("description", "").strip()
            venue = request.form.get("venue", "").strip()
            date = request.form.get("date", "").strip()
            category = request.form.get("category", "").strip()

            try:
                capacity = int(request.form.get("capacity", ""))
            except (ValueError, TypeError):
                return "Please enter a valid capacity.", 400

            if not title or not venue or not date:
                return "Title, venue and date are required.", 400

            if capacity < 1:
                return "Capacity must be at least 1.", 400

            registered_count = conn.execute(
                """
                SELECT COUNT(*) AS total
                FROM registration
                WHERE event_id = ? AND status = 'Confirmed'
                """,
                (event_id,)
            ).fetchone()["total"]

            if capacity < registered_count:
                return (
                    f"Capacity cannot be less than the "
                    f"{registered_count} confirmed registrations.",
                    400
                )

            conn.execute(
                """
                UPDATE event
                SET title = ?, description = ?, venue = ?,
                    date = ?, capacity = ?, category = ?
                WHERE event_id = ?
                """,
                (
                    title, description, venue,
                    date, capacity, category, event_id
                )
            )

            conn.commit()
            return redirect(url_for("admin_dashboard"))

        return render_template("edit_event.html", event=event)

    except Exception:
        conn.rollback()
        app.logger.exception("Event update failed")
        return "Unable to update the event. Please try again.", 500

    finally:
        conn.close()


# -----------------------------------
# DELETE EVENT - ADMIN ONLY
# -----------------------------------
@app.route("/delete-event/<int:event_id>", methods=["POST"])
def delete_event(event_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "Admin":
        return "Access denied! Admins only.", 403

    conn = get_db_connection()

    try:
        event = conn.execute(
            "SELECT event_id FROM event WHERE event_id = ?",
            (event_id,)
        ).fetchone()

        if event is None:
            return "Event not found.", 404

        # Remove records linked to this event first.
        conn.execute(
            "DELETE FROM notification WHERE event_id = ?",
            (event_id,)
        )

        conn.execute(
            "DELETE FROM registration WHERE event_id = ?",
            (event_id,)
        )

        conn.execute(
            "DELETE FROM event WHERE event_id = ?",
            (event_id,)
        )

        conn.commit()

    except Exception:
        conn.rollback()
        app.logger.exception("Event deletion failed")
        return "Unable to delete the event. Please try again.", 500

    finally:
        conn.close()

    return redirect(url_for("admin_dashboard"))

# -----------------------------------
# EVENT DETAILS
# -----------------------------------
@app.route("/event/<int:event_id>")
def event_details(event_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    event = conn.execute(
        "SELECT * FROM event WHERE event_id = ?",
        (event_id,)
    ).fetchone()

    registration = None

    if session.get("role") != "Admin" and event is not None:
        registration = conn.execute(
            """
            SELECT * FROM registration
            WHERE user_id = ? AND event_id = ?
            """,
            (session["user_id"], event_id)
        ).fetchone()

    conn.close()

    if event is None:
        return "Event not found!", 404

    return render_template(
        "event_details.html",
        event=event,
        registration=registration
    )




# -----------------------------------
# REGISTER FOR EVENT
# -----------------------------------
@app.route("/event/<int:event_id>/register", methods=["GET", "POST"])
def register_event(event_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") != "Student":
        return "Only students can register for events.", 403

    conn = get_db_connection()

    try:
        # Check whether the event exists
        event = conn.execute(
            "SELECT * FROM event WHERE event_id = ?",
            (event_id,)
        ).fetchone()

        if event is None:
            return "Event not found.", 404

        # Get the student's account details
        user = conn.execute(
            "SELECT name, email FROM user WHERE user_id = ?",
            (session["user_id"],)
        ).fetchone()

        # Check for an existing registration
        existing_registration = conn.execute(
            """
            SELECT registration_id
            FROM registration
            WHERE user_id = ? AND event_id = ?
            """,
            (session["user_id"], event_id)
        ).fetchone()

        if existing_registration:
            return redirect(url_for("my_events"))

        if request.method == "POST":
            phone = request.form.get("phone", "").strip()
            department = request.form.get("department", "").strip()
            year_of_study = request.form.get("year_of_study", "").strip()
            class_division = request.form.get("class_division", "").strip()

            # Validate required fields
            if not all([
                phone, department, year_of_study, class_division
            ]):
                return render_template(
                    "event_registration.html",
                    event=event,
                    user=user,
                    error="Please fill in all required fields."
                )

                      # Check available capacity
            registered_count = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM registration
                WHERE event_id = ? AND status = 'Confirmed'
                """,
                (event_id,)
            ).fetchone()["count"]

            if registered_count >= event["capacity"]:
                return render_template(
                    "event_full.html",
                    event_title=event["title"]
                ), 400

            # Save registration and student details
            conn.execute(
                """
                INSERT INTO registration (
                    user_id, event_id, status, phone,
                    department, year_of_study, class_division
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session["user_id"],
                    event_id,
                    "Confirmed",
                    phone,
                    department,
                    year_of_study,
                    class_division
                )
            )
            # Create a notification
            conn.execute(
                """
                INSERT INTO notification (user_id, event_id, message)
                VALUES (?, ?, ?)
                """,
                (
                    session["user_id"],
                    event_id,
                    f"You successfully registered for {event['title']}!"
                )
            )

            conn.commit()

            # Open My Events after successful registration
            return redirect(url_for("my_events"))

        # GET request: display the registration form
        return render_template(
            "event_registration.html",
            event=event,
            user=user,
            error=None
        )

    except Exception:
        conn.rollback()
        app.logger.exception("Event registration failed")
        return "Registration failed. Please try again.", 500

    finally:
        conn.close()

@app.context_processor
def inject_unread_notification_count():
    unread_notification_count = 0

    if (
        "user_id" in session
        and session.get("role") == "Student"
    ):
        conn = get_db_connection()

        try:
            unread_notification_count = conn.execute(
                """
                SELECT COUNT(*)
                FROM notification
                WHERE user_id = ? AND is_read = 0
                """,
                (session["user_id"],)
            ).fetchone()[0]

        finally:
            conn.close()

    return {
        "unread_notification_count": unread_notification_count
    }



# -----------------------------------
# CANCEL EVENT REGISTRATION
# -----------------------------------
@app.route("/event/<int:event_id>/cancel", methods=["POST"])
def cancel_registration(event_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    if session.get("role") == "Admin":
        return "Admins cannot cancel student registrations.", 403

    conn = get_db_connection()

    registration = conn.execute(
        """
        SELECT * FROM registration
        WHERE user_id = ? AND event_id = ?
        """,
        (session["user_id"], event_id)
    ).fetchone()

    if registration is None:
        conn.close()
        return "You are not registered for this event!"

    event = conn.execute(
        "SELECT title FROM event WHERE event_id = ?",
        (event_id,)
    ).fetchone()

    conn.execute(
        """
        DELETE FROM registration
        WHERE user_id = ? AND event_id = ?
        """,
        (session["user_id"], event_id)
    )

    if event:
        conn.execute(
            """
            INSERT INTO notification (user_id, event_id, message)
            VALUES (?, ?, ?)
            """,
            (
                session["user_id"],
                event_id,
                f"Your registration for {event['title']} was cancelled."
            )
        )

    conn.commit()
    conn.close()

    return redirect(url_for("my_events"))



# -----------------------------------
# MY EVENTS
# -----------------------------------
@app.route("/my-events")
def my_events():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    registered_events = conn.execute(
        """
        SELECT event.*, registration.status
        FROM registration
        INNER JOIN event
            ON registration.event_id = event.event_id
        WHERE registration.user_id = ?
        ORDER BY event.date ASC
        """,
        (session["user_id"],)
    ).fetchall()

    conn.close()

    return render_template(
        "my_events.html",
        events=registered_events,
        user_name=session.get("user_name", "Student")
    )




# -----------------------------------
# NOTIFICATIONS
# -----------------------------------
@app.route("/notifications")
def notifications():
    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db_connection()

    try:
        # Mark this student's notifications as read
        conn.execute(
            """
            UPDATE notification
            SET is_read = 1
            WHERE user_id = ? AND is_read = 0
            """,
            (session["user_id"],)
        )
        conn.commit()

        # Fetch all notifications; keep read ones visible
        notifications = conn.execute(
            """
            SELECT *
            FROM notification
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (session["user_id"],)
        ).fetchall()

        # Count remaining unread notifications
        unread_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM notification
            WHERE user_id = ? AND is_read = 0
            """,
            (session["user_id"],)
        ).fetchone()[0]

    finally:
        conn.close()

    return render_template(
        "notifications.html",
        notifications=notifications,
        unread_count=unread_count
    )

# -----------------------------------
# RUN APPLICATION
# -----------------------------------
if __name__ == "__main__":
    app.run(debug=True)

