from django.urls import include, path, re_path
from frontend_api import views
from frontend_api.router import urlpatterns as frontend_api
from django.conf.urls import url

urlpatterns = [
    url(r'^', include(frontend_api)),
    re_path(r'^users/(?P<pk>[^/.]+)/status/$',
            views.UserViewSet.as_view({'patch': 'patch_status'}),
            name='user-status'),

    re_path(r'^users/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            views.UserViewSet.as_view({'get': 'retrieve_related', 'patch': 'patch_related'}),
            name='user-related'),

    re_path(r'^users/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=views.UserRelationshipView.as_view(),
            name='user-relationships'
            ),

    re_path(r'^companies/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            views.CompanyViewSet.as_view({'get': 'retrieve_related', 'patch': 'patch_related'}),
            name='company-related'),

    re_path(r'^companies/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=views.CompanyRelationshipView.as_view(),
            name='company-relationships'
            ),

    # Invite/resend_invite
    re_path(r'^accounts/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            views.AccountViewSet.as_view({'get': 'retrieve_related', 'patch': 'patch_related'}),
            name='account-related'),

    re_path(r'^accounts/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=views.AccountRelationshipView.as_view(),
            name='account-relationships'
            ),

    url(r'^accounts/(?P<pk>[^/.]+)/$',
        views.AccountViewSet.as_view({'get': 'retrieve'}),
        name='useraccount-detail'),

    re_path(r'^user_accounts/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            views.UserAccountViewSet.as_view({'get': 'retrieve_related', 'patch': 'patch_related'}),
            name='user-account-related'),

    re_path(r'^user_accounts/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=views.UserAccountRelationshipView.as_view(),
            name='user-account-relationships'
            ),

    re_path(r'^sub_user_accounts/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            views.SubUserAccountViewSet.as_view({'get': 'retrieve_related', 'patch': 'patch_related'}),
            name='sub-user-account-related'),

    re_path(r'^sub_user_accounts/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=views.SubUserAccountRelationshipView.as_view(),
            name='sub-user-account-relationships'
            ),
    re_path(r'^sub_user_permissions/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            views.SubUserPermissionViewSet.as_view({'get': 'retrieve_related', 'patch': 'patch_related'}),
            name='sub-user-permission-related'),

    re_path(r'^sub_user_permissions/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=views.SubUserPermissionRelationshipView.as_view(),
            name='sub-user-permission-relationships'
            ),

    re_path(r'^admin_user_accounts/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            views.AdminUserAccountViewSet.as_view({'get': 'retrieve_related', 'patch': 'patch_related'}),
            name='admin-user-account-related'),
    re_path(r'^admin_user_accounts/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=views.AdminUserAccountRelationshipView.as_view(),
            name='admin-user-account-relationships'
            ),
    re_path(r'^admin_user_permissions/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            views.AdminUserPermissionViewSet.as_view({'get': 'retrieve_related', 'patch': 'patch_related'}),
            name='admin-user-permission-related'),

    re_path(r'^admin_user_permissions/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=views.AdminUserPermissionRelationshipView.as_view(),
            name='admin-user-permission-relationships'
            ),

    re_path(r'^shareholders/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            views.ShareholderViewSet.as_view({'get': 'retrieve_related', 'patch': 'patch_related'}),
            name='shareholder-related'),

    re_path(r'^shareholders/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=views.ShareholderRelationshipView.as_view(),
            name='shareholder-relationships'
            ),

    re_path(r'^address/(?P<pk>[^/.]+)/(?P<related_field>\w+)/$',
            views.AddressViewSet.as_view({'get': 'retrieve_related'}),
            name='address-related'),

    re_path(r'^address/(?P<pk>[^/.]+)/relationships/(?P<related_field>[^/.]+)$',
            view=views.AddressRelationshipView.as_view(),
            name='address-relationships'
            ),

    path('presigned-urls/', view=views.PreSignedUrlView.as_view(), name="presigned-urls"),
    path('profiles/<pk>/', view=views.ProfileView.as_view(), name='profiles'),
]
