# -*- coding: utf-8 -*-
import operator
import time
import logging

from django.db.models import Q, F
from django.db import IntegrityError

from .resource import AbstractDataStreamDBDAO
from core import settings
from core.choices import StatusChoices, STATUS_CHOICES
from core.exceptions import SearchIndexNotFoundException
from core.helpers import slugify
from core.models import DatastreamI18n, DataStream, DataStreamRevision, Category, DataStreamHits
from core.lib.searchify import SearchifyIndex
from core.lib.elastic import ElasticsearchIndex


class DataStreamDBDAO(AbstractDataStreamDBDAO):
    """ class for manage access to datastreams' database tables """

    def create(self, datastream=None, user=None, **fields):
        """create a new datastream if needed and a datastream_revision"""

        if datastream is None:
            # Create a new datastream (TITLE is for automatic GUID creation)
            datastream = DataStream.objects.create(user=user, title=fields['title'])

        if isinstance(fields['category'], int):
            fields['category'] = Category.objects.get(id=fields['category'])

        datastream_revision = DataStreamRevision.objects.create(
            datastream=datastream,
            user=user,
            dataset=fields['dataset'],
            status=fields['status'],
            category=fields['category'],
            data_source=fields['data_source'],
            select_statement=fields['select_statement']
        )

        DatastreamI18n.objects.create(
            datastream_revision=datastream_revision,
            language=fields['language'],
            title=fields['title'].strip().replace('\n', ' '),
            description=fields['description'].strip().replace('\n', ' '),
            notes=fields['notes'].strip()
        )

        datastream_revision.add_tags(fields['tags'])
        datastream_revision.add_sources(fields['sources'])
        datastream_revision.add_parameters(fields['parameters'])

        return datastream, datastream_revision

    def update(self, datastream_revision, changed_fields, **fields):
        fields['title'] = fields['title'].strip().replace('\n', ' ')
        fields['description'] = fields['description'].strip().replace('\n', ' ')
        fields['notes'] = fields['notes'].strip()

        datastream_revision.update(changed_fields, **fields)

        DatastreamI18n.objects.get(datastream_revision=datastream_revision, language=fields['language']).update(
            changed_fields,
            **fields
        )

        if 'tags' in fields:
            datastream_revision.add_tags(fields['tags'])
        if 'sources' in fields:
            datastream_revision.add_sources(fields['sources'])

        return datastream_revision

    def get(self, language, datastream_id=None, datastream_revision_id=None, published=True):
        """ Get full data """
        fld_revision_to_get = 'datastream__last_published_revision' if published else 'datastream__last_revision'
        datastream_revision = datastream_id is None and \
                           DataStreamRevision.objects.select_related().get(
                               pk=datastream_revision_id, category__categoryi18n__language=language,
                               datastreami18n__language=language) or \
                           DataStreamRevision.objects.select_related().get(
                               pk=F(fld_revision_to_get), category__categoryi18n__language=language,
                               datastreami18n__language=language)

        tags = datastream_revision.tagdatastream_set.all().values('tag__name', 'tag__status', 'tag__id')
        sources = datastream_revision.sourcedatastream_set.all().values('source__name', 'source__url', 'source__id')
        #parameters = datastream_revision.datastreamparameter_set.all().values('name', 'value') # TODO: Reveer
        parameters = []

        # Get category name
        category = datastream_revision.category.categoryi18n_set.get(language=language)
        datastreami18n = DatastreamI18n.objects.get(datastream_revision=datastream_revision, language=language)
        dataset_revision = datastream_revision.dataset.last_revision

        # Muestro el link del micrositio solo si esta publicada la revision
        public_url = ''
        if datastream_revision.status == StatusChoices.PUBLISHED:
            domain = datastream_revision.user.account.get_preference('account.domain')
            if not domain.startswith('http'):
                domain = 'http://' + domain
            public_url = '{}/dataviews/{}/{}'.format(domain, datastream_revision.datastream.id, slugify(datastreami18n.title))


        datastream = dict(
            datastream_revision_id=datastream_revision.id,
            dataset_id=datastream_revision.dataset.id,
            user_id=datastream_revision.user.id,
            author=datastream_revision.user.nick,
            account_id=datastream_revision.user.account.id,
            category_id=datastream_revision.category.id,
            category_name=category.name,
            end_point=dataset_revision.end_point,
            collect_type=dataset_revision.impl_type,
            impl_type=dataset_revision.impl_type,
            status=datastream_revision.status,
            modified_at=datastream_revision.created_at,
            meta_text=datastream_revision.meta_text,
            guid=datastream_revision.dataset.guid,
            created_at=datastream_revision.dataset.created_at,
            last_revision_id=datastream_revision.dataset.last_revision_id,
            last_published_date=datastream_revision.dataset.last_published_revision.created_at,
            title=datastreami18n.title,
            description=datastreami18n.description,
            notes=datastreami18n.notes,
            tags=tags,
            sources=sources,
            parameters=parameters,
            public_url=public_url,
        )

        return datastream

    def query(self, account_id=None, language=None, page=0, itemsxpage=settings.PAGINATION_RESULTS_PER_PAGE,
          sort_by='-id', filters_dict=None, filter_name=None, exclude=None):
        """ Consulta y filtra los datastreams por diversos campos """

        query = DataStreamRevision.objects.filter(
            id=F('datastream__last_revision'),
            datastream__user__account=account_id,
            datastreami18n__language=language,
            category__categoryi18n__language=language
        )

        if exclude:
            query.exclude(**exclude)

        if filter_name:
            query = query.filter(datastreami18n__title__icontains=filter_name)

        if filters_dict:
            predicates = []
            for filter_class, filter_value in filters_dict.iteritems():
                if filter_value:
                    predicates.append((filter_class + '__in', filter_value))
            q_list = [Q(x) for x in predicates]
            if predicates:
                query = query.filter(reduce(operator.and_, q_list))

        total_resources = query.count()
        query = query.values('datastream__user__nick', 'status', 'id', 'datastream__guid', 'category__id',
                             'datastream__id', 'category__categoryi18n__name', 'datastreami18n__title',
                             'datastreami18n__description', 'created_at', 'datastream__user__id',
                             'datastream__last_revision_id', 'dataset__last_revision__dataseti18n__title',
                             'dataset__last_revision__impl_type', 'dataset__last_revision__id'
                             )

        query = query.order_by(sort_by)

        # Limit the size.
        nfrom = page * itemsxpage
        nto = nfrom + itemsxpage
        query = query[nfrom:nto]

        return query, total_resources

    def query_filters(self, account_id=None, language=None):
        """
        Reads available filters from a resource array. Returns an array with objects and their
        i18n names when available.
        """
        query = DataStreamRevision.objects.filter(
                                                id=F('datastream__last_revision'),
                                                dataset__user__account=account_id,
                                                datastreami18n__language=language,
                                                category__categoryi18n__language=language)

        query = query.values('datastream__user__nick', 'status',
                             'category__categoryi18n__name')

        filters = set([])

        for res in query:
            status = res.get('status')

            filters.add(('status', status,
                unicode(STATUS_CHOICES[status])
                ))
            if 'category__categoryi18n__name' in res:
                filters.add(('category', res.get('category__categoryi18n__name'),
                    res.get('category__categoryi18n__name')))
            if res.get('datastream__user__nick'):
                filters.add(('author', res.get('datastream__user__nick'),
                    res.get('datastream__user__nick')))

        return [{'type':k, 'value':v, 'title':title} for k,v,title in filters]

    def query_childs(self, datastream_id, language):
        """ Devuelve la jerarquia completa para medir el impacto """

        related = dict(
            visualizations=dict()
        )
        return related

    def hit(self, id, channel_type):
        """agrega un hit al datastream. """

        try:
            hit=DataStreamHits.objects.create(datastream_id=id, channel_type=channel_type)
        except IntegrityError:
            # esta correcto esta excepcion?
            raise DataStreamNotFoundException()

        # utilizo el ID del hit porque es confiable como contador,
        # aunque lo correcto sería hacer un count de los hits que tiene ese ds_id
        DatastreamHitsDAO(hit.datastream).hit(hit.id)
    


class DatastreamSearchDAOFactory():
    """ select Search engine"""

    def __init__(self):
        pass

    def create(self, datastream_revision):
        if settings.USE_SEARCHINDEX == 'searchify':
            self.search_dao = DatastreamSearchifyDAO(datastream_revision)
        elif settings.USE_SEARCHINDEX == 'elasticsearch':
            self.search_dao = DatastreamElasticsearchDAO(datastream_revision)
        elif settings.USE_SEARCHINDEX == 'test':
            self.search_dao = DatastreamSearchDAO(datastream_revision)
        else:
            raise SearchIndexNotFoundException()

        return self.search_dao

        
class DatastreamSearchDAO():
    """ class for manage access to datastream index"""

    TYPE="ds"
    def __init__(self, datastream_revision):
        self.datastream_revision=datastream_revision
        self.search_index = SearchifyIndex()

    def _get_type(self):
        return self.TYPE
    def _get_id(self):
        """ Get Tags """
        return "%s::%s" %(self.TYPE.upper(),self.datastream_revision.datastream.guid)

    def _get_tags(self):
        """ Get Tags """
        return self.datastream_revision.tagdatastream_set.all().values_list('tag__name', flat=True)

    def _get_category(self):
        """ Get category name """
        return self.datastream_revision.category.categoryi18n_set.all()[0]

    def _get_i18n(self):
        """ Get category name """
        return DatastreamI18n.objects.get(datastream_revision=self.datastream_revision)
        
    def _build_document(self):

        tags = self._get_tags()

        category = self._get_category()
        datastreami18n = self._get_i18n()

        text = [datastreami18n.title, datastreami18n.description, self.datastream_revision.user.nick, self.datastream_revision.datastream.guid]
        text.extend(tags) # datastream has a table for tags but seems unused. I define get_tags funcion for dataset.
        text = ' '.join(text)

        document = {
                'docid' : self._get_id(),
                'fields' :
                    {'type' : self.TYPE,
                     'datastream_id': self.datastream_revision.datastream.id,
                     'datastream__revision_id': self.datastream_revision.id,
                     'title': datastreami18n.title,
                     'text': text,
                     'description': datastreami18n.description,
                     'owner_nick' :self.datastream_revision.user.nick,
                     'tags' : ','.join(tags),
                     'account_id' : self.datastream_revision.user.account.id,
                     'parameters': "",
                     'timestamp': int(time.mktime(self.datastream_revision.created_at.timetuple())),
                     'hits': 0,
                     'end_point': self.datastream_revision.dataset.last_published_revision.end_point,
                    },
                'categories': {'id': unicode(category.category_id), 'name': category.name}
                }

        return document


class DatastreamSearchifyDAO(DatastreamSearchDAO):
    """ class for manage access to datastreams searchify documents """
    def __init__(self, datastream_revision):
        self.datastream_revision=datastream_revision
        self.search_index = SearchifyIndex()
        
    def add(self):
        self.search_index.indexit(self._build_document())
        
    def remove(self, datastream_revision):
        self.search_index.delete_documents([self._get_id()])


class DatastreamElasticsearchDAO(DatastreamSearchDAO):
    """ class for manage access to datastreams elasticsearch documents """

    def __init__(self, datastream_revision):
        self.datastream_revision=datastream_revision
        self.search_index = ElasticsearchIndex()
        
    def add(self):
        self.search_index.indexit(self._build_document())
        
    def remove(self):
        self.search_index.delete_documents([{"type": self._get_type(), "docid": self._get_id()}])

class DatastreamHitsDAO():
    """class for manage access to Hits in DB and index"""

    def __init__(self, datastream):
        self.datastream=datastream
        self.search_index = ElasticsearchIndex()
        self.logger=logging.getLogger(__name__)

    def hit(self, count):

        self.logger.info("DatastreamHitsDAO hit! (guid: %s, hits: %s)" % ( self.datastream.guid,count))
        # armo el documento para actualizar el index.
        doc={'docid':"DS::%s" % self.datastream.guid,
                "type": "ds",
                "hits": count}

        return self.search_index.update(doc)
