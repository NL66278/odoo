# -*- encoding: utf-8 -*-
##############################################################################
#
# Copyright (c) 2005-2006 TINY SPRL. (http://tiny.be) All Rights Reserved.
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
##############################################################################

import time
import pooler
from report import report_sxw
import datetime
import operator
import osv

class budget_report(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(budget_report, self).__init__(cr, uid, name, context)
        self.localcontext.update( {
            'funct': self.funct,
            'funct_total': self.funct_total,
            'time': time,
        })
        self.context=context

    def funct(self,object,form,ids={}, done=None, level=1):

        if not ids:
            ids = self.ids
#       if not ids:
#           return []
        if not done:
            done={}

        global tot
        tot={
            'theo':0.00,
            'pln':0.00,
            'prac':0.00,
            'perc':0.00
        }
        result=[]

        budgets = self.pool.get('crossovered.budget').browse(self.cr, self.uid, [object.id], self.context.copy())

        c_b_lines_obj=self.pool.get('crossovered.budget.lines')
        for budget_id in budgets:

            res={}
            budget_lines=[]
            budget_ids=[]
            d_from=form['date_from']
            d_to=form['date_to']

            for line in budget_id.crossovered_budget_line:
                budget_ids.append(line.id)

            if not budget_ids:
                return []

            b_line_ids=','.join([str(x) for x in budget_ids])

#            bd_ids = ','.join([str(x) for x in budget_lines])
            self.cr.execute('select distinct(analytic_account_id) from crossovered_budget_lines where id in (%s)'%(b_line_ids))
            an_ids=self.cr.fetchall()

            context={'wizard_date_from':d_from,'wizard_date_to':d_to}
            for i in range(0,len(an_ids)):

                analytic_name=self.pool.get('account.analytic.account').browse(self.cr, self.uid,[an_ids[i][0]])

                res={
                    'b_id':'-1',
                    'a_id':'-1',
                    'name':analytic_name[0].name,
                    'status':1,
                    'theo':0.00,
                    'pln':0.00,
                    'prac':0.00,
                    'perc':0.00
                }
                result.append(res)

                line_ids = c_b_lines_obj.search(self.cr, self.uid, [('id', 'in', budget_ids),('analytic_account_id','=',an_ids[i][0])])

                line_id = c_b_lines_obj.browse(self.cr,self.uid,line_ids)
                tot_theo=tot_pln=tot_prac=tot_perc=0.00

                done_budget=[]
                for line in line_id:

                    if line.id in budget_ids:
                        theo=pract=0.00
                        theo=c_b_lines_obj._theo_amt(self.cr, self.uid, [line.id],context)[line.id]
                        pract=c_b_lines_obj._prac_amt(self.cr, self.uid, [line.id],context)[line.id]

                        if line.general_budget_id.id in done_budget:

                            for record in result:
                                if record['b_id']==line.general_budget_id.id  and record['a_id']==line.analytic_account_id.id:

                                    record['theo'] +=theo
                                    record['pln'] +=line.planned_amount
                                    record['prac'] +=pract
                                    if record['theo']<>0.00:
                                        perc=(record['prac']/record['theo'])*100
                                    else:
                                        perc=0.00
                                    record['perc'] =perc
                                    tot_theo += theo
                                    tot_pln +=line.planned_amount
                                    tot_prac +=pract
                                    tot_perc +=perc

                        else:

                            if theo<>0.00:
                                perc=(pract/theo)*100
                            else:
                                perc=0.00
                            res1={
                                    'a_id':line.analytic_account_id.id,
                                    'b_id':line.general_budget_id.id,
                                    'name':line.general_budget_id.name,
                                    'status':2,
                                    'theo':theo,
                                    'pln':line.planned_amount,
                                    'prac':pract,
                                    'perc':perc,
                            }
                            tot_theo += theo
                            tot_pln +=line.planned_amount
                            tot_prac +=pract
                            tot_perc +=perc
                            if form['report']=='analytic-full':
                                result.append(res1)
                                done_budget.append(line.general_budget_id.id)
                    else:

                        if line.general_budget_id.id in done_budget:
                            continue
                        else:
                            res1={
                                    'a_id':line.analytic_account_id.id,
                                    'b_id':line.general_budget_id.id,
                                    'name':line.general_budget_id.name,
                                    'status':2,
                                    'theo':0.00,
                                    'pln':0.00,
                                    'prac':0.00,
                                    'perc':0.00
                                }

                            if form['report']=='analytic-full':
                                result.append(res1)
                                done_budget.append(line.general_budget_id.id)

                if tot_theo==0.00:
                    tot_perc=0.00
                else:
                    tot_perc=float(tot_prac /tot_theo)*100

                if form['report']=='analytic-full':

                    result[-(len(done_budget) +1)]['theo']=tot_theo
                    tot['theo'] +=tot_theo
                    result[-(len(done_budget) +1)]['pln']=tot_pln
                    tot['pln'] +=tot_pln
                    result[-(len(done_budget) +1)]['prac']=tot_prac
                    tot['prac'] +=tot_prac
                    result[-(len(done_budget) +1)]['perc']=tot_perc
                else:
                    result[-1]['theo']=tot_theo
                    tot['theo'] +=tot_theo
                    result[-1]['pln']=tot_pln
                    tot['pln'] +=tot_pln
                    result[-1]['prac']=tot_prac
                    tot['prac'] +=tot_prac
                    result[-1]['perc']=tot_perc
            if tot['theo']==0.00:
                tot['perc'] =0.00
            else:
                tot['perc']=float(tot['prac'] /tot['theo'])*100
        return result

    def funct_total(self,form):
        result=[]
        res={}

        res={
             'tot_theo':tot['theo'],
             'tot_pln':tot['pln'],
             'tot_prac':tot['prac'],
             'tot_perc':tot['perc']
        }
        result.append(res)

        return result

report_sxw.report_sxw('report.crossovered.budget.report', 'crossovered.budget', 'addons/account_budget/report/crossovered_budget_report.rml',parser=budget_report,header=False)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

