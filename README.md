
# SYNQ – College Event Management Portal

<p align="center">
  <b>A centralized platform for managing college events and student registrations.</b>
</p>

<p align="center">
  <a href="https://synq-event-portal.onrender.com">
    Live Demo
  </a>
</p>

---

## 📌 About the Project

SYNQ is a web-based College Event Management Portal
developed to simplify and centralize the process of
organizing, managing, and participating in college events.

The platform provides separate Student and Admin roles,
allowing administrators to manage events while students
can explore events and manage their registrations.

## ✨ Features

### 👨‍🎓 Student
- User registration and login
- Browse available college events
- Register for events
- View registered events
- Cancel event registrations

### 🛠️ Admin
- Secure Admin login
- Create, update and delete events
- View registered participants
- Access participant registration details

### 🔐 Security
- Password hashing
- Session management
- Role-based access control

## 🧰 Technologies Used

| Category | Technology |
|---|---|
| Backend | Python, Flask |
| Frontend | HTML, CSS, JavaScript |
| Database | PostgreSQL |
| Database Hosting | Neon |
| Deployment | Render |
| Version Control | Git, GitHub |

## 🏗️ System Architecture

SYNQ follows a three-layer architecture:

1. **Presentation Layer:** HTML, CSS and JavaScript
   provide the user interface.
2. **Application Layer:** Flask handles authentication,
   event management and registration logic.
3. **Database Layer:** PostgreSQL stores user, event
   and registration information.

## 🗄️ Database Design

The application uses three main entities:

- **User:** Stores student and administrator details.
- **Event:** Stores event information.
- **Registration:** Stores student-event registration
  records.

A user can have multiple registrations, and an event
can have multiple registrations.

## 📸 Screenshots

Add your actual application screenshots here.

| Page | Screenshot |
|---|---|
| Login Page | Add screenshot |
| Student Dashboard | Add screenshot |
| Event Management | Add screenshot |
| Registration Page | Add screenshot |
| Admin Participants | Add screenshot |

## 🚀 Live Application

[Visit SYNQ](https://synq-event-portal.onrender.com)

## 💻 Running Locally

### 1. Clone the repository

```bash
git clone https://github.com/ansaletmj-cmd/synq-event-portal.git
cd synq-event-portal
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it:

Windows:
```bash
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Set the database connection string and other
required configuration values using a local `.env`
file or your environment configuration.

Never commit real credentials or secret keys.

### 5. Run the application

Use the startup command configured in the project.
For example, if the Flask entry point is `app.py`:

```bash
python app.py
```

Open the local address displayed in the terminal.

## 🔮 Future Enhancements

- Automated email notifications
- QR-based event attendance
- Advanced event analytics
- Multi-administrator support
- Calendar-based event scheduling

## 👩‍💻 Development Team

- Ansalet M J
- Nidhi Vijayakumar
- Rani Kurian

## 📄 License

This project was developed as an academic
minor project.
