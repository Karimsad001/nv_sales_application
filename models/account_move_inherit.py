from odoo import models, api
from logging import getLogger

_logger = getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'account.move'

    @api.model
    def execute_raw_sql_query_dict(self, query, params=None):
        # Executes a raw SQL query and returns the results as a list of dictionaries.
        # :param query: SQL query string to be executed
        # :param params: Parameters to be used in the SQL query (optional)
        # :return: List of dictionaries containing the query result
        try:
            self.env.cr.execute(query, params or [])
            rows = self.env.cr.dictfetchall()
            rows = [
                {k: (v if v is not None else '') for k, v in row.items()}
                for row in rows
            ]
            return rows
        except Exception as e:
            _logger.error("An error occurred: %s", e)
            return []
        
    @api.model
    def get_invoice(self, sale_id):
        # #this function used to return an invoice ..
        # #How to use:
        # #result = models.execute_kw(db, uid, password, 'account.move', 'get_invoice', [sale_id])
        # Params: sale_id this is the sale order id that we want to retrieve the invoice infos related in it after  
        # #return an invoice with it associated invoices lines. the invoice is a dict dictionary.
        query ="""
            SELECT
                solir.order_line_id,
                solir.invoice_line_id
            FROM
                sale_order_line as sol
            JOIN
                sale_order_line_invoice_rel as solir
            ON
                sol.id = solir.order_line_id
            WHERE
                sol.order_id = %s
        """
        res = self.execute_raw_sql_query_dict(query, [sale_id])
        invoice_line_ids = []
        for rec in res:
            invoice_line_ids.append(rec["invoice_line_id"])
        inv_tuple = tuple(invoice_line_ids)
        sub_query = """
            SELECT
                am.id,
                am.move_id,
                am.product_id,
                am.name,
                am.account_id,
                am.deferred_start_date,
                am.deferred_end_date,
                am.quantity,
                am.price_unit,
                STRING_AGG(at.account_tax_id::TEXT, ',') as account_tax_id,
                am.price_subtotal
            FROM
                account_move_line as am
            JOIN
                account_move_line_account_tax_rel as at
            ON
                id = at.account_move_line_id
            WHERE
                am.id IN %s
            GROUP BY
                am.id
            """
            # JOIN
                # sale_order_line_invoice_rel as sal
            # ON
                # am.id = sal.invoice_line_id
        sub_results = self.execute_raw_sql_query_dict(sub_query, [inv_tuple])
        move_id = tuple([record['move_id'] for record in sub_results])
        super_query = """
            SELECT
                am.id,
                am.name,
                am.partner_id,
                am.invoice_date,
                am.payment_reference,
                am.invoice_date_due,
                am.invoice_payment_term_id,
                am.journal_id,
                am.currency_id,
                cu.name as currency_name,
                am.amount_untaxed,
                am.amount_tax,
                am.amount_total,
                am.amount_residual
            FROM
                account_move as am
            JOIN
                res_currency as cu
            ON
                am.currency_id = cu.id
            WHERE
                am.id IN %s"""
        super_results = self.execute_raw_sql_query_dict(super_query, [move_id])
        for order in super_results:
            invoice_line = []
            order["invoice_line"] = invoice_line
            for line in sub_results:
                if (line["move_id"] == order["id"]):
                    line["account_tax_id"] = line["account_tax_id"].split(',')
                    invoice_line.append(line)
        return super_results