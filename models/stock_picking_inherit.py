from odoo import models, api
from logging import getLogger

_logger = getLogger(__name__)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

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
    def get_delivery(self, sale):
        #this function used to return list of delivery adresses ..
        #How to use:
        #result = models.execute_kw(db, uid, password, 'stock.picking', 'get_delivery', [])
        #Params: sale: sale order id that we want to retrieve his stock picking informations.
        #return stock picking with it associated product line. the stock picking is a dictionary.
        super_query = """
            SELECT
                id,
                name,
                partner_id,
                picking_type_id,
                scheduled_date,
                date_done,
                origin
            FROM
                stock_picking
            WHERE
                sale_id = %s
        """
        super_results = self.execute_raw_sql_query_dict(super_query, [sale])
        sub_query = """
            SELECT
                id,
                product_id,
                product_uom_qty,
                quantity,
                picking_id
            FROM
                stock_move
        """
        sub_results = self.execute_raw_sql_query_dict(sub_query)
        
        for order in super_results:
            product_line = []
            order["product_line"] = product_line
            for line in sub_results:
                if (line["picking_id"] == order["id"]):
                    product_line.append(line)
        return super_results