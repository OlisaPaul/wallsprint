from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import Group
from store.models import Customer
from ..models import ExtendedGroup

@receiver(post_save, sender=Group)
def create_extended_group(sender, instance, **kwargs):
    print("Called")
    if kwargs['created']:
        ExtendedGroup.objects.create(group=instance)

@receiver(post_delete, sender=Customer)
def delete_associated_user(sender, instance, **kwargs):
    if instance.user:
        instance.user.delete()