from rest_framework import routers
from authentication.cognito.views import AuthView
router = routers.DefaultRouter()
router.register(r'auth', AuthView, basename='auth')
urlpatterns = router.urls
