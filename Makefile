install:
	python -m pip install -r requirements.txt

run:
	python wsgi.py

test:
	pytest -q

compile:
	python -m compileall -q app

db-init:
	flask --app wsgi db init

db-migrate:
	flask --app wsgi db migrate -m "schema update"

db-upgrade:
	flask --app wsgi db upgrade

seed:
	flask --app wsgi seed-demo
