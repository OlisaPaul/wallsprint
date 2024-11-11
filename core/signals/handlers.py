from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import Group
from ..models import ExtendedGroup

@receiver(post_save, sender=Group)
def create_extended_group(sender, instance, **kwargs):
    print("Called")
    if kwargs['created']:
        ExtendedGroup.objects.create(group=instance)
