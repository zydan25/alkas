# نشر ملاعب الكأس

الافتراض الحالي للنشر هو:
- المسار: /home/root/projects/alkaas
- المنفذ الداخلي: 4041
- النطاق: alkaas.alattab.site

إن كان النطاق الفعلي مختلفًا، عدّل server_name في ملف Nginx وSOCKETIO_CORS في .env قبل التشغيل.

## PostgreSQL

sudo -u postgres psql -c "DO \\$\$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'alkaas') THEN CREATE ROLE alkaas LOGIN PASSWORD 'alkaas'; ELSE ALTER ROLE alkaas WITH LOGIN PASSWORD 'alkaas'; END IF; END \\$\$;"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='alkaas'" | grep -q 1 || sudo -u postgres createdb -O alkaas alkaas
sudo -u postgres psql -c "ALTER DATABASE alkaas OWNER TO alkaas;"

## التطبيق

cd /home/root/projects
git clone https://github.com/zydan25/alkas.git alkaas
cd alkaas
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env

اضبط DATABASE_URL إلى:
postgresql+psycopg://alkaas:alkaas@127.0.0.1:5432/alkaas

ثم:
flask --app wsgi db upgrade
flask --app wsgi create-admin --username admin --password 'ضع-كلمة-مرور-قوية'
flask --app wsgi seed-demo

## PM2

sudo npm install -g pm2
pm2 start deploy/ecosystem.config.cjs
pm2 save
pm2 startup systemd

نفّذ الأمر الذي يطبعه pm2 startup.

## Nginx

sudo mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
sudo ln -sf /home/root/projects/alkaas/deploy/nginx/alkaas.alattab.site.conf /etc/nginx/sites-enabled/alkaas.alattab.site.conf
sudo nginx -t
sudo systemctl reload nginx
sudo certbot --nginx -d alkaas.alattab.site

## تحرير الحجوزات المؤقتة

(crontab -l 2>/dev/null; echo "* * * * * /home/root/projects/alkaas/venv/bin/flask --app /home/root/projects/alkaas/wsgi.py expire-holds >/dev/null 2>&1") | crontab -

## التحقق

curl -I http://127.0.0.1:4041/health
pm2 status
sudo nginx -t

اسم مستخدم/قاعدة/كلمة مرور PostgreSQL كلها alkaas كما طُلب، لكنها بيانات اعتماد بسيطة ويُفضّل تغييرها في الإنتاج.