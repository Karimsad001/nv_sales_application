from odoo import models, api
from logging import getLogger

_logger = getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = 'stock.quant'

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
    def get_products_by_salesman(self, salesman_id):
    #this function used to return a location that has the id in params..
    #How to use:
    #result = models.execute_kw(db, uid, password, 'stock.quant', 'get_products_by_salesman', [salesman_id])
    #Params: salesman_id: salesman id that we want to retrieve his products in warehouse in each location in the warehouse related.
    #return warehouse with its associated locations as list inside it products in the locations as list. the warehouse is a dictionary.
        try:
            salesman_users = self.env["res.users"].browse(int(salesman_id))
            # salesman_users = self.env["res.users"].search([('id', '=', int(salesman_id))])
            property_warehouse_id = salesman_users.property_warehouse_id.id if salesman_users.property_warehouse_id else None
            property_warehouse_name = salesman_users.property_warehouse_id.name if salesman_users.property_warehouse_id else None
            results = []
            warehouses = {
                # 'id': salesman_users.id,
                # 'name': salesman_users.name,
                'property_warehouse_id': property_warehouse_id,
                'property_warehouse_name': property_warehouse_name,
            }
            results.append(warehouses)
            warehouse_id = tuple(row['property_warehouse_id'] for row in results)
            super_query = """
                SELECT
                    id,
                    name,
                    warehouse_id
                FROM
                    stock_location
                WHERE
                    warehouse_id IN %s AND usage = 'internal' AND active = True
            """
            super_results = self.execute_raw_sql_query_dict(super_query, [warehouse_id])
            location_ids = tuple(row['id'] for row in super_results)
            sub_query = """
                SELECT
                    location_id,
                    product_id,
                    quantity,
                    reserved_quantity as reserved_quantity,
                    quantity-reserved_quantity as available_quantity
                FROM
                    stock_quant
                WHERE
                    location_id IN %s
                """
            sub_results = self.execute_raw_sql_query_dict(sub_query, [location_ids])
            for warehouse in results:
                locations = []
                warehouse["locations"] = locations
                for location in super_results:
                    if(warehouse["property_warehouse_id"] == location["warehouse_id"]):
                        locations.append(location)
                    products = []
                    location["products"] = products
                    for product in sub_results:
                        if(location["id"] == product["location_id"]):
                            products.append(product)
            return results
        except Exception as e:
            _logger.error("An error occurred: %s", e)
            return []