# Setup Environment

```textmate
# install python3
apt-get install python3-pip python3-dev
pip3 install --upgrade pip

python --version
apt-get remove --purge python2.7

```
* Make python3 default
`vim ~/.bash_aliases` and add `alias python=python3` save then run `source ~/.bash_aliases`.

* Install `virtualenv`

```textmate
sudo pip install virtualenv virtualenvwrapper
echo "export VIRTUALENVWRAPPER_PYTHON=/usr/bin/python3" >> ~/.bashrc
echo "export WORKON_HOME=~/Env" >> ~/.bashrc
echo "source /usr/local/bin/virtualenvwrapper.sh" >> ~/.bashrc
source ~/.bashrc
```

* Install `uwsgi`

```textmate
# General
sudo pip3 install uwsgi
sudo mkdir -p /etc/uwsgi/sites
mkdir -p /var/log/uwsgi

cp /var/www/html/project/deploy/uwsgi.service /etc/systemd/system/
sudo systemctl enable uwsgi
sudo systemctl restart uwsgi
sudo systemctl status uwsgi

# Avoid error with pip install

sudo apt-get install libmysqlclient-dev
sudo apt-get install libcurl4-openssl-dev
sudo apt-get install libpq-dev python3-dev libxml2-dev libxslt1-dev libldap2-dev libsasl2-dev libffi-dev

#For project
cd /var/www/html/project
mkvirtualenv project
workon project
pip3 install -r requirments.txt
ln -s /var/www/html/project/deploy/project.ini /etc/uwsgi/sites/project.ini
ln -s /var/www/html/project/deploy/local.project.vn /etc/nginx/sites-enabled/local.project.vn

```
* Edit local `hosts`
```textmate
115.146.127.8 local.project.vn
service uwsgi restart
service nginx restart
mysql -uroot -ptieungao -e "CREATE DATABASE project CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic
```
* Browser to `local.project.vn/admin`