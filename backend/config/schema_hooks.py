"""وسمُ كل عملية بالمورد الذي تخصّه، مشتقّاً من مسارها.

**لماذا هذا موجود:** بلا وسمٍ صريح يضع drf-spectacular العمليةَ تحت أول جزءٍ من
المسار — فوقعت العمليات الإحدى والأربعون كلُّها تحت وسمٍ واحد اسمه `v1`. والوسم
ليس زينةً في العقد: مولّد عميل Dart يصنع صنفاً لكل وسم، فوَسمٌ واحد يعني صنفاً
واحداً ضخماً اسمه `V1Api` بدل تسعة أصناف يقرأها التطبيق بأسمائها
(`AuthApi`، `WalletApi`، `BidsApi`…). أي أن العقد كان يُملي على كل عميلٍ يستهلكه
شكلاً لا يقول شيئاً عن الموارد.

**والاشتقاق من المسار لا قائمةٌ مكتوبة بيد:** قائمةٌ ثانية تُصان تنحرف عن
المسارات يوم يُضاف مسار — وتنحرف صامتةً، لأن لا شيء يقارنها بها. المسار هو
المصدر، والوسمُ اسمُ المورد فيه.
"""

from drf_spectacular.openapi import AutoSchema

#: ما بعده هو المورد.
_PREFIX = "/api/v1/"


class ResourceTaggedAutoSchema(AutoSchema):
    """`AutoSchema` تسمّي الوسمَ باسم المورد في المسار.

    وسمٌ كُتب صراحةً بـ`@extend_schema(tags=[...])` يفوز دائماً: `super()` هي من
    تقرأ التصريح، ولا نتجاوزها إلا حين تُرجع الوسمَ الافتراضيَّ المشتقَّ من أول
    جزءٍ في المسار — وهو `v1` هنا، أي «لا وسم». فهذا يملأ فراغاً ولا ينقض قراراً.
    """

    def get_tags(self) -> list[str]:
        tags = super().get_tags()
        if tags != ["v1"]:
            return tags
        resource = _resource_of(self.path)
        return [resource] if resource else tags


def _resource_of(path: str) -> str | None:
    """اسمُ المورد في هذا المسار، أو `None` إن كان خارج `/api/v1/`."""
    if not path.startswith(_PREFIX):
        return None
    parts = [p for p in path[len(_PREFIX) :].split("/") if p and not p.startswith("{")]
    return parts[0] if parts else None


#: غلافُ الخطأ الموحَّد، بشكله في `apps/core/exceptions.envelope`.
_ERROR_ENVELOPE = {
    "type": "object",
    "description": (
        "غلافُ كل خطأ تردّ به هذه الواجهة — بلا استثناء. يُبنى في "
        "`apps.core.exceptions.envelope` وحدها، فلا عرضٌ يخترع شكلاً ثانياً."
    ),
    "required": ["error"],
    "properties": {
        "error": {
            "type": "object",
            "required": ["code", "message", "detail"],
            "properties": {
                "code": {
                    "type": "string",
                    "description": (
                        "رمزٌ ثابت يفرّق سببَ الرفض عن سببٍ آخر. **هو ما "
                        "يُفرَّع عليه في العميل**، لا الرسالة ولا رمز HTTP."
                    ),
                },
                "message": {
                    "type": "string",
                    "description": (
                        "جملةٌ عربية جاهزة للعرض كما هي. لا يُترجمها العميل "
                        "ولا يستبدلها: نصٌّ واحد للسبب الواحد (المادة ٤-٥)."
                    ),
                },
                "detail": {
                    "type": "object",
                    "additionalProperties": True,
                    "description": (
                        "حقولٌ تخصّ هذا الرفض بعينه — مبلغٌ قائم، حقلٌ ناقص. "
                        "كائنٌ فارغ حين لا تفصيل، لا `null`."
                    ),
                },
            },
        }
    },
}


def state_enum_defaults_in_prose(result, generator, request, public):
    """ينقل القيمة الافتراضية لحقلٍ تعداديّ من `default` إلى وصفه.

    **العطل:** حقلٌ نوعُه `$ref` إلى تعداد ومعه `default: login` يجعل مولّد
    عميل Dart يكتب `SendCodePurposeEnum? purpose = login` — اسمَ العضو بلا اسم
    تعداده، فلا يُصرَّف: «Undefined name 'login'». والعميل لا يُبنى أصلاً،
    فيسقط التطبيق كلُّه على حقلين اثنين (`purpose` و`method`).

    **ولماذا النقل لا الحذف:** الافتراضيّ حقيقةٌ عن الخادم — من لم يرسل
    `purpose` يُعامَل على أنه `login`. حذفُه صمتاً يجعل العقد يُخفي سلوكاً
    قائماً، وذلك أسوأ من فقدِ حقلٍ يقرأه مولّد. فيبقى مكتوباً حيث يقرأه
    إنسانٌ ومولّدُ توثيق، ويغيب حيث يُنتج شيفرةً لا تُصرَّف.

    ولا يمسّ الحقول العادية: `default` على نصٍّ أو رقمٍ يُترجَم سليماً،
    والمسّ به يفقد ما لا سبب لفقده.
    """
    del generator, request, public

    for schema in _schemas_in(result):
        default = schema.get(_DEFAULT)
        if default is None or not _is_enum_ref(schema):
            continue
        schema.pop(_DEFAULT)
        note = f"الافتراضيّ حين لا يُرسَل الحقل: `{default}`."
        description = schema.get("description")
        schema["description"] = f"{description}\n\n{note}" if description else note
    return result


_DEFAULT = "default"


def _is_enum_ref(schema: dict) -> bool:
    """هل نوعُ هذا الحقل إشارةٌ إلى تعداد (مباشرةً أو داخل `oneOf`/`allOf`)."""
    if "$ref" in schema:
        return True
    for key in ("oneOf", "allOf", "anyOf"):
        members = schema.get(key)
        if isinstance(members, list) and any(
            isinstance(member, dict) and "$ref" in member for member in members
        ):
            return True
    return False


def _schemas_in(result: dict):
    """كل مخطط حقلٍ في المكوّنات وفي معاملات المسارات."""
    for component in result.get("components", {}).get("schemas", {}).values():
        properties = component.get("properties")
        if isinstance(properties, dict):
            yield from (p for p in properties.values() if isinstance(p, dict))
    for operations in result.get("paths", {}).values():
        for operation in operations.values():
            if not isinstance(operation, dict):
                continue
            for parameter in operation.get("parameters", []) or []:
                schema = parameter.get("schema")
                if isinstance(schema, dict):
                    yield schema


def describe_the_error_envelope(result, generator, request, public):
    """خطّافُ ما بعد المعالجة: يصف غلافَ الخطأ ويربطه بكل عملية.

    **لماذا هذا موجود:** الغلاف قائمٌ في الكود منذ الفيز 007 — «ظرفٌ واحد لكل
    خطأ، فللتطبيق فرعٌ واحد يكتبه» — ولم يكن في المخطط سطرٌ واحد عنه. فكان
    العقد يصف طريق النجاح وحده، وكلُّ عميلٍ يُولَّد منه يجهل شكلَ الرفض تماماً
    ويُعيد اكتشافه بيد. وهذا ما كان: التطبيق يفكّ الغلاف بنموذجٍ كتبه لنفسه.

    والوصف هنا لا في كل عرض: الغلاف واحدٌ لكل النقاط، وكتابته في واحدةٍ
    وأربعين موضعاً يعني واحداً وأربعين موضعاً يُنسى فيها.
    """
    del generator, request, public

    components = result.setdefault("components", {}).setdefault("schemas", {})
    components["ApiErrorEnvelope"] = _ERROR_ENVELOPE

    reference = {"$ref": "#/components/schemas/ApiErrorEnvelope"}
    for operations in result.get("paths", {}).values():
        for operation in operations.values():
            if not isinstance(operation, dict):
                continue
            responses = operation.setdefault("responses", {})
            # `default` لا رمزاً بعينه: الرموز تختلف بحسب الرفض (409 لقاعدة
            # عمل، 404 لصفٍّ لا يُرى، 429 لحدّ معدّل) والغلاف لا يختلف. ووصفُه
            # `default` يقول ذلك بالضبط بدل تعداد رموزٍ ينقص واحدها يوماً.
            responses.setdefault(
                "default",
                {
                    "description": "رفضٌ أو خطأ، بالغلاف الموحَّد.",
                    "content": {"application/json": {"schema": reference}},
                },
            )
    return result
