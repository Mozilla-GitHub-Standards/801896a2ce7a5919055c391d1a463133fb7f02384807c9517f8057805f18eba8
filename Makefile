build:
	sh scripts/build_proxy.sh

lint: build
	docker run -t -i -u root app:build sh -c "flake8 ."

test: build 
	docker run -t -i -u root app:build sh -c "nosetests proxy/ --nocapture --with-coverage --cover-package=proxy --cover-min-percentage=100"

check: build
	docker run -t -i -u root app:build sh -c "flake8 . && nosetests proxy/ --nocapture --with-coverage --cover-package=proxy --cover-min-percentage=100"

compose_build: build
	docker-compose build

shell: compose_build
	docker-compose run app ipython 

up: compose_build
	docker-compose up
