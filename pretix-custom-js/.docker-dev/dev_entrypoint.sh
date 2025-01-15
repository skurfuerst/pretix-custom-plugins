#!/bin/bash

cd /pretix-custom-js
python setup.py develop

cd /pretix/src
#python manage.py migrate
pretix taskworker &
pretix runserver 0.0.0.0:8000
