from rest_framework import routers
from authentication.cognito.views import AuthView
router = routers.DefaultRouter()
router.register(r'auth', AuthView, base_name='auth')
urlpatterns = router.urls
