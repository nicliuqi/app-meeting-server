from django.urls import path
from meetings.views import LoginView, GroupMembersView, NonGroupMembersView, SigsView, GroupUserAddView, \
    GroupUserDelView, UpdateUserInfoView, CreateMeetingView, MeetingsListView, MeetingDetailView, UserGroupView, \
    UserInfoView, CollectMeetingView, CollectionDelView, MyCollectionsView, MyMeetingsView, CancelMeetingView, \
    HandleRecordView, GroupsView, FeedbackView, ParticipantsView, SponsorsView, NonSponsorsView, SponsorsAddView, \
    SponsorsDelView, ActivityCreateView, ActivityUpdateView, DraftUpdateView, WaitingActivities, WaitingActivity, \
    ApproveActivityView, DenyActivityView, ActivityDeleteView, DraftView, ActivitiesListView, ActivityDetailView, \
    DraftsListView, ActivityCollectView, ActivityCollectionsView, ActivityCollectionDelView, ActivityRegisterView, \
    ActivitySignView, MyCountsView, CityMembersView, NonCityMembersView, CitiesView, AddCityView, CityUserAddView, \
    CityUserDelView, UserCityView, RecentActivitiesView, PublishedActivitiesView, WaitingPublishingActivitiesView, \
    RegisteredActivitiesView, ApplicantsInfoView, ApplicantInfoView, ActivityRegistrantsView, CountActivitiesView, \
    TicketView, MeetingsDataView, ActivitiesDataView

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
    path('users_include_city/', CityMembersView.as_view()),  # 城市组成员列表
    path('users_exclude_city/', NonCityMembersView.as_view()),  # 非城市组成员列表
    path('cities/', CitiesView.as_view()),  # 城市列表
    path('city/', AddCityView.as_view()),  # 添加城市
    path('cityuser/action/new/', CityUserAddView.as_view()),  # 批量新增城市组成员
    path('cityuser/action/del/', CityUserDelView.as_view()),  # 批量移除城市组成员
    path('usercity/<int:pk>/', UserCityView.as_view()),  # 查询用户的城市组关系
    path('sponsors/', SponsorsView.as_view()),  # 活动发布者列表
    path('nonsponsors/', NonSponsorsView.as_view()),  # 非活动发布者列表
    path('sponsor/action/new/', SponsorsAddView.as_view()),  # 批量添加活动发布者
    path('sponsor/action/del/', SponsorsDelView.as_view()),  # 批量删除活动发布者
    path('activity/', ActivityCreateView.as_view()),  # 创建活动
    path('activityupdate/<int:pk>/', ActivityUpdateView.as_view()),  # 修改活动
    path('draftupdate/<int:pk>/', DraftUpdateView.as_view()),  # 修改活动草案
    path('waitingactivities/', WaitingActivities.as_view()),  # 待审核列表
    path('waitingactivity/<int:pk>/', WaitingActivity.as_view()),  # 待审核活动
    path('activity/action/approve/<int:pk>/', ApproveActivityView.as_view()),  # 通过审核
    path('activity/action/deny/<int:pk>/', DenyActivityView.as_view()),  # 驳回申请
    path('activity/action/del/<int:pk>/', ActivityDeleteView.as_view()),  # 删除活动
    path('draft/<int:pk>/', DraftView.as_view()),  # 查询、删除活动草案
    path('activities/', ActivitiesListView.as_view()),  # 活动列表
    path('mypublishedactivities/', PublishedActivitiesView.as_view()),  # 我的已发布活动列表
    path('mywaitingactivities/', WaitingPublishingActivitiesView.as_view()),  # 我的待发布活动列表
    path('activity/<int:pk>/', ActivityDetailView.as_view()),  # 活动详情
    path('drafts/', DraftsListView.as_view()),  # 活动草案列表
    path('activity/action/collect/', ActivityCollectView.as_view()),  # 收藏活动
    path('activitycollections/', ActivityCollectionsView.as_view()),  # 活动收藏列表
    path('activity/action/collectdel/<int:pk>/', ActivityCollectionDelView.as_view()),  # 取消收藏活动
    path('register/', ActivityRegisterView.as_view()),  # 活动报名
    path('myregisterdactivities/', RegisteredActivitiesView.as_view()),  # 我报名的活动
    path('sign/', ActivitySignView.as_view()),  # 活动签到
    path('counts/', MyCountsView.as_view()),  # 我的各类计数
    path('recentactivities/', RecentActivitiesView.as_view()),  # 最近的活动
    path('applicants/', ApplicantsInfoView.as_view()),  # 导出活动报名表单
    path('applicant/<int:pk>/', ApplicantInfoView.as_view()),  # 活动报名者信息详情
    path('registrants/<int:pk>/', ActivityRegistrantsView.as_view()),  # 活动报名者列表查询
    path('countactivities/', CountActivitiesView.as_view()),  # 各类活动计数
    path('ticket/<int:pk>/', TicketView.as_view()),  # 活动门票
    path('meetingsdata/', MeetingsDataView.as_view()),  # 会议日历数据
    path('activitiesdata/', ActivitiesDataView.as_view()),  # 活动日历数据
]
