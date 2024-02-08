# Docker окружение для проекта Star Burger

Настройки окружения с помощью `docker compose` для проекта https://github.com/fdrov/star_burger_2



## Подготовка
Создайте файлы переменных окружения .env.* на основе файлов .env.*.example. Заполните вашими данными.

## Запуск
### Development

Сервером приложения и статики выступает djando runserver.

`docker compose -f compose.dev.yml up -d --build`

`docker compose -f compose.dev.yaml down` остановить

`docker compose -f compose.dev.yaml down -v` остановить с удалением volumes

### Staging
Gunicorn + Nginx + Postgres

В этом случае сертификат будет запрашиваться через тестовый https://acme-staging-v02.api.letsencrypt.org/directory , чтобы отладить выпуск сертификата и не потратить лимит выпусков.

`docker compose -f compose.staging.yml up -d --build`

Сайт будет доступен по адресу [http://localhost:8000/](http://localhost:8000/)

### Production

Запустить production версию с выпуском сертефиката Let'sEncrypt с автопродлением

`docker compose -f compose.prod.yml up -d --build`

`docker compose -f compose.prod.yml down -v` - остророжно, БД тоже удалится.

## Загрузить тестовые данные

Примените миграции `python manage.py migrate`

Загрузите данные `docker compose -f compose.dev.yaml exec web python manage.py loaddata fixtures/db.json`

(если возникает ошибка, то может помочь `python manage.py loaddata  data.json  -e=contenttypes -e=auth.permission`)

Изображения для тестовых данных находятся в папке ./media

## TODO
- запускать prod контейнер не от root
- возможно мы не захотим хранить БД внутри контейнера
- делать wheels в стадии builder
- chmod +x entrypoint.sh
