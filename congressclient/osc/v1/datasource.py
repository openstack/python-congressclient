#   Copyright 2012-2013 OpenStack, LLC.
#
#   Licensed under the Apache License, Version 2.0 (the "License"); you may
#   not use this file except in compliance with the License. You may obtain
#   a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#   WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#   License for the specific language governing permissions and limitations
#   under the License.

"""Datasource action implemenations"""

import logging

from cliff import command
from cliff import lister
from cliff import show
from keystoneclient.openstack.common.apiclient import exceptions
from openstackclient.common import parseractions
import six

from congressclient.common import utils


def get_resource_id_from_name(name, results):
    # FIXME(arosen): move to common lib and add tests...
    name_match = None
    id_match = None
    double_name_match = False
    for result in results['results']:
        if result['id'] == name:
            id_match = result['id']
        if result['name'] == name:
            if name_match:
                double_name_match = True
            name_match = result['id']
    if not double_name_match and name_match:
        return name_match
    if double_name_match and not id_match:
        # NOTE(arosen): this should only occur is using congress
        # as admin and multiple tenants use the same datsource name.
        raise exceptions.Conflict(
            "Multiple resources have this name %s. Delete by id." % name)
    if id_match:
        return id_match

    raise exceptions.NotFound("Resource %s not found" % name)


class ListDatasources(lister.Lister):
    """List Datasources."""

    log = logging.getLogger(__name__ + '.ListDatasources')

    def get_parser(self, prog_name):
        parser = super(ListDatasources, self).get_parser(prog_name)
        return parser

    def take_action(self, parsed_args):
        client = self.app.client_manager.congressclient
        data = client.list_datasources()['results']
        columns = ['id', 'name', 'enabled', 'type', 'config']
        formatters = {'Datasources': utils.format_list}
        return (columns,
                (utils.get_dict_properties(s, columns,
                                           formatters=formatters)
                 for s in data))


class ListDatasourceTables(lister.Lister):
    """List datasource tables."""

    log = logging.getLogger(__name__ + '.ListDatasourceTables')

    def get_parser(self, prog_name):
        parser = super(ListDatasourceTables, self).get_parser(prog_name)
        parser.add_argument(
            'datasource_name',
            metavar="<datasource-name>",
            help="Name of the datasource")
        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)' % parsed_args)
        client = self.app.client_manager.congressclient
        data = client.list_datasource_tables(
            parsed_args.datasource_name)['results']
        columns = ['id']
        formatters = {'DatasourceTables': utils.format_list}
        return (columns,
                (utils.get_dict_properties(s, columns,
                                           formatters=formatters)
                 for s in data))


class ShowDatasourceStatus(show.ShowOne):
    """List status for datasource."""

    log = logging.getLogger(__name__ + '.ShowDatasourceStatus')

    def get_parser(self, prog_name):
        parser = super(ShowDatasourceStatus, self).get_parser(prog_name)
        parser.add_argument(
            'datasource_name',
            metavar="<datasource-name>",
            help="Name of the datasource")
        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)' % parsed_args)
        client = self.app.client_manager.congressclient

        results = client.list_datasources()
        datasource_id = get_resource_id_from_name(parsed_args.datasource_name,
                                                  results)

        data = client.list_datasource_status(datasource_id)
        return zip(*sorted(six.iteritems(data)))


class ShowDatasourceSchema(lister.Lister):
    """Show schema for datasource."""

    log = logging.getLogger(__name__ + '.ShowDatasourceSchema')

    def get_parser(self, prog_name):
        parser = super(ShowDatasourceSchema, self).get_parser(prog_name)
        parser.add_argument(
            'datasource_name',
            metavar="<datasource-name>",
            help="Name of the datasource")
        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)' % parsed_args)
        client = self.app.client_manager.congressclient
        results = client.list_datasources()
        datasource_id = get_resource_id_from_name(parsed_args.datasource_name,
                                                  results)
        data = client.show_datasource_schema(datasource_id)
        formatters = {'columns': utils.format_long_dict_list}
        newdata = [{'table': x['table_id'],
                    'columns': x['columns']}
                   for x in data['tables']]
        columns = ['table', 'columns']
        return (columns,
                (utils.get_dict_properties(s, columns,
                                           formatters=formatters)
                 for s in newdata))


class ShowDatasourceTableSchema(lister.Lister):
    """Show schema for datasource table."""

    log = logging.getLogger(__name__ + '.ShowDatasourceTableSchema')

    def get_parser(self, prog_name):
        parser = super(ShowDatasourceTableSchema, self).get_parser(prog_name)
        parser.add_argument(
            'datasource_name',
            metavar="<datasource-name>",
            help="Name of the datasource")
        parser.add_argument(
            'table_name',
            metavar="<table-name>",
            help="Name of the table")
        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)' % parsed_args)
        client = self.app.client_manager.congressclient
        data = client.show_datasource_table_schema(
            parsed_args.datasource_name,
            parsed_args.table_name)
        columns = ['name', 'description']
        return (columns,
                (utils.get_dict_properties(s, columns)
                 for s in data['columns']))


class ListDatasourceRows(lister.Lister):
    """List datasource rows."""

    log = logging.getLogger(__name__ + '.ListDatasourceRows')

    def get_parser(self, prog_name):
        parser = super(ListDatasourceRows, self).get_parser(prog_name)
        parser.add_argument(
            'datasource_name',
            metavar="<datasource-name>",
            help="Name of the datasource to show")
        parser.add_argument(
            'table',
            metavar="<table>",
            help="Table to get the datasource rows from")
        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)' % parsed_args)
        client = self.app.client_manager.congressclient

        results = client.list_datasources()
        datasource_id = get_resource_id_from_name(parsed_args.datasource_name,
                                                  results)
        results = client.list_datasource_rows(datasource_id,
                                              parsed_args.table)['results']
        if results:
            columns = client.show_datasource_table_schema(
                datasource_id, parsed_args.table)['columns']
            columns = [col['name'] for col in columns]
        else:
            columns = ['data']  # doesn't matter because the rows are empty
        return (columns, (x['data'] for x in results))


class ShowDatasourceTable(show.ShowOne):
    """Show Datasource Table properties."""

    log = logging.getLogger(__name__ + '.ShowDatasourceTable')

    def get_parser(self, prog_name):
        parser = super(ShowDatasourceTable, self).get_parser(prog_name)
        parser.add_argument(
            'datasource_name',
            metavar='<datasource-name>',
            help="Name of datasource")
        parser.add_argument(
            'table_id',
            metavar='<table-id>',
            help="Table id")

        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)' % parsed_args)
        client = self.app.client_manager.congressclient
        data = client.show_datasource_table(parsed_args.datasource_name,
                                            parsed_args.table_id)
        return zip(*sorted(six.iteritems(data)))


class CreateDatasource(show.ShowOne):
    """Create a datasource."""

    log = logging.getLogger(__name__ + '.CreateDatasource')

    def get_parser(self, prog_name):
        parser = super(CreateDatasource, self).get_parser(prog_name)
        parser.add_argument(
            'driver',
            metavar="<datasource-driver>",
            help="Selected datasource driver")
        parser.add_argument(
            'name',
            metavar="<datasource-name>",
            help="Name you want to call the datasource")
        parser.add_argument(
            '--description',
            metavar="<datasource-description>",
            help="Description of the datasource")

        parser.add_argument(
            '--config',
            metavar="<key=value>",
            action=parseractions.KeyValueAction,
            help="config dictionary to pass in")

        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)' % parsed_args)
        client = self.app.client_manager.congressclient
        body = {'name': parsed_args.name,
                'driver': parsed_args.driver,
                'config': parsed_args.config}
        if parsed_args.description:
            body['description'] = parsed_args.description
        results = client.create_datasource(body)
        return zip(*sorted(six.iteritems(results)))


class DeleteDatasource(command.Command):
    """Delete a datasource."""

    log = logging.getLogger(__name__ + '.DeletePolicyRule')

    def get_parser(self, prog_name):
        parser = super(DeleteDatasource, self).get_parser(prog_name)
        parser.add_argument(
            'datasource',
            metavar="<datasource-name>",
            help="Name of the policy to delete")
        return parser

    def take_action(self, parsed_args):
        self.log.debug('take_action(%s)' % parsed_args)
        client = self.app.client_manager.congressclient
        results = client.list_datasources()
        datasource_id = get_resource_id_from_name(parsed_args.datasource,
                                                  results)
        client.delete_datasource(datasource_id)
