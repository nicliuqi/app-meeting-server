from django.urls import path
from meetings.views import GiteeAuthView, GiteeBackView, UserInfoView, MeetingsDataView, CreateMeetingView, \
        UpdateMeetingView, DeleteMeetingView, MeetingDetailView, GroupsView


urlpatterns = [
    path('gitee_login/', GiteeAuthView.as_view()),
    path('gitee_back/', GiteeBackView.as_view()),
    path('user/', UserInfoView.as_view()),
    path('meetingsdata/', MeetingsDataView.as_view()),
    path('meetings/', CreateMeetingView.as_view()),
    path('meeting/<int:pk>/', MeetingDetailView.as_view()),
    path('meeting/action/update/<int:mid>/', UpdateMeetingView.as_view()),
    path('meeting/action/delete/<int:mid>/', DeleteMeetingView.as_view()),
    path('groups/', GroupsView.as_view()),
]
