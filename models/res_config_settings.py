# -*- coding: utf-8 -*-
from odoo import api, fields, models
from odoo.exceptions import UserError
try:
    from facturacion_electronica import __version__
except:
    __version__ = '0.0.0'


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    show_atributes_on_reports = fields.Selection([
        ('show_attributes','Mostrar Atributos'),
        ('hide_attributes','No mostrar Atributos'),
        ], string='Atributos en reportes', default='hide_attributes', 
        readonly=False, config_parameter="show_atributes_on_reports")
    show_quantities_grouped = fields.Selection([
        ('show_grouped','Agrupar Productos por plantilla'),
        ('show_detail','Mostrar Productos detallados'),
        ], string='Cantidades en reportes', default='show_detail', readonly=False, config_parameter="show_quantities_grouped")
    show_discount_on_report = fields.Selection([
        ('percentaje','Porcentaje'),
        ('amount','Monto'),
    ], string='Mostrar descuento como', default='percentaje', readonly=False, config_parameter="show_discount_on_report")
    print_total_qty_reports = fields.Boolean('Impimir Cantidad total?', 
        related='company_id.print_total_qty_reports', readonly=False)
    max_number_documents = fields.Integer(u'Numero maximo de lineas', 
        related="company_id.max_number_documents", readonly=False)
    size_calzado_id = fields.Many2one('product.attribute', 'Atributo de Tamaño(Calzado)', 
        related="company_id.size_calzado_id", readonly=False)
    size_vestuario_id = fields.Many2one('product.attribute', 'Atributo de Tamaño(Vestuario)', 
        related="company_id.size_vestuario_id", readonly=False)
    color_id = fields.Many2one('product.attribute', 'Atributo de Color', 
        related="company_id.color_id", readonly=False)
    auto_send_dte = fields.Integer(
            string="Tiempo de Espera para Enviar DTE automático al SII (en horas)",
            default=12,
            config_parameter="account.auto_send_dte",
        )
    auto_send_email = fields.Boolean(
            string="Enviar Email automático al Auto Enviar DTE al SII",
            default=True,
            config_parameter="account.auto_send_email",
        )
    auto_send_persistencia = fields.Integer(
            string="Enviar Email automático al Cliente cada  n horas",
            default=24,
            config_parameter="account.auto_send_persistencia",
        )
    dte_email_id = fields.Many2one(
        'mail.alias',
        related="company_id.dte_email_id"
    )
    limit_dte_lines = fields.Boolean(
        string="Limitar Cantidad de líneas por documento",
        default=False,
        config_parameter="account.limit_dte_lines",
    )
    url_remote_partners = fields.Char(
            string="Url Remote Partners",
            default="https://sre.cl/api/company_info",
            config_parameter="partner.url_remote_partners"
    )
    token_remote_partners = fields.Char(
            string="Token Remote Partners",
            default="token_publico",
            config_parameter="partner.token_remote_partners"
    )
    sync_remote_partners = fields.Boolean(
            string="Sync Remote Partners",
            default=False,
            config_parameter="partner.sync_remote_partners",
    )
    url_apicaf = fields.Char(
            string="URL APICAF",
            default='https://apicaf.cl/api/caf',
            config_parameter="dte.url_apicaf",
    )
    token_apicaf = fields.Char(
            string="Token APICAF",
            default='token_publico',
            config_parameter="dte.token_apicaf",
    )
    cf_autosend = fields.Boolean(
            string="AutoEnviar Consumo de Folios",
            default=False,
            config_parameter="cf_extras.cf_autosend",
        )
    fe_version = fields.Char(
        string="Versión FE instalado",
        readonly=True,
    )

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res.update(
                fe_version=__version__,
            )
        return res

    @api.multi
    def set_values(self):
        super(ResConfigSettings, self).set_values()
        if self.dte_email_id and not self.external_email_server_default:
            raise UserError('Debe Cofigurar Servidor de Correo Externo en la pestaña Opciones Generales')
