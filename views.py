from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse
from Chains_Test.models import Experiment
from django.template import Context, loader


def home(request):
    experiment_list = Experiment.objects.all()
    t = loader.get_template('experiment/index.html')
    c = Context({
        'experiment_list': experiment_list
    })
    return HttpResponse(t.render(c))
