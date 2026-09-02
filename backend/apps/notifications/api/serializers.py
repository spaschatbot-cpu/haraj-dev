"""What a device registration takes. T620.

There is no `user` field, and its absence is the whole design. In v1 the client
sent the account id alongside the token, so anybody could point somebody else's
push notifications at their own handset — and the bid alerts that go out on this
channel say what a person is bidding on.
"""

from __future__ import annotations

from rest_framework import serializers


class DeviceRegistrationSerializer(serializers.Serializer):
    """One handset, identified by the token its push provider issued."""

    #: FCM tokens are long and opaque. Bounded because an unbounded text field
    #: reachable by an authenticated caller is a way to fill a table.
    token = serializers.CharField(max_length=255, trim_whitespace=True)

    platform = serializers.ChoiceField(choices=["android", "ios", "web"])

    def validate(self, attrs: dict) -> dict:
        unknown = set(self.initial_data) - set(self.fields)
        if unknown:
            # `user` and `user_id` land here, which is the point: a client that
            # tries to name an account is told plainly that it may not, rather
            # than having the field silently dropped and believing it worked.
            raise serializers.ValidationError(
                {name: "حقل غير معروف." for name in sorted(unknown)}
            )
        return attrs


class DeviceSerializer(serializers.Serializer):
    """A registered handset, as its owner sees it."""

    id = serializers.IntegerField()
    platform = serializers.CharField()
    created_at = serializers.DateTimeField()

    #: The token itself is never returned. It is a credential for sending to
    #: this handset, and a response that carries it puts it in a log, a proxy
    #: cache and a client's crash report.
    token_tail = serializers.CharField(help_text="آخر ستة أحرف، للتمييز فقط")
