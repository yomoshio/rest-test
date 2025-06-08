#REST-TEST

This is a Python-based application with a PostgreSQL database, containerized using Docker.

## Prerequisites
- Docker
- Docker Compose

## Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/yomoshio/rest-test
   cd rest-test

## Start the services
2. ```bash
    docker-compose up --build

## Stop the services
3. ```bash
   docker-compose down

## If you debug
4. ```bash
   source venv/bin/activate
   python -m app.main

### Notes
- The `docker-compose.yml` includes a `db` service with PostgreSQL and links it to the `app` service. The `populate_db` script runs after `app.main` using a `bash -c` command.
- The `.env` file is used to pass environment variables to both services.
- The Dockerfile assumes a `requirements.txt` file exists in the root directory. Ensure it includes all necessary Python packages (e.g., `psycopg2` for PostgreSQL, etc.).
- The README provides basic setup and usage instructions. Adjust the repository URL and additional details as needed.

5. Testing
   Just go to tour_url:PORT/docs 
