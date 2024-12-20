from django.shortcuts import render
from django.http import HttpResponse
import subprocess

def client_view(request):
    if request.method == 'POST':
        server_ip = request.POST.get('server_ip')  # Lấy địa chỉ IP từ form
        try:
            # Chạy client.py và truyền địa chỉ IP
            subprocess.Popen(['python', 'scripts/client.py', server_ip])
            return HttpResponse(f"Client đang kết nối đến server {server_ip}...")
        except Exception as e:
            return HttpResponse(f"Lỗi khi chạy client: {e}")
    return render(request, 'client_app/client.html')
