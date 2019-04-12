from rest_framework import routers
from authentication.cognito.views import AuthView
# from customate.routers import router
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'auth', AuthView, basename='auth')
urlpatterns = router.urls
