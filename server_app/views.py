from django.shortcuts import render
from django.http import HttpResponse
import subprocess

def server_view(request):
    if request.method == 'POST':
        try:
            subprocess.Popen(['python', 'scripts/server.py'])
            return HttpResponse("Server đang chạy...")
        except Exception as e:
            return HttpResponse(f"Lỗi khi chạy server: {e}")
    return render(request, 'server_app/server.html')
