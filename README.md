# web2py-model-class-declaration
web2py model class declaration plugin

This plugin adds pyDAL weppy class-bassed model declaration to web2py

# How use it

1- Install the plugin

2- Import plugin in the db.py file (before the DAL() call):

    from plugin_model_class_declaration.dal.apis import *
    from plugin_model_class_declaration.dal import DAL, Model, Field
    
3- Use the weppy table definition syntax (http://weppy.org/docs/0.5/dal)
