# ملاعب الكأس — Alkas Sports City Management

نظام إدارة متكامل لمدينة ملاعب ومنشأة رياضية، مبني بـ Flask/Python وPostgreSQL مع تصميم Modular Monolith.

## النطاق

الحجز بالوقت مع ملعب واحد أو عدة ملاعب، أكثر من فترة في الطلب الواحد، حزم موارد، Hold مؤقت، عدّاد انتهاء، فحص توافر، Quote، منع تعارض PostgreSQL، قائمة انتظار، إلغاء، وسياسة استرجاع.

المسار المالي والتشغيلي:

Booking → Invoice → Payment → Accounting → Notification → Realtime Dashboard

المالية: الفواتير، المدفوعات، الصناديق والورديات، شجرة الحسابات، القيود المزدوجة، الفترات المالية، الإقفال، الاسترجاع والقيود العكسية، التقارير.

الموارد والموظفون: الملاعب والمناطق والرياضات، حزم الموارد، التسعير حسب المورد/الرياضة/اليوم/الساعة/المدة، الصيانة، الموظفون، الحضور، الورديات والرواتب.

الرياضة: العضويات، الباقات، التدريب، البطولات، المباريات، الفرق واللاعبون.

المحتوى والإعلام: الأخبار، العروض، الكوبونات، الحملات الإعلانية، بطاقات الصفحة الرئيسية، البث المباشر، وصفحات الجمهور العامة.

بطاقات الصفحة الرئيسية تدعم النص والصورة والفيديو والرابط والبطاقات المؤقتة مع أولوية ووقت بداية ونهاية.

الإشعارات: مركز داخل التطبيق، قراءة فردية/جماعية، WebSocket فوري، سجل قنوات التسليم وتفضيلات Push/WhatsApp/SMS/Email.

الصلاحيات: RBAC مستقل مع admin.access وصلاحيات منفصلة لكل Module.

التدقيق: Audit Log للمستخدم والعملية والكيان والمعرف والحالة وIP وUser-Agent.

## الهيكل

app/ يحتوي على تطبيقات accounting, bookings, cashier, closing, customers, employees, inventory, invoices, live, maintenance, memberships, news, notifications, offers, packages, payments, payroll, policies, pricing, public, reports, resources, shifts, staff, suppliers, teams, tournaments, training, users, settings. وapp/models/ أصبح طبقة compatibility/re-export فقط.

القاعدة المعمارية: Route → Service → Domain/Event → Persistence

## PostgreSQL وFlask-Migrate

مجلد migrations موجود ويحتوي baseline revision. على خادم جديد:

cd /home/root/projects/alkas
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
ثم اضبط DATABASE_URL وSECRET_KEY.

بعدها:

flask --app wsgi db upgrade
flask --app wsgi create-admin --username admin --password 'CHANGE_THIS'
flask --app wsgi seed-demo

بعد تعديل Models:

flask --app wsgi db migrate -m 'describe the schema change'
flask --app wsgi db upgrade

تنظيف الحجوزات المؤقتة:

flask --app wsgi expire-holds

## PWA

الـManifest أصبح ديناميكيًا من إعدادات الموقع، والـService Worker يوفر shell أساسيًا للعمل دون اتصال. الهوية والألوان يمكن تغييرها من الإعدادات مع زيادة asset_version تلقائيًا.

## CI

GitHub Actions يثبت Python 3.12، يشغل PostgreSQL 16، ينفذ compileall، ثم flask db upgrade ثم pytest.

## ملاحظة عن الـbaseline

baseline غير هدّام: ينشئ metadata على قاعدة جديدة ولا ينفذ drop على قاعدة موجودة. بعد اعتماده يجب أن تمر التغييرات اللاحقة عبر migrations جديدة قابلة للمراجعة.