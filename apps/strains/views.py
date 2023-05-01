from django.shortcuts import render, get_object_or_404
from .models import Strain
from django.core.paginator import Paginator


def strain_detail(request, slug):
    strain = get_object_or_404(Strain, slug=slug)
    context = {'strain': strain}
    return render(request, 'strain_detail.html', context)


def strain_list(request):
    strains = Strain.objects.filter(active=True).order_by('name')
    paginator = Paginator(strains, 9)

    page = request.GET.get('page')
    strains_page = paginator.get_page(page)

    context = {'strains': strains_page}
    return render(request, 'strain_list.html', context)
