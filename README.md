# URL Shortener API

## Introduction

![Postman Demo](rsc/postman.gif)
![Diagram](rsc/diagram.png)


This project is a URL Shortener API built using FastAPI. It demonstrates how to integrate FastAPI with PostgreSQL, Redis, and other key technologies to create a robust and efficient web service. The project is designed not only as a practical tool but also as a learning resource for developers who want to deepen their understanding of backend development, API design, and the deployment of scalable web applications.

## Features

- **URL Shortening**: Convert long URLs into concise, easily shareable short codes.
- **URL Retrieval**: Retrieve the original URL using the short code.
- **Redirection**: Automatically redirect users to the original URL when they access the short code.
- **URL Update**: Modify the original URL associated with an existing short code.
- **URL Deletion**: Remove a short code and its associated URL from the system.
- **Access Logging**: Track the number of accesses to each URL.
- **IP Geolocation**: Log the geographical locations from where the short URLs are accessed.
- **Caching**: Use Redis to cache responses and improve the performance of the API.
- **Rate Limiting**: Implement rate limiting to prevent abuse and ensure the API remains available to all users.

## Learning Objective

The primary goal of this project is
to develop a practical understanding of how to build and deploy a URL shortening service,
covering areas such as API design, database management, caching strategies, and production deployment.
It's designed for equipping developers with the necessary infrastructure to build robust,
high-performance URLs shortening services.

## Tech Stack

- **Python**: A high-level, interpreted programming language known for its simplicity and readability.
- **FastAPI**: A modern, fast (high-performance) web framework for building APIs with Python.
- **PostgreSQL**: A powerful, open-source object-relational database system.
- **Redis**: An in-memory data structure store, used as a database, cache, and message broker.
- **Docker**: Used to containerize the application for easy deployment.
- **Uvicorn/Gunicorn**: ASGI servers used to run FastAPI applications in production.

## Prerequisites

Before you start, ensure that you have the following tools installed:

- **Python 3.8+**: The core programming language used in this project.
- **PostgreSQL**: For storing URL data and managing database operations.
- **Redis**: To handle caching and improve the API’s performance.
- **Docker**: Optional, but recommended for containerizing the application.
- **Git**: To clone the repository and manage version control.

## Getting Started

### 1. Clone the Repository

Start by cloning the repository:

```bash
git clone https://github.com/pyoneerC/urlshortener.git
cd urlshortener
```

### 2. Install Dependencies

Set up a virtual environment and install the required dependencies:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the root directory and add your configuration:

```bash
# Database
DATABASE_URL=postgresql://<username>:<password>@<host>:<port>/<database>

# Redis
REDIS_HOST=<redis-host>
REDIS_PORT=<redis-port>
REDIS_PASSWORD=<redis-password>
REDIS_SSL=true

# IP Geolocation API
API_KEY=<your-ip-geolocation-api-key>
```

### 4. Initialize the Database

Set up your PostgreSQL database with the necessary table:

```sql
CREATE TABLE urls (
    id SERIAL PRIMARY KEY,
    short_code VARCHAR(10) UNIQUE NOT NULL,
    original_url TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL,
    last_updated_at TIMESTAMP NOT NULL,
    expiration_date TIMESTAMP NOT NULL,
    access_count INT NOT NULL
);
```

### 5. Run the Application

Start the FastAPI server:

```bash
uvicorn main:app --reload
```

Your API will now be accessible at `http://127.0.0.1:8000`.

## API Endpoints

Here are the main endpoints for the API:

- `POST /shorten`: Shorten a new URL.
- `GET /shorten/{short_code}`: Retrieve the original URL using the short code.
- `PUT /shorten`: Update an existing short URL.
- `DELETE /shorten/{short_code}`: Delete a short URL.
- `GET /`: Redirect to the original URL using the short code.
- `GET /health`: Health check endpoint to ensure the API is running.

## Deployment

### Manual Deployment

For manual deployment on a cloud server, follow these steps:

1. **Set Up Environment Variables**: Configure the necessary environment variables on your server.
2. **Install PostgreSQL and Redis**: Ensure both PostgreSQL and Redis are installed and running.
3. **Run the Application**: Use Uvicorn or Gunicorn to run the FastAPI application.
4. **Configure a Reverse Proxy**: Set up a reverse proxy, such as Nginx, to manage incoming traffic and serve your API securely.

### Deploying with Docker

If you prefer to use Docker, you can containerize the application and deploy it with ease:

1. **Create a `Dockerfile`**: Define the Dockerfile for your application.
2. **Build the Docker Image**: Run `docker build -t url-shortener-api .` to build the image.
3. **Run the Container**: Deploy the container using `docker run -d -p 8000:8000 --env-file .env url-shortener-api`.

## Contributing

Contributions are welcome! If you find a bug or have a feature request, please open an issue or submit a pull request. Your contributions can help to make this project better.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.