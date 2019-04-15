#!/bin/bash

crontab cron_jobs
service cron start
export FLASK_APP=app/__init__.py
export FLASK_DEBUG=1
flask run --host=0.0.0.0 --without-threads
