# هندسة ملاعب الكأس

## 1. حدود النظام

Alkas هو Modular Monolith في المرحلة الأولى. كل Domain مستقل داخليًا، مع Service Layer واضحة، ثم يمكن استخراج أي Domain إلى خدمة مستقلة عندما يظهر احتياج حقيقي.

## 2. المجالات

- auth / users / permissions
- customers / CRM
- venues / zones / sports / resources
- bookings / availability / holds / waitlists
- pricing / discounts / memberships / packages
- payments / invoices / refunds
- cashier / shifts / closing
- accounting / chart of accounts / journal / ledger
- employees / HR / attendance / payroll
- tournaments / teams / matches / standings
- training / coaches / lessons
- inventory / suppliers
- maintenance / resource blocking
- content / announcements / offers / media
- notifications / push / WhatsApp / SMS / email
- live / streams / public events
- reports / exports / saved reports
- audit / system settings

## 3. قاعدة الحجز

Booking هو العملية التجارية، وBookingAllocation هو تخصيص زمني لمورد. لذلك يمكن لعملية واحدة أن تضم أكثر من ملعب.

المورد Resource هو ما يمكن حجزه. ResourceBundle هو مجموعة موارد يمكن حجزها كعملية واحدة مثل جميع ملاعب كرة القدم.

حالات الحجز والحالة المالية منفصلتان عمدًا.

Booking:
hold -> pending -> confirmed -> checked_in -> in_progress -> completed
ومسارات الإلغاء/no_show مستقلة.

Payment:
unpaid -> partially_paid -> paid
والاسترجاع يملك دورة مستقلة.

## 4. منع التعارض

لا يعتمد منع التعارض على JavaScript. PostgreSQL يملك Exclusion Constraint على resource_id + الزمن في booking_allocations. التطبيق يعطي تجربة سريعة، وقاعدة البيانات هي الحكم النهائي.

## 5. المحاسبة

كل عملية مالية لها مصدر تجاري واضح. مثال:
Customer -> Booking -> Invoice -> Payment -> JournalEntry.

القيود المرحلة لا تعدل مباشرة. التصحيح المحاسبي يتم بعكس القيد ثم إنشاء قيد صحيح.

## 6. الإشعارات

الأحداث التجارية تبث من Services/Domain Events. طبقة notifications هي التي تحدد القناة والمحتوى والمستلم.

الـSocket.IO مقسم إلى غرف المستخدم وغرفة العمليات، ولا يرسل تفاصيل الحجوزات الخاصة للعملاء العموميين.

## 7. الإعدادات

الهوية البصرية من قاعدة البيانات:
- الاسم والشعار والأيقونة
- الألوان
- نصف قطر البطاقات
- أسلوب البطاقات
- الخط
- كثافة الواجهة
- الحركة
- خيارات لوحة الإعلانات
- النصوص الرئيسية

تتغير دون تعديل CSS أو إعادة بناء الواجهة. يتم تغيير asset_version لتفادي كاش الأصول القديمة.

## 8. التوسع

المرحلة الحالية تجهز النواة. الوحدات الأكبر تضاف على نفس العقود:
Route -> Service -> Event -> Persistence.

لا يتم وضع SQL أو محاسبة أو سياسات التسعير داخل Jinja/JavaScript.
