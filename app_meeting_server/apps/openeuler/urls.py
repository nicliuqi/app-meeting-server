from django.urls import path
from openeuler.views import LoginView, GroupsView, MeetingView, MeetingsView, UsersExcludeView, UserView, \
    GroupUserAddView, MeetingDelView, MeetingsWeeklyView, MeetingsDailyView, UsersIncludeView, UserGroupView, \
    GroupUserDelView, UserInfoView, SigMeetingsDataView, MyMeetingsView, AllMeetingsView, \
    CollectView, CollectDelView, MyCollectionsView, ParticipantsView, SponsorsView, NonSponsorView, SponsorAddView, \
    SponsorDelView, DraftsView, DraftView, ActivityPublishView, ActivityRejectView, ActivityDelView, \
    ActivityView, ActivitiesView, RecentActivitiesView, SponsorActivitiesView, ActivityRetrieveView, \
    ActivityUpdateView, ActivityDraftView, ActivitiesDraftView, SponsorActivityDraftView, DraftUpdateView, \
    DraftPublishView, SponsorActivitiesPublishingView, ActivityCollectView, ActivityCollectDelView, \
    MyActivityCollectionsView, CountActivitiesView, MyCountsView, MeetingsRecentlyView, \
    AgreePrivacyPolicyView, RevokeAgreementView, LogoutView, LogoffView, PingView, MeetingsGroupView, \
    RefreshView, MeetingActivityDateView, MeetingActivityDataView

urlpatterns = [
    # common
    path('ping/', PingView.as_view()),                                 # ping

    # user
    path('login/', LoginView.as_view()),                                # 登陆
    path('refresh/', RefreshView.as_view()),                            # 刷新token
    path('logout/', LogoutView.as_view()),                              # 登出账号
    path('logoff/', LogoffView.as_view()),                              # 注销账号
    path('agree/', AgreePrivacyPolicyView.as_view()),                   # 同意更新隐私政策
    path('revoke/', RevokeAgreementView.as_view()),                     # 撤销同意更新隐私政策
    path('groups/', GroupsView.as_view()),                              # 查询所有SIG组的名称
    path('users_exclude/<int:pk>/', UsersExcludeView.as_view()),        # 查询不在该组的所有成员的nickname、gitee_name、avatar
    path('users_include/<int:pk>/', UsersIncludeView.as_view()),        # 获取该SIG组的所有成员的nickname、gitee_name、avatar
    path('groupuser/action/new/', GroupUserAddView.as_view()),          # 批量给SIG组新增成员
    path('groupuser/action/del/', GroupUserDelView.as_view()),          # 批量删除SIG组成员
    path('sponsors/', SponsorsView.as_view()),                          # 活动发起人列表
    path('nonsponsors/', NonSponsorView.as_view()),                     # 非活动发起人列表
    path('sponsor/action/new/', SponsorAddView.as_view()),              # 批量添加活动发起人
    path('sponsor/action/del/', SponsorDelView.as_view()),              # 批量删除活动发起人
    path('userinfo/<int:pk>/', UserInfoView.as_view()),                 # 查询本机用户的level和gitee_name
    path('user/<int:pk>/', UserView.as_view()),                         # 更新gitee_name
    path('usergroup/<int:pk>/', UserGroupView.as_view()),               # 查询该成员的组名以及etherpad
    path('mycounts/', MyCountsView.as_view()),                          # 我的各类计数

    # meeting
    path('meetings/', MeetingsView.as_view()),                          # 新建会议
    path('meetings_weekly/', MeetingsWeeklyView.as_view()),             # 查询前后一周会议详情
    path('meetings_group/', MeetingsGroupView.as_view()),               # 查询前后一周会议的组名
    path('meetings_daily/', MeetingsDailyView.as_view()),               # 查询当日会议详情
    path('meetings_recently/', MeetingsRecentlyView.as_view()),         # 查询近期的会议
    path('meeting/<int:mid>/', MeetingDelView.as_view()),               # 删除会议
    path('meetings/<int:pk>/', MeetingView.as_view()),                  # 查询单个会议详情
    path('mymeetings/', MyMeetingsView.as_view()),                      # 查询我创建的会议
    path('collect/', CollectView.as_view()),                            # 添加收藏
    path('collect/<int:pk>/', CollectDelView.as_view()),                # 取消收藏
    path('collections/', MyCollectionsView.as_view()),                  # 我收藏的会议
    path('sigmeetingsdata/<str:gn>/', SigMeetingsDataView.as_view()),   # 分页官网网页SIG会议数据

    # activity
    path('activity/', ActivityView.as_view()),                                        # 1.创建活动并申请发布
    path('activitydraft/', ActivityDraftView.as_view()),                              # 2.创建活动草案
    path('draftupdate/<int:pk>/', DraftUpdateView.as_view()),                         # 3.修改草案
    path('draftpublish/<int:pk>/', DraftPublishView.as_view()),                       # 4.修改活动草案并申请发布活动
    path('sponsoractivitydraft/<int:pk>/', SponsorActivityDraftView.as_view()),       # 5.查询、删除活动草案
    path('activitypublish/<int:pk>/', ActivityPublishView.as_view()),                 # 6.通过审核
    path('activityreject/<int:pk>/', ActivityRejectView.as_view()),                   # 7.驳回申请
    path('activitydel/<int:pk>/', ActivityDelView.as_view()),                         # 8.删除活动
    path('activityupdate/<int:pk>/', ActivityUpdateView.as_view()),                   # 9.修改活动
    path('collectactivity/', ActivityCollectView().as_view()),                        # 10.收藏活动
    path('collectactivitydel/<int:pk>/', ActivityCollectDelView.as_view()),           # 11.取消收藏活动
    path('drafts/', DraftsView.as_view()),                                            # 审核列表
    path('draft/<int:pk>/', DraftView.as_view()),                                     # 待发布详情
    path('recentactivities/', RecentActivitiesView.as_view()),                        # 最近的活动
    path('sponsoractivities/', SponsorActivitiesView.as_view()),                      # 活动发起人的活动列表
    path('activitiesdraft/', ActivitiesDraftView.as_view()),                          # 活动发起人的活动草案列表
    path('sponsoractivitiespublishing/', SponsorActivitiesPublishingView.as_view()),  # 发布中(个人)的活动
    path('collectactivities/', MyActivityCollectionsView.as_view()),                  # 我收藏的活动列表
    path('countactivities/', CountActivitiesView.as_view()),                          # 各类活动计数
    path('activities/', ActivitiesView.as_view()),                                    # 官网网页活动列表+分页
    path('activity/<int:pk>/', ActivityRetrieveView.as_view()),                       # 官网网页查询单个活动

    # 提供给官网的公共接口
    path('meeting_activity_date/', MeetingActivityDateView.as_view()),
    path('meeting_activity_data/', MeetingActivityDataView.as_view()),


]
