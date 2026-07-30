from django import forms
from .models import Itinerary, Destination, Review, Activity
from .models import ItineraryDay

class ItineraryForm(forms.ModelForm):
    destinations = forms.ModelMultipleChoiceField(
        queryset=Destination.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )
    class Meta:
        model = Itinerary
        fields = ["name", "start_date", "end_date", "destinations"]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
        }

class ReviewForm(forms.ModelForm):
    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        widget=forms.RadioSelect(choices=[(i, "⭐"*i) for i in range(1,6)])
    )
    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "comment": forms.Textarea(attrs={
                "rows":4, 
                "class":"border rounded px-2 py-1", 
                "placeholder":"Write your review..."
            }),
        }

    def clean_rating(self):
        rating = self.cleaned_data.get("rating")
        if rating < 1 or rating > 5:
            raise forms.ValidationError("Rating must be between 1 and 5 stars.")
        return rating

    def clean_comment(self):
        comment = self.cleaned_data.get("comment")
        if not comment or comment.strip() == "":
            raise forms.ValidationError("Comment cannot be empty.")
        return comment
    
class ItineraryDayForm(forms.ModelForm):
    class Meta:
        model = ItineraryDay
        fields = ['notes']
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter day notes...', 'class': 'w-full border rounded p-2 mb-3 resize-none'}),
        }

class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ["title", "description", "time", "cost"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 2}),
            "time": forms.TimeInput(attrs={"type": "time"}),
            "cost": forms.NumberInput(attrs={"step": "0.01", "placeholder": "Cost (optional)"}),
        }