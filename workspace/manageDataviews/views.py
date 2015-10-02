import logging

from django.http import HttpResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.utils.translation import ugettext
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from django.core.serializers.json import DjangoJSONEncoder
from core.shortcuts import render_to_response
from core.auth.decorators import login_required
from workspace.decorators import *
from workspace.manageDataviews.forms import *
from workspace.templates import *
from core.daos.datastreams import DataStreamDBDAO
from core.lifecycle.datastreams import DatastreamLifeCycleManager
from core.exceptions import DataStreamNotFoundException, DatasetNotFoundException
from workspace.exceptions import DatastreamSaveException
from core.models import DatasetRevision, Account, CategoryI18n, DataStreamRevision
from core.http import JSONHttpResponse
from core.decorators import datal_cache_page
from core.v8.factories import AbstractCommandFactory
from core.utils import DateTimeEncoder



logger = logging.getLogger(__name__)


@login_required
@require_GET
def action_view(request, revision_id):
    
    language = request.auth_manager.language
    try:
        datastream = DataStreamDBDAO().get(language, datastream_revision_id=revision_id)
    except DataStreamRevision.DoesNotExist:
        raise DataStreamNotFoundException()

    account_id = request.auth_manager.account_id
    credentials = request.auth_manager
    categories = CategoryI18n.objects.filter(language=language, category__account=account_id).values('category__id','name')
    status_options = credentials.get_allowed_actions()

    return render_to_response('viewDataStream/index.html', locals())


@login_required
# quitarlo por que ya se maneja dentro @requires_any_dataset() #account must have almost one dataset
@require_privilege("workspace.can_query_datastream")
@require_GET
def index(request):
    """ list all dataviews """
    ds_dao = DataStreamDBDAO()
    filters = ds_dao.query_filters(account_id=request.user.account.id,
                                    language=request.user.language)

    return render_to_response('manageDataviews/index.html', locals())


@login_required
@require_GET
@require_privilege("workspace.can_query_datastream")
def filter(request, page=0, itemsxpage=settings.PAGINATION_RESULTS_PER_PAGE):
    """ filter resources """
    bb_request = request.GET
    filters_param = bb_request.get('filters')
    filters_dict = dict()
    filter_name = ''
    sort_by = '-id'

    if filters_param is not None and filters_param != '':
        filters = json.loads(filters_param)

        filters_dict['impl_type'] = filters.get('type')
        filters_dict['category__categoryi18n__name'] = filters.get('category')
        filters_dict['datastream__user__nick'] = filters.get('author')
        filters_dict['status'] = filters.get('status')

    if bb_request.get('page') is not None and bb_request.get('page') != '':
        page = int(bb_request.get('page'))
    if bb_request.get('itemxpage') is not None and bb_request.get('itemxpage') != '':
        itemsxpage = int(bb_request.get('itemxpage'))
    if bb_request.get('q') is not None and bb_request.get('q') != '':
        filter_name = bb_request.get('q')
    if bb_request.get('sort_by') is not None and bb_request.get('sort_by') != '':
        if bb_request.get('sort_by') == "title":
            sort_by ="datastreami18n__title"
        if bb_request.get('sort_by') == "dataset_title":
            sort_by ="dataset__last_revision__dataseti18n__title"
        if bb_request.get('sort_by') == "author":
            sort_by ="datastream__user__nick"
        if bb_request.get('order')=="desc":
            sort_by = "-"+ sort_by

    total_resources = request.stats['account_total_datastreams']

    resources,total_entries = DataStreamDBDAO().query(
        account_id=request.account.id,
        language=request.user.language,
        page=page,
        itemsxpage=itemsxpage,
        filters_dict=filters_dict,
        sort_by=sort_by,
        filter_name=filter_name
    )

    for resource in resources:
        # resources[i]['url'] = LocalHelper.build_permalink('manageDataviews.view', '&datastream_revision_id=' + str(resources[i]['id']))
        resource['url'] = reverse('manageDataviews.view', urlconf='workspace.urls', kwargs={'revision_id': resource['id']})
        resource['dataset_url'] = reverse('manageDatasets.view', urlconf='workspace.urls', kwargs={'revision_id': resource['dataset__last_revision__id']})

    data = {'total_entries': total_entries, 'total_resources': total_resources, 'resources': resources, 'total_entries': total_entries}
    response = DatastreamList().render(data)
    
    return JSONHttpResponse(response)


@login_required
@require_privilege("workspace.can_query_dataset")
@require_GET
def get_filters_json(request):
    """ List all Filters available """
    filters = DataStreamDBDAO().query_filters(account_id=request.user.account.id, language=request.user.language)
    return JSONHttpResponse(json.dumps(filters))


@login_required
@require_GET
def related_resources(request):
    language = request.auth_manager.language
    revision_id = request.GET.get('datastream_id', '')
    associated_visualizations = DataStreamDBDAO().query_childs(datastream_id=revision_id, language=language)['visualizations']

    list_result = []
    for associated_visualization in associated_visualizations:
        associated_visualization['type'] = 'visualization'
        list_result.append(associated_visualization) 
    
    dump = json.dumps(list_result, cls=DjangoJSONEncoder)
    return HttpResponse(dump, mimetype="application/json")


@login_required
@require_privilege("workspace.can_delete_datastream")
@requires_review
@transaction.commit_on_success
def remove(request, datastream_revision_id, type="resource"):
    """ remove resource """
    lifecycle = DatastreamLifeCycleManager(user=request.user, datastream_revision_id=datastream_revision_id)

    if type == 'revision':
        lifecycle.remove()
        # si quedan revisiones, redirect a la ultima revision, si no quedan, redirect a la lista.
        if lifecycle.datastream.last_revision_id:
            last_revision_id = lifecycle.datastream.last_revision.id
        else:
            last_revision_id = -1

        return JSONHttpResponse(json.dumps({
            'status': True,
            'messages': [ugettext('APP-DELETE-DATASTREAM-REV-ACTION-TEXT')],
            'revision_id': last_revision_id,
        }))
        
    else:
        lifecycle.remove(killemall=True)
        return HttpResponse(json.dumps({
            'status': True,
            'messages': [ugettext('APP-DELETE-DATASTREAM-ACTION-TEXT')],
            'revision_id': -1,
        }), content_type='text/plain')


@login_required
@require_http_methods(['POST', 'GET'])
@require_privilege("workspace.can_create_datastream")
@requires_dataset()
@requires_published_parent()
@transaction.commit_on_success
def create(request):
    auth_manager = request.auth_manager
    if request.method == 'POST':
        """ save new or update dataset """
        form = CreateDataStreamForm(request.POST)

        if not form.is_valid():
            raise DatastreamSaveException('Invalid form data: %s' % str(form.errors.as_text()))

        dataset_revision = DatasetRevision.objects.get(pk=form.cleaned_data['dataset_revision_id'])

        dataview = DatastreamLifeCycleManager(user=request.user)
        dataview.create(
            dataset=dataset_revision.dataset,
            language=request.auth_manager.language,
            category_id=form.cleaned_data['category'],
            **form.cleaned_data
        )

        response = dict(
            status='ok',
            datastream_revision_id=dataview.datastream_revision.id,
            messages=[ugettext('APP-DATASET-CREATEDSUCCESSFULLY-TEXT')]
        )

        return JSONHttpResponse(json.dumps(response))

    elif request.method == 'GET':
        form = InitalizeCollectForm(request.GET)

        if form.is_valid():
            is_update = False
            is_update_selection = False
            data_set_id = form.cleaned_data['dataset_revision_id']
            datastream_id = None

            if auth_manager.is_level('level_5'):
                meta_data = Account.objects.get(pk=auth_manager.account_id).meta_data

            try:
                dataset_revision = DatasetRevision.objects.get(pk= data_set_id)
            except DatasetRevision.DoesNotExist:
                raise DatasetNotFoundException()

            end_point = dataset_revision.end_point
            type = dataset_revision.dataset.type
            impl_type = dataset_revision.impl_type
            impl_details = dataset_revision.impl_details
            bucket_name = request.bucket_name

            return render_to_response('view_manager/insertForm.html', locals())
        else:
            raise Http404


@login_required
@require_http_methods(['POST', 'GET'])
@require_privilege("workspace.can_edit_datastream")
@requires_published_parent()
@requires_review
@transaction.commit_on_success
def edit(request, datastream_revision_id=None):
    if request.method == 'GET':
        account_id = request.auth_manager.account_id
        credentials = request.auth_manager
        language = request.auth_manager.language
        categories = CategoryI18n.objects.filter(
            language=language,
            category__account=account_id
        ).values('category__id', 'name')
        status_options = credentials.get_allowed_actions()
        lifecycle = DatastreamLifeCycleManager(user=request.user, datastream_revision_id=datastream_revision_id)
        status = lifecycle.datastream_revision.status
        response = DefaultDataViewEdit(template='datastream_edit_response.json').render(
            categories,status,
            status_options,
            lifecycle.datastream_revision,
            lifecycle.datastreami18n
        )

        return JSONHttpResponse(response)

    elif request.method == 'POST':
        """update dataset """

        form = EditDataStreamForm(request.POST)

        if not form.is_valid():
            raise LifeCycleException('Invalid form data: %s' % str(form.errors.as_text()))

        if form.is_valid():
            dataview = DatastreamLifeCycleManager(user=request.user, datastream_revision_id=datastream_revision_id)

            dataview.edit(
                language=request.auth_manager.language,
                changed_fields=form.changed_data,
                **form.cleaned_data
            )

            response = dict(
                status='ok',
                datastream_revision_id= dataview.datastream_revision.id,
                messages=[ugettext('APP-DATASET-CREATEDSUCCESSFULLY-TEXT')],
            )

            return JSONHttpResponse(json.dumps(response))


@login_required
@require_POST
@transaction.commit_on_success
def change_status(request, datastream_revision_id=None):
    """
    Change dataview status
    :param request:
    :param datastream_revision_id:
    :return: JSON Object
    """
    if request.method == 'POST' and datastream_revision_id:
        lifecycle = DatastreamLifeCycleManager(
            user=request.user,
            datastream_revision_id=datastream_revision_id
        )
        action = request.POST.get('action')

        if action == 'approve':
            lifecycle.accept()
            response = dict(
                status='ok',
                messages={
                    'title': ugettext('APP-DATAVIEW-APPROVED-TITLE'),
                    'description': ugettext('APP-DATAVIEW-APPROVED-TEXT')
                }
            )
        elif action == 'reject':
            lifecycle.reject()
            response = dict(
                status='ok',
                messages={
                    'title': ugettext('APP-DATAVIEW-REJECTED-TITLE'),
                    'description': ugettext('APP-DATAVIEW-REJECTED-TEXT')
                }
            )
        elif action == 'publish':
            lifecycle.publish()
            response = dict(
                status='ok',
                messages={
                    'title': ugettext('APP-DATAVIEW-PUBLISHED-TITLE'),
                    'description': ugettext('APP-DATAVIEW-PUBLISHED-TEXT')
                }
            )
        elif action == 'unpublish':
            killemall = True if request.POST.get('killemall', False) == 'true' else False
            lifecycle.unpublish(killemall=killemall)
            if( killemall == True ):
                description = ugettext('APP-DATAVIEW-UNPUBLISHALL-TEXT')
            else:
                description = ugettext('APP-DATAVIEW-UNPUBLISH-TEXT')
            response = dict(
                status='ok',
                messages={
                    'title': ugettext('APP-DATAVIEW-UNPUBLISH-TITLE'),
                    'description': description
                }
            )
        elif action == 'send_to_review':
            lifecycle.send_to_review()
            response = dict(
                status='ok',
                messages={
                    'title': ugettext('APP-DATAVIEW-SENDTOREVIEW-TITLE'),
                    'description': ugettext('APP-DATAVIEW-SENDTOREVIEW-TEXT')
                }
            )
        else:
            raise NoStatusProvidedException()

        # Limpio un poco
        response['result'] = DataStreamDBDAO().get(request.user.language, datastream_revision_id=datastream_revision_id)
        response['result'].pop('parameters')
        response['result'].pop('tags')
        response['result'].pop('sources')

        return JSONHttpResponse(json.dumps(response, cls=DateTimeEncoder))
    
