# sistema/signals.py
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import (
    SistemaUsuario, SistemaEvento, SistemaAsistencia,
    SistemaLectura, SistemaPago, SistemaMedidor, SistemaTarifa
)

@receiver(pre_save, sender=SistemaUsuario)
@receiver(pre_save, sender=SistemaEvento)
@receiver(pre_save, sender=SistemaAsistencia)
@receiver(pre_save, sender=SistemaLectura)
@receiver(pre_save, sender=SistemaPago)
@receiver(pre_save, sender=SistemaMedidor)
@receiver(pre_save, sender=SistemaTarifa)
def update_timestamp(sender, instance, **kwargs):
    instance.updated_at = timezone.now()
