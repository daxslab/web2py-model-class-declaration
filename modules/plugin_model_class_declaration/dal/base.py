# -*- coding: utf-8 -*-
"""
    weppy.dal.base
    --------------

    Provides base pyDAL implementation for weppy.

    :copyright: (c) 2015 by Giovanni Barillari
    :license: BSD, see LICENSE for more details.
"""

from gluon import current

import os
from pydal import DAL as _pyDAL, Field as _Field
from pydal.objects import Table as _Table
from .._compat import copyreg
# from ..datastructures import sdict
from gluon.storage import Storage as sdict
from ..handlers import Handler
# from ..security import uuid as _uuid
from gluon.utils import web2py_uuid as _uuid
# from ..serializers import _custom_json, xml
from gluon.serializers import custom_json as _custom_json
from gluon.serializers import xml
from ..validators import ValidateFromDict


from pydal.objects import Row, Rows, Query, Set, Expression
from pydal import SQLCustomType, geoPoint, geoLine, geoPolygon
# from gluon.utils import web2py_uuid
from gluon import sqlhtml


from pydal.drivers import DRIVERS
if not DRIVERS.get('pymysql'):
    try:
        from .contrib import pymysql
        DRIVERS['pymysql'] = pymysql
    except:
        pass
if not DRIVERS.get('pyodbc'):
    try:
        from .contrib import pypyodbc as pyodbc
        DRIVERS['pyodbc'] = pyodbc
    except:
        pass
if not DRIVERS.get('pg8000'):
    try:
        from .contrib import pg8000
        DRIVERS['pg8000'] = pg8000
    except:
        pass




def _default_validators(db, field):
    """
    Field type validation, using web2py's validators mechanism.

    makes sure the content of a field is in line with the declared
    fieldtype
    """
    from gluon import validators
    field_type, field_length = field.type, field.length
    requires = []

    if field_type in (('string', 'text', 'password')):
        requires.append(validators.IS_LENGTH(field_length))
    elif field_type == 'json':
        requires.append(validators.IS_EMPTY_OR(validators.IS_JSON()))
    elif field_type == 'double' or field_type == 'float':
        requires.append(validators.IS_FLOAT_IN_RANGE(-1e100, 1e100))
    elif field_type == 'integer':
        requires.append(validators.IS_INT_IN_RANGE(-2**31, 2**31))
    elif field_type == 'bigint':
        requires.append(validators.IS_INT_IN_RANGE(-2**63, 2**63))
    elif field_type.startswith('decimal'):
        requires.append(validators.IS_DECIMAL_IN_RANGE(-10**10, 10**10))
    elif field_type == 'date':
        requires.append(validators.IS_DATE())
    elif field_type == 'time':
        requires.append(validators.IS_TIME())
    elif field_type == 'datetime':
        requires.append(validators.IS_DATETIME())
    elif db and field_type.startswith('reference') and \
            field_type.find('.') < 0 and \
            field_type[10:] in db.tables:
        referenced = db[field_type[10:]]
        if hasattr(referenced, '_format') and referenced._format:
            requires = validators.IS_IN_DB(db, referenced._id,
                                           referenced._format)
            if field.unique:
                requires._and = validators.IS_NOT_IN_DB(db, field)
            if field.tablename == field_type[10:]:
                return validators.IS_EMPTY_OR(requires)
            return requires
    elif db and field_type.startswith('list:reference') and \
            field_type.find('.') < 0 and \
            field_type[15:] in db.tables:
        referenced = db[field_type[15:]]
        if hasattr(referenced, '_format') and referenced._format:
            requires = validators.IS_IN_DB(db, referenced._id,
                                           referenced._format, multiple=True)
        else:
            requires = validators.IS_IN_DB(db, referenced._id,
                                           multiple=True)
        if field.unique:
            requires._and = validators.IS_NOT_IN_DB(db, field)
        if not field.notnull:
            requires = validators.IS_EMPTY_OR(requires)
        return requires
    if field.unique:
        requires.append(validators.IS_NOT_IN_DB(db, field))
    sff = ['in', 'do', 'da', 'ti', 'de', 'bo']
    if field.notnull and not field_type[:2] in sff:
        requires.append(validators.IS_NOT_EMPTY())
    elif not field.notnull and field_type[:2] in sff and requires:
        requires[0] = validators.IS_EMPTY_OR(requires[0])
    return requires

_pyDAL.validators_method = _default_validators

class DALHandler(Handler):
    def __init__(self, db):
        self.db = db

    def on_start(self):
        self.db._adapter.reconnect()

    def on_success(self):
        self.db.commit()

    def on_failure(self):
        self.db.rollback()

    def on_end(self):
        self.db._adapter.close()


class Table(_Table):
    def _create_references(self):
        self._referenced_by = []
        self._referenced_by_list = []
        self._references = []
        return


class DAL(_pyDAL):
    serializers = {'json': _custom_json, 'xml': xml}
    logger = None
    uuid = lambda x: _uuid()

    @staticmethod
    def uri_from_config(config=None):
        if config is None or config.adapter is None:
            config = sdict(adapter="sqlite", host="dummy.db")
        if config.adapter == "<zombie>":
            return config.adapter
        if config.adapter == "sqlite" and config.host == "memory":
            return config.adapter+":"+config.host
        uri = config.adapter+"://"
        if config.user:
            uri = uri+config.user+":"+config.password+"@"
        uri = uri+config.host
        if config.database:
            uri += "/"+config.database
        return uri

    def __new__(cls, uri, *args, **kwargs):
        # config = kwargs.get('config', sdict()) or app.config.db
        # uri = config.uri or DAL.uri_from_config(config)
        # uri = uri
        return super(DAL, cls).__new__(cls, uri, *args, **kwargs)

    # def __init__(self, app, config=sdict(), pool_size=0, folder=None,
    #              **kwargs):
    #     self.logger = app.log
    #     config = config or app.config.db
    #     if not config.uri:
    #         config.uri = self.uri_from_config(config)
    #     self.config = config
    #     #: load config data
    #     kwargs['check_reserved'] = config.check_reserved or \
    #         kwargs.get('check_reserved', None)
    #     kwargs['migrate'] = config.migrate or kwargs.get('migrate', True)
    #     kwargs['fake_migrate'] = config.fake_migrate or \
    #         kwargs.get('fake_migrate', False)
    #     kwargs['fake_migrate_all'] = config.fake_migrate_all or \
    #         kwargs.get('fake_migrate_all', False)
    #     kwargs['driver_args'] = config.driver_args or \
    #         kwargs.get('driver_args', None)
    #     kwargs['adapter_args'] = config.adapter_args or \
    #         kwargs.get('adapter_args', None)
    #     #: set directory
    #     folder = folder or 'databases'
    #     folder = os.path.join(app.root_path, folder)
    #     if not os.path.exists(folder):
    #         os.mkdir(folder)
    #     #: finally setup pyDAL instance
    #     super(DAL, self).__init__(self.config.uri, pool_size, folder, **kwargs)


    def __init__(self, uri, config=sdict(), pool_size=0, folder=None,
                 **kwargs):
        # self.logger = app.log
        # config = config or app.config.db
        config = config
        if not config.uri:
            config.uri = self.uri_from_config(config)
        self.config = config
        #: load config data
        kwargs['check_reserved'] = config.check_reserved or \
            kwargs.get('check_reserved', None)
        kwargs['migrate'] = config.migrate or kwargs.get('migrate', True)
        kwargs['fake_migrate'] = config.fake_migrate or \
            kwargs.get('fake_migrate', False)
        kwargs['fake_migrate_all'] = config.fake_migrate_all or \
            kwargs.get('fake_migrate_all', False)
        kwargs['driver_args'] = config.driver_args or \
            kwargs.get('driver_args', None)
        kwargs['adapter_args'] = config.adapter_args or \
            kwargs.get('adapter_args', None)
        #: set directory
        folder = folder or current.request.env.web2py_path+'/applications/'+current.request.application+'/databases'
        # folder = os.path.join(app.root_path, folder)
        if not os.path.exists(folder):
            os.mkdir(folder)
        #: finally setup pyDAL instance

        self.serializers = {'json': _custom_json, 'xml': xml}
        # self.validators_method = _default_validators
        self.uuid = lambda x: _uuid()
        self.representers = {
            'rows_render': sqlhtml.represent,
            'rows_xml': sqlhtml.SQLTABLE
            }
        self.Field = Field
        self.Table = Table

        super(DAL, self).__init__(uri, pool_size, folder, **kwargs)


    @property
    def handler(self):
        return DALHandler(self)

    def define_models(self, *models):
        if len(models) == 1 and isinstance(models[0], (list, tuple)):
            models = models[0]
        for model in models:
            if not hasattr(self, model.__name__):
                # store db instance inside model
                model.db = self
                # init model
                obj = model()
                obj._define_props_()
                obj._define_relations_()
                obj._define_virtuals_()
                # define table and store in model
                #model.fields = obj.fields
                args = dict(
                    migrate=obj.migrate,
                    format=obj.format,
                    table_class=Table
                )
                model.table = self.define_table(
                    obj.tablename, *obj.fields, **args
                )
                model.table._model_ = obj
                model.id = model.table.id
                # load user's definitions
                obj._define_()
                # set reference in db for model name
                self.__setattr__(model.__name__, obj.table)


def _DAL_unpickler(db_uid):
    fake_app_obj = sdict(config=sdict(db=sdict()))
    fake_app_obj.config.db.adapter = '<zombie>'
    return DAL(fake_app_obj, db_uid=db_uid)


def _DAL_pickler(db):
    return _DAL_unpickler, (db._db_uid,)

copyreg.pickle(DAL, _DAL_pickler, _DAL_unpickler)


class Field(_Field):
    _weppy_types = {
        'integer': 'int', 'double': 'float', 'bigint': 'int',
        'boolean': 'bool', 'list:integer': 'list:int'
    }
    _pydal_types = {
        'int': 'integer', 'bool': 'boolean', 'list:int': 'list:integer'
    }
    _inst_count_ = 0
    _obj_created_ = False

    def __init__(self, type='string', *args, **kwargs):
        self.modelname = None
        self._auto_validation = True
        #: convert type
        self._type = self._weppy_types.get(type, type)
        #: convert 'rw' -> 'readable', 'writeable'
        if 'rw' in kwargs:
            if isinstance(kwargs['rw'], (tuple, list)):
                read, write = kwargs['rw']
            else:
                read = write = kwargs['rw']
            kwargs['readable'] = read
            kwargs['writable'] = write
            del kwargs['rw']
        #: convert 'info' -> 'comment'
        _info = kwargs.get('info')
        if _info:
            kwargs['comment'] = _info
            del kwargs['info']
        #: get auto validation preferences
        if 'auto_validation' in kwargs:
            self._auto_validation = kwargs['auto_validation']
            del kwargs['auto_validation']
        #: intercept validation (will be processed by `_make_field`)
        self._requires = {}
        self._custom_requires = []
        if 'validation' in kwargs:
            if isinstance(kwargs['validation'], dict):
                self._requires = kwargs['validation']
            else:
                self._custom_requires = kwargs['validation']
                if not isinstance(self._custom_requires, list):
                    self._custom_requires = [self._custom_requires]
            del kwargs['validation']
        self._validation = {}
        self._vparser = ValidateFromDict()
        #: store args and kwargs for `_make_field`
        self._args = args
        self._kwargs = kwargs
        #: increase creation counter (used to keep order of fields)
        self._inst_count_ = Field._inst_count_
        Field._inst_count_ += 1

    def _default_validation(self):
        rv = {}
        auto_types = [
            'int', 'float', 'decimal', 'date', 'time', 'datetime', 'json'
        ]
        if self._type in auto_types:
            rv['is'] = self._type
        if self._type == 'bool':
            rv['in'] = (False, True)
        if self._type in ['string', 'text', 'password']:
            rv['len'] = {'lt': self.length}
        if self._type == 'list:int':
            rv['_is'] = {'list:int'}
        if self.notnull or self._type.startswith('reference') or \
                self._type.startswith('list:reference'):
            rv['presence'] = True
        if self.unique:
            rv['unique'] = True
        return rv

    def _parse_validation(self):
        for key in list(self._requires):
            self._validation[key] = self._requires[key]
        self.requires = self._vparser(self, self._validation) + \
            self._custom_requires

    #: `_make_field` will be called by `Model` class or `Form` class
    #  it will make weppy's Field class compatible with the pyDAL's one
    def _make_field(self, name, model=None):
        if self._obj_created_:
            return self
        if model is not None:
            self.modelname = model.__class__.__name__
        #: convert field type to pyDAL ones if needed
        ftype = self._pydal_types.get(self._type, self._type)
        #: create pyDAL's Field instance
        super(Field, self).__init__(name, ftype, *self._args, **self._kwargs)
        #: add automatic validation (if requested)
        if self._auto_validation:
            auto = True
            if self.modelname:
                auto = model.auto_validation
            if auto:
                self._validation = self._default_validation()
        #: validators
        if not self.modelname:
            self._parse_validation()
        self._obj_created_ = True
        return self

    def __str__(self):
        if self._obj_created_:
            return super(Field, self).__str__()
        return object.__str__(self)

    def __repr__(self):
        if self.modelname and hasattr(self, 'name'):
            return "<%s.%s (%s) field>" % (self.modelname, self.name,
                                           self._type)
        return super(Field, self).__repr__()
