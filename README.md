# AccountingWeb

The project has been in development since late 2023. The purpose of it was to create a bookkeeping system that would impose all the required checks to prevent any
mistakes that might happen during the paper bookkeeping (yes, some people do that!). It was chosen to make the system as a website build on Django in a connection
with the SQLite database to record transactions. 

The website includes:
  - Home page to greet the user;
  - Income Statement page with Revenue, Expenses, and Profit breakdown, and the ability to look them up for different time frames;
  - Balance Sheet page with all the required Assets, Liabilities, and Equities accounts listed in a table;
  - Transaction History page with the record of all transactions;
  - New Transaction page which allows for the proper input;
  - Summary page where you can look at the change of your accounts up to one year;
  - A html5 theme, and a set of images to make the website nicer in Swiss-style.

# Usage

This project uses **uv** for Python dependency management and **Docker** for running the application in a reproducible environment.
Running the app via Docker is the **recommended approach**, especially for anything beyond local experimentation.

**Prerequisites**:
* Python **3.12+**
* [uv](https://github.com/astral-sh/uv)
* Docker & Docker Compose

### Local development (without Docker)

1. Install dependencies with uv:

```bash
uv sync
```

2. Configure environment variables:

```env
DB_ENGINE=...
DB_NAME=...
SECRET_KEY=your-secret-key
DEBUG=True
```

3. Run migrations and start the server manually:

```bash
uv run python manage.py migrate
uv run python manage.py runserver
```

### Running with Docker

1. Build the image from the project root:

```bash
docker build -t accountingweb:local .
```

2. Run the container directly. Example command:

```bash
docker run --rm \
  --name accountingweb \
  -p 127.0.0.1:8000:8000 \
  -e DB_HOST=... \
  -e DB_ENGINE=... \
  -e DB_PORT=... \
  -e DB_USER=... \
  -e DB_PASSWORD=... \
  -e DB_NAME=... \
  -e SECRET_KEY=... \
  -e DEBUG=True/False \
  --add-host host.docker.internal:host-gateway \
  accountingweb:local
```

### Docker Compose

Below is the **recommended Docker Compose configuration**, matching the current production layout:

```yaml
services:
  web:
    container_name: accountingweb
    image: <image>
    restart: always
    ports:
      - "127.0.0.1:8000:8000"

    environment:
      - DB_HOST=...
      - DB_ENGINE=...
      - DB_PORT=...
      - DB_USER=...
      - DB_PASSWORD=...
      - DB_NAME=...
      - SECRET_KEY=...
      - DEBUG=False

    extra_hosts:
      - "host.docker.internal:host-gateway"
```

To start the service:

```bash
docker compose up -d
```
