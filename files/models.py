from cloudinary.models import CloudinaryField
from django.db import models
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class Image(models.Model):
    # Fields for storing image data
    path = CloudinaryField('image', blank=True, null=True)
    upload_date = models.DateTimeField(auto_now_add=True)

    # Generic Foreign Key fields
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return f"Image for {self.content_object}"
