import json

from django.forms.models import model_to_dict

from apps.accounts.models import User

rows = []
for user in User.objects.filter(is_staff=True):
    data = model_to_dict(user, exclude=["id", "groups", "user_permissions"])
    data["password"] = user.password
    rows.append({k: (str(v) if v is not None and not isinstance(v, (bool, int, str)) else v) for k, v in data.items()})
with open("/home/ubuntu/v1dump/staff.json", "w", encoding="utf-8") as out:
    json.dump(rows, out, ensure_ascii=False, default=str)
print("exported", len(rows))
