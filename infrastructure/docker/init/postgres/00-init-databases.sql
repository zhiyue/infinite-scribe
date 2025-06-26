-- Create Prefect database
CREATE DATABASE prefect WITH ENCODING='UTF-8' LC_COLLATE='en_US.utf8' LC_CTYPE='en_US.utf8';

-- Grant all privileges on prefect database to the postgres user
GRANT ALL PRIVILEGES ON DATABASE prefect TO postgres;