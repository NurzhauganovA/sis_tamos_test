-- Создание пользователя postgres если не существует
DO
$do$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'postgres') THEN
      CREATE USER postgres WITH PASSWORD '5693';
   ELSE
      ALTER USER postgres PASSWORD '5693';
   END IF;
END
$do$;

-- Даем права на создание БД
ALTER USER postgres CREATEDB;

-- Создаем базу данных
CREATE DATABASE sis OWNER postgres;

-- Даем все привилегии
GRANT ALL PRIVILEGES ON DATABASE sis TO postgres;