from django.conf.urls import url,include

from web.views import account
from web.views import home
from web.views import project
from web.views import wiki
from web.views import file
from web.views import setting
from web.views import issues
from web.views import dashboard
from web.views import statistics
urlpatterns = [
    url(r'^register/$', account.register,name="register"),
    url(r'^login/sms/$', account.login_sms,name="login_sms"),
    url(r'^send/sms/$', account.send_sms,name="send_sms"),
    url(r'^index/$', home.index,name="index"),
    url(r'^login/$', account.login,name="login"),
    url(r'^image_code/$', account.image_code,name="image_code"),
    url(r'^logout/$', account.logout,name="logout"),
    url(r'^price/$', home.price,name="price"),
    url(r'^price/(?P<policy_id>\d+)/$', home.payment,name="payment"),
    url(r'^price/pay/$', home.pay,name="pay"),
    url(r'^price/pay/notify/$', home.pay_notify,name="pay_notify"),

    #项目列表
    url(r'^project/list/$', project.project_list,name="project_list"),
    #/project/star/my/1/
    #/project/star/join/2/
    url(r'^project/star/(?P<project_type>\w+)/(?P<project_id>\d+)/$', project.project_star,name="project_star"),
    url(r'^project/unstar/(?P<project_type>\w+)/(?P<project_id>\d+)/$', project.project_unstar,name="project_unstar"),

    #项目管理 如果很多URL前部分都是一样的，可以采用以下形式
    url(r'^manage/(?P<project_id>\d+)/', include([ #前缀URL末尾不能加$ r'^manage/(?P<project_id>\d+)/$'
        url(r'^dashboard/$',dashboard.dashboard,name='dashboard'),
        url(r'^dashboard/issues/chart/$',dashboard.issues_chart,name='issues_chart'),

        url(r'^statistics/$',statistics.statistics,name='statistics'),
        url(r'^statistics/chart/$',statistics.statistics_chart,name='statistics_chart'),
        url(r'^statistics/project/user/$',statistics.statistics_project_user,name='statistics_project_user'),

        url(r'^file/$',file.file,name='file'),
        url(r'^file/delete/$',file.folder_delete,name='file_delete'),
        url(r'^file/save/$',file.file_save,name='file_save'),
        url(r'^file/download/(?P<download_id>\d+)/$',file.file_download,name='file_download'),
        url(r'^file/credential/$', file.file_credential,name="file_credential"),

        url(r'^wiki/$',wiki.wiki,name='wiki'),
        url(r'^wiki/wiki_add/$',wiki.wiki_add,name='wiki_add'),
        url(r'^wiki/wiki_catalog/$',wiki.wiki_catalog,name='wiki_catalog'),
        url(r'^wiki/wiki_delete/(?P<wiki_id>\d+)/$',wiki.wiki_delete,name='wiki_delete'),
        url(r'^wiki/wiki_edit/(?P<wiki_id>\d+)/$',wiki.wiki_edit,name='wiki_edit'),
        url(r'^wiki/wiki_upload/$',wiki.wiki_upload,name='wiki_upload'),

        url(r'^setting/$',setting.setting,name='setting'),
        url(r'^setting/delete/$',setting.setting_delete,name='setting_delete'),

        url(r'^issues/$',issues.issues,name='issues'),
        url(r'^issues/detail/(?P<issue_id>\d+)/$',issues.issues_detail,name='issues_detail'),
        url(r'^issues/record/(?P<issue_id>\d+)/$',issues.issues_record,name='issues_record'),
        url(r'^issues/change/(?P<issue_id>\d+)/$',issues.issues_change,name='issues_change'),
        url(r'^issues/invite/url/$',issues.invite_url,name='invite_url'),
    ],None,None)),
    url(r'^issues/invite/join/(?P<code>\w+)/$',issues.invite_join,name='invite_join'),
]
