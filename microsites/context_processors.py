import json
from django.conf import settings

def request_context(request):
    obj = {}
    if hasattr(request, 'account'):
        account = request.account
        path = request.path
        obj = {'tracking_id': account.get_preference('account.ga.tracking')}
        ga_obj = account.get_preference('account.ga')

        msprotocol = 'https' if account.get_preference('account.microsite.https') else 'http'

        if ga_obj == '':
            ga_obj = '{}'
        if 'visualizations' in path and 'embed' not in path:
            if 'dataview_view' in json.loads(ga_obj):
                final = {}
                final['dataview_view'] = json.loads(ga_obj)['dataview_view']
                obj.update({'ga': json.dumps(final)})
        elif 'datastreams' in path and 'embed' not in path:
            if 'dataview_view' in json.loads(ga_obj):
                final = {}
                final['dataview_view'] = json.loads(ga_obj)['dataview_view']
                obj.update({'ga': json.dumps(final)})
        elif 'search' in path:
            if 'search_view' in json.loads(ga_obj):
                final = {}
                final['search_view'] = json.loads(ga_obj)['search_view']
                obj.update({'ga': json.dumps(final)})
        else:
            obj = {}
    else:
        msprotocol = 'http'

    obj['microsite_domain']=settings.DOMAINS['microsites']
    obj['microsite_uri']=msprotocol
    return obj
