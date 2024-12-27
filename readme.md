# Wallsprint Project

Wallsprint is a Django-based web application designed to manage user authentication, content management, and e-commerce functionalities. This project leverages Django's robust framework along with several third-party packages to provide a comprehensive solution for managing users, permissions, and content.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Contributing](#contributing)
- [License](#license)

## Features

- **User Authentication**: Utilizes JWT for secure user authentication.
- **Role-Based Access Control**: Middleware to enforce role-based access to different parts of the application.
- **Content Management**: Manage portals, catalogs, and content with nested relationships.
- **E-commerce**: Manage orders, carts, and catalog items.
- **Notifications**: Email notifications for various events like file transfers and order creations.
- **REST API**: Exposes a RESTful API for interaction with the application.

## Installation

1. **Clone the repository**:

   ```bash
   git clone https://github.com/OlisaPaul/wallsprint.git
   cd wallsprint
   ```

2. **Create a virtual environment**:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the database**:

   ```bash
   python manage.py migrate
   ```

5. **Create a superuser**:

   ```bash
   python manage.py createsuperuser
   ```

6. **Run the development server**:
   ```bash
   python manage.py runserver
   ```

## Configuration

- **Environment Variables**: Use a `.env` file to configure environment-specific settings. Refer to `dotenv` for loading environment variables.
- **Django Settings**: Modify `wallsprint/settings.py` for database configurations, middleware, and installed apps.

## Usage

- **Admin Panel**: Access the Django admin panel at `/api/v1/admin/` to manage users, groups, and permissions.
- **API Documentation**: Swagger UI is available at `/api/v1/swagger/` for exploring the API endpoints.

## API Endpoints

- **Authentication**:

  - `/api/v1/auth/` for user authentication and token management.
  - `/api/v1/auth/logout/` for logging out users.

- **Content Management**:

  - `/api/v1/store/portals/` for managing portals and their contents.
  - `/api/v1/store/catalogs/` for managing catalogs and items.

- **User Management**:
  - `/api/v1/auth/groups/` for managing user groups.
  - `/api/v1/auth/staffs/` for managing staff users.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request for any enhancements or bug fixes.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
