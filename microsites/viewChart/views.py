from django.conf import settings
from django.http import HttpResponse, Http404
from django.views.decorators.clickjacking import xframe_options_exempt
from core.helpers import RequestProcessor
from core.choices import ChannelTypes
from core.models import *
from core.daos.datastreams import DataStreamDBDAO
from core.daos.visualizations import VisualizationDBDAO
from core.engine import invoke, invoke_chart
from core.http import get_domain_with_protocol
from core.shortcuts import render_to_response
from core.reports_manager.helpers import create_report
from microsites.viewChart import forms
from core.utils import set_dataset_impl_type_nice
import urllib
import json
import logging


def action_view(request, id, slug):
    """
    Show a microsite view
    """
    try:
        account = request.account
        is_free = False
    except AttributeError:
        try:
            account_id = Visualization.objects.values('user__account_id').get(pk=id)['user__account_id']
            account = Account.objects.get(pk=account_id)
            is_free = True
        except (Visualization.DoesNotExist, Account.DoesNotExist), e:
            return HttpResponse("Viz doesn't exist!")  # TODO

    preferences = request.preferences
    if not is_free:
        base_uri = 'http://' + preferences['account_domain']
    else:
        base_uri = get_domain_with_protocol('microsites')

    try:
        visualizationrevision_id = VisualizationRevision.objects.get_last_published_id(id)
        visualization_revision = VisualizationDBDAO().get(
            preferences['account_language'],
            visualization_revision_id=visualizationrevision_id

        )
        # verify if this account is the owner of this viz
        vis = Visualization.objects.get(pk=id)
        if account.id != vis.user.account.id:
            raise Http404

        #for datastream sidebar functions (downloads and others)
        datastream = DataStreamDBDAO().get(
            preferences['account_language'],
            datastream_revision_id=visualization_revision.datastream_revision_id
        )
        impl_type_nice = set_dataset_impl_type_nice(datastream.impl_type).replace('/', ' ')
    except VisualizationRevision.DoesNotExist:
        return HttpResponse("Viz-Rev doesn't exist!")  # TODO
    else:

        #url_query = urllib.urlencode(RequestProcessor(request).get_arguments(datastream.parameters))
        chartSizes = settings.DEFAULT_MICROSITE_CHART_SIZES
        chartWidth = chartSizes["embed"]["width"]
        chartHeight = chartSizes["embed"]["height"]
        url_query = "width=%d&height=%d" % (chartWidth, chartHeight)

        can_download = preferences['account_dataset_download'] == 'on' or preferences['account_dataset_download'] or preferences['account_dataset_download'] == 'True'
        can_export = True
        can_share = False

        create_report(visualization_revision.visualization_id, VisualizationHits, ChannelTypes.WEB)

        visualization_revision_parameters = RequestProcessor(request).get_arguments(visualization_revision.parameters)

        chart_type = json.loads(visualization_revision.impl_details).get('format').get('type')

        try:
            if chart_type != "mapchart":
                visualization_revision_parameters['pId'] = visualization_revision.datastreamrevision_id
                result, content_type = invoke(visualization_revision_parameters)
                #logger = logging.getLogger(__name__)
                #logger.debug(result)

            else:
                join_intersected_clusters = request.GET.get('joinIntersectedClusters',"1")
                #visualization_revision_parameters['pId'] = visualization_revision.visualizationrevision_id
                #visualization_revision_parameters['pLimit'] = 1000
                #visualization_revision_parameters['pPage'] = 0
                # mapCharts are loaded by ajax after
                # result, content_type = invoke_chart(visualization_revision_parameters)
        except:
            result = '{fType="ERROR"}'

        visualization_revision_parameters = urllib.urlencode(visualization_revision_parameters)

        return render_to_response('viewChart/index.html', locals())


@xframe_options_exempt
def action_embed(request, guid):
    """
    Show an embed microsite view
    """
    account = request.account
    preferences = request.preferences
    base_uri = 'http://' + preferences['account_domain']

    try:
        visualizationrevision_id = VisualizationRevision.objects.get_last_published_by_guid(guid)
        visualization_revision = VisualizationDBDAO().get(
            preferences['account_language'],
            visualization_revision_id=visualizationrevision_id
        )

        datastream = DataStreamDBDAO().get(
            preferences['account_language'],
            datastream_revision_id=visualization_revision.datastream_revision_id
        )
    except:
        return render_to_response('viewChart/embed404.html',{'settings': settings, 'request' : request})

    create_report(visualization_revision.visualization_id, VisualizationHits, ChannelTypes.WEB)
    width = request.REQUEST.get('width', False) # TODO get default value from somewhere
    height = request.REQUEST.get('height', False) # TODO get default value from somewhere

    visualization_revision_parameters = RequestProcessor(request).get_arguments(visualization_revision.parameters)
    visualization_revision_parameters['pId'] = visualization_revision.datastream_revision_id
    json, type = invoke(visualization_revision_parameters)
    visualization_revision_parameters = urllib.urlencode(visualization_revision_parameters)

    return render_to_response('viewChart/embed.html', locals())


def action_invoke(request):
    form = forms.RequestForm(request.GET)
    if form.is_valid():
        preferences = request.preferences
        try:
            visualizationrevision_id = form.cleaned_data.get('visualization_revision_id')
            visualization_revision = VZ(visualizationrevision_id, preferences['account_language'])
        except VisualizationRevision.DoesNotExist:
            return HttpResponse("Viz doesn't exist!") # TODO
        else:
            query = RequestProcessor(request).get_arguments(visualization_revision.parameters)
            query['pId'] = visualizationrevision_id

            zoom = form.cleaned_data.get('zoom')
            if zoom is not None:
                query['pZoom'] = zoom

            bounds = form.cleaned_data.get('bounds')
            if bounds is not None:
                query['pBounds'] = bounds
            else:
                query['pBounds'] = ""

            limit = form.cleaned_data.get('limit')
            if limit is not None:
                query['pLimit'] = limit

            page = form.cleaned_data.get('page')
            if page is not None:
                query['pPage'] = page

            #query["ver"] = 6
            #return HttpResponse(str(query) + str(request.GET), "json")

            result, content_type = invoke_chart(query)
            if not result:
                result = "SIN RESULTADO para %s" % query
            return HttpResponse(result, mimetype=content_type)
    else:
        return HttpResponse('Form Error!')