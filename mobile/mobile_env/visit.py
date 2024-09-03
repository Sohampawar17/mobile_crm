import frappe
from datetime import datetime
from frappe import _
import json
from erpnext.accounts.utils import getdate
from mobile.mobile_env.app_utils import (
    gen_response,
    ess_validate,
    prepare_json_data,
    get_employee_by_user,
    exception_handel,
)
from frappe.utils import (
    cstr,
    get_date_str,
    today,
    nowdate,
    getdate,
    now_datetime,
    get_first_day,
    get_last_day,
    date_diff,
    flt,
    pretty_date,
    fmt_money,
)


@frappe.whitelist()
def create_visit(**kwargs):
    try:
        emp_data = get_employee_by_user(frappe.session.user)
        data = kwargs
        if data.get("name"):
            if not frappe.db.exists("Visit", data.get("name")):
                return gen_response(500, "Invalid Visit id.")
            visit_doc = frappe.get_doc("Visit", data.get("name"))
            
            visit_doc.customer = data.get("customer")    
            visit_doc.visit_type = data.get("visit_type")
            visit_doc.description = data.get("description")
            visit_doc.location = data.get("location")
            visit_doc.latitude=data.get('latitude')
            visit_doc.longitude=data.get('longitude')
            visit_doc.employee = emp_data.get("name")
            visit_doc.save(ignore_permissions=True)
            return gen_response(200, "Visit updated Successfully")
        else:
            visit_doc = frappe.new_doc("Visit")
            frappe.msgprint(str(data.get("visit_type")))
            frappe.msgprint(str(data.get("description")))
            visit_doc.customer = data.get("customer")
            visit_doc.visit_type = data.get("visit_type")
            visit_doc.description = data.get("description")
            visit_doc.latitude=data.get('latitude')
            visit_doc.longitude=data.get('longitude')
            visit_doc.location = data.get("location")
            visit_doc.employee = emp_data.get("name")
            visit_doc.insert()
            return gen_response(200, "Visit created Successfully")
    except Exception as e:
        return exception_handel(e)


@frappe.whitelist()
def get_visit_list():
    try:
        visit_list = frappe.get_list(
            "Visit",
            fields=[
                "name",
                "customer_name",
                "DATE_FORMAT(date, '%d-%m-%Y') as date",
                "time_format(time, '%h:%i:%s') as time",
                "visit_type",
            ],
        )
        return gen_response(200, "Visit list get successfully", visit_list)
    except Exception as e:
        return exception_handel(e)


import json
import frappe
from frappe.utils import getdate, pretty_date
from datetime import datetime

@frappe.whitelist()
def get_visit(Id):
    try:
        visit_doc = json.loads(frappe.get_doc("Visit", Id).as_json())
        frappe.msgprint(str(visit_doc))
        
        # Convert and format the date
        date = getdate(visit_doc["date"])
        visit_doc["date"] = date.strftime("%d-%m-%Y")
        
        # Convert and format the time, handling microseconds
        visit_doc["time"] = datetime.strptime(visit_doc["time"].split('.')[0], "%H:%M:%S").strftime("%I:%M:%S %p")
        
        # Prepare the JSON data
        visit_data = prepare_json_data(
            [
                "name",
                "customer",
                "customer_name",
                "date",
                "time",
                "visit_type",
                "description",
                "location",
                "employee",
                "user",
            ],
            visit_doc,
        )
        
        # Get visit comments
        visit_data["comments"]=get_visit_comments(visit=visit_doc)
        
        return gen_response(200, "Visit detail get successfully", visit_data)
    except Exception as e:
        return exception_handel(e)

def get_visit_comments(visit):
    comments = frappe.get_all(
        "Comment",
        filters={
            "reference_name": ["like", "%{0}%".format(visit.get("name"))],
            "comment_type": "Comment",
        },
        fields=[
            "content as comment",
            "comment_by",
            "reference_name",
            "creation",
            "comment_email",
        ],
    )
    
    for comment in comments:
        comment["commented"] = pretty_date(comment["creation"])
        # comment["creation"] = datetime.strptime(comment["creation"], "%Y-%m-%d %H:%M:%S.%f").strftime("%I:%M %p")
        
        user_image = frappe.get_value(
            "User", comment["comment_email"], "user_image", cache=True
        )
        comment["user_image"] = user_image

    return comments

  