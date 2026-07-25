
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from .models import Itinerary, Destination, Favorite, ItineraryDay
from .forms import ItineraryForm, ReviewForm
from .utils import get_filtered_destinations, get_average_rating
from .forms import ItineraryDayForm, ActivityForm
from .models import Activity, Review
from django.db.models import Avg
from django.core.mail import send_mail
from django.utils import timezone
from datetime import timedelta
# ---------------------------
# AUTHENTICATION VIEWS
# ---------------------------
def login_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect("home")
        messages.error(request, "Invalid username or password")

    return render(request, "core/login.html")


def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("home")


def signup_view(request):
    if request.user.is_authenticated:
        return redirect("home")

    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            messages.error(request, "Passwords do not match")
            return redirect("signup")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("signup")

        user = User.objects.create_user(username=username, email=email, password=password1)
        user.save()
        messages.success(request, "Account created successfully. Please login.")
        return redirect("login")

    return render(request, "core/signup.html")


@login_required(login_url="login")
def profile_view(request):
    total_trips = request.user.itineraries.count()
    total_destinations = Destination.objects.filter(itineraries__user=request.user).distinct().count()
    avg_rating = Review.objects.filter(user=request.user).aggregate(Avg('rating'))['rating__avg'] or 0.0

    context = {
        "user": request.user,
        "total_trips": total_trips,
        "total_destinations": total_destinations,
        "avg_rating": round(avg_rating, 1)
    }
    return render(request, "core/profile.html", context)

@login_required
def send_reminders(request):
    upcoming_itineraries = Itinerary.objects.filter(
        user=request.user,
        start_date__gte=timezone.now().date(),
        start_date__lte=timezone.now().date() + timedelta(days=7)
    )
    if upcoming_itineraries.exists():
        for itinerary in upcoming_itineraries:
            send_mail(
                subject=f"Upcoming Trip Reminder: {itinerary.name}",
                message=f"Hi {request.user.username},\n\nYour trip '{itinerary.name}' is starting on {itinerary.start_date}.\nGet ready!",
                from_email="noreply@travelplanner.com",
                recipient_list=[request.user.email],
            )
        messages.success(request, f"Sent reminders for {upcoming_itineraries.count()} upcoming trips!")
    else:
        messages.info(request, "No trips scheduled in the next 7 days.")
    return redirect('profile')


# ---------------------------
# HOME / DESTINATIONS
# ---------------------------
def home(request):
    query = request.GET.get("search", "")
    if query:
        destinations = Destination.objects.filter(name__icontains=query)
    else:
        destinations = Destination.objects.all()[:3]

    return render(request, "core/home.html", {"destinations": destinations, "query": query})


def destination_list(request):
    destinations = get_filtered_destinations(request.GET)

    countries = Destination.objects.values_list("country", flat=True).distinct()
    price_ranges = ["$", "$$", "$$$"]
    ratings = [4, 3, 2, 1]
    query = request.GET.get("search")

    context = {
        "destinations": destinations,
        "countries": countries,
        "price_ranges": price_ranges,
        "ratings": ratings,
        "selected_country": request.GET.get("country"),
        "selected_price": request.GET.get("price"),
        "selected_rating": request.GET.get("rating"),
        "query": query,
    }
    return render(request, "core/destination_list.html", context)


def destination_detail(request, slug):
    destination = get_object_or_404(Destination, slug=slug)
    average_rating = get_average_rating(destination)
    reviews = destination.reviews.all().order_by("-created_at")

    # Check if the user has favorited this destination
    is_favorite = False
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, destination=destination).exists()

    return render(
        request,
        "core/destination_detail.html",
        {
            "destination": destination,
            "reviews": reviews,
            "average_rating": average_rating,
            "is_favorite": is_favorite,
        },
    )


@login_required
def add_review(request, slug):
    destination = get_object_or_404(Destination, slug=slug)

    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.user = request.user
            review.destination = destination
            review.save()
            messages.success(request, "Your review has been submitted!")
            return redirect("destination_detail", slug=slug)
        messages.error(request, "Please correct the errors below.")
    else:
        form = ReviewForm()

    return render(request, "core/add_review.html", {"form": form, "destination": destination})


# ---------------------------
# ITINERARY VIEWS
# ---------------------------
@login_required
def itinerary_list(request):
    itineraries = Itinerary.objects.filter(user=request.user)
    query = request.GET.get('search', '')
    start_date = request.GET.get('start_date', '')
    
    if query:
        itineraries = itineraries.filter(name__icontains=query)
    if start_date:
        itineraries = itineraries.filter(start_date__gte=start_date)
        
    return render(request, "core/itinerary_list.html", {
        "itineraries": itineraries,
        "query": query,
        "start_date": start_date
    })


@login_required
def itinerary_detail(request, pk):
    itinerary = get_object_or_404(Itinerary, pk=pk, user=request.user)
    return render(request, "core/itinerary_detail.html", {"itinerary": itinerary})


@login_required
def itinerary_create(request):
    destination_id = request.GET.get("destination")
    destination = get_object_or_404(Destination, id=destination_id) if destination_id else None
    user_itineraries = Itinerary.objects.filter(user=request.user)

    if request.method == "POST":
        form_type = request.POST.get("form_type")
        if form_type == "add_existing":
            itinerary_id = request.POST.get("itinerary")
            itinerary = get_object_or_404(Itinerary, id=itinerary_id, user=request.user)
            if destination:
                itinerary.destinations.add(destination)
                messages.success(request, f'"{destination.name}" added to "{itinerary.name}"')
            return redirect("itinerary_list")
        else:
            form = ItineraryForm(request.POST)
            if form.is_valid():
                itinerary = form.save(commit=False)
                itinerary.user = request.user
                itinerary.save()
                form.save_m2m()
                messages.success(request, f'Itinerary "{itinerary.name}" created successfully!')
                return redirect("itinerary_list")
    else:
        form = ItineraryForm(initial={"destinations": [destination]} if destination else None)

    return render(
        request,
        "core/itinerary_create.html",
        {"form": form, "destination": destination, "user_itineraries": user_itineraries},
    )


@login_required
def itinerary_delete(request, pk):
    itinerary = get_object_or_404(Itinerary, pk=pk, user=request.user)
    if request.method == "POST":
        itinerary.delete()
        messages.success(request, f'Itinerary "{itinerary.name}" deleted successfully!')
        return redirect("itinerary_list")
    return render(request, "core/itinerary_confirm_delete.html", {"itinerary": itinerary})

@login_required
def add_favorite(request, destination_id):
    destination = get_object_or_404(Destination, id=destination_id)

    Favorite.objects.get_or_create(
        user=request.user,
        destination=destination
    )

    return redirect("destination_detail", slug=destination.slug)


@login_required
def remove_favorite(request, destination_id):
    destination = get_object_or_404(Destination, id=destination_id)

    Favorite.objects.filter(
        user=request.user,
        destination=destination
    ).delete()

    return redirect("destination_detail", slug=destination.slug)

@login_required
def my_favorites(request):
    favorites = (
        Favorite.objects
        .filter(user=request.user)
        .select_related("destination")
        .order_by("-created_at")
    )

    return render(request, "core/my_favorites.html", {
        "favorites": favorites
    })

@login_required
def add_itinerary_day(request, itinerary_id):
    itinerary = get_object_or_404(Itinerary, id=itinerary_id, user=request.user)
    if request.method == 'POST':
        form = ItineraryDayForm(request.POST)
        if form.is_valid():
            day = form.save(commit=False)
            day.itinerary = itinerary
            day.save()
            return redirect('itinerary_detail', pk=itinerary.id)  # <- change here
    else:
        form = ItineraryDayForm()
    return render(request, 'core/add_itinerary_day.html', {'form': form, 'itinerary': itinerary})

@login_required
def add_activity(request, day_id):
    day = get_object_or_404(ItineraryDay, id=day_id, itinerary__user=request.user)
    if request.method == "POST":
        form = ActivityForm(request.POST)
        if form.is_valid():
            activity = form.save(commit=False)
            activity.day = day
            activity.save()
            return redirect("itinerary_detail", pk=day.itinerary.id)
    else:
        form = ActivityForm()
    return render(request, "core/add_activity.html", {"form": form, "day": day})

@login_required
def edit_activity(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id, day__itinerary__user=request.user)
    if request.method == "POST":
        form = ActivityForm(request.POST, instance=activity)
        if form.is_valid():
            form.save()
            messages.success(request, "Activity updated successfully!")
            return redirect("itinerary_detail", pk=activity.day.itinerary.id)
    else:
        form = ActivityForm(instance=activity)
    return render(request, "core/edit_activity.html", {"form": form, "activity": activity})

@login_required
def delete_activity(request, activity_id):
    activity = get_object_or_404(Activity, id=activity_id, day__itinerary__user=request.user)
    itinerary_id = activity.day.itinerary.id
    if request.method == "POST":
        activity.delete()
        messages.success(request, "Activity deleted successfully!")
        return redirect("itinerary_detail", pk=itinerary_id)
    return render(request, "core/delete_activity_confirm.html", {"activity": activity})