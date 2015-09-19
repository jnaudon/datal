from django.conf.urls import *

urlpatterns = patterns('',
    url(r'^(?P<id>\d+)/(?P<slug>[A-Za-z0-9\-]+)/$', 'microsites.viewDataStream.views.view',
        name='viewDataStream.view'),
    url(r'^datastreams/embed/(?P<guid>[A-Z0-9\-]+)$', 'microsites.viewDataStream.views.embed',
        name='datastream_manager.embed'),
   url(r'^(?P<id>\d+)-(?P<slug>[A-Za-z0-9\-]+).download$', 'microsites.viewDataStream.views.download',
        name='datastream_manager.download'),
    url(r'^(?P<id>\d+)-(?P<slug>[A-Za-z0-9\-]+).csv$', 'microsites.viewDataStream.views.csv',
        name='datastream_manager.csv'),
    url(r'^(?P<id>\d+)-(?P<slug>[A-Za-z0-9\-]+).html$', 'microsites.viewDataStream.views.html',
        name='datastream_manager.html'),
    url(r'^(?P<id>\d+)-(?P<slug>[A-Za-z0-9\-]+).xls(?:$|x$)', 'microsites.viewDataStream.views.xls',
        name='datastream_manager.xls'),
    url(r'^updategrid$', 'microsites.viewDataStream.views.updategrid',
        name='datastream_manager.updategrid'),
    url(r'^get_last_30_days_datastream/(?P<id>\d+)$', 'microsites.viewDataStream.views.hits_stats',
        name='datastream_manager.get_last_30_days_datastream'),
    url(r'^category/(?P<category_slug>[A-Za-z0-9\-]+)/$', 'microsites.search.views.action_browse',
        name='search.action_browse'),
    url(r'^category/(?P<category_slug>[A-Za-z0-9\-]+)/page/(?P<page>\d+)/$', 'microsites.search.views.action_browse',
        name='search.action_browse'),
    url(r'^invoke$', 'microsites.viewDataStream.views.invoke'),
)
