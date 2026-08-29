# حراج واحد v2

منصة مزادات السيارات — النسخة الثانية. خلفية Django/DRF وتطبيق Flutter،
مبنية حول دفتر فلوس بقيد مزدوج.

الخطة الكاملة ومبرّرات التصميم في [docs/PLAN.md](docs/PLAN.md).

## التشغيل محلياً

يتطلب Python 3.13 و[uv](https://docs.astral.sh/uv/) وPostgreSQL 16+ وRedis.

```bash
cd backend
cp .env.example .env      # ثم املأ SECRET_KEY وDATABASE_URL
uv sync
uv run python manage.py migrate
uv run python manage.py runserver
```

الاختبارات:

```bash
cd backend && uv run pytest
```

## البنية

```
backend/
  config/            إعدادات المشروع، celery، المسارات
  apps/
    accounts/        المستخدمون والشركات
    money/           الدفتر — الحساب، المعاملة، القيد، الحجز، الفاتورة
    odoo/            الحدود مع أودو: وارد، صادر، ربط العملاء، مقارنة الأرصدة
    auctions/        المزادات والمركبات
    bidding/         المزايدات وسجلّ الرفض
    notifications/   الرسائل الصادرة للعملاء
mobile/              تطبيق Flutter
docs/                الخطة وقرارات التصميم
```

## القاعدة الوحيدة التي لا تُكسر

لا شيء يكتب في الدفتر إلا `apps.money.services.post`. لا شاشة، ولا مهمة
خلفية، ولا لوحة إدارة تُنشئ قيداً بنفسها. كل ما عدا ذلك يُبنى فوقها.
