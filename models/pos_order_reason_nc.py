from odoo import models, api, fields
import odoo.addons.decimal_precision as dp
from odoo.tools.translate import _

class PosOrderReasonNC(models.Model):

    _name = 'pos.order.reason.nc'
    _description = 'Motivos de Nota de Credito'
    
    name = fields.Char(string='Nombre', required=True)
    active = fields.Boolean('Activo?', default=True)