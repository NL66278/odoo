# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import base64

from osv import osv, fields
from osv.orm import except_orm
import urlparse
import pooler

import os


#
# An object that represent an uri
#   path: the uri of the object
#   content: the Content it belongs to (_print.pdf)
#   type: content or collection
#       content: objct = res.partner
#       collection: object = directory, object2 = res.partner
#       file: objct = ir.attachement
#   root: if we are at the first directory of a ressource
#

def get_node_context(cr, uid, context):
	return node_context(cr,uid,context)

class node_context(object):
    """ This is the root node, representing access to some particular
	context """
    cached_roots = {}

    def __init__(self, cr, uid, context=None):
	# we don't cache the cr!
	#self.cr = cr
	self.uid = uid
	self.context = context
	self._dirobj = pooler.get_pool(cr.dbname).get('document.directory')
	assert self._dirobj
	self.rootdir = self._dirobj._get_root_directory(cr,uid,context)

    def get_uri(self, cr,  uri):
	""" Although this fn passes back to doc.dir, it is needed since
	it is a potential caching point """
	print "node get uri:",uri
	
	return self._dirobj._locate_child(cr,self.uid, self.rootdir,uri, None, self)


class node_database():
    """ A node representing the database directory
	Useless?
	"""
    def __init__(self,ncontext):
	self.nctx = ncontext




class node_class(object):
    our_type = 'baseclass'
    def __init__(self, path, parent, context):
	assert isinstance(context,node_context)
	assert (not parent ) or isinstance(parent,node_class)
        self.path = path
        self.context = context
        self.type=self.our_type
	self.parent = parent
	
    def full_path(self):
	if parent:
	    s = parent.full_path()
	else:
	    s = []
	s.append(self.path)
	return s

    def children(self):
        print "node_class.children()"
	return [] #stub

    def child(self, name):
	print "node_class.child()"
        return None

    def path_get(self):
	print "node_class.path_get()"
	return False

class node_dir(node_class):
    our_type = 'collection'
    def __init__(self,path, parent, context, dirr):
	super(node_dir,self).__init__(path, parent,context)
	self.dir_id = dirr.id
	#todo: more info from dirr
	

    def children(self,cr):
        return self._child_get(cr) + self._file_get(cr)

    def child(self,cr, name):
        res = self._child_get(cr,name)
        if res:
            return res[0]
        res = self._file_get(cr,name)
        if res:
            return res[0]
        return None

    def _file_get(self,cr, nodename=False):
	return []

    def _child_get(self,cr,name = None):
	dirobj = self.context._dirobj
	uid = self.context.uid
	ctx = self.context.context
	where = [('parent_id','=',self.dir_id) ]
	if name:
		where.append(('name','=',name))
	ids = dirobj.search(cr, uid, where,context=ctx)
	res = []
	if ids:
	    for dirr in dirobj.browse(cr,uid,ids,context=ctx):
		res.append(node_dir(dirr.name,self,self.context,dirr))
		
	fil_obj=dirobj.pool.get('ir.attachment')
	ids = fil_obj.search(cr,uid,where,context=ctx)
	if ids:
	    for fil in fil_obj.browse(cr,uid,ids,context=ctx):
		res.append(node_file(fil.name,self,self.context,fil))
	
	return res

class node_file(node_class):
    our_type = 'file'
    def __init__(self,path, parent, context, fil):
	super(node_file,self).__init__(path, parent,context)
	self.file_id = fil.id
	#todo: more info from ir_attachment

class old_class():
    # the old code, remove..
    def __init__(self, cr, uid, path, object, object2=False, context={}, content=False, type='collection', root=False):
        self.cr = cr
    def _file_get(self, nodename=False):
        if not self.object:
            return []
        pool = pooler.get_pool(self.cr.dbname)
        fobj = pool.get('ir.attachment')
        res2 = []
        where = []
        if self.object2:
            where.append( ('res_model','=',self.object2._name) )
            where.append( ('res_id','=',self.object2.id) )
        else:
            where.append( ('parent_id','=',self.object.id) )
            where.append( ('res_id','=',False) )
        if nodename:
            where.append( (fobj._rec_name,'=',nodename) )
        for content in self.object.content_ids:
	    res3 = content._table._file_get(self,nodename,content)
	    if res3:
		res2.extend(res3)

        ids = fobj.search(self.cr, self.uid, where+[ ('parent_id','=',self.object and self.object.id or False) ])
        if self.object and self.root and (self.object.type=='ressource'):
            ids += fobj.search(self.cr, self.uid, where+[ ('parent_id','=',False) ])
        res = fobj.browse(self.cr, self.uid, ids, context=self.context)
        return map(lambda x: node_class(self.cr, self.uid, self.path+'/'+eval('x.'+fobj._rec_name), x, False, context=self.context, type='file', root=False), res) + res2
    
    def get_translation(self,value,lang):
        # Must go, it works on arbitrary models and could be ambiguous.
        result = value
        pool = pooler.get_pool(self.cr.dbname)        
        translation_ids = pool.get('ir.translation').search(self.cr, self.uid, [('value','=',value),('lang','=',lang),('type','=','model')])
        if len(translation_ids):
            tran_id = translation_ids[0]
            translation = pool.get('ir.translation').read(self.cr, self.uid, tran_id, ['res_id','name'])
            res_model,field_name = tuple(translation['name'].split(','))  
            res_id = translation['res_id']        
            res = pool.get(res_model).read(self.cr, self.uid, res_id, [field_name])
            if res:
                result = res[field_name]
        return result 
    
    def directory_list_for_child(self,nodename,parent=False):
        pool = pooler.get_pool(self.cr.dbname)
        where = []
        if nodename:
            nodename = self.get_translation(nodename, self.context['lang'])
            where.append(('name','=',nodename))
        if (self.object and self.object.type=='directory') or not self.object2:
            where.append(('parent_id','=',self.object and self.object.id or False))
        else:
            where.append(('parent_id','=',False))
        if self.object:
            where.append(('ressource_parent_type_id','=',self.object.ressource_type_id.id))
        else:
            where.append(('ressource_parent_type_id','=',False))

        ids = pool.get('document.directory').search(self.cr, self.uid, where+[('ressource_id','=',0)])
        if self.object2:
            ids += pool.get('document.directory').search(self.cr, self.uid, where+[('ressource_id','=',self.object2.id)])        
        res = pool.get('document.directory').browse(self.cr, self.uid, ids, self.context)
        return res

    def _child_get(self, nodename=False):
        if self.type not in ('collection','database'):
            return []
        res = self.directory_list_for_child(nodename)
        result= map(lambda x: node_class(self.cr, self.uid, self.path+'/'+x.name, x, x.type=='directory' and self.object2 or False, context=self.context, root=self.root), res)
        if self.type=='database':
            pool = pooler.get_pool(self.cr.dbname)
            fobj = pool.get('ir.attachment')
            vargs = [('parent_id','=',False),('res_id','=',False)]
            if nodename:
                vargs.append((fobj._rec_name,'=',nodename))
            file_ids=fobj.search(self.cr,self.uid,vargs)

            res = fobj.browse(self.cr, self.uid, file_ids, context=self.context)
            result +=map(lambda x: node_class(self.cr, self.uid, self.path+'/'+eval('x.'+fobj._rec_name), x, False, context=self.context, type='file', root=self.root), res)
        if self.type=='collection' and self.object.type=="ressource":
            where = self.object.domain and eval(self.object.domain, {'active_id':self.root, 'uid':self.uid}) or []
            pool = pooler.get_pool(self.cr.dbname)
            obj = pool.get(self.object.ressource_type_id.model)
            _dirname_field = obj._rec_name
            if len(obj.fields_get(self.cr, self.uid, ['dirname'])):
                _dirname_field = 'dirname'

            name_for = obj._name.split('.')[-1]
            if nodename  and nodename.find(name_for) == 0  :
                id = int(nodename.replace(name_for,''))
                where.append(('id','=',id))
            elif nodename:
                if nodename.find('__') :
                    nodename=nodename.replace('__','/')
                for invalid in INVALID_CHARS:
                    if nodename.find(INVALID_CHARS[invalid]) :
                        nodename=nodename.replace(INVALID_CHARS[invalid],invalid)
                nodename = self.get_translation(nodename, self.context['lang'])
                where.append((_dirname_field,'=',nodename))

            if self.object.ressource_tree:
                if obj._parent_name in obj.fields_get(self.cr,self.uid):
                    where.append((obj._parent_name,'=',self.object2 and self.object2.id or False))
                    ids = obj.search(self.cr, self.uid, where)
                    res = obj.browse(self.cr, self.uid, ids,self.context)
                    result+= map(lambda x: node_class(self.cr, self.uid, self.path+'/'+x.name.replace('/','__'), self.object, x, context=self.context, root=x.id), res)
                    return result
                else :
                    if self.object2:
                        return result
            else:
                if self.object2:
                    return result

            
            ids = obj.search(self.cr, self.uid, where)
            res = obj.browse(self.cr, self.uid, ids,self.context)
            for r in res:
                if len(obj.fields_get(self.cr, self.uid, [_dirname_field])):
                    r.name = eval('r.'+_dirname_field)
                else:
                    r.name = False
                if not r.name:
                    r.name = name_for + '%d'%r.id
                for invalid in INVALID_CHARS:
                    if r.name.find(invalid) :
                        r.name = r.name.replace(invalid,INVALID_CHARS[invalid])
            result2 = map(lambda x: node_class(self.cr, self.uid, self.path+'/'+x.name.replace('/','__'), self.object, x, context=self.context, root=x.id), res)
            if result2:
                if self.object.ressource_tree:
                    result += result2
                else:
                    result = result2
        return result


    def path_get(self):
        path = self.path
        if self.path[0]=='/':
            path = self.path[1:]
        return path
