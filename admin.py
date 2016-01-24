from django.contrib import admin
from Chains_Test.models import Experiment
from Chains_Test.models import Overlay
from Chains_Test.models import Node

# Register your models here.


class ExperimentAdmin(admin.ModelAdmin):
    pass

admin.site.register(Experiment, ExperimentAdmin)

admin.site.register(Node)


class NodeInline(admin.StackedInline):
    model = Overlay.nodes.through
    extra = 3


class OverlayAdmin(admin.ModelAdmin):
    inlines = [NodeInline]

admin.site.register(Overlay, OverlayAdmin)


class NodeAdmin(admin.ModelAdmin):
    list_display = ('name', 'ip')
