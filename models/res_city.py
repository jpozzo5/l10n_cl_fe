# -*- encoding: utf-8 -*-
from odoo import fields, models, api
from odoo.tools.translate import _


class ResCity(models.Model):
    _inherit = 'res.city'

    code = fields.Char(
            string='City Code',
            help='The city code.\n',
            required=True,
        )
    localidad_ids = fields.One2many('res.city.sector', 'city_id', u'Localidades')


class ResCitySector(models.Model):
    _name = 'res.city.sector'
    _description = 'Localidades de Comunas' 
    
    name = fields.Char(u'Nombre', required=True)
    code = fields.Char(u'Codigo')
    city_id = fields.Many2one('res.city', u'Comuna', required=True, index=True)
