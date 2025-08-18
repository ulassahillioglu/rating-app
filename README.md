Social Rating App

A Django-based web application that enables users to rate each other anonymously across admin-defined categories.
This project is designed to provide structured peer feedback, where categories (such as Teamwork, Communication, Reliability, etc.) are managed by the application administrator.

🚀 Features

🔑 Authentication System – Secure user registration and login.

📝 Anonymous Ratings – Users can rate each other without revealing their identity.

⚙️ Admin-Defined Categories – Only admins can create and manage rating categories.

📊 Aggregated Scores – Each user’s profile displays average ratings across categories.

📱 Responsive UI – Works smoothly on desktop and mobile.

🛠️ Django Admin Panel – Full control over users, categories, and ratings.

📂 Project Structure
project_root/
│
├── CoreApp/          # Core functionality of the platform
├── UserAuth/         # Handles user authentication and sessions
├── templates/        # HTML templates
├── static/           # Static assets (CSS, JS, images)
├── manage.py         # Django project manager
└── requirements.txt  # Dependencies

⚙️ Installation
1. Clone the repository
git clone https://github.com/your-username/your-new-repo.git
cd your-new-repo

2. Set up a virtual environment
python -m venv venv
source venv/bin/activate   # On Linux/Mac
venv\Scripts\activate      # On Windows

3. Install dependencies
pip install -r requirements.txt

4. Apply database migrations
python manage.py migrate

5. Create a superuser (admin)
python manage.py createsuperuser

6. Run the development server
python manage.py runserver


Now visit: http://127.0.0.1:8000/ 🎉

🔧 Usage

Admin Login → Go to /admin to add rating categories.

Users → Register or log in to the platform.

Rating → Users can rate each other anonymously across available categories.

Profiles → Each profile shows aggregated scores based on received ratings.

✅ Future Improvements

⭐ Weighted rating system

📬 Notifications for new ratings

🔍 Search and filter by categories

📊 Exportable reports

📜 License

This project is licensed under the MIT License – feel free to use, modify, and distribute.
