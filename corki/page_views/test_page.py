from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView


class Home3(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return render(request, 'home3.html')
