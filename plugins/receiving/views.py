"""HTTP face of the receiving engine. Token-auth only; no session, no CSRF."""
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.authentication import ApiTokenAuthentication


class _View(APIView):
    authentication_classes = [ApiTokenAuthentication]
    permission_classes = [IsAuthenticated]


class PingView(_View):
    def get(self, request):
        return Response({"ok": True, "plugin": "receiving", "user": request.user.username})
