from django.shortcuts import render
from django.http import HttpResponse

def home(request):
    blog = {"title": "45", "number": 5}
    
    # પેહલો આર્ગ્યુમેન્ટ 'request' હોવો જોઈએ અને બીજો આર્ગ્યુમેન્ટ HTML ફાઈલનું નામ
    return render(request, "home.html", {"blog": blog})