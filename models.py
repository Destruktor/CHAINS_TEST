from django.db import models

# Create your models here.
class SessionData(models.Model):
    data_file = models.FileField(upload_to='/home/citadel_nrhodes/data/data_file')


class Node(models.Model):
    name = models.CharField(max_length = 100)
    ip = models.IPAddressField()
    app_port_num = models.PositiveIntegerField()
    node_port_num = models.PositiveIntegerField()

    def __unicode__(self):
        return self.name


class LatencyGraph(models.Model):
    time_created = models.DateTimeField(auto_now_add=True)


class Overlay(models.Model):
    # Foreign key relations
    latency_graph = models.OneToOneField(LatencyGraph)
    nodes = models.ManyToManyField(Node)


class Experiment(models.Model):
    time_start = models.DateTimeField()
    time_end = models.DateTimeField()
    latency_graph_timeout = models.PositiveIntegerField()
    name = models.CharField(max_length=50)

    # Foreign key relations
    data_file = models.OneToOneField(SessionData)
    overlay = models.ForeignKey(Overlay)


class Delay(models.Model):
    one_way_delay = models.PositiveIntegerField()

    # Foreign Key relations
    latency_graph = models.ForeignKey(LatencyGraph)
    node_1 = models.ForeignKey(Node, related_name='delay_node_1')
    node_2 = models.ForeignKey(Node, related_name='delay_node_2')


class Chains(models.Model):

    # Foreign Key relations
    experiment = models.ManyToManyField(Experiment)


class ChainElement(models.Model):
    order = models.PositiveIntegerField()
    value = models.PositiveIntegerField()

    # Foreign Key relations
    chain = models.ForeignKey(Chains)
    node = models.ForeignKey(Node)
