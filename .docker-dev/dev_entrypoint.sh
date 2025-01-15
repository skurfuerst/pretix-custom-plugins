#!/bin/bash

cd /plugins/pretix-custom-js
python setup.py develop

cd /plugins/pretix-auto-paid
python setup.py develop

cd /pretix/src
#python manage.py migrate
pretix taskworker &
pretix runserver 0.0.0.0:8000
