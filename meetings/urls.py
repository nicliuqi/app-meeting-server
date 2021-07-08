from django.urls import path
from meetings.views import LoginView, GroupMembersView, NonGroupMembersView, SigsView, GroupUserAddView, \
        GroupUserDelView, UpdateUserInfoView, CreateMeetingView, MeetingsListView, MeetingDetailView, UserGroupView, \
        UserInfoView, CollectMeetingView, CollectionDelView, MyCollectionsView, MyMeetingsView, CancelMeetingView, \
        HandleRecordView, GroupsView, FeedbackView, ParticipantsView


urlpatterns = [
    path('login/', LoginView.as_view()),  # 登录
    path('users_include/', GroupMembersView.as_view()),  # 组成员
    path('users_exclude/', NonGroupMembersView.as_view()),  # 非组成员
    path('sigs/', SigsView.as_view()),  # sigs列表
    path('groupuser/action/new/', GroupUserAddView.as_view()),  # 批量添加成员
    path('groupuser/action/del/', GroupUserDelView.as_view()),  # 批量删除成员
    path('user/<int:pk>/', UpdateUserInfoView.as_view()),  # 修改用户信息
    path('usergroup/<int:pk>/', UserGroupView.as_view()),  # 用户的组信息
    path('userinfo/<int:pk>/', UserInfoView.as_view()),  # 查询用户信息
    path('meetings/', CreateMeetingView.as_view()),  # 预定会议
    path('meeting/<int:mmid>/', CancelMeetingView.as_view()),  # 取消会议
    path('meetings/<int:pk>/', MeetingDetailView.as_view()),  # 会议详情
    path('meetingslist/', MeetingsListView.as_view()),  # 会议列表
    path('collect/', CollectMeetingView.as_view()),  # 收藏会议
    path('collect/<int:pk>/', CollectionDelView.as_view()),  # 取消收藏会议
    path('collections/', MyCollectionsView.as_view()),  # 我收藏的会议
    path('mymeetings/', MyMeetingsView.as_view()),  # 我预定的会议
    path('handlerecord/', HandleRecordView.as_view()),  # 录像处理
    path('groups/', GroupsView.as_view()),  # 组列表
    path('feedback/', FeedbackView.as_view()),  # 意见反馈
    path('participants/<int:mid>/', ParticipantsView.as_view()),  # 会议参会者名单
]
