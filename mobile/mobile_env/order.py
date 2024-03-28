import json
import frappe
from frappe import _

from erpnext.accounts.utils import getdate
from mobile.mobile_env.app_utils import (
    gen_response,
    ess_validate,
    get_ess_settings,
    prepare_json_data,
    get_global_defaults,
    exception_handel,
)
from erpnext.accounts.party import get_dashboard_info



@frappe.whitelist()
def get_customer_list():
    try:
        customer_list = frappe.get_list(
            "Customer",
            fields=["name", "customer_name"],
        )
        gen_response(200, "Customer list get successfully", customer_list)
    except Exception as e:
        return exception_handel(e)


"""get item list for mobile app to make order"""

@frappe.whitelist()
def get_warehouselist():
    global_defaults = get_global_defaults()
    company = global_defaults.get("default_company")
    try:
        warehouselist = frappe.get_list(
            "Warehouse",
            # fields=["name", "company"],
            filters={"company": company}
        )
        
        gen_response(200, "warehouse list successfully", warehouselist)
    except Exception as e:
        exception_handel(e)



@frappe.whitelist()
def get_item_list(warehouse=None):
    
    try:
        item_list = frappe.get_list(
            "Item",
            fields=["name", "item_name", "item_code", "image"],
        )
        items = get_items_data(item_list,warehouse)
        gen_response(200, "Item list get successfully", items)
    except Exception as e:
        exception_handel(e)


def get_items_data(items,warehouse):
    items_data = []
    for item in items:
        item_data = {
            "name": item.name,
            "item_name": item.item_name,
            "item_code": item.item_code,
            "image": item.image,
            "actual_qty": float(get_actual_qty(item.item_code,warehouse)),
            "rate": get_item_rate(item.item_code)  # Fetch rate
        }
        items_data.append(item_data)
    return items_data


def get_actual_qty(item_code,warehouse):
    bin_data = frappe.get_all(
        "Bin",
        filters={"item_code": item_code,"warehouse":warehouse},
        fields=["actual_qty", "warehouse"]
    )
    if bin_data:
        return bin_data[0].get("actual_qty", 0)
    else:
        return 0


def get_item_rate(item_code):
    item_price = frappe.get_all(
        "Item Price",
        filters={"item_code": item_code,"price_list":"Standard Selling"},
        fields=["price_list_rate"],
        order_by="creation desc",  # Add this to get the latest price
        limit=1  # Add this to get only the latest price
    )
    if item_price:
        return item_price[0].get("price_list_rate", 0)
    else:
        return 0.0


# Continue with your code as needed

@frappe.whitelist()
def prepare_order_totals(**kwargs):
    try:
        data = kwargs
        if not data.get("customer"):
            return gen_response(500, "Customer is required.")
        # ess_settings = get_ess_settings()
        # default_warehouse = ess_settings.get("default_warehouse")
        delivery_date = data.get("delivery_date")
        for item in data.get("items"):
            item["delivery_date"] = delivery_date
            item["warehouse"] = data.get("set_warehouse")
        global_defaults = get_global_defaults()
        company = global_defaults.get("default_company")
        sales_order_doc = frappe.get_doc(dict(doctype="Sales Order", company=company))
        sales_order_doc.update(data)
        sales_order_doc.run_method("set_missing_values")
        sales_order_doc.run_method("calculate_taxes_and_totals")
        order_data = (
            prepare_json_data(
                [
                    "taxes_and_charges",
                    "total_taxes_and_charges",
                    "net_total",
                    "discount_amount",
                    "grand_total",
                ],
                json.loads(sales_order_doc.as_json()),
            ),
        )
        gen_response(200, "Order details get successfully", order_data)
    except Exception as e:
        return exception_handel(e)


@frappe.whitelist()
def get_order_list():
    try:
        order_list = frappe.get_list(
            "Sales Order",
            fields=[
                "name",
                "customer_name",
                "DATE_FORMAT(transaction_date, '%d-%m-%Y') as transaction_date",
                "grand_total",
                "status",
                "total_qty",
            ],
             order_by='creation desc',
        )
        gen_response(200, "Order list get successfully", order_list)
    except Exception as e:
        return exception_handel(e)




@frappe.whitelist()
def create_order(**kwargs):
    try:
        data = kwargs
        if not data.get("customer"):
            return gen_response(500, "Customer is required.")
        if not data.get("items") or len(data.get("items")) == 0:
            return gen_response(500, "Please select items to proceed.")
        if not data.get("delivery_date"):
            return gen_response(500, "Please select delivery date to proceed.")

        global_defaults = get_global_defaults()
        company = global_defaults.get("default_company")
        # ess_settings = get_ess_settings()
        # default_warehouse = ess_settings.get("default_warehouse")
        
        if data.get("name"):
            if not frappe.db.exists("Sales Order", data.get("name"), cache=True):
                return gen_response(500, "Invalid order id.")
            sales_order_doc = frappe.get_doc("Sales Order", data.get("name"))
            delivery_date = data.get("delivery_date")
            # for item in data.get("items"):
            #     item["delivery_date"] = delivery_date
            #     item["warehouse"] = default_warehouse
            sales_order_doc.update(data)
            sales_order_doc.run_method("set_missing_values")
            sales_order_doc.run_method("calculate_taxes_and_totals")
            sales_order_doc.save()
            gen_response(200, "Order updated successfully.", sales_order_doc)
           
        else:
            sales_order_doc = frappe.get_doc(
                dict(doctype="Sales Order", company=company)
            )
            delivery_date = data.get("delivery_date")
            # for item in data.get("items"):
            #     item["delivery_date"] = delivery_date
            #     item["warehouse"] = default_warehouse
            sales_order_doc.update(data)
            sales_order_doc.run_method("set_missing_values")
            sales_order_doc.run_method("calculate_taxes_and_totals")
            sales_order_doc.insert()

            if data.get("attachments") is not None:
                for file in data.get("attachments"):
                    file_doc = frappe.get_doc(
                        {
                            "doctype": "File",
                            "file_url": file.get("file_url"),
                            "attached_to_doctype": "Sales Order",
                            "attached_to_name": sales_order_doc.name,
                        }
                    )
                    file_doc.insert(ignore_permissions=True)
            gen_response(200, "Order created successfully.", sales_order_doc)

    except Exception as e:
        return exception_handel(e)