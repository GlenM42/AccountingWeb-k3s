# AccountingWeb

The project was in development since late 2023. The purpose of it was to create a bookkeeping system that would impose all the required checks to prevent any
mistakes that might happen during the paper bookkeeping (yes, some people do that!). It was chosen to make the system as a website build on Django in a connection
with the SQLite database to record transactions. 

The website includes:
  - Home page to greet the user;
  - Income Statement page which is in development (has Revenue, Expenses, and calculates Profit);
  - Balance Sheet page with all the required Assets, Liabilities, and Equities accounts listed in a table;
  - Transaction History page with the record of all transactions;
  - A html5 theme, and a set of images to make the website nicer;
  - The html is handled by the nginx.

# Usage

After copying the repo you need to get all requirements:
```
pip install -r requirements.txt
```

If you need to run the application locally, you would need a .env file with this configuration:
```
DB_ENGINE=...
DB_NAME=...
SECRET_KEY=...
DEBUG=...
```

Otherwise, put your information in the docker-compose.yml:
```
name: accountingweb
services:
    accountingweb:
        ports:
            - 80:8000
        environment:
            - DB_ENGINE=...
            - DB_NAME=...
            - SECRET_KEY='...
            - DEBUG=...
        image: ...
        restart: always
        volumes:
          - ${PWD}... # <- this is for mirroring the db
```
