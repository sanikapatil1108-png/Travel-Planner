from django.db import models
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.utils import timezone

class Destination(models.Model):
    name = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='destinations/')
    price_range = models.CharField(max_length=50)
    rating = models.DecimalField(max_digits=2, decimal_places=1)
    slug = models.SlugField(unique=True, blank=True, null=True)  # new field for URL
    tag = models.CharField(max_length=50, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name}, {self.country}"

class Itinerary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='itineraries')
    destinations = models.ManyToManyField('Destination', related_name='itineraries')
    name = models.CharField(max_length=100)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_cost(self):
        return sum(day.total_cost for day in self.days.all())

    def __str__(self):
        return f"{self.name} by {self.user.username}"
    
class Review(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    destination = models.ForeignKey(
        'Destination',
        related_name='reviews',
        on_delete=models.CASCADE
    )
    rating = models.PositiveIntegerField()
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.destination.name} ({self.rating})"
    
class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "destination")

    def __str__(self):
        return f"{self.user.username} - {self.destination.name}"
    
class ItineraryDay(models.Model):
    itinerary = models.ForeignKey(Itinerary, on_delete=models.CASCADE, related_name="days")
    day_number = models.PositiveIntegerField(default=1)  # <-- add default
    date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        # Auto-calculate day_number based on existing days in this itinerary
        if self.pk is None and self.day_number == 1:
            last_day = ItineraryDay.objects.filter(itinerary=self.itinerary).order_by('-day_number').first()
            self.day_number = last_day.day_number + 1 if last_day else 1

        # Auto-set date based on itinerary start date
        if self.itinerary.start_date and not self.date:
            self.date = self.itinerary.start_date + timezone.timedelta(days=self.day_number-1)

        super().save(*args, **kwargs)

    @property
    def total_cost(self):
        return sum(activity.cost or 0 for activity in self.activities.all())

    def __str__(self):
        return f"Day {self.day_number} of {self.itinerary.name}"
    
class Activity(models.Model):
    day = models.ForeignKey(ItineraryDay, on_delete=models.CASCADE, related_name="activities")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    time = models.TimeField(null=True, blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.day.itinerary.name} - Day {self.day.day_number})"
