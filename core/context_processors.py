from .models import Favorite


def favorite_count(request):
    if request.user.is_authenticated:
        count = Favorite.objects.filter(user=request.user).count()
        return {"favorite_count": count}
    return {"favorite_count": 0}
