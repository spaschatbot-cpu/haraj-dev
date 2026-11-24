import json

from django.db import connection

from apps.accounts.models import User

assert connection.settings_dict["NAME"] == "haraj2_v2", connection.settings_dict["NAME"]
rows = json.load(open("/home/ubuntu/v1dump/staff.json", encoding="utf-8"))
fields = {f.name: f for f in User._meta.concrete_fields}
made = 0
for row in rows:
    data = {}
    for key, value in row.items():
        field = fields.get(key) or fields.get(key + "_id")
        if field is None or field.is_relation:
            continue
        data[field.name] = field.to_python(value) if value is not None else None
    phone = data.get("phone")
    if phone and User.objects.filter(phone=phone).exists():
        User.objects.filter(phone=phone).update(**{k: v for k, v in data.items() if k != "phone"})
        print("updated existing", phone[-4:])
    else:
        User.objects.create(**data)
        made += 1
print("created", made, "staff now", User.objects.filter(is_staff=True).count())
