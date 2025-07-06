from django.db import models

# Create your models here.

class CarProfile(models.Model):
    user_id = models.CharField(max_length=128)
    make = models.CharField(max_length=64)
    model = models.CharField(max_length=64)
    year = models.PositiveIntegerField()
    resale_pref = models.CharField(max_length=64, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Mod(models.Model):
    car = models.ForeignKey(CarProfile, on_delete=models.CASCADE, related_name='mods')
    name = models.CharField(max_length=128)
    brand = models.CharField(max_length=64, blank=True, null=True)
    status = models.CharField(max_length=16, choices=[("installed", "Installed"), ("planned", "Planned")])
    install_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    source_link = models.URLField(blank=True, null=True)


class Symptom(models.Model):
    car = models.ForeignKey(CarProfile, on_delete=models.CASCADE, related_name='symptoms')
    description = models.TextField()
    severity = models.CharField(max_length=16, choices=[("low", "Low"), ("medium", "Medium"), ("high", "High")], blank=True, null=True)
    reported_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)
    resolution_notes = models.TextField(blank=True, null=True)


class MaintenanceLog(models.Model):
    car = models.ForeignKey(CarProfile, on_delete=models.CASCADE, related_name='maintenance_logs')
    title = models.CharField(max_length=128)
    description = models.TextField()
    date = models.DateField()
    cost = models.FloatField(blank=True, null=True)


class BuildGoal(models.Model):
    car = models.ForeignKey(CarProfile, on_delete=models.CASCADE, related_name='goals')
    goal_type = models.CharField(max_length=64)
    priority = models.PositiveIntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    