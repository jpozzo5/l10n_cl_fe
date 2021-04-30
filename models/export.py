# -*- coding: utf-8 -*-
from collections import OrderedDict
from odoo import models

class LibroXlsx(models.AbstractModel):
    _name = 'report.account.move.book.xlsx'
    _inherit = 'report.report_xlsx.abstract'
    
    def _get_lines_by_date(self, move_ids):
        LibroModel = self.env['account.move.book']
        move_data = OrderedDict()
        default_data = {
            'total': 0.0,
            'folio_start': 0,
            'folio_end': 0,
            'count': 0,
        }
        line_count = 0
        folio_start = 0
        folio_end = 0
        count = 0
        is_set = False
        moves = move_ids.sorted(key=lambda x: "%s_%s" % (x.date, x.sii_document_number or x.ref))
        date_compare = False
        if moves:
            date_compare = moves[0].date
        for mov in moves:
            totales = LibroModel.getResumenBoleta(mov, mov.currency_id)
            tienda_name = ""
            if hasattr(mov, 'branch_id'):
                tienda_name = mov.branch_id.name
            if not is_set:
                is_set = True
                folio_start = mov.sii_document_number
            else:
                if ((folio_end+1) != mov.sii_document_number) or date_compare != mov.date:
                    line_count += 1
                    folio_start = mov.sii_document_number
                    count = 0
                    date_compare = mov.date
            count += 1
            folio_end = mov.sii_document_number
            line_key = (mov.date, mov.document_class_id, tienda_name, line_count)
            move_data.setdefault(line_key, default_data.copy())
            move_data[line_key]['total'] += totales.get('MntTotal') or 0
            move_data[line_key]['folio_start'] = folio_start
            move_data[line_key]['folio_end'] = folio_end
            move_data[line_key]['count'] = count
        return move_data

    def generate_xlsx_report(self, workbook, data, libro):
        for obj in libro:
            FIELDS_SHOW = [
                'dte',
                'document_number',
                'date',
                'rut',
                'partner',
                'afecto',
                'exento',
                'iva',
                'total',
            ]
            COLUM_SIZE = {
                'dte': 6,
                'document_number': 12,
                'date': 12,
                'rut': 14,
                'partner': 30,
                'afecto': 14,
                'exento': 14,
                'iva': 14,
                'total': 14,
            }
            COLUM_HEADER = {
                'dte': 'DTE',
                'document_number': 'Número',
                'date': 'Fecha Emisión',
                'rut': 'RUT',
                'partner': 'Entidad',
                'afecto': 'Afecto',
                'exento': 'Exento',
                'iva': 'IVA',
                'total': 'Total',
            }
            if obj.tipo_operacion == 'BOLETA':
                FIELDS_SHOW = [
                    'date',
                    'dte',
                    'tienda_name',
                    'folio_start',
                    'folio_end',
                    'count',
                    'total',
                ]
                COLUM_SIZE = {
                    'date': 12,
                    'dte': 6,
                    'tienda_name': 30,
                    'folio_start': 14,
                    'folio_end': 14,
                    'count': 14,
                    'total': 14,
                }
                COLUM_HEADER = {
                    'date': 'Fecha',
                    'dte': 'DTE',
                    'tienda_name': 'Tienda',
                    'folio_start': 'Desde',
                    'folio_end': 'Hasta',
                    'count': '# Docs',
                    'total': 'Total',
                }
            # generar una posicion segun el orden que aparecen en la lista
            # para que en caso de querer cambiar la posicion de un campo, solo moverlo en la lista
            # y no tener que estar recalculando posiciones manualmente
            COLUM_POS = dict([(f, i) for i, f in enumerate(FIELDS_SHOW)])
            line = 0
            report_name = obj.name
            # One sheet by partner
            sheet = workbook.add_worksheet(report_name[:31])
            bold = workbook.add_format({'bold': True})
            sheet.merge_range(line, COLUM_POS[FIELDS_SHOW[0]], line, COLUM_POS[FIELDS_SHOW[-1]], obj.company_id.name, bold)
            line += 1
            sheet.write(line, 0, obj.name, bold)
            sheet.write(line, 2, obj.periodo_tributario, bold)
            sheet.write(line, 3, obj.tipo_operacion, bold)
            sheet.write(line, 4, obj.tipo_libro, bold)
            line += 2
            for key, value in COLUM_HEADER.items():
                sheet.write(line, COLUM_POS[key], value, bold)
            line += 1
            if obj.tipo_operacion == 'BOLETA':
                move_data = self._get_lines_by_date(obj.move_ids)
                for line_key in move_data:
                    line_vals = move_data[line_key]
                    move_date = line_key[0]
                    document_class = line_key[1]
                    tienda_name = line_key[2]
                    sheet.write(line, 0, move_date.strftime('%d/%m/%Y') )
                    sheet.write(line, 1, document_class.sii_code)
                    sheet.write(line, 2, tienda_name)
                    sheet.write(line, 3, line_vals['folio_start'])
                    sheet.write(line, 4, line_vals['folio_end'])
                    sheet.write(line, 5, line_vals['count'])
                    sheet.write(line, 6, line_vals['total'])
                    line += 1
            else:
                for mov in obj.move_ids:
                    sheet.write(line, 0, mov.document_class_id.sii_code)
                    sheet.write(line, 1, (mov.sii_document_number or mov.ref))
                    sheet.write(line, 2, mov.date.strftime('%d/%m/%Y') )
                    if mov.partner_id:
                        sheet.write(line, 3, mov.partner_id.document_number if mov.partner_id.document_number not in ['0', 0, ''] else '66666666-6')
                        sheet.write(line, 4, mov.partner_id.name)
                    else:
                        sheet.write(line, 3, "")
                        sheet.write(line, 4, "")
                    totales = mov.totales_por_movimiento()
                    sheet.write(line, 5, totales['neto'])
                    sheet.write(line, 6, totales['exento'])
                    sheet.write(line, 7, totales['iva'])
                    sheet.write(line, 8, mov.amount)
                    line += 1
                sheet.write(line, 0, "Total General", bold)
                sheet.write(line, 5, obj.total_afecto, bold)
                sheet.write(line, 6, obj.total_exento, bold)
                sheet.write(line, 7, obj.total_iva, bold)
                c = 8
                if obj.total_otros_imps > 0:
                    sheet.write(line, c , obj.total_otros_imps, bold)
                    c +=1
                #sheet.write(line, c, obj.total_no_rec, bold)
                sheet.write(line, c, obj.total, bold)
            # resumen por tipo de documento
            if obj.resumen_ids:
                line += 3
                sheet.write(line, 0, "RESUMEN", bold)
                line += 1
                sheet.write(line, 0, u"DTE", bold)
                sheet.write(line, 1, u"Documentos Emitidos", bold)
                sheet.write(line, 2, u"Afecto", bold)
                sheet.write(line, 3, u"Exento", bold)
                sheet.write(line, 4, u"IVA", bold)
                sheet.write(line, 5, u"Otros Imp.", bold)
                sheet.write(line, 6, u"Total", bold)
                line += 1
                for m in obj.resumen_ids:
                    sheet.write(line, 0, m.document_class_id.sii_code)
                    sheet.write(line, 1, m.documents_count)
                    sheet.write(line, 2, m.total_afecto)
                    sheet.write(line, 3, m.total_exento)
                    sheet.write(line, 4, m.total_iva)
                    sheet.write(line, 5, m.total_otros_imps)
                    sheet.write(line, 6, m.total)
                    line += 1
            # ancho de columnas
            for column_name, position in COLUM_POS.items():
                sheet.set_column(position, position, COLUM_SIZE[column_name])
                
